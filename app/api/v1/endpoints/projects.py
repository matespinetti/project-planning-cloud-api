"""Project endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.errors import OWNERSHIP_RESPONSES, ErrorDetail, ValidationErrorDetail
from app.schemas.proyecto import ProyectoCreate, ProyectoResponse, ProyectoUpdate
from app.services.proyecto_service import ProyectoService

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post(
    "/projects",
    response_model=ProyectoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        422: {
            "model": ValidationErrorDetail,
            "description": "Validation Error - Invalid proyecto data or nested etapas/pedidos",
            "content": {
                "application/json": {
                    "examples": {
                        "pydantic_validation": {
                            "summary": "Pydantic validation error",
                            "value": {
                                "detail": [
                                    {
                                        "loc": ["body", "titulo"],
                                        "msg": "ensure this value has at least 5 characters",
                                        "type": "value_error.any_str.min_length",
                                    }
                                ]
                            },
                        },
                        "service_validation": {
                            "summary": "Service layer validation error",
                            "value": {"detail": "Invalid proyecto data"},
                        },
                    }
                }
            },
        },
        500: {
            "model": ErrorDetail,
            "description": "Internal Server Error - Unexpected error during proyecto creation",
            "content": {
                "application/json": {
                    "example": {"detail": "Error creating proyecto: Database error"}
                }
            },
        },
    },
)
async def create_project(
    proyecto_data: ProyectoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProyectoResponse:
    """
    Crear un nuevo proyecto con etapas y pedidos anidados.
    El proyecto se asigna automáticamente al usuario autenticado.
    """
    try:
        logger.info(f"User {current_user.id} creating proyecto: {proyecto_data.titulo}")
        db_proyecto = await ProyectoService.create(db, proyecto_data, current_user)
        logger.info(f"Successfully created proyecto with ID: {db_proyecto.id}")
        return ProyectoResponse.model_validate(db_proyecto)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Error creating proyecto: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating proyecto: {str(e)}",
        )


@router.get(
    "/projects/{project_id}",
    response_model=ProyectoResponse,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        404: {
            "model": ErrorDetail,
            "description": "Not Found - Proyecto does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Proyecto with id 123e4567-e89b-12d3-a456-426614174000 not found"
                    }
                }
            },
        },
    },
)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ProyectoResponse:
    """
    Obtener un proyecto por ID con todos los datos anidados.
    Cualquier usuario autenticado puede ver proyectos.
    """
    logger.info(f"Fetching proyecto {project_id}")
    db_proyecto = await ProyectoService.get_by_id(db, project_id)

    if not db_proyecto:
        logger.warning(f"Proyecto {project_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proyecto with id {project_id} not found",
        )

    return ProyectoResponse.model_validate(db_proyecto)


@router.patch(
    "/projects/{project_id}",
    response_model=ProyectoResponse,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        403: OWNERSHIP_RESPONSES[403],
        404: OWNERSHIP_RESPONSES[404],
        422: {
            "model": ValidationErrorDetail,
            "description": "Validation Error - Invalid update data",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "bonita_case_id"],
                                "msg": "string does not match regex",
                                "type": "value_error.str.regex",
                            }
                        ]
                    }
                }
            },
        },
    },
)
async def update_project(
    project_id: UUID,
    update_data: ProyectoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProyectoResponse:
    """
    Actualización parcial de un proyecto (principalmente para info de Bonita).
    Solo el dueño del proyecto puede actualizarlo.
    """
    logger.info(f"User {current_user.id} updating proyecto {project_id}")
    db_proyecto = await ProyectoService.update(db, project_id, update_data, current_user)

    if not db_proyecto:
        logger.warning(f"Proyecto {project_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proyecto with id {project_id} not found",
        )

    logger.info(f"Successfully updated proyecto {project_id}")
    return ProyectoResponse.model_validate(db_proyecto)


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        403: {
            "model": ErrorDetail,
            "description": "Forbidden - User is not the owner of this project",
            "content": {
                "application/json": {
                    "example": {"detail": "You are not the owner of this project"}
                }
            },
        },
        404: {
            "model": ErrorDetail,
            "description": "Not Found - Project does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Proyecto with id 123e4567-e89b-12d3-a456-426614174000 not found"
                    }
                }
            },
        },
    },
)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Eliminar un proyecto (en cascada a etapas y pedidos).
    Solo el dueño del proyecto puede eliminarlo.
    """
    logger.info(f"User {current_user.id} deleting proyecto {project_id}")
    deleted = await ProyectoService.delete(db, project_id, current_user)

    if not deleted:
        logger.warning(f"Proyecto {project_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proyecto with id {project_id} not found",
        )

    logger.info(f"Successfully deleted proyecto {project_id}")
