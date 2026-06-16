"""Questionnaire service tests."""
import pytest
from datetime import datetime, timezone, timedelta

from app.services.questionnaire import (
    generate_share_code, generate_share_url,
    is_expired, compute_bean_age_days,
)
from app.core.config import settings


class TestShareCode:
    def test_generates_urlsafe_code(self):
        code = generate_share_code()
        assert code
        assert "/" not in code
        assert "+" not in code

    def test_codes_are_unique(self):
        codes = [generate_share_code() for _ in range(100)]
        assert len(set(codes)) == 100


class TestShareUrl:
    def test_uses_hash_router(self):
        url = generate_share_url("abc123")
        base = settings.public_frontend_base_url.rstrip("/")
        expected = f"{base}/#/eval/abc123"
        assert url == expected


class TestIsExpired:
    def test_not_expired(self):
        # Use a plain string for now; actual ORM object not needed
        class FakeQ:
            status = "open"
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        assert not is_expired(FakeQ())

    def test_expired(self):
        class FakeQ:
            status = "open"
            expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        assert is_expired(FakeQ())

    def test_closed_not_expired(self):
        class FakeQ:
            status = "closed"
            expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        assert not is_expired(FakeQ())


class TestBeanAge:
    def test_bean_age_days(self):
        roasted = datetime(2026, 6, 1, tzinfo=timezone.utc)
        submitted = datetime(2026, 6, 16, tzinfo=timezone.utc)
        assert compute_bean_age_days(roasted, submitted) == 15

    def test_none_roasted(self):
        submitted = datetime(2026, 6, 16, tzinfo=timezone.utc)
        assert compute_bean_age_days(None, submitted) is None
