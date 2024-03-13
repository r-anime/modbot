import re

import praw.models

import config_loader
from constants import post_constants
from utils import reddit
from utils.logger import logger


def replace_sidebar_link(name, new_link, subreddit=None):
    """
    Updates the sidebar text by replacing links to `name` with a permalink
    to `new_link`. Links formatting is defined by reddit.LINK_REGEX and LINK_FORMAT.

    For example, the default format for links is `'[{name}](.*)'`

    :param name: text of link to be changed
    :param new_link: new link to be set
    :param subreddit: PRAW subreddit instance
    :return:
    """

    pattern_match = post_constants.LINK_REGEX.format(name=name)
    pattern_replace = post_constants.LINK_FORMAT.format(name=name, link=new_link)

    if not subreddit:
        subreddit = reddit.get_reddit_instance(config_loader.REDDIT["auth"]).subreddit(
            config_loader.REDDIT["subreddit"]
        )
    sidebar = subreddit.wiki["config/sidebar"]
    sidebar_text = sidebar.content_md
    sidebar_updated_text = _replace_text(pattern_match, pattern_replace, sidebar_text)

    if sidebar_updated_text is None:
        logger.debug("No change necessary")
    else:
        sidebar.edit(content=sidebar_updated_text, reason=f"Changed link for {name}")
        logger.debug("Changes saved to sidebar")


def update_redesign_menus(name, short_name, post, subreddit=None):
    """
    Updates the menu and widget text on Redesign by replacing links to
    `name` with a permaling to `post`. Links formatting is identical to the
    formatting used on old Reddit.

    :param name: name of the link to format
    :param short_name: name of the link to use in topbar menu (max 20 characters)
    :param post: post which should be linked to
    :param subreddit: PRAW subreddit instance
    """
    logger.debug("Updating menus on Redesign")

    assert len(short_name) <= 20

    if not subreddit:
        subreddit = reddit.get_reddit_instance(config_loader.REDDIT["auth"]).subreddit(
            config_loader.REDDIT["subreddit"]
        )

    topmenu = _get_updated_redesign_topmenu(short_name, reddit.make_permalink(post, shortlink=True), subreddit)
    if topmenu is None:
        logger.debug("Error updating topmenu")
    else:
        topmenu.mod.update(data=list(topmenu))
        logger.debug("Topbar menu updated")

    pattern_match = post_constants.LINK_REGEX.format(name=name)
    pattern_replace = post_constants.LINK_FORMAT.format(name=name, link=reddit.make_permalink(post, shortlink=True))

    sidemenu = _get_redesign_sidemenu(name, subreddit)
    sidemenu_text = sidemenu.text
    sidemenu_updated_text = _replace_text(pattern_match, pattern_replace, sidemenu_text)

    if sidemenu_updated_text is None:
        logger.debug("No change necessary")
    else:
        sidemenu.mod.update(text=sidemenu_updated_text)
        logger.debug("Sidebar widget updated")


def _get_updated_redesign_topmenu(name, new_url, subreddit):
    """
    Update the menu by replacing links labeled `name` with `new_url` and
    return the updated menu. Updates are *not* reflected to the subreddit
    by calling this method.

    :param name: text of the menulink to update
    :param new_url: replacement url
    :param subreddit: PRAW subreddit instance
    """
    menu = subreddit.widgets.topbar[0]
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


def _get_redesign_sidemenu(name, subreddit):
    """
    Return the sidebar widget containing a link to `name`.

    :param name: name of the link to update
    """
    sidebar = subreddit.widgets.sidebar

    pattern_match = post_constants.LINK_REGEX.format(name=name)

    for widget in sidebar:
        if isinstance(widget, praw.models.TextArea):
            matches = re.findall(pattern_match, widget.text)
            if matches:
                logger.debug(f"Found matching side widget '{widget.shortName}'")
                return widget

    logger.debug("Found no sidebar widget with replaceable match")


def _replace_text(pattern_match, pattern_replace, text):
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
