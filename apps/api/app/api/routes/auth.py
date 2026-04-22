from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.services.audit import record_audit_log

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession) -> User:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role="user",
    )
    db.add(user)
    record_audit_log(db, actor_user_id=None, target_type="auth", target_id=None, action="register", metadata={"email": payload.email})
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user.last_login_at = datetime.now(timezone.utc)
    record_audit_log(db, actor_user_id=user.id, target_type="auth", target_id=user.id, action="login", metadata={})
    db.commit()
    return TokenResponse(
        access_token=create_token(user.id, token_type="access"),
        refresh_token=create_token(user.id, token_type="refresh"),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: TokenRefreshRequest, db: DbSession) -> TokenResponse:
    try:
        decoded = decode_token(payload.refresh_token, token_type="refresh")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user = db.scalar(select(User).where(User.id == decoded["sub"], User.is_active.is_(True)))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return TokenResponse(
        access_token=create_token(user.id, token_type="access"),
        refresh_token=create_token(user.id, token_type="refresh"),
    )


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> User:
    return user

