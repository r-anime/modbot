"""
Monitors a subreddit for new comments and saves them to a database.
"""

import time

from praw.models.reddit.comment import Comment

import config_loader
from services import post_service, comment_service
from services.rabbit_service import RabbitService
from utils import reddit as reddit_utils
from utils.logger import logger


def process_comment(reddit_comment: Comment, reddit, rabbit: RabbitService):
    """
    Process a single PRAW Comment. Adds it to the database if it didn't previously exist as well as parent comments
    and the thread it belongs to.
    """

    comment = comment_service.get_comment_by_id(reddit_comment.id)

    if comment:
        # Update our record of the comment if necessary.
        updated_comment = comment_service.update_comment(comment, reddit_comment)
        rabbit.publish_comment(reddit_comment, updated_comment, "update")
        return

    author_name = reddit_comment.author.name if reddit_comment.author is not None else "[deleted]"
    logger.info(f"Processing comment {reddit_comment.id} - /u/{author_name} (post {reddit_comment.submission.id})")

    # Post needs to exist before we can add a comment for it, start with that.
    post = post_service.get_post_by_id(reddit_comment.submission.id)

    if not post:
        post_service.add_post(reddit_comment.submission)

    # Since all comments will reference a parent if it exists, add all parent comments first.
    logger.debug(f"Saving parent comments of {reddit_comment.id}")
    comment_service.add_comment_parent_tree(reddit, reddit_comment)
    logger.debug(f"Saving comment {reddit_comment.id}")
    comment = comment_service.add_comment(reddit_comment)

    rabbit.publish_comment(reddit_comment, comment)
    logger.debug(f"Finished processing {comment.id36}")


def monitor_stream():
    """
    Monitor the subreddit for new comments and parse them when they come in. Will restart upon encountering an error.
    """

    while True:
        try:
            logger.info("Connecting to Reddit...")
            reddit = reddit_utils.get_reddit_instance(config_loader.REDDIT["auth"])
            subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])
            rabbit = RabbitService(config_loader.RABBITMQ)
            logger.info("Starting comment stream...")
            for comment in subreddit.stream.comments(skip_existing=False):
                process_comment(comment, reddit, rabbit)
        except Exception:
            delay_time = 30
            logger.exception(f"Encountered an unexpected error, restarting in {delay_time} seconds...")
            time.sleep(delay_time)


if __name__ == "__main__":
    monitor_stream()
