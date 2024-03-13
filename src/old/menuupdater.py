from datetime import datetime, timezone, timedelta
import re
import time

import praw

import config_loader
from constants import post_constants
from services import post_service, sidebar_service
from utils import reddit
from utils.logger import logger


SEARCH_TIMEOUT = 3600


class SubredditMenuUpdater:
    def __init__(self, name, short_name, author, debug=False):
        """
        Update the subreddit menu to the most recent post with <name>
        Used to replace links for weekly megathreads

        This script is supposed to run *at the same time* as the thread to
        update is posted. A timeout guarantees that if the post is not found
        soon, the script will stop with failure.

        The Reddit mod account, subreddit, and various script settings are
        configured in a static file (default `config.ini`).

        :param name: name of the post as written in the title and menu
        :param short_name: name to use in redesign topbar (max 20 characters)
        :param author: account from which the post was submitted
        :param debug: if True, no change will be made to the subreddit
        """

        logger.info(f"Started running subreddit menu updater for {name}")
        self.debug = debug
        self.reddit = reddit.get_reddit_instance(config_loader.REDDIT["auth"])
        self.subreddit = self.reddit.subreddit(config_loader.REDDIT["subreddit"])

        post = self._find_post(name, author)
        db_post = post_service.get_post_by_id(post.id)
        sidebar_service.replace_sidebar_link(name, reddit.make_relative_link(db_post), self.subreddit)
        sidebar_service.update_redesign_menus(name, short_name, db_post, self.subreddit)

        logger.info(f"Completed running subreddit menu updater for {name}")

    def _find_post(self, name, author):
        search_str = f'title:"{name}" author:{author}'.lower()
        search_start_time = time.time()

        logger.debug(f"Started search with query '{search_str}'")
        while True:
            post = next(self.subreddit.search(search_str, sort="new"), None)
            if post is not None:
                post_timestamp = datetime.fromtimestamp(post.created_utc, timezone.utc)
                if post_timestamp > datetime.now(timezone.utc) - timedelta(days=6):
                    # guarantees that the post found was created in the past week
                    logger.debug(f"Post found {post.permalink}")
                    return post

            if time.time() - search_start_time > SEARCH_TIMEOUT:
                raise TimeoutError("Post not found")
            time.sleep(15)
