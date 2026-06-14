"""Authentication endpoints."""
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from ..dependencies import DBSessionDep
from ...core.exceptions import UnauthorizedException, ValidationException
from ...core.security import create_access_token, hash_password, verify_password
from ...models.all_models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user_id: str
    display_name: str | None


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str | None = None


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: DBSessionDep):
    """Authenticate and return JWT token."""
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise UnauthorizedException("用户名或密码错误")

    if not user.is_active:
        raise UnauthorizedException("账户已被停用")

    token, expires_at = create_access_token(user.id)

    return LoginResponse(
        access_token=token,
        expires_at=expires_at.isoformat(),
        user_id=user.id,
        display_name=user.display_name,
    )


@router.post("/register", response_model=LoginResponse, status_code=201)
async def register(body: RegisterRequest, db: DBSessionDep):
    """Register a new user and return token (first-run setup)."""
    # Check existing
    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none():
        raise ValidationException("用户名已存在")

    if len(body.password) < 6:
        raise ValidationException("密码长度至少 6 位")

    user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        display_name=body.display_name or body.username,
    )
    db.add(user)
    await db.flush()

    token, expires_at = create_access_token(user.id)

    return LoginResponse(
        access_token=token,
        expires_at=expires_at.isoformat(),
        user_id=user.id,
        display_name=user.display_name,
    )
