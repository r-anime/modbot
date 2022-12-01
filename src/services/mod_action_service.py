from datetime import datetime, timezone
from typing import Optional

from praw.models.mod_action import ModAction

from constants import mod_constants
from data.post_data import PostModel
from data.mod_action_data import ModActionData, ModActionModel
from utils.reddit import base36decode

_mod_action_data = ModActionData()


def get_mod_action_by_id(mod_action_id: str) -> Optional[ModActionModel]:
    """
    Gets a single mod action from the database. mod_action_id is the UUID without the ModAction_ prefix.
    """

    return _mod_action_data.get_mod_action_by_id(mod_action_id)


def get_most_recent_approve_remove_by_post(post: PostModel) -> Optional[ModActionModel]:
    """
    Gets the most recent approve/remove/spam mod action taken against a post.
    :param post: PostModel
    :return: ModActionModel or None
    """

    action_list = [
        mod_constants.ModActionEnum.approve_post.value,
        mod_constants.ModActionEnum.remove_post.value,
        mod_constants.ModActionEnum.spam_post.value,
    ]
    action_list = _mod_action_data.get_mod_actions_targeting_post(post.id, action_list, 1, "DESC")
    if action_list:
        return action_list[0]
    return None


def get_mod_actions_targeting_username(
    username: str, actions: list[str] = None, start_date: str = None, end_date: str = None
) -> list[ModActionModel]:
    """
    Gets all mod actions against a user, optionally only specific actions within a specified time frame.
    """

    return _mod_action_data.get_mod_actions_targeting_username(username, actions, start_date, end_date)


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


def count_mod_actions(
    action: str,
    start_time: str,
    end_time: str,
    distinct: bool = True,
    details: str = "",
    description: str = "",
    mod_accounts_list: list = None,
    exclude_mod_accounts_list: list = None,
) -> int:
    """
    Count total numbers of the specified action for the time period.

    :param action: mod action to count
    :param start_time: count after this datetime
    :param end_time: count before this datetime
    :param distinct: whether to group all actions on a single target or not
    :param details: search on details field
    :param description: search on description field
    :param mod_accounts_list: mod accounts to count actions for, defaults to all if None
    :param exclude_mod_accounts_list: mod accounts to ignore when counting
    :return: number of actions taken
    """

    if not distinct:
        count = _mod_action_data.count_mod_actions(
            action,
            start_time,
            end_time,
            details=details,
            description=description,
            include_mods=mod_accounts_list,
            exclude_mods=exclude_mod_accounts_list,
        )
        return count

    if action in mod_constants.MOD_ACTIONS_USERS:
        distinct_target = "user"
    elif action in mod_constants.MOD_ACTIONS_POSTS:
        distinct_target = "post"
    elif action in mod_constants.MOD_ACTIONS_COMMENTS:
        distinct_target = "comment"
    else:
        raise ValueError(f"{action} is not recognized as an action type that can be counted as distinct.")

    count = _mod_action_data.count_mod_actions(
        action,
        start_time,
        end_time,
        distinct_target=distinct_target,
        details=details,
        description=description,
        include_mods=mod_accounts_list,
        exclude_mods=exclude_mod_accounts_list,
    )
    return count
