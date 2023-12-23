"""
Looks for users that commented in a minimum percentage of threads in the list. Use with -h for instructions.
"""

import argparse
from collections import Counter
from datetime import timedelta

from data.post_data import PostModel
from services import post_service, comment_service
from utils import reddit as reddit_utils
from utils.logger import logger


def get_post_users(post: PostModel, max_time_after: timedelta):
    comments = comment_service.get_comments_by_post_id(post.id36)
    usernames = set()
    for comment in comments:
        # Deleted/unknown users don't count.
        if not comment.author:
            continue
        # Skip comments past the time limit.
        if post.created_time + max_time_after < comment.created_time:
            continue
        usernames.add(comment.author)

    return usernames


def load_post_list(post_list: list[str]) -> list[str]:
    post_id_list = []
    for post_url in post_list:
        parsed_post_id = reddit_utils.POST_ID_REGEX.match(post_url)
        if not parsed_post_id:
            continue

        post_id_list.append(parsed_post_id.groupdict().get("id"))
    return post_id_list


def main(post_list: list[str], min_percentage: float, max_time_after: timedelta):
    post_id_list = load_post_list(post_list)
    post_with_users = {}
    for post_id in post_id_list:
        post = post_service.get_post_by_id(post_id)
        if not post:
            logger.warning(f"Post with ID {post_id} not found")
            continue

        user_set = get_post_users(post, max_time_after)
        user_set.add(post.author)
        post_with_users[post] = list(user_set)

    post_count = len(post_with_users)
    user_counts = Counter([username for user_list in post_with_users.values() for username in user_list])
    users_sorted = sorted(user_counts.items(), key=lambda kv: kv[1], reverse=True)
    for username, user_count in users_sorted:
        user_percentage = int(round(user_count / post_count, 2) * 100)
        if user_percentage < min_percentage:
            break
        logger.info(f"{username:>22}: {user_percentage:>3}% ({user_count:3} / {post_count:<3})")


def _get_parser() -> argparse.ArgumentParser:
    new_parser = argparse.ArgumentParser(description="Check users who commented on a post.")
    new_parser.add_argument(
        "-f", "--file", action="store", required=True, help="File path to list of post URLs to check."
    )
    new_parser.add_argument(
        "-p",
        "--percentage",
        action="store",
        type=int,
        default=80,
        help="Minimum percentage of threads required (default 80).",
    )
    new_parser.add_argument(
        "-d",
        "--max_days",
        type=lambda d: timedelta(days=int(d)),
        default=timedelta(days=7),
        help="Maximum number of days after thread posting to count comments toward participation (default 7).",
    )
    return new_parser


if __name__ == "__main__":
    parser = _get_parser()
    args = parser.parse_args()

    with open(args.file, "r") as post_file:
        post_url_list = [s.strip() for s in post_file.readlines()]

    main(post_url_list, args.percentage, args.max_days)
