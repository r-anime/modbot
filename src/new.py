"""
Monitors a subreddit and relays every new submission to a Discord channel via webhook.
Doesn't save any information locally, will only retrieve posts created after the script starts running.
"""

from datetime import datetime, timezone
import time

import config
from constants import Flair
from data.db import session_scope
from data.models import PostModel, UserModel
from processor import post_processor
from utils import reddit as reddit_utils
from utils import discord
from utils.logger import logger


def send_new_submission_message(submission):
    """
    Sends an embed to the specified Discord webhook with details of the Reddit submission.
    """

    # Escape any formatting characters in the title since it'll apply them in the embed.
    title = discord.escape_formatting(submission.title)

    flair = Flair.Unflaired
    if submission.link_flair_text is not None:
        flair = Flair.get_flair_by_id(submission.link_flair_template_id)

    embed_json = {
        "title": title[:253] + '...' if len(title) > 256 else title,
        "url": f"https://redd.it/{submission.id}",
        "author": {
            "name": f"/u/{submission.author.name}"
        },
        "timestamp": datetime.fromtimestamp(submission.created_utc, timezone.utc).isoformat(),
        "footer": {
            "text": f"{submission.id} | {submission.link_flair_text}"
        },
        "fields": [
        ],
        "color": flair.color
    }

    # Link posts include a direct link to the thing submitted as well.
    if not submission.is_self:
        embed_json["description"] = submission.url

    # If they're posting social media/Youtube channel links grab extra info for searching later.
    if submission.media is not None and submission.media.get("oembed"):
        if submission.media["oembed"].get("author_url"):
            media_info = {
                "name": "Media Channel",
                "value": submission.media["oembed"]["author_url"]
            }
            embed_json["fields"].append(media_info)

    logger.debug(embed_json)

    discord.send_webhook_message({"embeds": [embed_json]}, channel_webhook_url=config.DISCORD["webhook_feed"])


def save_to_db(submission):
    """
    Saves information about the post and its author to the database.
    :param submission: praw SubmissionModel object
    :return: True if a new submission not previously recorded in database, False otherwise (None if post was deleted)
    """

    # If a post was deleted immediately don't bother recording anything, just return.
    if submission.author is None:
        logger.debug(f'deleted post/user for {submission.id} - {submission.title}')
        return None

    is_new_submission = False

    with session_scope() as session:

        # Ensure post creator exists in the database first.
        username_lower = submission.author.name.lower()
        user_model = session.query(UserModel).filter_by(name=username_lower).one_or_none()
        if not user_model:
            user_model = UserModel(
                name=username_lower,
                name_formatted=submission.author.name
            )
            session.add(user_model)

        # Check to see if the post was already added to the database.
        post_model = session.query(PostModel).filter_by(id=submission.id).one_or_none()
        if not post_model:
            is_new_submission = True
            post_model = PostModel(
                id=submission.id,
                title=submission.title,
                author_psk=user_model.psk,
                created_time=datetime.fromtimestamp(submission.created_utc, tz=timezone.utc))
            session.add(post_model)
        post_model.flair_text = submission.link_flair_text  # flair may have changed, so update it
        # If no flair has been selected, link_flair_template_id won't exist as an attribute.
        if submission.link_flair_text is not None:
            post_model.flair_id = submission.link_flair_template_id

    return is_new_submission


def listen(subreddit):
    logger.info("Starting submission stream...")
    for submission in subreddit.stream.submissions(skip_existing=False):
        is_new = save_to_db(submission)
        # When the stream starts, it will grab the past 100 first and we don't want those to repeat if they were
        # already sent to Discord.
        if is_new:
            send_new_submission_message(submission)
            post_processor.new_post_job.apply_async((submission.id,), countdown=30)


if __name__ == "__main__":
    while True:
        try:
            logger.info("Connecting to Reddit...")
            reddit = reddit_utils.get_instance(reinitialize=True)
            subreddit = reddit.subreddit(config.REDDIT["subreddit"])
            listen(subreddit)
        except Exception:
            delay_time = 30
            logger.exception(f"Encountered an unexpected error, restarting in {delay_time} seconds...")
            time.sleep(delay_time)
