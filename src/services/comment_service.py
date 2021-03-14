from datetime import datetime, timezone
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


def add_comment(reddit_comment: Comment) -> CommentModel:
    """
    Parses some basic information for a comment and adds it to the database.
    Creates author and post if necessary.
    This also assumes its parent comment is already created, call
    add_comment_parent_tree first if necessary.
    """

    comment = _create_comment_model(reddit_comment)

    # Insert the author into the database if they don't exist yet.
    if reddit_comment.author is not None and not user_service.get_user(reddit_comment.author.name):
        user_service.add_user(reddit_comment.author)

    # Insert post into the database if it doesn't exist yet.
    if not post_service.get_post_by_id(reddit_comment.submission.id):
        post_service.add_post(reddit_comment.submission)

    new_comment = _comment_data.insert(comment, error_on_conflict=False)
    return new_comment


def update_comment(existing_comment: CommentModel, reddit_comment: Comment) -> CommentModel:
    """
    For the provided comment, update fields to the current state and save to the database if necessary.
    """

    new_comment = _create_comment_model(reddit_comment)
    for field in new_comment.columns:
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
    while not reddit_comment.is_root:
        parent_id = reddit_comment.parent_id.split("t1_")[1]
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
    comment.post_id = base36decode(reddit_comment.submission.id)

    if not reddit_comment.is_root:
        comment.parent_id = base36decode(reddit_comment.parent_id.split("t1_")[1])

    # Comments by deleted users won't have an author, same for deleted comments.
    if reddit_comment.author is not None:
        comment.author = reddit_comment.author.name

    # edited is either a timestamp or False if it hasn't been edited.
    if reddit_comment.edited:
        comment.edited = datetime.fromtimestamp(reddit_comment.edited, tz=timezone.utc)

    # distinguished is a string (usually "moderator", maybe "admin"?) or None.
    comment.distinguished = True if reddit_comment.distinguished else False

    # No easy way to verify that a comment is deleted, but it's unlikely that a user would make a comment
    # with a body of "[deleted]" or "[removed]" *and* delete their account afterward.
    if reddit_comment.author is None and reddit_comment.body in ("[deleted]", "[removed]"):
        comment.deleted = True

    # Unlike with posts, removed is still true if the post has been removed and deleted.
    comment.removed = True if reddit_comment.removed else False

    return comment
