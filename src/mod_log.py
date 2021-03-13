"""
Monitors a subreddit and saves all mod actions to the database.
Will send a notification to Discord if the action was taken by someone not previously registered as a mod.
"""

from datetime import datetime, timedelta, timezone
import time

import praw
from praw.models.mod_action import ModAction
from praw.models.subreddits import Subreddit

import config
from data.mod_action_data import ModActionModel
from services import base_data_service, comment_service, mod_action_service, post_service, user_service
from utils import discord, reddit as reddit_utils
from utils.logger import logger


# Cache a list of moderator usernames so we can tell if an action is taken by admins.
active_mods = []

# Current reddit session, initialized when first starting up or after an error.
reddit = None
subreddit = None


def parse_mod_action(mod_action: ModAction):

    # Check if we've already processed this mod action, do nothing if so.
    mod_action_id = mod_action.id.replace("ModAction_", "")
    if mod_action_service.get_mod_action_by_id(mod_action_id):
        logger.debug(f"Already processed, skipping mod action {mod_action_id}")
        return

    logger.info(
        f"Processing mod action {mod_action_id}: {mod_action.mod.name} - "
        f"{mod_action.action} - {mod_action.target_fullname}"
    )

    # If there's an action by an unknown moderator or admin, make a note of it and check to see
    # if they should be added to the mod list.
    send_notification = False
    if mod_action.mod.name not in active_mods:
        # Add them to the database if necessary.
        mod_user = user_service.get_user(mod_action.mod.name)
        if not mod_user:
            mod_user = user_service.add_user(mod_action.mod)

        # We'd normally send a notification for all actions from non-mods, but temporary mutes expiring
        # always come from reddit and we don't really care about those.
        if not (mod_action.mod.name == "reddit" and mod_action.action == "unmuteuser"):
            send_notification = True

        # For non-admin cases, check to see if they're a [new] mod of the subreddit and refresh the list if so.
        if mod_action.mod not in ("Anti-Evil Operations", "reddit"):
            logger.info(f"Unknown mod found: {mod_action.mod.name}")
            if mod_user.username in subreddit.moderator():
                logger.debug(f"Updating mod status for {mod_user}")
                mod_user.moderator = True
                base_data_service.update(mod_user)
                _get_moderators()

    # See if the user targeted by this action exists in the system, add them if not.
    # Bans and similar user-focused actions independent of posts/comments will also have
    # a target_fullname value (t2_...) but won't be necessary to check after this.
    if mod_action.target_author:
        user = user_service.get_user(mod_action.target_author)
        if not user:
            logger.debug(f"Saving user {mod_action.target_author}")
            user = user_service.add_user(reddit.redditor(name=mod_action.target_author))

        # For bans and unbans, update the user in the database.
        if mod_action.action == "banuser":
            # Weirdly this returns a ListingGenerator so we have to iterate over it; there should only be one though.
            # If the user isn't banned, the loop won't execute.
            for ban_user in subreddit.banned(redditor=user.username):
                # Permanent if days_left is None
                if ban_user.days_left is None:
                    user.banned_until = "infinity"
                # days_left will show 0 if they were banned for 1 day a few seconds ago; it seems like it rounds down
                # based on the time of the ban occurring, so we can safely assume that even if the ban happened
                # a few seconds before getting to this point, we should add an extra day onto the reported number.
                else:
                    ban_start = datetime.fromtimestamp(mod_action.created_utc, tz=timezone.utc)
                    user.banned_until = ban_start + timedelta(days=ban_user.days_left + 1)
                break
            base_data_service.update(user)
        elif mod_action.action == "unbanuser":
            user.banned_until = None
            base_data_service.update(user)

    # See if the post targeted by this action exists in the system, add it if not.
    if mod_action.target_fullname and mod_action.target_fullname.startswith("t3_"):
        post_id = mod_action.target_fullname.split("_")[1]
        post = post_service.get_post_by_id(post_id)
        reddit_post = reddit.submission(id=post_id)

        # Add or update post as necessary.
        if not post:
            logger.debug(f"Saving post {post_id}")
            post = post_service.add_post(reddit_post)
        else:
            post = post_service.update_post(post, reddit_post)

        # If the user deleted their text post, the mod action still has the post body that we can save in place.
        if post.deleted and post.body == "[deleted]" and post.body != mod_action.target_body:
            post.body = mod_action.target_body
            base_data_service.update(post)

    # See if the comment targeted by this action *and its post* exist in the system, add either if not.
    if mod_action.target_fullname and mod_action.target_fullname.startswith("t1_"):
        comment_id = mod_action.target_fullname.split("_")[1]
        comment = comment_service.get_comment_by_id(comment_id)
        reddit_comment = reddit.comment(id=comment_id)

        if not comment:
            # Post needs to exist before we can add a comment for it, start with that.
            post = post_service.get_post_by_id(reddit_comment.submission.id)

            if not post:
                post_service.add_post(reddit_comment.submission)

            # Since all comments will reference a parent if it exists, add all parent comments first.
            logger.debug(f"Saving parent comments of {comment_id}")
            comment_service.add_comment_parent_tree(reddit, reddit_comment)
            logger.debug(f"Saving comment {comment_id}")
            comment = comment_service.add_comment(reddit_comment)
        else:
            # Update our record of the comment if necessary.
            comment = comment_service.update_comment(comment, reddit_comment)

        # If the user deleted their comment, the mod action still has the body that we can save in place.
        if comment.deleted and comment.body != mod_action.target_body:
            comment.body = mod_action.target_body
            base_data_service.update(comment)

    logger.debug(f"Saving mod action {mod_action_id}")
    mod_action = mod_action_service.add_mod_action(mod_action)

    if send_notification:
        send_discord_message(mod_action)


def send_discord_message(mod_action: ModActionModel):
    logger.info(f"Attempting to send a message to Discord for {mod_action}")

    embed_json = {
        "author": {
            "name": f"Mod Log - /u/{mod_action.mod}",
        },
        "title": mod_action.action,
        "timestamp": mod_action.created_time.isoformat(),
        "fields": [],
        "color": 0xCC0000,
    }

    # Add a URL if there's a specific thing we can focus on, also update title if possible.
    target = None
    if mod_action.target_comment_id:
        target = comment_service.get_comment_by_id(mod_action.target_comment_id)
        embed_json["title"] = f"{mod_action.action} by {mod_action.target_user}"
    elif mod_action.target_post_id:
        target = post_service.get_post_by_id(mod_action.target_post_id)
        title = discord.escape_formatting(f"{mod_action.action} - {target.title}")
        embed_json["title"] = title[:253] + "..." if len(title) > 256 else title
    elif mod_action.target_user:
        target = user_service.get_user(mod_action.target_user)
        embed_json["title"] = f"{mod_action.action} - {mod_action.target_user}"
    if target:
        embed_json["url"] = reddit_utils.make_permalink(target)

    if mod_action.details:
        embed_json["description"] = mod_action.details

    if mod_action.description:
        desc_info = {"name": "Description", "value": mod_action.description}
        embed_json["fields"].append(desc_info)

    discord.send_webhook_message({"embeds": [embed_json]}, channel_webhook_url=config.DISCORD["webhook_notifications"])


def listen(subreddit: Subreddit):
    logger.info("Starting mod-log stream...")
    for mod_action in subreddit.mod.stream.log():
        parse_mod_action(mod_action)


def _get_moderators():
    """Initializes the list of currently active moderators."""

    # Clear out the previous list in case something changed.
    global active_mods
    active_mods = []

    mod_list = user_service.get_moderators()
    for mod in mod_list:
        active_mods.append(mod.username)


if __name__ == "__main__":
    while True:
        try:
            logger.info("Connecting to Reddit...")
            reddit = praw.Reddit(**config.REDDIT["auth"])
            subreddit = reddit.subreddit(config.REDDIT["subreddit"])
            _get_moderators()
            listen(subreddit)
        except Exception:
            delay_time = 30
            logger.exception(f"Encountered an unexpected error, restarting in {delay_time} seconds...")
            time.sleep(delay_time)
