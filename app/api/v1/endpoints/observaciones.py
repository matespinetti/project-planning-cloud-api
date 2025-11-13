"""Observacion endpoints."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.errors import OWNERSHIP_RESPONSES, ErrorDetail, ValidationErrorDetail
from app.schemas.observacion import (
    ObservacionCreate,
    ObservacionResolve,
    ObservacionResponse,
    ObservacionWithUserResponse,
)
from app.services.observacion_service import ObservacionService

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post(
    "/projects/{project_id}/observaciones",
    response_model=ObservacionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.COUNCIL))],
    responses={
        401: OWNERSHIP_RESPONSES[401],
        403: {
            "model": ErrorDetail,
            "description": "Forbidden - Only council members can create observations",
            "content": {
                "application/json": {
                    "example": {"detail": "Only council members can create observations"}
                }
            },
        },
        404: {
            "model": ErrorDetail,
            "description": "Not Found - Project does not exist",
            "content": {
                "application/json": {
                    "example": {"detail": "Proyecto with id ... not found"}
                }
            },
        },
        400: {
            "model": ErrorDetail,
            "description": "Bad Request - Project is not in execution state",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Observations can only be created for projects in 'en_ejecucion' state. Current state: pendiente"
                    }
                }
            },
        },
    },
)
async def create_observacion(
    project_id: UUID,
    observacion_data: ObservacionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ObservacionResponse:
    """
    Crear una nueva observación para un proyecto en ejecución.

    **Autorización:** Solo miembros del consejo (role=COUNCIL)

    **Validaciones:**
    - El usuario debe tener rol COUNCIL
    - El proyecto debe existir
    - El proyecto debe estar en estado 'en_ejecucion'

    **Comportamiento:**
    - La fecha límite se establece automáticamente a 5 días desde la creación
    - El estado inicial es 'pendiente'
    - Si no se resuelve antes de la fecha límite, se marca automáticamente como 'vencida'

    **Campos requeridos:**
    - descripcion: Descripción de la observación (mínimo 10 caracteres)

    **Ejemplo de request body:**
    ```json
    {
        "descripcion": "Se observa que el presupuesto destinado a materiales no incluye costos de transporte. Por favor revisar y ajustar."
    }
    ```
    """
    logger.info(
        f"Council user {current_user.id} creating observacion for project {project_id}"
    )

    observacion = await ObservacionService.create(
        db, project_id, observacion_data.descripcion, current_user
    )

    logger.info(
        f"Successfully created observacion {observacion.id} with deadline {observacion.fecha_limite}"
    )
    return ObservacionResponse.model_validate(observacion)


@router.get(
    "/projects/{project_id}/observaciones",
    response_model=List[ObservacionWithUserResponse],
    responses={
        401: OWNERSHIP_RESPONSES[401],
        404: {
            "model": ErrorDetail,
            "description": "Not Found - Project does not exist",
            "content": {
                "application/json": {
                    "example": {"detail": "Proyecto with id ... not found"}
                }
            },
        },
        400: {
            "model": ErrorDetail,
            "description": "Bad Request - Invalid estado filter",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid estado filter. Must be one of: ['pendiente', 'resuelta', 'vencida']"
                    }
                }
            },
        },
    },
)
async def list_observaciones(
    project_id: UUID,
    estado: Optional[str] = Query(
        None,
        description="Filter by estado (pendiente, resuelta, vencida)",
        pattern="^(pendiente|resuelta|vencida)$",
    ),
    db: AsyncSession = Depends(get_db),
) -> List[ObservacionWithUserResponse]:
    """
    Listar todas las observaciones de un proyecto.

    **Autorización:** Cualquier usuario autenticado

    **Filtros opcionales:**
    - `estado`: Filtrar por estado (pendiente, resuelta, vencida)

    **Comportamiento automático:**
    - Las observaciones pendientes se verifican automáticamente
    - Si han pasado más de 5 días desde su creación, se marcan como 'vencida'
    - Los resultados se ordenan por fecha de creación (más recientes primero)

    **Información incluida:**
    - Todos los campos de la observación
    - Email, organización y nombre del consejero que creó la observación

    **Ejemplos de uso:**
    - `/api/v1/projects/{id}/observaciones` - Todas las observaciones
    - `/api/v1/projects/{id}/observaciones?estado=pendiente` - Solo pendientes
    - `/api/v1/projects/{id}/observaciones?estado=vencida` - Solo vencidas
    """
    logger.info(
        f"Fetching observaciones for project {project_id} with estado filter: {estado}"
    )

    observaciones = await ObservacionService.list_by_proyecto(db, project_id, estado)

    # Convert to response with council user info
    response_observaciones = []
    for obs in observaciones:
        obs_dict = ObservacionWithUserResponse.model_validate(obs).model_dump()
        obs_dict["council_user_email"] = obs.council_user.email
        obs_dict["council_user_ong"] = obs.council_user.ong
        obs_dict["council_user_nombre"] = obs.council_user.nombre
        response_observaciones.append(ObservacionWithUserResponse(**obs_dict))

    logger.info(f"Returning {len(response_observaciones)} observaciones")
    return response_observaciones


@router.post(
    "/observaciones/{observacion_id}/resolve",
    response_model=ObservacionResponse,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        403: {
            "model": ErrorDetail,
            "description": "Forbidden - Only project executor can resolve observations",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Only the project executor (owner) can resolve observations"
                    }
                }
            },
        },
        404: {
            "model": ErrorDetail,
            "description": "Not Found - Observation does not exist",
            "content": {
                "application/json": {
                    "example": {"detail": "Observacion with id ... not found"}
                }
            },
        },
        400: {
            "model": ErrorDetail,
            "description": "Bad Request - Observation already resolved",
            "content": {
                "application/json": {
                    "example": {"detail": "Observacion is already resolved"}
                }
            },
        },
    },
)
async def resolve_observacion(
    observacion_id: UUID,
    resolve_data: ObservacionResolve,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ObservacionResponse:
    """
    Resolver una observación.

    **Autorización:** Solo el ejecutor del proyecto (dueño)

    **Validaciones:**
    - El usuario debe ser el dueño del proyecto asociado a la observación
    - La observación no debe estar ya resuelta

    **Comportamiento:**
    - Cambia el estado a 'resuelta'
    - Guarda la respuesta del ejecutor
    - Registra la fecha y hora de resolución
    - Puede resolver observaciones incluso si están vencidas

    **Campos requeridos:**
    - respuesta: Respuesta del ejecutor a la observación (mínimo 10 caracteres)

    **Ejemplo de request body:**
    ```json
    {
        "respuesta": "Gracias por la observación. He revisado el presupuesto y agregado una partida para costos de transporte de $500 USD. El documento actualizado está adjunto en la sección de archivos del proyecto."
    }
    ```
    """
    logger.info(f"User {current_user.id} attempting to resolve observacion {observacion_id}")

    observacion = await ObservacionService.resolve(
        db, observacion_id, resolve_data.respuesta, current_user
    )

    logger.info(f"Successfully resolved observacion {observacion_id}")
    return ObservacionResponse.model_validate(observacion)
