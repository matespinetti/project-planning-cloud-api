"""Authentication dependencies for protecting endpoints."""

import secrets
from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.services.user_service import UserService

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolve the currently authenticated user via a bearer token.

    Raises HTTP 401 if the token is missing, invalid, expired, or the user no longer exists.
    """
    settings = get_settings()

    if x_api_key:
        expected_api_key = settings.BONITA_API_KEY
        if not expected_api_key or not secrets.compare_digest(x_api_key, expected_api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Bonita API key",
            )

        bonita_user_id = settings.BONITA_SYSTEM_USER_ID
        if not bonita_user_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bonita system user is not configured",
            )

        try:
            bonita_user_uuid = UUID(bonita_user_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid BONITA_SYSTEM_USER_ID configuration",
            ) from exc

        system_user = await UserService.get_by_id(db, bonita_user_uuid)
        if not system_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bonita system user not found",
            )

        setattr(system_user, "is_bonita_actor", True)
        return system_user

    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_roles(*allowed_roles: UserRole):
    """
    Ensure the current user has one of the allowed roles.

    Usage:
        @router.get(..., dependencies=[Depends(require_roles(UserRole.COUNCIL))])
    """

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if allowed_roles and current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return dependency
