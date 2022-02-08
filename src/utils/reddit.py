"""Utilities regarding Reddit posts/users/etc"""

from typing import Optional

import praw
from praw.models.reddit.subreddit import Subreddit

import config_loader
from data.base_data import BaseModel


reddit: Optional[praw.Reddit] = None
subreddit: Optional[Subreddit] = None

_b36_alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"


def slug(submission):
    return submission.permalink.rsplit("/")[-2]


def base36encode(number: int) -> str:
    """
    Converts an integer to a base36 string.

    For the sake of speed this does not work with negative integers.
    """
    if not isinstance(number, int):
        raise TypeError("number must be an integer")

    base36 = ""

    if 0 <= number < len(_b36_alphabet):
        return _b36_alphabet[number]

    while number != 0:
        number, i = divmod(number, len(_b36_alphabet))
        base36 = _b36_alphabet[i] + base36

    return base36


def base36decode(number):
    return int(number, 36)


def make_permalink(model: BaseModel) -> str:
    # Avoiding circular imports.
    from data.comment_data import CommentModel
    from data.post_data import PostModel
    from data.user_data import UserModel

    base_url = "https://reddit.com/"

    if isinstance(model, CommentModel):
        return base_url + f"comments/{base36encode(model.post_id)}/-/{model.id36}"

    if isinstance(model, PostModel):
        return base_url + f"comments/{model.id36}"

    if isinstance(model, UserModel):
        return base_url + f"/user/{model.username}"

    raise TypeError(f"Unknown model {model.__class__}")


def initialize_reddit():
    global reddit, subreddit
    reddit = praw.Reddit(**config_loader.REDDIT["auth"])
    subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])


if reddit is None:
    initialize_reddit()
