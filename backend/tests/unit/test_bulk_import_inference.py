"""Tests for the bulk-import time inference logic — timezone-aware edition.

Date and time are resolved independently then combined. Local-time inputs
(CSV CookDate, filename dates, manual/user-provided times) are interpreted in
the app timezone (Asia/Shanghai) then stored as UTC. File.lastModified epoch‑ms
is absolute and stays in UTC. When a filename carries a pot-order suffix
(``_2``), that order drives the time spacing so out-of-order uploads still
resolve ``_1`` < ``_2``.
"""
from datetime import timezone, date, time

from app.core.timezone_utils import get_app_zone
from app.services.bulk_import import (
    infer_roasted_at,
    is_duplicate_file_hash,
    parse_client_last_modified,
    parse_filename_pot_order,
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
    res = infer_roasted_at(
        filename="260530_9.csv",
        parsed=_FakeParsed(),
        client_last_modified=None,
        default_roast_date=None,
        first_roast_time=None,
        order=1,
        strategy="filename",
    )
    assert res.roasted_at is not None
    # Stored in UTC. Check app-local date is correct.
    local = _local(res.roasted_at)
    assert local.year == 2026 and local.month == 5 and local.day == 30
    assert res.source == "filename"
    assert res.date_source == "filename"


def test_csv_content_strategy_uses_cooked_at():
    res = infer_roasted_at(
        filename="260530_9.csv",
        parsed=_FakeParsed(cooked_at="2026-05-29 14:30:00"),
        client_last_modified=None,
        default_roast_date=None,
        first_roast_time=None,
        order=1,
        strategy="csv_content",
    )
    assert res.roasted_at is not None
    # CookDate is local — check in app timezone
    local = _local(res.roasted_at)
    assert local.year == 2026 and local.month == 5 and local.day == 29
    assert local.hour == 14 and local.minute == 30
    assert res.source == "csv_content"


def test_upload_order_strategy_spacing():
    res1 = infer_roasted_at(
        filename="x.csv", parsed=_FakeParsed(), client_last_modified=None,
        default_roast_date="2026-05-30", first_roast_time="09:30", order=1,
        strategy="upload_order",
    )
    res2 = infer_roasted_at(
        filename="y.csv", parsed=_FakeParsed(), client_last_modified=None,
        default_roast_date="2026-05-30", first_roast_time="09:30", order=2,
        strategy="upload_order",
    )
    assert res1.time_source == "upload_order"
    assert res1.roasted_at is not None and res2.roasted_at is not None
    # spacing comes from settings.roast_spacing_minutes (default 45)
    diff_minutes = (res2.roasted_at - res1.roasted_at).total_seconds() / 60
    assert diff_minutes == 45


def test_auto_priority_csv_content_over_filename():
    res = infer_roasted_at(
        filename="260530_9.csv",
        parsed=_FakeParsed(cooked_at="2026-05-29 14:30:00"),
        client_last_modified=None,
        default_roast_date=None,
        first_roast_time=None,
        order=1,
        strategy=None,  # auto
    )
    assert res.source == "csv_content"


def test_auto_falls_back_to_filename_when_no_content():
    res = infer_roasted_at(
        filename="260530_9.csv",
        parsed=_FakeParsed(cooked_at=None),
        client_last_modified=None,
        default_roast_date=None,
        first_roast_time=None,
        order=1,
        strategy=None,
    )
    assert res.source == "filename"
    assert res.roasted_at is not None
    local = _local(res.roasted_at)
    assert local.year == 2026


def test_manual_strategy_needs_date():
    res = infer_roasted_at(
        filename="x.csv", parsed=_FakeParsed(), client_last_modified=None,
        default_roast_date=None, first_roast_time="09:30", order=1,
        strategy="manual",
    )
    # No default_roast_date -> manual cannot resolve
    assert res.roasted_at is None


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


# ============================================================
# P1-1: Auto time inference with pot-order spacing
# ============================================================
def test_filename_pot_order_parsing():
    assert parse_filename_pot_order("260621_2.csv") == 2
    assert parse_filename_pot_order("260621_1.csv") == 1
    assert parse_filename_pot_order("260621.csv") is None
    assert parse_filename_pot_order("260621_0.csv") is None  # non-positive
    assert parse_filename_pot_order("roast.csv") is None


def test_auto_no_cookdate_same_day_two_pots_spacing():
    """No CookDate, same-day filenames _1/_2 — Auto must space them by the
    configured spacing (default 45 min), not collapse both to 00:00."""
    res1 = infer_roasted_at(
        filename="260621_1.csv",
        parsed=_FakeParsed(cooked_at=None),
        client_last_modified=None,
        default_roast_date="2026-06-21",
        first_roast_time="09:30",
        order=1,
        pot_order=1,
        strategy=None,  # auto
    )
    res2 = infer_roasted_at(
        filename="260621_2.csv",
        parsed=_FakeParsed(cooked_at=None),
        client_last_modified=None,
        default_roast_date="2026-06-21",
        first_roast_time="09:30",
        order=2,
        pot_order=2,
        strategy=None,
    )
    assert res1.roasted_at is not None and res2.roasted_at is not None
    diff_minutes = (res2.roasted_at - res1.roasted_at).total_seconds() / 60
    assert diff_minutes == 45
    # date from filename, time from upload-order spacing
    assert res1.date_source == "filename"
    assert res1.time_source == "upload_order"
    assert res1.source == "filename+upload_order"
    # both stay on the same calendar day in app timezone
    app_zone = get_app_zone()
    assert res1.roasted_at.astimezone(app_zone).date() == date(2026, 6, 21)
    assert res2.roasted_at.astimezone(app_zone).date() == date(2026, 6, 21)


def test_pot_order_drives_spacing_out_of_upload_order():
    """Files uploaded as _2 then _1: pot order must still produce _1 < _2
    because spacing uses the pot-order suffix, not the upload index."""
    # _2 uploaded first (order=1) but pot_order=2 -> later time
    res_2 = infer_roasted_at(
        filename="260621_2.csv", parsed=_FakeParsed(), client_last_modified=None,
        default_roast_date="2026-06-21", first_roast_time="09:30",
        order=1, pot_order=2, strategy=None,
    )
    # _1 uploaded second (order=2) but pot_order=1 -> earlier time
    res_1 = infer_roasted_at(
        filename="260621_1.csv", parsed=_FakeParsed(), client_last_modified=None,
        default_roast_date="2026-06-21", first_roast_time="09:30",
        order=2, pot_order=1, strategy=None,
    )
    assert res_1.roasted_at < res_2.roasted_at
    diff = (res_2.roasted_at - res_1.roasted_at).total_seconds() / 60
    assert diff == 45


def test_cookdate_full_time_not_overridden_by_first_pot():
    """When CookDate has a full timestamp, Auto must use it (csv_content) and
    NOT override it with the first-pot time + spacing."""
    res = infer_roasted_at(
        filename="260621_1.csv",
        parsed=_FakeParsed(cooked_at="2026-06-21 13:45:00"),
        client_last_modified=None,
        default_roast_date="2026-06-21",
        first_roast_time="09:30",
        order=1,
        pot_order=1,
        strategy=None,  # auto
    )
    assert res.date_source == "csv_content"
    assert res.time_source == "csv_content"
    assert res.source == "csv_content"
    local = _local(res.roasted_at)
    assert local.hour == 13 and local.minute == 45


def test_last_modified_keeps_absolute_no_shanghai_drift():
    """When lastModified is the only source, the inferred instant must equal
    the absolute UTC epoch — no Shanghai reinterpretation drift."""
    from datetime import datetime as _dt
    absolute = _dt(2025, 1, 15, 3, 30, 0, tzinfo=timezone.utc)
    res = infer_roasted_at(
        filename="no_date.csv",
        parsed=_FakeParsed(),
        client_last_modified=absolute,
        default_roast_date=None,
        first_roast_time=None,
        order=1,
        strategy=None,  # auto -> falls back to file_last_modified
    )
    assert res.date_source == "file_last_modified"
    assert res.time_source == "file_last_modified"
    assert res.source == "file_last_modified"
    # same UTC instant, no 8h shift
    assert res.roasted_at == absolute


def test_inferred_datetime_round_trips_iso():
    """The inferred UTC datetime serialises to ISO 8601 and parses back to the
    same instant — the value a user would see/edit as datetime-local."""
    res = infer_roasted_at(
        filename="260621_1.csv",
        parsed=_FakeParsed(cooked_at="2026-06-21 09:30:00"),
        client_last_modified=None,
        default_roast_date=None,
        first_roast_time=None,
        order=1,
        strategy="csv_content",
    )
    iso = res.roasted_at.isoformat()
    from datetime import datetime as _dt
    reparsed = _dt.fromisoformat(iso)
    assert reparsed == res.roasted_at
