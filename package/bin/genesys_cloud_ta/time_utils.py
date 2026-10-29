from __future__ import annotations

from datetime import datetime, timedelta, timezone

from genesys_cloud_ta.constants import DEFAULT_HISTORICAL_DAYS


def get_start_date(
    curr_checkpoint: float, now: datetime, interval_seconds: int | None = None
) -> datetime:
    """Get start date: either from checkpoint or from a given point in the past.
    :param curr_checkpoint: Last checkpoint saved in the KVStore.
    :param now: Current datetime.
    :param interval_seconds: Seconds back from now.
    :return: The date to fetch data from.
    """
    if curr_checkpoint:
        return datetime.fromtimestamp(curr_checkpoint, tz=timezone.utc)
    if interval_seconds:
        return now - timedelta(seconds=interval_seconds)
    return now - timedelta(days=DEFAULT_HISTORICAL_DAYS)


def get_interval_str(start_time: datetime, end_time: datetime) -> str:
    """Format interval as per API specs."""
    return f"\
        {start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z/\
        {end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z"


def to_epoch(value: float | str) -> float:
    """Cast string datetime value into epoch."""
    if isinstance(value, float):
        return value

    if isinstance(value, str):
        # Supports strings like: "2026-10-29T12:34:56.123Z"
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc
        )
        return dt.timestamp()

    raise TypeError(f"Expected float or str, got {type(value).__name__}")


def exceed_range(
    start: str, end: str, max_days: int = 31, fmt: str = "%Y-%m-%dT%H:%M:%SZ"
) -> bool:
    """Verify interval range does not exceed threshold.
    :param start: Interval start string reference.
    :param end: Interval end string reference.
    :param max_days: Threshold in number of days.
    :param fmt: Datetime string format.
    :return: True if the range between start and end exceeds max_days.
    """
    start_dt = datetime.strptime(start, fmt)  # noqa: DTZ007
    end_dt = datetime.strptime(end, fmt)  # noqa: DTZ007

    if end_dt <= start_dt:
        raise ValueError(
            f"Invalid start date: {start} cannot be later or equal to {end}"
        )

    return (end_dt - start_dt) >= timedelta(days=max_days)
