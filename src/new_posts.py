"""
Monitors a subreddit and relays every new submission to a Discord channel via webhook.
"""

from datetime import datetime, timezone
import time

import praw
from praw.models.reddit.submission import Submission

import config
from services import post_service, base_data_service
from utils import discord
from utils.logger import logger


# Current reddit session and subreddit, initialized when first starting up or after an error.
reddit = None
subreddit = None


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

    send_new_submission_message(submission)
    post.sent_to_feed = True

    base_data_service.update(post)

    logger.debug(f"Finished processing {submission.id}")


def send_new_submission_message(submission: Submission):
    """
    Sends an embed to the specified Discord webhook with details of the Reddit submission.
    """

    # Escape any formatting characters in the title since it'll apply them in the embed.
    title = discord.escape_formatting(submission.title)

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
        "color": config.FLAIR_COLOR.get(submission.link_flair_text, 0)
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

    discord.send_webhook_message(config.DISCORD["webhook_new_posts"], {"embeds": [embed_json]})


def monitor_stream():
    """
    Monitor the subreddit for new posts and parse them when they come in. Will restart upon encountering an error.
    """

    global reddit, subreddit
    while True:
        try:
            logger.info("Connecting to Reddit...")
            reddit = praw.Reddit(**config.REDDIT["auth"])
            subreddit = reddit.subreddit(config.REDDIT["subreddit"])
            logger.info("Starting submission stream...")
            for submission in subreddit.stream.submissions(skip_existing=False):
                process_post(submission)
        except Exception:
            delay_time = 30
            logger.exception(f"Encountered an unexpected error, restarting in {delay_time} seconds...")
            time.sleep(delay_time)


if __name__ == "__main__":
    monitor_stream()
