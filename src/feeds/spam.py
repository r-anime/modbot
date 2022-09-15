"""
Monitors a subreddit's spam feed and saves new items to a database.
"""

import time

import config_loader
from feeds import new_comments, new_posts
from services import post_service
from utils import reddit as reddit_utils
from utils.logger import logger


def monitor_stream():
    """
    Monitor the subreddit for new items in the spam feed and parse them when they come in.
    Will restart upon encountering an error.
    """

    while True:
        try:
            logger.info("Connecting to Reddit...")
            reddit = reddit_utils.get_reddit_instance(config_loader.REDDIT["auth"])
            subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])
            logger.info("Loading flairs...")
            post_service.load_post_flairs(subreddit)
            logger.info("Starting spam stream...")
            for item in subreddit.mod.stream.spam(skip_existing=False):
                if item.fullname.startswith("t1_"):
                    new_comments.process_comment(item, reddit)
                elif item.fullname.startswith("t3_"):
                    new_posts.process_post(item)
        except Exception:
            delay_time = 30
            logger.exception(f"Encountered an unexpected error, restarting in {delay_time} seconds...")
            time.sleep(delay_time)


if __name__ == "__main__":
    monitor_stream()
