"""User endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.errors import OWNERSHIP_RESPONSES
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get(
    "/users/me",
    response_model=UserResponse,
    responses={
        401: OWNERSHIP_RESPONSES[401],
    },
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Obtener el perfil del usuario autenticado actualmente.

    Retorna todos los datos del usuario incluido su rol y timestamps.
    """
    logger.info(f"User {current_user.id} fetching their profile")
    return UserResponse.model_validate(current_user)
