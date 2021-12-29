import datetime
from typing import Optional

from sqlalchemy.sql import text

from data.base_data import BaseModel, BaseData


class TrafficMonthlyModel(BaseModel):
    """
    Note: date is the first day of the month.
    """

    _table = "traffic_monthly"
    _pk_field = "id"
    _columns = ["id", "date", "unique_pageviews", "total_pageviews"]


class TrafficDailyModel(BaseModel):
    _table = "traffic_daily"
    _pk_field = "id"
    _columns = ["id", "date", "unique_pageviews", "total_pageviews", "net_subscribers"]


class TrafficData(BaseData):
    def get_monthly_traffic_by_range(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> list[TrafficMonthlyModel]:
        """Gets the monthly traffic between the dates specified (inclusive)."""

        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()

        sql = text(
            """
        SELECT * FROM traffic_monthly
        WHERE date >= :start_date and date <= :end_date;
        """
        )

        result_rows = self.execute(sql, start_date=start_date_str, end_date=end_date_str)
        if not result_rows:
            return []

        return [TrafficMonthlyModel(row) for row in result_rows]

    def get_daily_traffic_by_range(self, start_date: datetime.date, end_date: datetime.date) -> list[TrafficDailyModel]:
        """Gets the daily traffic between the dates specified (inclusive)."""

        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()

        sql = text(
            """
        SELECT * FROM traffic_daily
        WHERE date >= :start_date and date <= :end_date;
        """
        )

        result_rows = self.execute(sql, start_date=start_date_str, end_date=end_date_str)
        if not result_rows:
            return []

        return [TrafficDailyModel(row) for row in result_rows]

    def get_monthly_traffic_by_datetime(self, target_date: datetime.date) -> Optional[TrafficMonthlyModel]:
        """Gets the monthly traffic for the date, rounding down from the provided target_date
        to the start of the month."""

        target_date_str = target_date.replace(day=1).isoformat()

        sql = text(
            """
        SELECT * FROM traffic_monthly
        WHERE date = :date;
        """
        )

        result_rows = self.execute(sql, date=target_date_str)
        if not result_rows:
            return None

        return TrafficMonthlyModel(result_rows[0])

    def get_daily_traffic_by_datetime(self, target_date: datetime.date) -> Optional[TrafficDailyModel]:
        """Gets the daily traffic for the date."""

        target_date_str = target_date.isoformat()

        sql = text(
            """
        SELECT * FROM traffic_daily
        WHERE date = :date;
        """
        )

        result_rows = self.execute(sql, date=target_date_str)
        if not result_rows:
            return None

        return TrafficDailyModel(result_rows[0])
