"""
Approves posts/comments from the specified user that were removed by Reddit's spam filter.

Use with -h for instructions.
"""

import argparse
from datetime import datetime, timezone

import config_loader
from services import post_service, comment_service
from utils import discord, reddit as reddit_utils
from utils.logger import logger

# Current reddit session, initialized when first starting up or after an error.
reddit = None


def approve_user_items(username, start_date, end_date):
    posts = post_service.get_posts_by_username(username, start_date, end_date)
    comments = comment_service.get_comments_by_username(username, start_date, end_date)

    id_list = [f"t3_{post.id36}" for post in posts if not post.removed]
    id_list.extend(f"t1_{comment.id36}" for comment in comments if not comment.removed)
    approve_list = []
    error_list = []
    skip_list = []

    logger.info(f"Found {len(id_list)} items in database by {username}")
    embed_json = {
        "author": {
            "name": f"Unspam - /u/{username}",
        },
        "title": f"Beginning to unspam /u/{username}",
        "description": f"Found {len(id_list)} items in the database",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "url": f"https://reddit.com/user/{username}",
        "fields": [],
        "color": 0x00CC00,
    }
    discord.send_webhook_message(config_loader.DISCORD["webhook_url"], {"embeds": [embed_json]})

    for item in reddit.info(fullnames=id_list):
        try:
            if item.banned_by is not True:  # not removed by spam filter
                skip_list.append(item.fullname)
                continue
            item.mod.approve()
            logger.info(f"Approved {item.fullname}")
            approve_list.append(item.fullname)
        except Exception:
            error_list.append(item.fullname)
            logger.exception(f"Ran into exception for {item}, continuing")

    logger.info(f"Finished unspamming {username}")
    logger.info(f"Total {len(approve_list)} approved, {len(skip_list)} skipped, {len(error_list)} errors.")
    embed_json = {
        "author": {
            "name": f"Unspam - /u/{username}",
        },
        "title": f"Finished unspamming /u/{username}",
        "description": f"{len(approve_list)} approved, {len(skip_list)} skipped, {len(error_list)} errors",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "url": f"https://reddit.com/user/{username}",
        "fields": [],
        "color": 0x00CC00,
    }
    discord.send_webhook_message(config_loader.DISCORD["webhook_url"], {"embeds": [embed_json]})


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
