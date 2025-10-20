"""Project endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.schemas.proyecto import ProyectoCreate, ProyectoResponse, ProyectoUpdate

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post(
    "/projects",
    response_model=ProyectoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    proyecto_data: ProyectoCreate,
    db: AsyncSession = Depends(get_db),
) -> ProyectoResponse:
    """
    Create a new proyecto with nested etapas and pedidos.
    """
    try:
        logger.info(f"Creating proyecto: {proyecto_data.titulo}")
        db_proyecto = await crud.proyecto.create_proyecto(db, proyecto_data)
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


@router.get("/projects/{project_id}", response_model=ProyectoResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ProyectoResponse:
    """
    Get a proyecto by ID with all nested data.
    """
    logger.info(f"Fetching proyecto {project_id}")
    db_proyecto = await crud.proyecto.get_proyecto(db, project_id)

    if not db_proyecto:
        logger.warning(f"Proyecto {project_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proyecto with id {project_id} not found",
        )

    return ProyectoResponse.model_validate(db_proyecto)


@router.patch("/projects/{project_id}", response_model=ProyectoResponse)
async def update_project(
    project_id: UUID,
    update_data: ProyectoUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProyectoResponse:
    """
    Partial update of a proyecto (mainly for Bonita info).
    """
    logger.info(f"Updating proyecto {project_id}")
    db_proyecto = await crud.proyecto.update_proyecto(db, project_id, update_data)

    if not db_proyecto:
        logger.warning(f"Proyecto {project_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proyecto with id {project_id} not found",
        )

    logger.info(f"Successfully updated proyecto {project_id}")
    return ProyectoResponse.model_validate(db_proyecto)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a proyecto (cascades to etapas and pedidos).
    Used by proxy API for rollback when Bonita fails.
    """
    logger.info(f"Deleting proyecto {project_id}")
    deleted = await crud.proyecto.delete_proyecto(db, project_id)

    if not deleted:
        logger.warning(f"Proyecto {project_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proyecto with id {project_id} not found",
        )

    logger.info(f"Successfully deleted proyecto {project_id}")
