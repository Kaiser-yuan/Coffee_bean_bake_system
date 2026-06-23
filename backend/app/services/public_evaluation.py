"""Public evaluation submission helpers.

Term resolution here is *read-only*: the public endpoint may only reference
already-existing, active standard terms — it never creates terms. Unknown or
inactive terms raise 422.

A single-process in-memory throttle caps submission rate and de-duplicates
repeats from the same (hashed) client. Only the hash of the client identifier
is retained — never the raw IP.
"""
import hashlib
import threading
import time
from collections import defaultdict

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.exceptions import RateLimitException, ValidationException
from ..repositories.terms import TermRepository


# ============================================================
# Term resolution (read-only — never creates terms)
# ============================================================
async def resolve_brew_method_term(db: AsyncSession, body) -> str | None:
    """Resolve the brew-method term id for a public submission.

    Prefers an explicit ``brew_method_term_id``; falls back to looking the
    display value up among *active* brew_method terms. Returns 422 when a
    value/id is supplied but no active term matches — never creates one.
    """
    if body.brew_method_term_id:
        term = await TermRepository(db).get_by_id(body.brew_method_term_id)
        if term is None or term.category != "brew_method" or not term.is_active:
            raise ValidationException(
                f"未知的冲煮方式: {body.brew_method_term_id}",
                status_code=422,
            )
        return term.id
    if body.brew_method:
        term = await TermRepository(db).get_by_category_and_value(
            "brew_method", body.brew_method.strip(), active_only=True,
        )
        if term is None:
            raise ValidationException(
                f"未知的冲煮方式: {body.brew_method}", status_code=422,
            )
        return term.id
    return None


async def resolve_flavor_term_ids(db: AsyncSession, body) -> list[str]:
    """Resolve flavor term ids for a public submission.

    Prefers explicit ``flavor_term_ids``; falls back to looking each
    ``flavor_notes`` value up among *active* flavor terms. Returns 422 on the
    first unknown/inactive value — never creates terms.
    """
    repo = TermRepository(db)
    if body.flavor_term_ids:
        ids: list[str] = []
        for term_id in body.flavor_term_ids[:50]:
            term = await repo.get_by_id(term_id)
            if term is None or term.category != "flavor" or not term.is_active:
                raise ValidationException(
                    f"未知的风味词: {term_id}", status_code=422,
                )
            ids.append(term.id)
        return ids

    ids: list[str] = []
    for flavor_value in body.flavor_notes[:50]:
        if not flavor_value or not flavor_value.strip():
            continue
        term = await repo.get_by_category_and_value(
            "flavor", flavor_value.strip(), active_only=True,
        )
        if term is None:
            raise ValidationException(
                f"未知的风味词: {flavor_value}", status_code=422,
            )
        ids.append(term.id)
    return ids


# ============================================================
# In-memory rate limiter + repeat de-duplication (single process)
# ============================================================
class PublicEvaluationThrottle:
    """Per-client sliding-window limiter + repeat de-dup.

    State is in-memory and per-process — fine for a single-worker deploy.
    For multi-worker, swap in Redis or a PostgreSQL atomic counter.

    Only SHA-256 hashes of the client identifier are stored; the raw IP is
    never persisted.
    """

    def __init__(self, limit_per_minute: int, repeat_window_seconds: int):
        self.limit = max(1, limit_per_minute)
        self.repeat_window = max(0, repeat_window_seconds)
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._last_submit: dict[str, float] = {}
        self._lock = threading.Lock()

    @staticmethod
    def client_id(request: Request) -> str:
        """Hash the originating client address (X-Forwarded-For first hop, else
        the connection peer). Only the hash is stored."""
        forwarded = request.headers.get("x-forwarded-for", "")
        raw = forwarded.split(",")[0].strip() if forwarded else (
            request.client.host if request.client else "unknown"
        )
        digest = hashlib.sha256(
            f"{raw}:{settings.secret_key}".encode("utf-8")
        ).hexdigest()
        return digest[:32]

    def check(self, client_id: str, questionnaire_id: str) -> None:
        """Gate the request: raise RateLimitException if this client is
        repeating the same questionnaire within the repeat window, or is over
        the per-minute rate limit.

        The rate-limit hit is counted here (so probing with bad data still
        consumes quota), but the *repeat* record is only stamped on a
        successful submission — a 422 must not block a legitimate retry.
        """
        now = time.monotonic()
        dedup_key = hashlib.sha256(
            f"{client_id}:{questionnaire_id}".encode("utf-8")
        ).hexdigest()[:32]

        with self._lock:
            # 1. Repeat de-dup: a successful submission of this same
            #    client+questionnaire within the window blocks a re-submit.
            last = self._last_submit.get(dedup_key)
            if last is not None and (now - last) < self.repeat_window:
                raise RateLimitException("该问卷您刚刚已提交，请稍后再试")

            # 2. Per-client sliding 60s window (counts the request).
            hits = self._hits[client_id]
            cutoff = now - 60.0
            recent = [t for t in hits if t > cutoff]
            if len(recent) >= self.limit:
                self._hits[client_id] = recent
                raise RateLimitException("提交过于频繁，请稍后再试")

            recent.append(now)
            self._hits[client_id] = recent

    def record_repeat(self, client_id: str, questionnaire_id: str) -> None:
        """Stamp a successful submission so an immediate re-submit of the same
        questionnaire is de-duplicated."""
        now = time.monotonic()
        dedup_key = hashlib.sha256(
            f"{client_id}:{questionnaire_id}".encode("utf-8")
        ).hexdigest()[:32]
        with self._lock:
            self._last_submit[dedup_key] = now


# Module-level singleton used by the public endpoint. Tests construct their
# own instance to avoid cross-test contamination.
throttle = PublicEvaluationThrottle(
    limit_per_minute=settings.public_evaluation_rate_limit_per_minute,
    repeat_window_seconds=settings.public_evaluation_repeat_window_seconds,
)
