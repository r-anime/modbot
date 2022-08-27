import datetime
from typing import Optional

from praw.models.reddit.submission import Submission

from data.snapshot_data import SnapshotData, SnapshotModel, SnapshotFrontpageModel
from services import post_service
from utils.logger import logger


_snapshot_data = SnapshotData()


def get_snapshot_by_datetime(target_datetime: datetime.datetime) -> SnapshotModel:
    """Get the specified snapshot from the database."""

    return _snapshot_data.get_snapshot_by_datetime(target_datetime)


def add_snapshot(current_datetime: datetime.datetime, subscribers: int) -> SnapshotModel:
    """Adds a new snapshot to the database."""

    snapshot = SnapshotModel()
    snapshot.date = current_datetime.date()
    snapshot.hour = current_datetime.hour
    snapshot.subscribers = subscribers

    saved_snapshot = _snapshot_data.insert(snapshot)
    return saved_snapshot


def update_hourly_traffic(traffic_data: list[list[int]]):
    """
    Expected format for each traffic_data list item should match the "hour" value of /about/traffic endpoint:
        [timestamp (start of hour), unique_pageviews, total_pageviews]
    """

    oldest_date = datetime.date.fromtimestamp(traffic_data[-1][0])
    today = datetime.datetime.now(datetime.timezone.utc).date()
    current_snapshot_rows = _snapshot_data.get_snapshots_by_date_range(oldest_date, today)
    current_snapshots_by_hour = {model.get_datetime(): model for model in current_snapshot_rows}

    for row in traffic_data:
        record_datetime = datetime.datetime.fromtimestamp(row[0], tz=datetime.timezone.utc)
        unique_pageviews, total_pageviews = row[1:3]

        # If, *somehow*, this date/hour doesn't exist in the database, skip for now (no subscriber count available).
        if record_datetime not in current_snapshots_by_hour:
            continue

        # Otherwise see if the data needs updating. Reddit's inconsistent with when they add data so...
        current_snapshot = current_snapshots_by_hour[record_datetime]
        if unique_pageviews != 0:
            current_snapshot.unique_pageviews = unique_pageviews
        if total_pageviews != 0:
            current_snapshot.total_pageviews = total_pageviews
        _snapshot_data.update(current_snapshot)


def add_frontpage_post(reddit_post: Submission, snapshot: SnapshotModel, rank: int) -> SnapshotFrontpageModel:
    """Adds the specified post ranking for the snapshot. Also inserts the post itself if necessary."""

    post_id = reddit_post.id
    post = post_service.get_post_by_id(post_id)

    # Add or update post as necessary.
    if not post:
        logger.debug(f"Saving post {post_id}")
        post = await post_service.add_post(reddit_post)
    else:
        post = await post_service.update_post(post, reddit_post)

    frontpage_model = SnapshotFrontpageModel()
    frontpage_model.post_id = post.id
    frontpage_model.snapshot_id = snapshot.id
    frontpage_model.rank = rank
    frontpage_model.score = reddit_post.score

    saved_frontpage_model = _snapshot_data.insert(frontpage_model)
    return saved_frontpage_model


def get_frontpage_rank(post_id: int, target_datetime: datetime.datetime, min_rank: int = 25) -> Optional[int]:
    """Gets the ranking of the post at the specified target_datetime, None if not ranked at that time.
    Will ignore anything below min_rank."""

    return _snapshot_data.get_rank_by_datetime(post_id, target_datetime, min_rank)


def get_post_hours_ranked(post_id: int, min_rank: int = 25) -> int:
    """Gets the number of hours a post has been ranked."""

    return _snapshot_data.get_post_hours_ranked(post_id, min_rank)
