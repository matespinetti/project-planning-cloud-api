"""CRUD helpers for user accounts."""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


class UserAlreadyExistsError(ValueError):
    """Raised when attempting to create a user with a duplicate email."""


class InvalidPasswordError(ValueError):
    """Raised when a password does not meet storage requirements."""


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Return a user by email if it exists."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str | UUID) -> Optional[User]:
    """Return a user by their ID."""
    try:
        user_uuid = UUID(str(user_id))
    except ValueError:
        return None

    result = await db.execute(select(User).where(User.id == user_uuid))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    ong: str,
    nombre: str,
    apellido: str,
    role: UserRole | None = None,
) -> User:
    """Create a new user with a hashed password."""
    if len(password.encode("utf-8")) > 72:
        raise InvalidPasswordError("Password cannot exceed 72 bytes in length")

    try:
        hashed_password = get_password_hash(password)
    except ValueError as exc:
        logger.warning("Failed to hash password for %s: %s", email, exc)
        raise InvalidPasswordError(str(exc)) from exc
    user_role = role or UserRole.MEMBER
    user = User(
        email=email,
        password=hashed_password,
        ong=ong,
        nombre=nombre,
        apellido=apellido,
        role=user_role,
    )
    db.add(user)

    try:
        await db.commit()
    except IntegrityError as exc:
        logger.warning("Failed to create user due to integrity error: %s", exc)
        await db.rollback()
        raise UserAlreadyExistsError("A user with this email already exists") from exc

    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """Validate a user's credentials."""
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user
