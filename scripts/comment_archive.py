"""
Saves old posts and comments into the database. Use with -h for instructions.
"""

import argparse
from datetime import datetime, timedelta
import time

import praw
from praw.models.reddit.submission import Submission
import psaw

import config_loader
from services import post_service, comment_service
from utils.logger import logger


# Current reddit session, subreddit, and Pushshift API client, initialized when first starting up or after an error.
reddit = None
subreddit = None
ps_api = None


def save_post_and_comments(reddit_submission: Submission, pushshift_submission=None):
    """
    Saves a single reddit post and its comments to the database.
    """

    post_name = reddit_submission.permalink

    # Ensure post is in the database first.
    post_service.add_post(reddit_submission)
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
    index = -1
    for index, reddit_comment in enumerate(reddit_submission.comments.list()):
        # Since all comments will reference a parent if it exists, add all parent comments first.
        logger.debug(f"Saving parent comments of {reddit_comment.id}")
        comment_service.add_comment_parent_tree(reddit, reddit_comment)
        logger.debug(f"Saving comment {reddit_comment.id}")
        comment_service.add_comment(reddit_comment)
        if (index + 1) % 500 == 0:
            logger.info(f"Completed {index + 1} comments on {post_name}")

    logger.info(f"Finished processing {post_name}, total {index + 1} comments")


def load_post_by_id(post_id: str):
    global reddit, subreddit
    reddit = praw.Reddit(**config_loader.REDDIT["auth"])
    subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])
    reddit_submission = reddit.submission(id=post_id)
    if reddit_submission.subreddit_name_prefixed != subreddit.display_name_prefixed:
        logger.info(f"Post {post_id} is not on {subreddit.display_name_prefixed}, skipping...")
        return

    save_post_and_comments(reddit_submission)


def load_post_list_file(archive_file_path: str):
    """
    Saves all posts and their comments into the database from the list of post URLs in the specified file.
    """

    archive_file = open(archive_file_path, "r")
    post_list = [s.strip() for s in archive_file.readlines()]

    for post in post_list:
        try:
            global reddit, subreddit
            reddit = praw.Reddit(**config_loader.REDDIT["auth"])
            subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])
            reddit_submission = reddit.submission(url=post)
            if reddit_submission.subreddit_name_prefixed != subreddit.display_name_prefixed:
                logger.info(f"Post {post} is not on {subreddit.display_name_prefixed}, skipping...")
                continue

            save_post_and_comments(reddit_submission)
        except Exception:
            logger.exception(f"Unable to save {post}, continuing in 30 seconds...")
            time.sleep(30)


def load_posts_from_dates(start_date: datetime, end_date: datetime, skip_cdf: bool = True):
    """
    Saves all posts made in the specified time frame and their comments.
    """
    current_date = start_date
    try:
        global reddit, subreddit, ps_api
        reddit = praw.Reddit(**config_loader.REDDIT["auth"])
        subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])
        ps_api = psaw.PushshiftAPI(reddit)
        while current_date < end_date:
            step_date = current_date + timedelta(hours=1)
            logger.info(f"Loading comments between {current_date} and {step_date}")
            comments = ps_api.search_comments(
                after=int(current_date.timestamp()), before=int(step_date.timestamp()), subreddit="anime"
            )
            index = -1
            logger.info("Comments loaded, processing...")
            for index, comment in enumerate(comments):
                try:
                    logger.debug(f"Saving parent comments of {comment.id}")
                    comment_service.add_comment_parent_tree(reddit, comment)
                    logger.debug(f"Saving comment {comment.id}")
                    comment_service.add_comment(comment)
                    if (index + 1) % 100 == 0:
                        logger.info(f"Completed {index + 1} comments after {current_date.isoformat()}")
                except Exception:
                    logger.exception(f"Unable to save comment {comment}, continuing in 10 seconds...")
                    time.sleep(10)
            logger.info(f"Finished {current_date.isoformat()} to {step_date.isoformat()}, total {index + 1} comments")
            current_date = step_date

    except Exception:
        logger.exception(f"Unable to save posts after {current_date}, continuing in 30 seconds...")
        time.sleep(30)


def _get_parser() -> argparse.ArgumentParser:
    new_parser = argparse.ArgumentParser(description="Archive posts and comments in them.")
    new_parser.add_argument("--file", action="store", help="File path to list of post URLs to archive.")
    new_parser.add_argument("--post", action="store", help="ID of single post to archive.")
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
        "-c", "--cdf", action="store_true", default=False, help="Don't skip FTF/CDF threads (when operating by date)."
    )
    return new_parser


if __name__ == "__main__":
    parser = _get_parser()
    args = parser.parse_args()
    if args.file:
        load_post_list_file(args.file)
    elif args.post:
        load_post_by_id(args.post)
    elif args.start_date and args.end_date:
        if args.start_date > args.end_date:
            raise ValueError("start_date must be before end_date")
        load_posts_from_dates(args.start_date, args.end_date, not args.cdf)
    else:
        raise ValueError("Must provide either --file, --post, or --start_date and --end_date.")
