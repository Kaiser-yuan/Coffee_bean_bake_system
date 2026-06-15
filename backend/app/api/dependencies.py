"""FastAPI dependencies: authentication and database session."""
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.exceptions import UnauthorizedException, ForbiddenException
from ..core.security import decode_access_token
from ..models.all_models import User

security_scheme = HTTPBearer(auto_error=False)

# --- DB Session ---

DBSessionDep = Annotated[AsyncSession, Depends(get_db)]


# --- Current User ---

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate JWT and return current user."""
    if credentials is None:
        raise UnauthorizedException()

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
    except Exception:
        raise UnauthorizedException("Invalid or expired token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise UnauthorizedException("User not found or inactive")

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


# --- Admin User ---

async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require admin role."""
    if not current_user.is_admin:
        raise ForbiddenException("Admin privileges required")
    return current_user


AdminUserDep = Annotated[User, Depends(get_admin_user)]


# --- Idempotency Key ---

async def get_idempotency_key(
    x_idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> str | None:
    return x_idempotency_key


IdempotencyKeyDep = Annotated[str | None, Depends(get_idempotency_key)]
