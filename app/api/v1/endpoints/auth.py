"""Authentication endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.db.session import get_db
from app.models.user import User
from app.schemas.errors import AuthErrorDetail, ErrorDetail, ValidationErrorDetail
from app.schemas.user import (
    TokenPair,
    TokenRefreshRequest,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.user_service import (
    InvalidPasswordError,
    UserAlreadyExistsError,
    UserService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_token_pair(user: User) -> TokenPair:
    """Create access and refresh tokens for a user."""
    claims = {"email": user.email, "role": user.role.value}
    access_token = security.create_access_token(subject=str(user.id), additional_claims=claims)
    refresh_token = security.create_refresh_token(subject=str(user.id), additional_claims=claims)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {
            "model": ErrorDetail,
            "description": "Bad Request - Email already exists, invalid password, or invalid registration data",
            "content": {
                "application/json": {
                    "examples": {
                        "email_exists": {
                            "summary": "Email already registered",
                            "value": {"detail": "A user with this email already exists"},
                        },
                        "invalid_password": {
                            "summary": "Password too long",
                            "value": {
                                "detail": "Password cannot exceed 72 bytes in length"
                            },
                        },
                        "invalid_data": {
                            "summary": "Invalid registration data",
                            "value": {"detail": "Invalid registration data"},
                        },
                    }
                }
            },
        },
        422: {
            "model": ValidationErrorDetail,
            "description": "Validation Error - Request body does not match expected schema",
        },
    },
)
async def register_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Registrar una nueva cuenta de usuario."""
    logger.info("Registering new user with email %s", payload.email)
    try:
        user = await UserService.create(
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


@router.post(
    "/login",
    response_model=TokenPair,
    responses={
        401: {
            "model": AuthErrorDetail,
            "description": "Unauthorized - Invalid email or password",
            "content": {
                "application/json": {
                    "example": {"detail": "Incorrect email or password"}
                }
            },
        },
        422: {
            "model": ValidationErrorDetail,
            "description": "Validation Error - Request body does not match expected schema",
        },
    },
)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    """Autenticar un usuario y retornar tokens JWT."""
    logger.info("User login attempt for email %s", credentials.email)
    user = await UserService.authenticate(db, credentials.email, credentials.password)
    if not user:
        logger.warning("Invalid credentials for email %s", credentials.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _build_token_pair(user)


@router.post(
    "/refresh",
    response_model=TokenPair,
    responses={
        401: {
            "model": AuthErrorDetail,
            "description": "Unauthorized - Invalid, expired, or malformed refresh token",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_token": {
                            "summary": "Invalid or expired token",
                            "value": {"detail": "Invalid refresh token"},
                        },
                        "user_not_found": {
                            "summary": "User no longer exists",
                            "value": {"detail": "Invalid refresh token"},
                        },
                    }
                }
            },
        },
        422: {
            "model": ValidationErrorDetail,
            "description": "Validation Error - Request body does not match expected schema",
        },
    },
)
async def refresh_tokens(
    payload: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    """Intercambiar un refresh token por un nuevo par de tokens."""
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

    user = await UserService.get_by_id(db, user_id)
    if not user:
        logger.error("User not found for refresh token subject %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _build_token_pair(user)
