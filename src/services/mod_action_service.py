from datetime import datetime, timezone
from typing import Union, Optional

from praw.models.mod_action import ModAction

from data.mod_action_data import ModActionData, ModActionModel
from utils.reddit import base36decode

_mod_action_data = ModActionData()


def get_mod_action_by_id(mod_action_id: str) -> Optional[ModActionModel]:
    """
    Gets a single mod action from the database. mod_action_id is the UUID without the ModAction_ prefix.
    """

    return _mod_action_data.get_mod_action_by_id(mod_action_id)


def add_mod_action(reddit_mod_action: ModAction) -> ModActionModel:
    """
    Parses some basic information for a mod action and adds it to the database.
    Assumes acting mod and target user/post/comment are already created if necessary,
    may raise an error on database integrity (foreign key relationship) if not.
    """

    mod_action = ModActionModel()

    mod_action.id = reddit_mod_action.id.replace("ModAction_", "")
    mod_action.mod = reddit_mod_action.mod.name
    mod_action.action = reddit_mod_action.action
    mod_action.details = reddit_mod_action.details
    mod_action.description = reddit_mod_action.description
    mod_action.created_time = datetime.fromtimestamp(reddit_mod_action.created_utc, tz=timezone.utc)

    if reddit_mod_action.target_author:
        mod_action.target_user = reddit_mod_action.target_author

    # If the target is either a post or comment, target_permalink will be set and have the post id in it,
    # e.g. /r/anime/comments/kp906e/meta_thread_month_of_january_03_2021/ghvmptk/
    # The extra "/comments/" check looks superfluous for now but is a safety measure.
    if reddit_mod_action.target_permalink and "/comments/" in reddit_mod_action.target_permalink:
        post_id = reddit_mod_action.target_permalink.split("/")[4]
        mod_action.target_post_id = base36decode(post_id)

    # Only need this section if comments are the target, posts should be handled by permalink section.
    if reddit_mod_action.target_fullname and reddit_mod_action.target_fullname.startswith("t1_"):
        comment_id = reddit_mod_action.target_fullname.replace("t1_", "")
        mod_action.target_comment_id = base36decode(comment_id)

    new_mod_action = _mod_action_data.insert(mod_action, error_on_conflict=False)
    return new_mod_action
