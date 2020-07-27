"""Utilities regarding Reddit posts/users/etc"""

import praw

import config
from utils.logger import logger


# Shared singleton session, always call get_instance to gain access to it. Can be recreated with get_instance.
_reddit_session = praw.Reddit(**config.REDDIT["auth"])
_subreddit = _reddit_session.subreddit(config.REDDIT["subreddit"])


def slug(submission):
    """
    Returns the part of the post URL that resembles the title, e.g. for
     https://www.reddit.com/r/anime/comments/hldbm3/meta_thread_month_of_july_05_2020/ it returns
     meta_thread_month_of_july_05_2020

    :param submission: praw SubmissionModel instance
    :return: string
    """
    return submission.permalink.rsplit('/')[-2]


def is_image(submission):
    """
    Checks if the post is a single image post (or is a text post only containing a link to a single image).

    Taken from flairbot with minor changes.

    :param submission: praw SubmissionModel instance
    :return: True if an image, False otherwise
    """

    # covers i.redd.it
    if submission.is_reddit_media_domain:
        return True

    if submission.is_self:
        body = submission.selftext.strip()
        if body.startswith('http') and len(body.split()) == 1:
            # body is a single link, can check this
            url = body
        else:
            return False
    else:
        url = submission.url

    # will check against each item in the tuple
    image_extensions = ('.jpg', '.png', '.gif')
    if url.endswith(image_extensions):
        return True

    if 'i.imgur.com' in url:
        return True
    if 'pbs.twimg.com' in url:
        return True
    if 'imgur' in url and not ('/a/' in url or 'gallery' in url):
        return True

    return False


def is_text(submission):
    """
    Checks if the post is a text post and additionally, that the text is more than just a link to an image.

    Taken from flairbot.

    :param submission: praw SubmissionModel instance
    :return: True if a text post that's not just an image link, False otherwise
    """

    return submission.is_self and not is_image(submission)


def get_instance(reinitialize=False):
    """
    Gets a usable connection to Reddit.

    :param reinitialize: boolean, whether to create a new Reddit instance (useful if encountering an error)
    :return: praw Reddit instance
    """
    global _reddit_session, _subreddit

    if reinitialize or _reddit_session is None:
        _reddit_session = praw.Reddit(**config.REDDIT["auth"])
        _subreddit = _reddit_session.subreddit(config.REDDIT["subreddit"])

    return _reddit_session


def message_user(username, subject, body, as_subreddit=True):
    """
    Sends a message to the specified user on Reddit.

    :param username: string, username to send to
    :param subject: string, title of message
    :param body: string, contents of message
    :param as_subreddit: boolean, whether or not to send as the subreddit (i.e. from modmail)
    :return: None
    """

    user = _reddit_session.redditor(username)
    if not config.DEBUG_MODE:
        if as_subreddit:
            user.message(subject, body, from_subreddit=_subreddit)
        else:
            user.message(subject, body)
    else:
        logger.debug(f"Sending message to user {username}, subreddit {as_subreddit}, subject {subject}, body {body}")
