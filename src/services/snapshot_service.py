from datetime import datetime, timezone
from typing import Union, Optional

from praw.models.reddit.submission import Submission
from praw import Reddit

from data.snapshot_data import SnapshotData, SnapshotModel, SnapshotFrontpageModel
from services import user_service, post_service
from utils.logger import logger



_snapshot_data = SnapshotData()


def add_snapshot(current_datetime: datetime, subscribers: int) -> SnapshotModel:
    """Adds a new snapshot to the database."""

    snapshot = SnapshotModel()
    snapshot.date = current_datetime.date()
    snapshot.hour = current_datetime.hour
    snapshot.subscribers = subscribers

    saved_snapshot = _snapshot_data.insert(snapshot)
    return saved_snapshot


def add_frontpage_post(reddit_post: Submission, snapshot: SnapshotModel, rank: int) -> SnapshotFrontpageModel:
    """Adds the specified post ranking for the snapshot. Also inserts the post itself if necessary."""

    post_id = reddit_post.id
    post = post_service.get_post_by_id(post_id)

    # Add or update post as necessary.
    if not post:
        logger.debug(f"Saving post {post_id}")
        post = post_service.add_post(reddit_post)
    else:
        post = post_service.update_post(post, reddit_post)

    frontpage_model = SnapshotFrontpageModel()
    frontpage_model.post_id = post.id
    frontpage_model.snapshot_id = snapshot.id
    frontpage_model.rank = rank
    frontpage_model.score = reddit_post.score

    saved_frontpage_model = _snapshot_data.insert(frontpage_model)
    return saved_frontpage_model


def get_frontpage_rank(post_id: int, target_datetime: datetime) -> Optional[int]:
    """Gets the ranking of the post at the specified target_datetime, None if not ranked at that time."""

    return _snapshot_data.get_rank_by_datetime(post_id, target_datetime)


def get_post_hours_ranked(post_id: int, min_rank: int = 25) -> int:
    """Gets the number of hours a post has been ranked."""

    return _snapshot_data.get_post_hours_ranked(post_id, min_rank)
