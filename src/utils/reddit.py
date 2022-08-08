"""Utilities regarding Reddit posts/users/etc"""

import copy
import typing

import mintotp
import praw

if typing.TYPE_CHECKING:
    from data.base_data import BaseModel


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


def make_permalink(model: "BaseModel") -> str:
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


def get_reddit_instance(config_dict: dict):
    """
    Initialize a reddit instance and return it.

    :param config_dict: dict containing necessary values for authenticating
    :return: reddit instance
    """

    auth_dict = copy.copy(config_dict)
    password = config_dict["password"]
    totp_secret = config_dict.get("totp_secret")

    if totp_secret:
        auth_dict["password"] = f"{password}:{mintotp.totp(totp_secret)}"

    reddit_instance = praw.Reddit(**auth_dict)
    return reddit_instance
