from datetime import date, datetime, timezone
from typing import Union, Optional

from praw.models.reddit.comment import Comment
from praw import Reddit

from data.comment_data import CommentData, CommentModel
from services import user_service, post_service
from utils.reddit import base36decode

_comment_data = CommentData()


def get_comment_by_id(comment_id: Union[str, int]) -> Optional[CommentModel]:
    """
    Gets a single comment from the database. comment_id is either base 10 (int) or base 36 (str)
    """

    if isinstance(comment_id, str):
        comment_id = base36decode(comment_id)

    return _comment_data.get_comment_by_id(comment_id)


def get_comments_by_post_id(post_id: Union[str, int]) -> list[CommentModel]:
    """
    Get all comments on the specified post. post_id is either base 10 (int) or base 36 (str)
    """

    if isinstance(post_id, str):
        post_id = base36decode(post_id)

    return _comment_data.get_comments_by_post_id(post_id)


def get_comments_by_username(username: str, start_date: str = None, end_date: str = None, exclude_cdf: bool = False) -> list[CommentModel]:
    """
    Gets all comments by a user, optionally within a specified time frame.
    """

    return _comment_data.get_comments_by_username(username, start_date, end_date, exclude_cdf)


def count_comments(start_date: date = None, end_date: date = None, exclude_authors: list = None) -> int:
    """
    Gets number of comments made in the given date range.
    """
    return _comment_data.get_comment_count(start_date, end_date, exclude_authors)


def count_comment_authors(start_date: date = None, end_date: date = None, exclude_authors: list = None) -> int:
    """
    Gets number of distinct authors making comments made in the given date range.
    """
    return _comment_data.get_comment_author_count(start_date, end_date, exclude_authors)


def add_comment(reddit_comment: Comment) -> CommentModel:
    """
    Parses some basic information for a comment and adds it to the database.
    Creates author and post if necessary.
    This also assumes its parent comment is already created, call
    add_comment_parent_tree first if necessary.
    """

    comment = _create_comment_model(reddit_comment)

    # Insert the author into the database if they don't exist yet.
    if reddit_comment.author is not None and not user_service.get_user(reddit_comment.author):
        user_service.add_user(reddit_comment.author)

    # Insert post into the database if it doesn't exist yet (and we have it available).
    if isinstance(reddit_comment, Comment) and not post_service.get_post_by_id(reddit_comment.submission.id):
        post_service.add_post(reddit_comment.submission)

    new_comment = _comment_data.insert(comment, error_on_conflict=False)
    return new_comment


def update_comment(existing_comment: CommentModel, reddit_comment: Comment) -> CommentModel:
    """
    For the provided comment, update fields to the current state and save to the database if necessary.
    """

    new_comment = _create_comment_model(reddit_comment)

    # Insert the author into the database if they don't exist yet.
    if (
        existing_comment.author is None
        and reddit_comment.author is not None
        and not user_service.get_user(reddit_comment.author)
    ):
        user_service.add_user(reddit_comment.author)

    # Fields that shouldn't be updated since they won't change.
    non_update_fields = ["author"] if existing_comment.author else []

    # If a user has deleted their post or admins took it down we don't want to overwrite the original text.
    # Removals by "anti_evil_ops" or "moderator" are fine since those don't change the body.
    if getattr(reddit_comment, "removal_reason", None) in ("legal",) or reddit_comment.author is None:
        non_update_fields.append("body")

    for field in new_comment.columns:
        if field in non_update_fields:
            continue
        if hasattr(new_comment, field):
            setattr(existing_comment, field, getattr(new_comment, field))

    updated_comment = _comment_data.update(existing_comment)
    return updated_comment


def add_comment_parent_tree(reddit: Reddit, reddit_comment: Comment):
    """
    Starting with the comment that's the *parent* of the specified comment (non-inclusive),
    recursively crawl up the tree and add all of them to the database.
    Stops when it reaches a comment that already exists in the database or upon reaching the root.
    Needs improvements for efficiency.
    """

    # Could do this with recursive calls to this function, but
    # I don't know how deep reddit comment chains are allowed to get.
    # So instead we need to keep a stack of comments so we can insert
    # them in the correct order, root first then down the chain.
    # This is necessary because the parent_id of each needs to already exist.
    comment_stack = []

    # At the start of each loop, if we're at the top comment of the tree there will be no parents to add.
    # parent_id will return a submission for top level comments, so check is_root instead.
    while not reddit_comment.parent_id.startswith("t3_"):
        parent_id = reddit_comment.parent_id[3:]
        parent_exists = get_comment_by_id(parent_id)

        # Once we reach a child where the parent already exists, we can stop adding new comments up the chain.
        if parent_exists:
            break

        # Parent now becomes the base comment, then create a model for it (but don't insert yet).
        reddit_comment = reddit.comment(id=parent_id)
        comment = _create_comment_model(reddit_comment)
        comment_stack.append(comment)

        # Insert the author into the database if they don't exist yet.
        if reddit_comment.author is not None and not user_service.get_user(reddit_comment.author.name):
            user_service.add_user(reddit_comment.author)

        # Insert post into the database if it doesn't exist yet.
        if not post_service.get_post_by_id(reddit_comment.submission.id):
            post_service.add_post(reddit_comment.submission)

    # Reverse the order that we're iterating through the stack for inserting, last->first.
    for comment in comment_stack[::-1]:
        _comment_data.insert(comment, error_on_conflict=False)


def _create_comment_model(reddit_comment: Comment) -> CommentModel:
    """
    Creates a model without inserting it into the database.
    """

    comment = CommentModel()

    comment.set_id(reddit_comment.id)
    comment.score = reddit_comment.score
    comment.created_time = datetime.fromtimestamp(reddit_comment.created_utc, tz=timezone.utc)
    comment.body = reddit_comment.body

    # PRAW vs. Pushshift differences
    if isinstance(reddit_comment, Comment):
        comment.post_id = base36decode(reddit_comment.submission.id)
        # Comments by deleted users won't have an author, same for deleted comments.
        if reddit_comment.author is not None:
            comment.author = reddit_comment.author.name

        # edited is either a timestamp or False if it hasn't been edited.
        if reddit_comment.edited:
            comment.edited = datetime.fromtimestamp(reddit_comment.edited, tz=timezone.utc)

        # distinguished is a string (usually "moderator", maybe "admin"?) or None.
        comment.distinguished = True if reddit_comment.distinguished else False

        # removed is *not* accurate if the comment has been removed by the spam filter or AutoModerator
        # so banned_by is used instead (moderator name or True for spam filter).
        comment.removed = True if getattr(reddit_comment, "banned_by", False) else False

    # Pushshift version, fewer details about current status
    else:
        comment.post_id = base36decode(reddit_comment.link_id[3:])  # fullname, strip t3_ from start
        comment.author = reddit_comment.author

    # parent_id will be post fullname if it's a top level comment, don't want to save those.
    if reddit_comment.parent_id.startswith("t1_"):
        comment.parent_id = base36decode(reddit_comment.parent_id[3:])

    # No easy way to verify that a comment is deleted, but it's unlikely that a user would make a comment
    # with a body of "[deleted]" or "[removed]" *and* delete their account afterward.
    if reddit_comment.author is None and reddit_comment.body in ("[deleted]", "[removed]"):
        comment.deleted = True

    return comment
