from datetime import datetime, timezone, timedelta
import re
import time

import praw

import config_loader
from utils import reddit
from utils.logger import logger

SEARCH_TIMEOUT = 3600
LINK_REGEX = r"\[{name}\]\(.*?\)"
LINK_FORMAT = "[{name}]({link})"


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
        self._update_menus(name, post)
        self._update_redesign_menus(name, short_name, post)
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

    def _update_menus(self, name, post):
        """
        Updates the sidebar text by replacing links to `name` with a permalink
        to `post`. Links formatting is defined by config.

        For example, the default format for links is `'[{name}](.*)'`

        :param name: name of the link to format
        :param post: post which should be linked to
        """
        logger.debug("Updating menus on old Reddit")

        pattern_match = LINK_REGEX.format(name=name)
        pattern_replace = LINK_FORMAT.format(name=name, link=post.shortlink)

        sidebar = self.subreddit.wiki["config/sidebar"]
        sidebar_text = sidebar.content_md
        sidebar_updated_text = self._replace_text(pattern_match, pattern_replace, sidebar_text)

        if sidebar_updated_text is None:
            logger.debug("No change necessary")
        elif self.debug:
            logger.debug("Running in debug mode, no change was made to sidebar")
        else:
            sidebar.edit(content=sidebar_updated_text, reason=f"Changed link for {name}")
            logger.debug("Changes saved to sidebar")

    def _update_redesign_menus(self, name, short_name, post):
        """
        Updates the menu and widget text on Redesign by replacing links to
        `name` with a permaling to `post`. Links formatting is identical to the
        formatting used on old Reddit.

        :param name: name of the link to format
        :param short_name: name of the link to use in topbar menu (max 20 characters)
        :param post: post which should be linked to
        """
        logger.debug("Updating menus on Redesign")

        assert len(short_name) <= 20

        topmenu = self._get_updated_redesign_topmenu(short_name, post.shortlink)
        if topmenu is None:
            logger.debug("Error updating topmenu")
        elif self.debug:
            logger.debug("Running in debug mode, no change was made to top menu")
        else:
            topmenu.mod.update(data=list(topmenu))
            logger.debug("Topbar menu updated")

        pattern_match = LINK_REGEX.format(name=name)
        pattern_replace = LINK_FORMAT.format(name=name, link=post.shortlink)

        sidemenu = self._get_redesign_sidemenu(name)
        sidemenu_text = sidemenu.text
        sidemenu_updated_text = self._replace_text(pattern_match, pattern_replace, sidemenu_text)

        if sidemenu_updated_text is None:
            logger.debug("No change necessary")
        elif self.debug:
            logger.debug("Running in debug mode, no change was made to side menu")
        else:
            sidemenu.mod.update(text=sidemenu_updated_text)
            logger.debug("Sidebar widget updated")

    def _get_updated_redesign_topmenu(self, name, new_url):
        """
        Update the menu by replacing links labeled `name` with `new_url` and
        return the updated menu. Updates are *not* reflected to the subreddit
        by calling this method.

        :param name: text of the menulink to update
        :param new_url: replacement url
        """
        menu = self.subreddit.widgets.topbar[0]
        assert isinstance(menu, praw.models.Menu)

        for item in menu:
            if isinstance(item, praw.models.MenuLink):
                if item.text == name:
                    logger.debug(f"Found replaceable MenuLink: {item.text}")
                    item.url = new_url
            elif isinstance(item, praw.models.Submenu):
                for subitem in item:
                    if isinstance(subitem, praw.models.MenuLink):
                        if subitem.text == name:
                            logger.debug(f"Found replaceable MenuLink: {item.text}")
                            subitem.url = new_url
                    else:
                        logger.debug(f"Wrong type found searching for MenuLink: {item.__class__}")
            else:
                logger.debug(f"Wrong type found searching for MenuLink: {item.__class__}")

        return menu

    def _get_redesign_sidemenu(self, name):
        """
        Return the sidebar widget containing a link to `name`.

        :param name: name of the link to update
        """
        sidebar = self.subreddit.widgets.sidebar

        pattern_match = LINK_REGEX.format(name=name)

        for widget in sidebar:
            if isinstance(widget, praw.models.TextArea):
                matches = re.findall(pattern_match, widget.text)
                if matches:
                    logger.debug(f"Found matching side widget '{widget.shortName}'")
                    return widget

        logger.debug("Found no sidebar widget with replaceable match")
        return None

    def _replace_text(self, pattern_match, pattern_replace, text):
        matches = re.findall(pattern_match, text)
        if not matches:
            logger.debug("Found no replaceable match")
            return None

        logger.debug(
            "Found replaceable matches\n"
            + f'\t\t\tOld text: {" // ".join(matches)}\n'
            + f"\t\t\tNew text: {pattern_replace}"
        )

        text_replaced = re.sub(pattern_match, pattern_replace, text)
        return text_replaced
