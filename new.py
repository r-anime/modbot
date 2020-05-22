"""
Monitors a subreddit and relays every new submission to a Discord channel via webhook.
Doesn't save any information locally, will only retrieve posts created after the script starts running.
"""

from datetime import datetime, timezone
import time

import praw

import config
from utils import discord
from utils.logger import logger


def send_new_submission_message(submission):
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

    discord.send_webhook_message({"embeds": [embed_json]}, channel_webhook_url=config.DISCORD["webhook_feed"])


def listen(subreddit):
    logger.info("Starting submission stream...")
    for submission in subreddit.stream.submissions(skip_existing=True):
        send_new_submission_message(submission)


if __name__ == "__main__":
    while True:
        try:
            logger.info("Connecting to Reddit...")
            reddit = praw.Reddit(**config.REDDIT["auth"])
            subreddit = reddit.subreddit(config.REDDIT["subreddit"])
            listen(subreddit)
        except Exception:
            delay_time = 30
            logger.exception(f"Encountered an unexpected error, restarting in {delay_time} seconds...")
            time.sleep(delay_time)
