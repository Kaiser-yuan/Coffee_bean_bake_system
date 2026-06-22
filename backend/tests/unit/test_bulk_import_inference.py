"""Tests for the bulk-import time inference logic — timezone-aware edition.

All local-time inputs (CSV CookDate, filename dates, manual/user-provided times)
are now interpreted in the app timezone (Asia/Shanghai) then stored as UTC.
File.lastModified epoch‑ms is absolute and stays in UTC.
"""
from datetime import timezone, date, time

from app.core.timezone_utils import get_app_zone
from app.services.bulk_import import (
    infer_roasted_at,
    is_duplicate_file_hash,
    parse_client_last_modified,
)
from app.parsers.kaleido_m1 import KaleidoParsedData, KaleidoParameters


class _FakeParsed:
    """Minimal stand-in for KaleidoParsedData used by infer_roasted_at."""

    def __init__(self, cooked_at: str | None = None):
        self.parameters = KaleidoParameters(cooked_at=cooked_at)


# Helper: convert a UTC datetime to app-local for assertions
def _local(dt):
    return dt.astimezone(get_app_zone())


def test_filename_strategy_parses_yymmdd():
    dt, source = infer_roasted_at(
        filename="260530_9.csv",
        parsed=_FakeParsed(),
        client_last_modified=None,
        default_roast_date=None,
        first_roast_time=None,
        order=1,
        strategy="filename",
    )
    assert dt is not None
    # Stored in UTC. Check app-local date is correct.
    local = _local(dt)
    assert local.year == 2026 and local.month == 5 and local.day == 30
    assert source == "filename"


def test_csv_content_strategy_uses_cooked_at():
    dt, source = infer_roasted_at(
        filename="260530_9.csv",
        parsed=_FakeParsed(cooked_at="2026-05-29 14:30:00"),
        client_last_modified=None,
        default_roast_date=None,
        first_roast_time=None,
        order=1,
        strategy="csv_content",
    )
    assert dt is not None
    # CookDate is local — check in app timezone
    local = _local(dt)
    assert local.year == 2026 and local.month == 5 and local.day == 29
    assert local.hour == 14 and local.minute == 30
    assert source == "csv_content"


def test_upload_order_strategy_spacing():
    dt1, s1 = infer_roasted_at(
        filename="x.csv", parsed=_FakeParsed(), client_last_modified=None,
        default_roast_date="2026-05-30", first_roast_time="09:30", order=1,
        strategy="upload_order",
    )
    dt2, _ = infer_roasted_at(
        filename="y.csv", parsed=_FakeParsed(), client_last_modified=None,
        default_roast_date="2026-05-30", first_roast_time="09:30", order=2,
        strategy="upload_order",
    )
    assert s1 == "upload_order"
    assert dt1 is not None and dt2 is not None
    # ROAST_SPACING_MINUTES = 45
    diff_minutes = (dt2 - dt1).total_seconds() / 60
    assert diff_minutes == 45


def test_auto_priority_csv_content_over_filename():
    dt, source = infer_roasted_at(
        filename="260530_9.csv",
        parsed=_FakeParsed(cooked_at="2026-05-29 14:30:00"),
        client_last_modified=None,
        default_roast_date=None,
        first_roast_time=None,
        order=1,
        strategy=None,  # auto
    )
    assert source == "csv_content"


def test_auto_falls_back_to_filename_when_no_content():
    dt, source = infer_roasted_at(
        filename="260530_9.csv",
        parsed=_FakeParsed(cooked_at=None),
        client_last_modified=None,
        default_roast_date=None,
        first_roast_time=None,
        order=1,
        strategy=None,
    )
    assert source == "filename"
    assert dt is not None
    local = _local(dt)
    assert local.year == 2026


def test_manual_strategy_needs_date():
    dt, source = infer_roasted_at(
        filename="x.csv", parsed=_FakeParsed(), client_last_modified=None,
        default_roast_date=None, first_roast_time="09:30", order=1,
        strategy="manual",
    )
    # No default_roast_date -> manual cannot resolve
    assert dt is None


def test_client_last_modified_epoch_millis():
    dt = parse_client_last_modified("1781971200000")
    assert dt is not None
    assert dt.tzinfo == timezone.utc


def test_client_last_modified_rejects_invalid_value():
    assert parse_client_last_modified("not-a-number") is None


def test_duplicate_hash_detects_existing_and_same_upload():
    seen: set[str] = set()
    existing = {"already-imported"}
    assert is_duplicate_file_hash("already-imported", existing, seen) is True
    assert is_duplicate_file_hash("new-file", existing, seen) is False
    assert is_duplicate_file_hash("new-file", existing, seen) is True


def test_naive_csv_and_manual_share_same_offset():
    """CookDate '2026-06-21 09:30' and manual 09:30 should both map to the
    same UTC instant — no 8-hour divergence between sources."""
    from app.services.bulk_import import _parse_csv_cooked_at
    from app.core.timezone_utils import combine_naive

    cooked = _parse_csv_cooked_at("2026-06-21 09:30:00")
    manual = combine_naive(date(2026, 6, 21), time(9, 30))

    assert cooked is not None
    assert cooked == manual


def test_last_modified_is_absolute():
    """File.lastModified is epoch‑ms — immune to timezone reinterpretation."""
    # 2025-01-15 03:30:00 UTC in epoch millis
    epoch_ms = str(int(
        __import__('datetime').datetime(2025, 1, 15, 3, 30, 0, tzinfo=timezone.utc).timestamp() * 1000
    ))
    dt = parse_client_last_modified(epoch_ms)
    assert dt is not None
    assert dt.year == 2025
    # Hour in UTC is preserved regardless of app timezone
    assert dt.hour == 3


def test_same_day_two_pots_get_different_times():
    """No CookDate, same-day filenames 260621_1.csv & 260621_2.csv —
    upload_order + order spacing must yield different UTC timestamps."""
    dt1, s1 = infer_roasted_at(
        filename="260621_1.csv",
        parsed=_FakeParsed(cooked_at=None),
        client_last_modified=None,
        default_roast_date="2026-06-21",
        first_roast_time="09:30",
        order=1,
        strategy="upload_order",
    )
    dt2, s2 = infer_roasted_at(
        filename="260621_2.csv",
        parsed=_FakeParsed(cooked_at=None),
        client_last_modified=None,
        default_roast_date="2026-06-21",
        first_roast_time="09:30",
        order=2,
        strategy="upload_order",
    )
    assert dt1 is not None and dt2 is not None
    assert s1 == "upload_order"
    diff_minutes = (dt2 - dt1).total_seconds() / 60
    assert diff_minutes == 45
    # Both should be on the same date in app timezone
    app_zone = get_app_zone()
    assert dt1.astimezone(app_zone).date() == date(2026, 6, 21)
    assert dt2.astimezone(app_zone).date() == date(2026, 6, 21)
