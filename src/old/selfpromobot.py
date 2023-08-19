#!/usr/bin/env python3

import time
from datetime import datetime, timezone, timedelta

import config_loader
from utils import reddit as reddit_utils
from utils.logger import logger

global DEBUG

REMOVAL_MESSAGE_TEMPLATE = """Sorry, your submission has been removed.\n\n{message}\n\n
*I am a bot, and this action was performed automatically. Please
[contact the moderators of this subreddit](https://www.reddit.com/message/compose/?to=/r/anime)
if you have any questions or concerns.*"""

# Number of posts to check on each run
posts_per_run = 25
# Maximum number of items to check in a user's history
history = 500
# Interval between multiple checks
interval = 60


def main(subreddit):
    """
    Main loop.

    :param subreddit: the praw Subreddit instance
    """

    # Only check posts once
    checked = list()

    if DEBUG:
        logger.warning("Running in debug mode")

    while True:
        logger.info(f"Checking for the {posts_per_run} most recent posts")
        for post in subreddit.new(limit=posts_per_run):
            if post not in checked:
                # Note : only the first violation will be reported
                # Check fanart frequency
                if is_fanart(post):
                    logger.debug(f"Found fanart {post} by {post.author.name}")
                    check_fanart_frequency(post)
                # Check clip frequency
                if is_clip(post):
                    logger.debug(f"Found clip {post} by {post.author.name}")
                    check_clip_frequency(post)
                # Check video edit frequency
                if is_video_edit(post):
                    logger.debug(f"Found video edit {post} by {post.author.name}")
                    check_video_edit_frequency(post)
                # Check video frequency
                if is_video(post):
                    logger.debug(f"Found video {post} by {post.author.name}")
                    check_video_frequency(post)
                checked.append(post)

        # Only remember the most recent posts, as the others won't flow back into /new
        checked = checked[-3 * posts_per_run :]  # noqa: E203

        time.sleep(interval)


def remove(post, reason, message=None):
    if DEBUG:
        logger.info(f"  !-> Not removing {post} by {post.author.name} in debug mode")
    else:
        logger.info(f"  --> Removing post {post} by {post.author.name}")
        if is_removed(post):
            logger.warning("  !-> Post already removed")
            return
        post.mod.remove(mod_note=reason)
        if message is not None:
            formatted_message = REMOVAL_MESSAGE_TEMPLATE.format(message=message)
            post.mod.send_removal_message(formatted_message)


def is_removed(item):
    return item.removed or item.banned_by is not None


##########################################
# OC fanart frequency verification block #
##########################################


def check_fanart_frequency(post):
    count = 0
    for submission in post.author.submissions.new():
        if submission.subreddit.display_name == config_loader.REDDIT["subreddit"] and is_removed(submission):
            continue

        created_at = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
        if datetime.now(timezone.utc) - created_at > timedelta(days=6, hours=23, minutes=45):
            break
        if is_fanart(submission):
            count += 1
        if count > 2:
            remove(
                post,
                f"Recent fanart (id: {submission.id})",
                message="You may only submit two fanart posts in a 7-day period.",
            )
            break

    logger.debug(f"Finished checking history of {post.author.name} for fanart frequency")


def is_fanart(post):
    return post.subreddit.display_name == config_loader.REDDIT["subreddit"] and post.link_flair_text == "Fanart"


#####################################
# Clip frequency verification block #
#####################################


def check_clip_frequency(post):
    count = 0
    for submission in post.author.submissions.new():
        if submission.subreddit.display_name == config_loader.REDDIT["subreddit"] and is_removed(submission):
            continue

        created_at = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
        if datetime.now(timezone.utc) - created_at > timedelta(days=29, hours=23, minutes=45):
            break
        if is_clip(submission):
            count += 1
        if count > 2:
            remove(post, "Too many clips submitted", message="You may only submit two clips every 30 days.")
            break

    logger.debug(f"Finished checking history of {post.author.name} for clip frequency")


def is_clip(post):
    return post.subreddit.display_name == config_loader.REDDIT["subreddit"] and post.link_flair_text == "Clip"


#####################################
# Video Edit frequency verification block #
#####################################


def check_video_edit_frequency(post):
    count = 0
    for submission in post.author.submissions.new():
        if submission.subreddit.display_name == config_loader.REDDIT["subreddit"] and is_removed(submission):
            continue

        created_at = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
        if datetime.now(timezone.utc) - created_at > timedelta(days=29, hours=23, minutes=45):
            break
        if is_video_edit(submission):
            count += 1
        if count > 2:
            remove(post, "Too many clips submitted", message="You may only submit two video edits every 30 days.")
            break

    logger.debug(f"Finished checking history of {post.author.name} for video edit frequency")


def is_video_edit(post):
    return post.subreddit.display_name == config_loader.REDDIT["subreddit"] and post.link_flair_text == "Video Edit"


#####################################
# Video frequency verification block #
#####################################


def check_video_frequency(post):
    count = 0
    for submission in post.author.submissions.new():
        if submission.subreddit.display_name == config_loader.REDDIT["subreddit"] and is_removed(submission):
            continue

        created_at = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
        if datetime.now(timezone.utc) - created_at > timedelta(days=6, hours=23, minutes=45):
            break
        if is_video(submission):
            count += 1
        if count > 2:
            remove(post, "Too many videos submitted", message="You can only submit 2 videos at most every 7 days.")
            break

    logger.debug(f"Finished checking history of {post.author.name} for video frequency")


def is_video(post):
    return post.subreddit.display_name == config_loader.REDDIT["subreddit"] and post.link_flair_text == "Video"


#####################################


def monitor_stream():
    """
    Monitor the subreddit for new posts and parse them when they come in. Will restart upon encountering an error.
    """

    while True:
        try:
            logger.info("Connecting to Reddit...")
            reddit = reddit_utils.get_reddit_instance(config_loader.REDDIT["auth"])
            subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])
            logger.info("Starting submission processing...")
            main(subreddit)
        except Exception:
            delay_time = 30
            logger.exception(f"Encountered an unexpected error, restarting in {delay_time} seconds...")
            time.sleep(delay_time)


if __name__ == "__main__":
    DEBUG = False
    monitor_stream()
