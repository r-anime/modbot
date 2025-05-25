#!/usr/bin/env python3

import time
from datetime import datetime, timezone, timedelta
import humanize
from dataclasses import dataclass

from praw.models import Submission

import config_loader
from data.post_data import PostModel
from services import post_service
from utils import reddit as reddit_utils
from utils.logger import logger

global DEBUG


@dataclass(frozen=True)
class FlairConfig:
    db_flairs: list[str]  # this is the DB flair text
    period: timedelta
    allowed_count: int
    reporting_flair_name: str  # This is displayed to users
    reporting_period: str  # This is displayed to users


REMOVAL_MESSAGE_TEMPLATE = """Sorry, your submission has been removed.\n\n{message}\n\n
*I am a bot, and this action was performed automatically. Please
[contact the moderators of this subreddit](https://www.reddit.com/message/compose/?to=/r/anime)
if you have any questions or concerns.*"""

REMOVAL_REASON_TEMPLATE = "Too many {reporting_flair_name} submitted: {posts}"
REMOVAL_MESSAGE_SUB_TEMPLATE = """
You may only submit {allowed_count} {reporting_flair_name} post{plural} {reporting_period}.\n
Your previous {reporting_flair_name} post{plural} on r/{sub_name}:\n
{previous_posts}\n
You may make another {reporting_flair_name} in approximately {duration_left} from now.""".strip()

FANART_CONFIG = FlairConfig(
    db_flairs=["Fanart", "Cosplay"],
    period=timedelta(days=6, hours=23, minutes=45),
    allowed_count=1,
    reporting_flair_name="Fanart/Cosplay",
    reporting_period="in a 7-day period",
)
CLIP_CONFIG = FlairConfig(
    db_flairs=["Clip"],
    period=timedelta(days=29, hours=23, minutes=45),
    allowed_count=2,
    reporting_flair_name="Clip",
    reporting_period="in a 30 day period",
)
VIDEO_EDIT_CONFIG = FlairConfig(
    db_flairs=["Video Edit"],
    period=timedelta(days=29, hours=23, minutes=45),
    allowed_count=2,
    reporting_flair_name="Video Edit",
    reporting_period="in a 30 day period",
)
VIDEO_CONFIG = FlairConfig(
    db_flairs=["Video"],
    period=timedelta(days=6, hours=23, minutes=45),
    allowed_count=2,
    reporting_flair_name="Video",
    reporting_period="in a 7 day period",
)

FLAIR_CONFIGS = [FANART_CONFIG, CLIP_CONFIG, VIDEO_EDIT_CONFIG, VIDEO_CONFIG]

# Number of posts to check on each run
posts_per_run = 25
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
                for flair_config in FLAIR_CONFIGS:
                    if flair_applicable(flair_config, post):
                        logger.debug(f"Found {flair_config.reporting_flair_name} {post} by {post.author.name}")
                        check_frequency(flair_config, post)
                        (
                            logger.debug(
                                f"Finished checking history of {post.author.name}"
                                + f" for {flair_config.reporting_flair_name} frequency"
                            )
                        )
                        break
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


def flair_applicable(flair_config: FlairConfig, post: Submission):
    return (
        post.subreddit.display_name == config_loader.REDDIT["subreddit"]
        and post.link_flair_text in flair_config.db_flairs
    )


def check_frequency(flair_config: FlairConfig, post: Submission):
    author = post.author.name
    end_date = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
    start_date = end_date - flair_config.period
    db_posts_raw = post_service.get_flaired_posts_by_username(
        author, flair_config.db_flairs, exclude_reddit_ids=[post.id], start_date=str(start_date), end_date=str(end_date)
    )
    db_posts = []
    for db_post in db_posts_raw:
        db_posts.append(db_post)
        if len(db_posts) + 1 > flair_config.allowed_count:
            remove(
                post,
                pretty_removal_reason(flair_config, db_posts),
                message=pretty_removal_message(flair_config, db_posts),
            )
            break


def pretty_removal_reason(flair_config: FlairConfig, db_posts: list[PostModel]) -> str:
    mods_recent_posts = ", ".join([f'{{id: "{item.id36}", posted: "{str(item.created_time)}"}}' for item in db_posts])
    return REMOVAL_REASON_TEMPLATE.format(
        reporting_flair_name=flair_config.reporting_flair_name, posts=mods_recent_posts
    )


def pretty_removal_message(flair_config: FlairConfig, db_posts: list[PostModel]) -> str:
    previous_posts = "\n".join(
        [
            f"{index + 1}. [{item.flair_text}] [{item.title}](https://redd.it/{item.id36})"
            for index, item in enumerate(db_posts)
        ]
    )
    allowed_timestamp = db_posts[0].created_time + flair_config.period + timedelta(minutes=15)
    duration_left = humanize.precisedelta(
        allowed_timestamp - datetime.now(tz=timezone.utc), suppress=["minutes", "seconds"]
    )
    return REMOVAL_MESSAGE_SUB_TEMPLATE.format(
        reporting_flair_name=flair_config.reporting_flair_name,
        allowed_count=flair_config.allowed_count,
        plural=("s" if flair_config.allowed_count > 1 else ""),
        sub_name=config_loader.REDDIT["subreddit"],
        previous_posts=previous_posts,
        duration_left=duration_left,
        reporting_period=flair_config.reporting_period,
    )


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
