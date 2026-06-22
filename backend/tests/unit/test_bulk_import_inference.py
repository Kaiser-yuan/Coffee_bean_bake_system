"""Tests for the bulk-import time inference logic."""
from datetime import timezone

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
    assert dt.year == 2026 and dt.month == 5 and dt.day == 30
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
    assert dt.year == 2026 and dt.month == 5 and dt.day == 29
    assert dt.hour == 14 and dt.minute == 30
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
    assert dt is not None and dt.year == 2026


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
