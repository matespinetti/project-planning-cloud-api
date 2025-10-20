"""Authentication endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.core import security
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    TokenPair,
    TokenRefreshRequest,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.crud.user import UserAlreadyExistsError, InvalidPasswordError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_token_pair(user: User) -> TokenPair:
    """Create access and refresh tokens for a user."""
    claims = {"email": user.email, "role": user.role.value}
    access_token = security.create_access_token(subject=str(user.id), additional_claims=claims)
    refresh_token = security.create_refresh_token(subject=str(user.id), additional_claims=claims)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user account."""
    logger.info("Registering new user with email %s", payload.email)
    try:
        user = await crud.user.create_user(
            db,
            email=payload.email,
            password=payload.password,
            ong=payload.ong,
            nombre=payload.nombre,
            apellido=payload.apellido,
            role=payload.role,
        )
    except UserAlreadyExistsError as exc:
        logger.warning("Attempt to register an existing email: %s", payload.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except InvalidPasswordError as exc:
        logger.warning("Invalid password provided for email %s", payload.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        logger.error("Unexpected validation error during registration: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid registration data",
        ) from exc

    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    """Authenticate a user and return JWT tokens."""
    logger.info("User login attempt for email %s", credentials.email)
    user = await crud.user.authenticate_user(db, credentials.email, credentials.password)
    if not user:
        logger.warning("Invalid credentials for email %s", credentials.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _build_token_pair(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(
    payload: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    """Exchange a refresh token for a new token pair."""
    logger.info("Refreshing access token")
    try:
        token_data = security.decode_refresh_token(payload.refresh_token)
    except ValueError as exc:
        logger.warning("Invalid refresh token used")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = token_data.get("sub")
    if not user_id:
        logger.error("Refresh token missing subject claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await crud.user.get_user_by_id(db, user_id)
    if not user:
        logger.error("User not found for refresh token subject %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _build_token_pair(user)
