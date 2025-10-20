"""Password hashing and JWT helpers."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that the provided password matches the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)


def _create_token(
    subject: str,
    secret_key: str,
    expires_delta: timedelta,
    additional_claims: Dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT token."""
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
    }
    if additional_claims:
        payload.update(additional_claims)

    return jwt.encode(payload, secret_key, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str, additional_claims: Dict[str, Any] | None = None) -> str:
    """Create a short-lived access token."""
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(subject, settings.JWT_SECRET_KEY, expires, additional_claims)


def create_refresh_token(subject: str, additional_claims: Dict[str, Any] | None = None) -> str:
    """Create a long-lived refresh token."""
    expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    return _create_token(subject, settings.JWT_REFRESH_SECRET_KEY, expires, additional_claims)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate an access token."""
    return _decode_token(token, settings.JWT_SECRET_KEY)


def decode_refresh_token(token: str) -> Dict[str, Any]:
    """Decode and validate a refresh token."""
    return _decode_token(token, settings.JWT_REFRESH_SECRET_KEY)


def _decode_token(token: str, secret_key: str) -> Dict[str, Any]:
    """Decode a token and ensure it is valid."""
    try:
        return jwt.decode(token, secret_key, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:  # pragma: no cover - jose raises multiple subclasses
        raise ValueError("Invalid or expired token") from exc

