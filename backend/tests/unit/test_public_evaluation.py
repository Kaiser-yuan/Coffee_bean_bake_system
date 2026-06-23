"""Unit tests for the public-evaluation throttle (P1-2).

In-memory sliding-window limiter + repeat de-dup. A failed submission (422)
must not stamp the repeat record, so a legitimate retry is not blocked.
"""
import pytest

from app.services.public_evaluation import PublicEvaluationThrottle
from app.core.exceptions import RateLimitException


def _make(limit=3, repeat_window=300):
    return PublicEvaluationThrottle(limit_per_minute=limit, repeat_window_seconds=repeat_window)


def test_rate_limit_allows_up_to_limit_then_429():
    t = _make(limit=3)
    cid = "client-a"
    # 3 requests allowed
    for _ in range(3):
        t.check(cid, "q-1")
    # 4th over the limit
    with pytest.raises(RateLimitException):
        t.check(cid, "q-2")


def test_rate_limit_is_per_client():
    t = _make(limit=2)
    t.check("client-a", "q-1")
    t.check("client-a", "q-2")
    # different client has its own budget
    t.check("client-b", "q-1")
    t.check("client-b", "q-2")
    with pytest.raises(RateLimitException):
        t.check("client-b", "q-3")


def test_repeat_within_window_raises_only_after_success():
    t = _make(limit=10, repeat_window=300)
    cid = "client-a"
    # first check passes, but submission *fails* (no record_repeat)
    t.check(cid, "q-1")
    # immediate retry of the same questionnaire must NOT be blocked by dedup,
    # because the previous attempt did not succeed.
    t.check(cid, "q-1")  # passes (rate budget allows)

    # now a successful submission stamps the repeat record
    t.record_repeat(cid, "q-1")
    # immediate re-submit of the same questionnaire is now blocked
    with pytest.raises(RateLimitException):
        t.check(cid, "q-1")


def test_different_questionnaire_not_deduped():
    t = _make(limit=10, repeat_window=300)
    cid = "client-a"
    t.check(cid, "q-1")
    t.record_repeat(cid, "q-1")
    # same client, different questionnaire — not a repeat
    t.check(cid, "q-2")


def test_client_id_is_hashed_and_deterministic():
    """client_id must be a stable hash (never the raw IP)."""

    class FakeClient:
        host = "203.0.113.7"

    class FakeRequest:
        headers = {}
        client = FakeClient()

    cid = PublicEvaluationThrottle.client_id(FakeRequest())
    assert cid != "203.0.113.7"
    assert len(cid) == 32
    assert all(c in "0123456789abcdef" for c in cid)
    # deterministic
    assert PublicEvaluationThrottle.client_id(FakeRequest()) == cid


def test_client_id_uses_forwarded_for_first_hop():
    class FakeClient:
        host = "203.0.113.7"

    class FakeRequest:
        headers = {"x-forwarded-for": "198.51.100.2, 10.0.0.1"}
        client = FakeClient()

    class FakeRequestDirect:
        headers = {}
        client = FakeClient()

    cid_forwarded = PublicEvaluationThrottle.client_id(FakeRequest())
    cid_direct = PublicEvaluationThrottle.client_id(FakeRequestDirect())
    assert cid_forwarded != cid_direct
