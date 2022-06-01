from datetime import datetime, timezone
from typing import Union, Optional

from praw.models.reddit.submission import Submission

from data.post_data import PostData, PostModel
from services import user_service
from utils import reddit, discord
from utils.logger import logger

_post_data = PostData()
_flair_colors = {}


def get_post_by_id(post_id: Union[str, int]) -> Optional[PostModel]:
    """
    Gets a single post from the database. post_id is either base 10 (int) or base 36 (str)
    """

    if isinstance(post_id, str):
        post_id = reddit.base36decode(post_id)

    return _post_data.get_post_by_id(post_id)


def get_posts_by_username(username: str, start_date: str = None, end_date: str = None) -> list[PostModel]:
    """
    Gets all posts by a user, optionally within a specified time frame.
    """

    return _post_data.get_posts_by_username(username, start_date, end_date)


def add_post(reddit_post: Submission) -> PostModel:
    """
    Parses some basic information for a post and adds it to the database.
    Creates post author if necessary.
    """

    post = _create_post_model(reddit_post)

    # And insert the author into the database if they don't exist yet.
    if reddit_post.author is not None and not user_service.get_user(reddit_post.author.name):
        user_service.add_user(reddit_post.author)

    new_post = _post_data.insert(post, error_on_conflict=False)
    return new_post


def update_post(existing_post: PostModel, reddit_post: Submission) -> PostModel:
    """
    For the provided post, update fields to the current state and save to the database if necessary.
    """

    new_post = _create_post_model(reddit_post)

    non_update_fields = ["author", "title", "url"]

    # If a user has deleted their post or admins took it down we don't want to overwrite the original text.
    # Removals by "anti_evil_ops" or "moderator" are fine since those don't change the body.
    if reddit_post.removed_by_category in ("deleted", "content_takedown") or reddit_post.removal_reason in ("legal",):
        non_update_fields.append("body")

    for field in new_post.columns:
        if field in non_update_fields:
            continue
        if hasattr(new_post, field):
            setattr(existing_post, field, getattr(new_post, field))

    updated_post = _post_data.update(existing_post)
    return updated_post


def format_post_embed(post: PostModel):
    """
    Formats the post as a Discord embed for sending to a webhook.
    """

    # Escape any formatting characters in the title since it'll apply them in the embed.
    title = discord.escape_formatting(post.title)

    embed_json = {
        "title": title[:253] + "..." if len(title) > 256 else title,
        "url": f"https://redd.it/{post.id36}",
        "author": {"name": f"/u/{post.author}"},
        "timestamp": post.created_time.isoformat(),
        "footer": {"text": f"{post.id36} | {post.flair_text}"},
        "fields": [],
        "color": _flair_colors.get(str(post.flair_id), 0),
    }

    # Link posts include a direct link to the thing submitted as well.
    if post.url:
        embed_json["description"] = post.url

    # If they're posting social media/Youtube channel links grab extra info for searching later.
    if post.metadata and post.metadata.get("media"):
        media_metadata = post.metadata.get("media")

        if channel_name := media_metadata.get("channel"):
            media_info = {"name": "Media Channel", "value": channel_name}
            embed_json["fields"].append(media_info)

        if resolution := media_metadata.get("resolution"):
            media_info = {
                "name": "Resolution",
                "value": f'{resolution["width"]}x{resolution["height"]}',
                "inline": True,
            }
            embed_json["fields"].append(media_info)

        if duration := media_metadata.get("duration"):
            minutes, seconds = duration // 60, duration % 60
            media_info = {"name": "Duration", "value": f"{minutes}:{seconds:02}", "inline": True}
            embed_json["fields"].append(media_info)

    return embed_json


def load_post_flairs(subreddit):
    """
    Loads flair colors from the subreddit, used to color Discord embeds.
    """

    global _flair_colors
    _flair_colors = {}
    flair_list = subreddit.flair.link_templates
    for flair in flair_list:
        color_hex = flair["background_color"].replace("#", "")
        _flair_colors[flair["id"]] = int(color_hex, base=16)
    logger.info(f"Flairs loaded: {_flair_colors}")


def _create_post_model(reddit_post: Submission) -> PostModel:
    """
    Populate a new PostModel based on the Reddit thread.
    """

    post = PostModel()

    post.set_id(reddit_post.id)
    post.title = reddit_post.title
    post.score = reddit_post.score
    post.created_time = datetime.fromtimestamp(reddit_post.created_utc, tz=timezone.utc)

    # If link_flair_text is None, link_flair_template_id won't even exist. Still using getattr for safety.
    if reddit_post.link_flair_text:
        post.flair_id = getattr(reddit_post, "link_flair_template_id", None)
        post.flair_text = reddit_post.link_flair_text

    # To differentiate between text and link posts, only one of the two fields should be filled and the other null.
    if reddit_post.is_self:
        post.body = reddit_post.selftext
    else:
        post.url = reddit_post.url

    # If they're posting social media/Youtube channel links grab extra info for searching later.
    metadata = {}
    if reddit_post.media is not None and reddit_post.media.get("oembed"):
        if reddit_post.media["oembed"].get("author_url"):
            if "media" not in metadata:
                metadata["media"] = {}
            metadata["media"]["channel"] = reddit_post.media["oembed"]["author_url"]

    # Videos uploaded to reddit include resolution and duration.
    if reddit_post.media is not None and reddit_post.media.get("reddit_video"):
        reddit_video = reddit_post.media["reddit_video"]
        if "height" in reddit_video and "width" in reddit_video:
            if "media" not in metadata:
                metadata["media"] = {}
            metadata["media"]["resolution"] = {"width": reddit_video["width"], "height": reddit_video["height"]}
        if "duration" in reddit_video:
            if "media" not in metadata:
                metadata["media"] = {}
            metadata["media"]["duration"] = reddit_video["duration"]

    post.metadata = metadata

    # Posts by deleted users won't have an author.
    if reddit_post.author is not None:
        post.author = reddit_post.author.name

    # edited is either a timestamp or False if it hasn't been edited.
    if reddit_post.edited:
        post.edited = datetime.fromtimestamp(reddit_post.edited, tz=timezone.utc)

    # distinguished is a string (usually "moderator", maybe "admin"?) or None.
    post.distinguished = True if reddit_post.distinguished else False

    # removed_by_category is "deleted" if the post has been deleted
    # or "moderator" if it's been removed by a mod but not deleted.
    if reddit_post.removed_by_category == "deleted":
        post.deleted = True

    # removed is *not* accurate if the post has been deleted, so banned_by is used instead.
    # banned_by will have a mod name if the post was removed even if it's also been deleted.
    post.removed = True if reddit_post.banned_by else False

    return post
