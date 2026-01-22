from datetime import datetime, timezone
from typing import Optional, Union

from praw.models.reddit.redditor import Redditor
from prawcore.exceptions import NotFound

from data.user_data import UserData, UserModel

_user_data = UserData()


def get_user(username: Union[Redditor, str]) -> Optional[UserModel]:
    """Gets a single user from the database, None if they don't exist."""

    if isinstance(username, str):
        return _user_data.get_user(username)
    elif isinstance(username, Redditor):
        return _user_data.get_user(username.name)


def add_user(reddit_user: Union[Redditor, str]) -> UserModel:
    """Parses some basic information for the user and adds them to the database."""

    user = UserModel()
    # Worst case we just have their username, insert that anyway.
    if isinstance(reddit_user, str):
        user.username = reddit_user
        return _user_data.insert(user, error_on_conflict=False)

    user.username = reddit_user.name

    # If the user's been suspended, the flag will be set.
    # If they're deleted, it'll raise an exception.
    # Everyone else won't have the attribute set, so default it to false.
    try:
        user.suspended = getattr(reddit_user, "is_suspended", False)
    except NotFound:
        # In this case, the user's been deleted.
        user.deleted = True
        return _user_data.insert(user, error_on_conflict=False)

    # If the user's suspended, we can't get any other information about them.
    if user.suspended:
        return _user_data.insert(user, error_on_conflict=False)

    user.created_time = datetime.fromtimestamp(reddit_user.created_utc, tz=timezone.utc)

    return _user_data.insert(user, error_on_conflict=False)


def update_user(existing_user: UserModel, reddit_user: Redditor) -> UserModel:
    """
    For the provided user, update fields to the current state and save to the database if necessary.
    For the moment, the only things that can change overall are whether the user is deleted or suspended.
    """

    # If the user's been suspended, the flag will be set.
    # If they're deleted, it'll raise an exception.
    # Everyone else won't have the attribute set, so default it to false.
    try:
        existing_user.suspended = getattr(reddit_user, "is_suspended", False)
    except NotFound:
        # In this case, the user's been deleted.
        existing_user.deleted = True

    updated_user = _user_data.update(existing_user)
    return updated_user


def get_moderators() -> list[UserModel]:
    """Get the list of currently active moderators."""

    return _user_data.get_moderators()
