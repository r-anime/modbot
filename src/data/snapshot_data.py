import datetime
from typing import Optional

from sqlalchemy.sql import text

from data.base_data import BaseModel, BaseData


class SnapshotModel(BaseModel):
    _table = "snapshots"
    _pk_field = "id"
    _columns = [
        "id",
        "creation_time",
        "date",
        "hour",
        "subscribers"
    ]

    def set_date_and_hour(self, start_datetime: datetime.datetime):
        """Sets the date and hour on the model, rounding down from the provided start_datetime.
        Assumes UTC if no timezone provided."""

        if start_datetime.tzname() is None:
            copy_datetime = start_datetime.replace(tzinfo=datetime.timezone.utc)
        else:
            copy_datetime = start_datetime.astimezone(datetime.timezone.utc)

        self.date = copy_datetime.date()
        self.hour = copy_datetime.hour


class SnapshotFrontpageModel(BaseModel):
    _table = "snapshot_frontpage"
    _pk_field = "snapshot_id"
    _columns = [
        "post_id",
        "snapshot_id",
        "rank",
        "score"
    ]


class SnapshotData(BaseData):

    def get_snapshot_by_datetime(self, target_datetime: datetime.datetime) -> Optional[SnapshotModel]:
        """Gets the snapshot for the date and hour, rounding down from the provided start_datetime.
        Assumes UTC if no timezone provided."""

        if target_datetime.tzname() is None:
            copy_datetime = target_datetime.replace(tzinfo=datetime.timezone.utc)
        else:
            copy_datetime = target_datetime.astimezone(datetime.timezone.utc)

        date = copy_datetime.date().isoformat()
        hour = copy_datetime.hour

        sql = text(
            """
        SELECT * FROM snapshots
        WHERE date = :date AND hour = :hour;
        """
        )

        result_rows = self.execute(sql, date=date, hour=hour)
        if not result_rows:
            return None

        return SnapshotModel(result_rows[0])

    def get_rank_by_datetime(self, post_id: int, target_datetime: datetime.datetime, min_rank: int) -> Optional[int]:
        """Gets ranking of the specified post at the time provided, None if not ranked then.
        Ignores rankings below min_rank. Assumes UTC if no timezone provided, rounds down to the hour."""

        if target_datetime.tzname() is None:
            copy_datetime = target_datetime.replace(tzinfo=datetime.timezone.utc)
        else:
            copy_datetime = target_datetime.astimezone(datetime.timezone.utc)

        date = copy_datetime.date().isoformat()
        hour = copy_datetime.hour

        sql = text(
            """
        SELECT * FROM snapshot_frontpage JOIN snapshots s on snapshot_frontpage.snapshot_id = s.id
        WHERE s.date = :date AND s.hour = :hour 
        AND snapshot_frontpage.post_id = :post_id 
        AND snapshot_frontpage.rank <= :min_rank;
        """
        )

        result_rows = self.execute(sql, date=date, hour=hour, post_id=post_id, min_rank=min_rank)
        if not result_rows:
            return None

        frontpage_model = SnapshotFrontpageModel(result_rows[0])
        return frontpage_model.rank

    def get_post_hours_ranked(self, post_id: int, min_rank: int = 25) -> int:
        """Gets the number of hours a post has been ranked."""

        sql = text(
            """
        SELECT count(*) as total_hours FROM snapshot_frontpage WHERE post_id = :post_id AND rank <= :min_rank;
        """
        )

        result_rows = self.execute(sql, post_id=post_id, min_rank=min_rank)
        hours_ranked = result_rows[0]["total_hours"]
        return hours_ranked
