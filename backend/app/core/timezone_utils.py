"""
Timezone utilities — ensures naive datetimes from CSVs, filenames, and forms
are interpreted in the application timezone then stored as UTC.

Design convention:
- All database columns are TIMESTAMPTZ (stores UTC).
- All service-layer inputs are naive datetimes assumed to be in
  settings.app_timezone.
- The HTTP layer receives ISO 8601 strings (with or without offset) and
  converts them to UTC before passing them to services.
- Frontend displays always render in the browser's local timezone.
"""

import zoneinfo
from datetime import datetime, timezone, date, time, timedelta


def get_app_zone() -> zoneinfo.ZoneInfo:
    """Return the application's configured timezone."""
    from ..core.config import settings
    return zoneinfo.ZoneInfo(settings.app_timezone)


def naive_to_utc(dt: datetime) -> datetime:
    """Convert a timezone-naive datetime to UTC via the app timezone.

    If dt is already timezone-aware, it is converted to UTC directly
    (no reinterpretation).
    """
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc)
    app_zone = get_app_zone()
    return dt.replace(tzinfo=app_zone).astimezone(timezone.utc)


def utc_to_naive(dt: datetime) -> datetime:
    """Convert a UTC datetime to the app timezone, then drop the tzinfo.

    Useful for display/JSON serialisation while keeping the local-wall-clock
    representation.
    """
    if dt.tzinfo is None:
        return dt
    app_zone = get_app_zone()
    return dt.astimezone(app_zone).replace(tzinfo=None)


def now_utc() -> datetime:
    """Current time in UTC (alias for datetime.now(timezone.utc))."""
    return datetime.now(timezone.utc)


def combine_naive(d: date, t: time) -> datetime:
    """Combine a date and time, interpret in the app timezone, return UTC."""
    app_zone = get_app_zone()
    naive = datetime.combine(d, t)
    return naive.replace(tzinfo=app_zone).astimezone(timezone.utc)
