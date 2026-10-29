from datetime import datetime, timedelta, timezone

from genesys_cloud_ta.time_utils import exceed_range


def validate_date(start_date: str):
    fmt_str = "%Y-%m-%d"
    if start_date is not None and exceed_range(
        start_date, datetime.now(timezone.utc).strftime(fmt_str), fmt=fmt_str
    ):
        raise ValueError(
            f"Invalid start date {start_date}. Start date for data collection cannot exceed 31 days from now."
        )
