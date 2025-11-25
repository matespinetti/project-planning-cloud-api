"""Observacion endpoints."""

import logging
from datetime import date
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
    ObservacionDetailedResponse,
    ObservacionListResponse,
    ObservacionResolve,
    ObservacionResponse,
    ObservacionWithUserResponse,
)
from app.services.observacion_service import ObservacionService

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get(
    "/observaciones",
    response_model=ObservacionListResponse,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        400: {
            "model": ErrorDetail,
            "description": "Bad Request - Invalid filter parameters",
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
async def list_all_observaciones(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    # Pagination
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page (max 100)"),
    # Filtering
    estado: Optional[str] = Query(
        None,
        description="Filter by estado (pendiente, resuelta, vencida)",
    ),
    proyecto_id: Optional[UUID] = Query(None, description="Filter by specific project"),
    council_user_id: Optional[UUID] = Query(None, description="Filter by council member who created"),
    # Searching
    search: Optional[str] = Query(
        None,
        min_length=3,
        description="Search in descripcion and respuesta fields (minimum 3 characters)",
    ),
    # Sorting
    sort_by: str = Query(
        "created_at",
        description="Field to sort by (created_at, fecha_limite, fecha_resolucion, updated_at)",
    ),
    sort_order: str = Query(
        "desc",
        description="Sort order (asc, desc)",
    ),
    # Date range
    fecha_desde: Optional[date] = Query(None, description="Filter observations created after this date"),
    fecha_hasta: Optional[date] = Query(None, description="Filter observations created before this date"),
) -> ObservacionListResponse:
    """
    Obtener todas las observaciones con filtrado avanzado, búsqueda, ordenamiento y paginación.

    **Autorización:**
    - COUNCIL users: Ven todas las observaciones que crearon
    - MEMBER users: Ven solo observaciones para sus propios proyectos (como ejecutor)

    **Parámetros de paginación:**
    - `page`: Número de página (por defecto 1)
    - `page_size`: Resultados por página (por defecto 20, máximo 100)

    **Parámetros de filtrado:**
    - `estado`: Filtrar por estado (pendiente, resuelta, vencida)
    - `proyecto_id`: Filtrar por proyecto específico
    - `council_user_id`: Filtrar por consejero que creó la observación
    - `fecha_desde`: Observaciones creadas después de esta fecha
    - `fecha_hasta`: Observaciones creadas antes de esta fecha

    **Búsqueda:**
    - `search`: Buscar en descripción y respuesta (mínimo 3 caracteres)

    **Ordenamiento:**
    - `sort_by`: Campo por el cual ordenar (created_at, fecha_limite, fecha_resolucion, updated_at)
    - `sort_order`: Orden de clasificación (asc, desc)

    **Ejemplos de uso:**
    - `GET /api/v1/observaciones` - Todas las observaciones del usuario
    - `GET /api/v1/observaciones?estado=pendiente&sort_by=fecha_limite&sort_order=asc` - Observaciones pendientes ordenadas por urgencia
    - `GET /api/v1/observaciones?proyecto_id=123...` - Observaciones de un proyecto específico
    - `GET /api/v1/observaciones?search=presupuesto&page=1&page_size=20` - Buscar observaciones sobre presupuesto
    - `GET /api/v1/observaciones?estado=vencida&sort_by=fecha_limite` - Observaciones vencidas
    - `GET /api/v1/observaciones?fecha_desde=2025-01-01&fecha_hasta=2025-01-31` - Observaciones del mes
    """
    logger.info(
        f"User {current_user.id} fetching observaciones with filters: "
        f"estado={estado}, proyecto_id={proyecto_id}, search={search}, "
        f"page={page}, page_size={page_size}"
    )

    # Get observaciones with service
    observaciones, total_count = await ObservacionService.get_all_observaciones(
        db=db,
        current_user=current_user,
        estado_filter=estado,
        proyecto_id=proyecto_id,
        council_user_id=council_user_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        page=page,
        page_size=page_size,
    )

    # Build detailed response with nested objects
    response_items = []
    for obs in observaciones:
        # Get executor (project owner) info if available
        executor_user = None
        if obs.proyecto and obs.proyecto.user_id:
            from app.models.user import User as UserModel
            executor = await db.get(UserModel, obs.proyecto.user_id)
            if executor:
                executor_user = {
                    "id": executor.id,
                    "email": executor.email,
                    "ong": executor.ong,
                    "nombre": executor.nombre,
                }

        # Build response item
        obs_item = {
            "id": obs.id,
            "proyecto_id": obs.proyecto_id,
            "council_user_id": obs.council_user_id,
            "descripcion": obs.descripcion,
            "estado": obs.estado.value,
            "fecha_limite": obs.fecha_limite,
            "respuesta": obs.respuesta,
            "fecha_resolucion": obs.fecha_resolucion,
            "created_at": obs.created_at,
            "updated_at": obs.updated_at,
            "proyecto": {
                "id": obs.proyecto.id,
                "titulo": obs.proyecto.titulo,
                "estado": obs.proyecto.estado,
            },
            "council_user": {
                "id": obs.council_user.id,
                "email": obs.council_user.email,
                "ong": obs.council_user.ong,
                "nombre": obs.council_user.nombre,
            },
            "executor_user": executor_user,
        }
        response_items.append(ObservacionDetailedResponse(**obs_item))

    # Calculate pagination info
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    logger.info(
        f"Returning {len(response_items)} observaciones (page {page}/{total_pages}, total: {total_count})"
    )

    return ObservacionListResponse(
        items=response_items,
        total=total_count,
        page=page,
        page_size=page_size,
        pages=total_pages,
    )


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
        db,
        project_id,
        observacion_data.descripcion,
        current_user,
        bonita_case_id=observacion_data.bonita_case_id,
        bonita_process_instance_id=observacion_data.bonita_process_instance_id,
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
