import datetime

from data.traffic_data import TrafficData, TrafficMonthlyModel, TrafficDailyModel


_traffic_data = TrafficData()


def add_daily_traffic(
    target_date: datetime.date, unique_pageviews: int, total_pageviews: int, subscribers: int
) -> TrafficDailyModel:
    """Adds a new row of daily traffic data to the database."""

    traffic = TrafficDailyModel()
    traffic.date = target_date
    traffic.unique_pageviews = unique_pageviews
    traffic.total_pageviews = total_pageviews
    traffic.subscribers = subscribers

    saved_traffic = _traffic_data.insert(traffic)
    return saved_traffic


def add_monthly_traffic(target_date: datetime.date, unique_pageviews: int, total_pageviews: int) -> TrafficMonthlyModel:
    """Adds a new row of monthly traffic data to the database."""

    traffic = TrafficMonthlyModel()
    traffic.date = target_date
    traffic.unique_pageviews = unique_pageviews
    traffic.total_pageviews = total_pageviews

    saved_traffic = _traffic_data.insert(traffic)
    return saved_traffic


def update_monthly_traffic(traffic_data: list[list[int]]):
    """
    Expected format for each traffic_data list item should match the "month" value of /about/traffic endpoint:
        [timestamp (start of month), unique_pageviews, total_pageviews]
    """

    oldest_date = datetime.date.fromtimestamp(traffic_data[-1][0])
    today = datetime.datetime.now(datetime.timezone.utc).date()
    current_traffic_rows = _traffic_data.get_monthly_traffic_by_range(oldest_date, today)
    current_traffic_by_date = {model.date: model for model in current_traffic_rows}

    for row in traffic_data:
        date = datetime.date.fromtimestamp(row[0])
        unique_pageviews, total_pageviews = row[1:3]

        # New entry, date not currently in database.
        if date not in current_traffic_by_date:
            add_monthly_traffic(date, unique_pageviews, total_pageviews)
            continue

        # Otherwise see if the data needs updating for some reason.
        current_traffic = current_traffic_by_date[date]
        if unique_pageviews != 0:
            current_traffic.unique_pageviews = unique_pageviews
        if total_pageviews != 0:
            current_traffic.total_pageviews = total_pageviews
        _traffic_data.update(current_traffic)


def update_daily_traffic(traffic_data: list[list[int]]):
    """
    Expected format for each traffic_data list item should match "day" value of the /about/traffic endpoint:
        [timestamp (start of day), unique_pageviews, total_pageviews, subscribers]
    """

    oldest_date = datetime.date.fromtimestamp(traffic_data[-1][0])
    today = datetime.datetime.now(datetime.timezone.utc).date()
    current_traffic_rows = _traffic_data.get_daily_traffic_by_range(oldest_date, today)
    current_traffic_by_date = {model.date: model for model in current_traffic_rows}

    for row in traffic_data:
        date = datetime.date.fromtimestamp(row[0])
        unique_pageviews, total_pageviews, subscribers = row[1:4]

        # New entry, date not currently in database.
        if date not in current_traffic_by_date:
            add_daily_traffic(date, unique_pageviews, total_pageviews, subscribers)
            continue

        # Otherwise see if the data needs updating for some reason.
        current_traffic = current_traffic_by_date[date]
        if unique_pageviews != 0:
            current_traffic.unique_pageviews = unique_pageviews
        if total_pageviews != 0:
            current_traffic.total_pageviews = total_pageviews
        current_traffic.subscribers = subscribers
        _traffic_data.update(current_traffic)
