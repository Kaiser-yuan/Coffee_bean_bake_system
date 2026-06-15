"""Questionnaire business logic."""
import secrets
import logging
from datetime import datetime, timezone

from ..models.all_models import Questionnaire

logger = logging.getLogger("coffee-roast.questionnaire")


def generate_share_code() -> str:
    """Generate a secure, unpredictable share code."""
    return secrets.token_urlsafe(12)


def generate_share_url(share_code: str) -> str:
    """Generate the public share URL using configured frontend base URL."""
    from ..core.config import settings
    base = settings.public_frontend_base_url.rstrip("/")
    # Hash router frontend: /#/eval/{share_code}
    return f"{base}/#/eval/{share_code}"


def is_expired(questionnaire: Questionnaire) -> bool:
    """Check if questionnaire has expired (without modifying DB)."""
    if questionnaire.status == "closed":
        return False
    if questionnaire.expires_at:
        return datetime.now(timezone.utc) > questionnaire.expires_at
    return False


def compute_bean_age_days(roasted_at: datetime | None, submitted_at: datetime) -> int | None:
    """Calculate rest days from roast to evaluation."""
    if not roasted_at:
        return None
    return (submitted_at.date() - roasted_at.date()).days
