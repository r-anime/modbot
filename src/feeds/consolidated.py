"""
consolidated.py

Monitors a subreddit for new posts, comments, and mod log events.
Combined new_posts, new_comments, mod_log, and spam feeds.
"""

import argparse
import time

import config_loader
from feeds import mod_log, new_comments, new_posts
from services import post_service
from utils import reddit as reddit_utils
from utils.logger import logger


def monitor_streams(posts: bool = False, comments: bool = False, log: bool = False, spam: bool = False):
    """
    Monitor the subreddit for new events and parse them when they come in. Will restart upon encountering an error.
    """

    submission_stream = None
    comment_stream = None
    mod_log_stream = None
    spam_stream = None

    while True:
        try:
            logger.info("Connecting to Reddit...")
            reddit = reddit_utils.get_reddit_instance(config_loader.REDDIT["auth"])
            subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])
            mod_log.get_moderators()
            logger.debug("Loading flairs...")
            post_service.load_post_flairs(subreddit)
            if posts:
                logger.info("Initializing submission stream...")
                submission_stream = subreddit.stream.submissions(skip_existing=False, pause_after=-1)
            if comments:
                logger.info("Initializing comment stream...")
                comment_stream = subreddit.stream.comments(skip_existing=False, pause_after=-1)
            if log:
                logger.info("Initializing mod log stream...")
                mod_log_stream = subreddit.mod.stream.log(skip_existing=False, pause_after=-1)
            if spam:
                logger.info("Initializing spam stream...")
                spam_stream = subreddit.mod.stream.spam(skip_existing=False, pause_after=-1)

            while True:
                if log:
                    logger.debug("Starting mod log stream...")
                    for mod_action in mod_log_stream:
                        if mod_action is None:
                            time.sleep(3)
                            break
                        mod_log.parse_mod_action(mod_action, reddit, subreddit)

                if posts:
                    logger.debug("Starting post stream...")
                    for submission in submission_stream:
                        if submission is None:
                            time.sleep(3)
                            break
                        new_posts.process_post(submission)

                if comments:
                    logger.debug("Starting comment stream...")
                    for comment in comment_stream:
                        if comment is None:
                            time.sleep(3)
                            break
                        new_comments.process_comment(comment, reddit)

                if spam:
                    logger.debug("Starting spam stream...")
                    for item in spam_stream:
                        if item is None:
                            time.sleep(3)
                            break
                        if item.fullname.startswith("t1_"):
                            new_comments.process_comment(item, reddit)
                        elif item.fullname.startswith("t3_"):
                            new_posts.process_post(item)

        except Exception:
            delay_time = 30
            logger.exception(f"Encountered an unexpected error, restarting in {delay_time} seconds...")
            time.sleep(delay_time)


def _get_parser() -> argparse.ArgumentParser:
    new_parser = argparse.ArgumentParser(description="Monitor one or more feeds in turn.")
    new_parser.add_argument("-p", "--posts", action="store_true", default=False, help="Monitor new post feed")
    new_parser.add_argument("-c", "--comments", action="store_true", default=False, help="Monitor new comment feed")
    new_parser.add_argument("-m", "--mod_log", action="store_true", default=False, help="Monitor mod log feed")
    new_parser.add_argument("-s", "--spam", action="store_true", default=False, help="Monitor spam feed")
    return new_parser


if __name__ == "__main__":
    parser = _get_parser()
    args = parser.parse_args()
    monitor_streams(args.posts, args.comments, args.mod_log, args.spam)
