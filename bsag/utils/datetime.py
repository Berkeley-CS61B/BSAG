from datetime import datetime, timedelta

from pytz import timezone

ZERO_TD = timedelta()


def format_datetime(
    dt: datetime,
    time_zone: str = "UTC",
    time_format: str = "%A %B %d %Y, %H:%M:%S %Z",
) -> str:
    return dt.astimezone(timezone(time_zone)).strftime(time_format)
