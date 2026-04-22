from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_token(subject: str, token_type: Literal["access", "refresh"]) -> str:
    settings = get_settings()
    expires_delta = (
        timedelta(minutes=settings.access_token_expire_minutes)
        if token_type == "access"
        else timedelta(minutes=settings.refresh_token_expire_minutes)
    )
    secret = settings.jwt_secret_key if token_type == "access" else settings.jwt_refresh_secret_key
    expire_at = datetime.now(timezone.utc) + expires_delta
    payload: dict[str, Any] = {"sub": subject, "type": token_type, "exp": expire_at}
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, token_type: Literal["access", "refresh"]) -> dict[str, Any]:
    settings = get_settings()
    secret = settings.jwt_secret_key if token_type == "access" else settings.jwt_refresh_secret_key
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
    if payload.get("type") != token_type:
        raise ValueError("Unexpected token type")
    return payload
