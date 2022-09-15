"""
Saves old posts and comments into the database. Use with -h for instructions.
"""

import argparse
from datetime import datetime
import time

from praw.models.reddit.submission import Submission
import psaw

import config_loader
from services import post_service, comment_service, user_service, base_data_service
from utils import reddit as reddit_utils
from utils.logger import logger


# Current reddit session, subreddit, and Pushshift API client, initialized when first starting up or after an error.
reddit = None
subreddit = None
ps_api = None


def save_comments(reddit_submission: Submission):
    """
    Saves all comments on a single post to the database.
    """

    post_name = reddit_submission.permalink

    logger.info(f"Loading {reddit_submission.num_comments} comments on {post_name}")

    # Load all comments
    retry_count = 0
    while True:
        try:
            retry_count += 1
            if retry_count > 3:
                logger.info(f"Unable to load all comments for {post_name}")
                return
            reddit_submission.comments.replace_more(limit=None)
            break
        except Exception:
            logger.exception("Handling replace_more exception")
            time.sleep(5)

    logger.info(f"Processing comments on {post_name}")
    processed_comment_ids = []
    comment_list = list(reddit_submission.comments.list())
    processed_any = False
    # Loop through and add all top-level comments, then all of their children, etc. in order for efficiency.
    while comment_list:
        for reddit_comment in comment_list:
            if reddit_comment.is_root:
                comment_service.add_comment(reddit_comment)
                comment_list.remove(reddit_comment)
                processed_comment_ids.append(reddit_comment.id)
                if len(processed_comment_ids) % 500 == 0:
                    logger.info(f"Completed {len(processed_comment_ids)} comments on {post_name}")
                processed_any = True
                continue
            parent_id = reddit_comment.parent_id.split("t1_")[1]
            if parent_id in processed_comment_ids:
                comment_service.add_comment(reddit_comment)
                comment_list.remove(reddit_comment)
                processed_comment_ids.append(reddit_comment.id)
                if len(processed_comment_ids) % 500 == 0:
                    logger.info(f"Completed {len(processed_comment_ids)} comments on {post_name}")
                processed_any = True
                continue
        # There may be some odd cases that won't be handled by this process so add a check to avoid infinite looping.
        if not processed_any:
            break

    # If there are any left, go through the slower process crawling up the tree to clean up any leftovers.
    for index, reddit_comment in enumerate(comment_list):
        comment_service.add_comment_parent_tree(reddit, reddit_comment)
        comment_service.add_comment(reddit_comment)
        processed_comment_ids.append(reddit_comment.id)
        if len(processed_comment_ids) % 500 == 0:
            logger.info(f"Completed {len(processed_comment_ids)} comments on {post_name}")

    logger.info(f"Finished processing {post_name}, total {len(processed_comment_ids)} comments")


def load_post_by_id(post_id: str):
    global reddit, subreddit
    reddit = reddit_utils.get_reddit_instance(config_loader.REDDIT["auth"])
    subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])
    reddit_submission = reddit.submission(id=post_id)
    if reddit_submission.subreddit_name_prefixed != subreddit.display_name_prefixed:
        logger.info(f"Post {post_id} is not on {subreddit.display_name_prefixed}, skipping...")
        return

    post_service.add_post(reddit_submission)
    save_comments(reddit_submission)


def load_post_list_file(archive_file_path: str):
    """
    Saves all posts and their comments into the database from the list of post URLs in the specified file.
    """

    archive_file = open(archive_file_path, "r")
    post_list = [s.strip() for s in archive_file.readlines()]

    for post in post_list:
        # Skip blank lines.
        if not post:
            continue
        try:
            global reddit, subreddit
            reddit = reddit_utils.get_reddit_instance(config_loader.REDDIT["auth"])
            subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])
            reddit_submission = reddit.submission(url=post)
            if reddit_submission.subreddit_name_prefixed != subreddit.display_name_prefixed:
                logger.info(f"Post {post} is not on {subreddit.display_name_prefixed}, skipping...")
                continue
            post_service.add_post(reddit_submission)
            save_comments(reddit_submission)
        except Exception:
            logger.exception(f"Unable to save {post}, continuing in 30 seconds...")
            time.sleep(30)


def load_posts_from_dates(start_date: datetime, end_date: datetime, skip_cdf: bool = False):
    """
    Saves all posts made in the specified time frame.
    """
    global ps_api, reddit, subreddit

    reddit = reddit_utils.get_reddit_instance(config_loader.REDDIT["auth"])
    subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])
    ps_api = psaw.PushshiftAPI()

    logger.info(f"Fetching posts between {start_date.isoformat()} and {end_date.isoformat()}")

    ps_list = list(
        ps_api.search_submissions(
            subreddit=config_loader.REDDIT["subreddit"],
            after=int(start_date.timestamp()),
            before=int(end_date.timestamp()),
        )
    )
    post_list = ps_list[::-1]  # reverse to go in chronological ascending order
    total_posts = len(post_list)
    error_posts = []

    logger.info(f"Found {len(post_list)} posts between {start_date.isoformat()} and {end_date.isoformat()}")
    for ps_post in post_list:
        if ps_post.subreddit != config_loader.REDDIT["subreddit"]:
            continue
        try:
            post = post_service.get_post_by_id(ps_post.id)
            if post:
                if post.author is None:
                    post.author = ps_post.author
                    if not user_service.get_user(post.author):
                        user_service.add_user(post.author)
                if post.body == "[deleted]" and getattr(ps_post, "selftext", None) not in (
                    "[deleted]",
                    "[removed]",
                    None,
                ):
                    post.body = ps_post.selftext
                base_data_service.update(post)
            else:
                post_service.add_post(ps_post)
        except Exception:
            logger.exception(f"Unable to save or update post {ps_post.id}")
            error_posts.append(ps_post.id)

    # Don't add CDF/FTF threads to the list of posts to get comments for if flag is set.
    skipped_posts = 0
    if skip_cdf:
        post_fullname_list = []
        for post in post_list:
            if (
                post.title.startswith("Casual Discussion Fridays") or post.title.startswith("Free Talk Fridays")
            ) and post.author.lower() in ("animemod", "automoderator"):
                logger.info(f"Skipping getting comments for {post.permalink}")
                skipped_posts += 1
                continue
            post_fullname_list.append(f"t3_{post.id}")
    else:
        post_fullname_list = [f"t3_{post.id}" for post in post_list]

    processed_posts = 0
    error_posts = []
    reddit_post_list = reddit.info(fullnames=post_fullname_list)
    for reddit_post in reddit_post_list:
        try:
            save_comments(reddit_post)
            processed_posts += 1
        except Exception:
            logger.exception(f"Unable to save comments on {reddit_post.id}, continuing in 30 seconds...")
            error_posts.append(reddit_post.id)
            time.sleep(30)
    logger.info(f"Finished with {processed_posts} processed, {skipped_posts} skipped, {total_posts} total.")
    if error_posts:
        logger.error(f"Errored on posts: {', '.join(error_posts)}")


def load_comments_from_dates(start_date: datetime, end_date: datetime):
    """
    Saves all comments made in the specified time frame.
    """
    pass


def _get_parser() -> argparse.ArgumentParser:
    new_parser = argparse.ArgumentParser(description="Archive posts and comments in them.")
    new_parser.add_argument("--file", action="store", help="File path to list of post URLs to archive.")
    new_parser.add_argument("--id", action="store", help="ID of single post to archive.")
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
    new_parser.add_argument(
        "-c", "--comments", action="store_true", default=False, help="Gather comments (for date only)"
    )
    new_parser.add_argument("-p", "--posts", action="store_true", default=False, help="Gather posts (for date only)")
    new_parser.add_argument(
        "--skip_cdf",
        action="store_true",
        default=False,
        help="Don't add comments from Casual Discussion Fridays / Free Talk Fridays threads",
    )
    return new_parser


if __name__ == "__main__":
    parser = _get_parser()
    args = parser.parse_args()
    if args.file:
        load_post_list_file(args.file)
    elif args.id:
        load_post_by_id(args.id)
    elif args.start_date and args.end_date:
        if args.start_date > args.end_date:
            raise ValueError("start_date must be before end_date.")
        if not (args.posts or args.comments):
            raise ValueError("Must provide --posts and/or --comments with date values.")
        if args.posts:
            load_posts_from_dates(args.start_date, args.end_date, skip_cdf=args.skip_cdf)
        if args.comments:
            load_comments_from_dates(args.start_date, args.end_date)
    else:
        raise ValueError("Must provide either --file, --id, or --start_date and --end_date.")
