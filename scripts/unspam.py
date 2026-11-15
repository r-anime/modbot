"""
Approves posts/comments from the specified user that were removed by Reddit's spam filter.

Use with -h for instructions.
"""

import argparse
import time
from datetime import datetime, timezone

import config_loader
from services import post_service, comment_service
from utils import discord, reddit as reddit_utils
from utils.logger import logger

# Current reddit session, initialized when first starting up or after an error.
reddit = None
THROTTLE_START = 0.50  # throttle starts %
THROTTLE_END = 0.80  # enough sleep for it to make it to the next window by this %
THROTTLE_WIDTH = THROTTLE_END - THROTTLE_START


def approve_user_items(username, start_date, end_date):
    posts = post_service.get_posts_by_username(username, start_date, end_date)
    comments = comment_service.get_comments_by_username(username, start_date, end_date)

    id_list = [f"t3_{post.id36}" for post in posts if not post.removed]
    id_list.extend(f"t1_{comment.id36}" for comment in comments if not comment.removed)
    approve_list = []
    error_list = []
    skip_list = []

    logger.info(f"Found {len(id_list):,} items in database by {username}")
    send_to_discord(
        ["mod_log_webhook_url"],
        username,
        f"Beginning to unspam /u/{username}",
        f"Found {len(id_list):,} items in the database",
    )

    total_items = len(id_list)
    item_count = 0
    rate_limit_count = 0
    cycle_start_time = datetime.now()
    for item in reddit.info(fullnames=id_list):
        item_count += 1
        new_rate_limit_count = rate_limit_count
        try:
            if item.banned_by is not True:  # not removed by spam filter
                skip_list.append(item.fullname)
                continue
            new_rate_limit_count = wait_for_rate_limit(rate_limit_count)
            item.mod.approve()
            logger.info(f"Approved {item.fullname} ({item_count:,}/{total_items:,}) for /u/{username}")
            approve_list.append(item.fullname)
        except Exception:
            error_list.append(item.fullname)
            logger.exception(
                f"Ran into exception for {item} ({item_count:,}/{total_items:,}) for /u/{username}, continuing"
            )
        if new_rate_limit_count < rate_limit_count:
            # cycle reset
            remaining = len(id_list) - len(approve_list) - len(skip_list) - len(error_list)
            rate = rate_limit_count / (datetime.now() - cycle_start_time).total_seconds()
            eta = int(datetime.now().timestamp() + remaining / rate)
            send_to_discord(
                ["mod_log_webhook_url"],
                username,
                f"Unspamming /u/{username} progress report",
                f"{len(approve_list):,} approved, {remaining:,} remaining"
                + f", {len(skip_list):,} skipped, {len(error_list):,} errors"
                + f"\nETA: <t:{eta}:F> (<t:{eta}:R>), current rate: {rate * 60:,.2f} approvals / min",
            )
            cycle_start_time = datetime.now()
        rate_limit_count = new_rate_limit_count

    logger.info(f"Finished unspamming {username}")
    logger.info(f"Total {len(approve_list):,} approved, {len(skip_list):,} skipped, {len(error_list):,} errors.")
    send_to_discord(
        ["mod_log_webhook_url"],
        username,
        f"Finished unspamming /u/{username}",
        f"{len(approve_list):,} approved, {len(skip_list):,} skipped, {len(error_list):,} errors",
    )


# uses the reddit rate limit vars to slow the script down so other things don't get rate limited as badly.
def wait_for_rate_limit(rate_limit_count: int):
    limits = reddit.auth.limits
    if limits["used"] is None:
        return rate_limit_count + 1

    used = limits["used"]
    remaining = limits["remaining"]
    total_limit = used + remaining
    window_size = reddit.config.window_size
    usage = used / total_limit

    if used < rate_limit_count:
        return 1  # new rate limit cycle

    if usage < THROTTLE_START:
        return rate_limit_count + 1

    delay = (usage - THROTTLE_START) / THROTTLE_WIDTH * window_size / (total_limit * THROTTLE_WIDTH / 2)
    logger.debug(f"Used: {used:,}, remaining: {remaining:,}, delay: {delay:,} seconds")
    time.sleep(delay)
    return rate_limit_count + 1


def send_to_discord(webhook_keys: list[str], username: str, title: str, message: str):
    embed_json = {
        "author": {
            "name": f"Unspam - /u/{username}",
        },
        "title": title,
        "description": message,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "url": f"https://reddit.com/user/{username}",
        "fields": [],
        "color": 0x00CC00,
    }
    for webhook_key in webhook_keys:
        discord.send_webhook_message(config_loader.DISCORD[webhook_key], {"embeds": [embed_json]})


def _get_parser() -> argparse.ArgumentParser:
    new_parser = argparse.ArgumentParser(
        description="Approves posts/comments by a user that were removed by Reddit's spam filter."
    )
    new_parser.add_argument("-u", "--user", action="store", required=True, help="Username to approve things for.")
    # new_parser.add_argument(
    #     "-p", "--pushshift", action="store", default=False, help="Include posts/comments from Pushshift"
    # )
    new_parser.add_argument(
        "-s",
        "--start_date",
        type=lambda d: datetime.fromisoformat(d),
        help="Date to start getting posts/comments (ISO 8601 format).",
    )
    new_parser.add_argument(
        "-e",
        "--end_date",
        type=lambda d: datetime.fromisoformat(d),
        help="Date to stop getting posts/comments (ISO 8601 format).",
    )
    return new_parser


if __name__ == "__main__":
    parser = _get_parser()
    args = parser.parse_args()
    if args.start_date and args.end_date:
        if args.start_date > args.end_date:
            raise ValueError("start_date must be before end_date")
    reddit = reddit_utils.get_reddit_instance(config_loader.REDDIT["auth"])
    logger.info(f"Starting to unspam {args.user}")
    approve_user_items(args.user, args.start_date, args.end_date)
