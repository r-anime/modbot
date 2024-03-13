"""
Monitors a subreddit, saves every new submission, and relays them to a Discord channel via webhook.
"""

import time

from praw.models.reddit.submission import Submission

import config_loader
from constants import post_constants
from services import post_service, base_data_service
from utils import discord, reddit as reddit_utils
from utils.logger import logger


def process_post(submission: Submission):
    """
    Process a single PRAW Submission. Adds it to the database if it didn't previously exist, updates post if necessary.
    """

    # If we've already saved the post and sent it to Discord, no need to do anything (likely upon restart).
    post = post_service.get_post_by_id(submission.id)
    if post and post.sent_to_feed:
        logger.debug(f"Already processed, skipping post {submission.id}")
        return

    author_name = submission.author.name if submission.author is not None else "[deleted]"
    logger.info(f"Processing post {submission.id} - /u/{author_name} - {submission.link_flair_text}")

    if post:
        post = post_service.update_post(post, submission)
    else:
        post = post_service.add_post(submission)

    discord_embed = post_service.format_post_embed(post)
    # Add extra info if it was removed by the spam filter.
    if getattr(submission, "banned_by", False) is True:
        field = {"inline": True, "value": "spam filter", "name": "Removed By reddit"}
        discord_embed["fields"].append(field)
    discord_message_id = discord.send_webhook_message(
        config_loader.DISCORD["post_webhook_url"], {"embeds": [discord_embed]}, return_message_id=True
    )
    if discord_message_id:
        post.sent_to_feed = True
        post.discord_message_id = discord_message_id

    base_data_service.update(post)

    # If this is a new daily thread, do all the updating for it.
    if (
        author_name == post_constants.DAILY_THREAD_AUTHOR
        and post_constants.DAILY_THREAD_NAME.lower() in post.title.lower()
    ):
        try:
            post_service.rotate_daily_thread(post)
        except Exception:
            logger.exception("Unable to process new daily thread")

    logger.debug(f"Finished processing {post.id36}")


def monitor_stream():
    """
    Monitor the subreddit for new posts and parse them when they come in. Will restart upon encountering an error.
    """

    while True:
        try:
            logger.info("Connecting to Reddit...")
            reddit = reddit_utils.get_reddit_instance(config_loader.REDDIT["auth"])
            subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])
            logger.info("Loading flairs...")
            post_service.load_post_flairs(subreddit)
            logger.info("Starting submission stream...")
            for submission in subreddit.stream.submissions(skip_existing=False):
                process_post(submission)
        except Exception:
            delay_time = 30
            logger.exception(f"Encountered an unexpected error, restarting in {delay_time} seconds...")
            time.sleep(delay_time)


if __name__ == "__main__":
    monitor_stream()
