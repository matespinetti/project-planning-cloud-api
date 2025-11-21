"""Project endpoints."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.proyecto import EstadoProyecto
from app.models.user import User
from app.schemas.errors import OWNERSHIP_RESPONSES, ErrorDetail, ValidationErrorDetail
from app.schemas.proyecto import (
    PaginatedProyectoResponse,
    ProyectoCompleteResponse,
    ProyectoCreate,
    ProyectoListItem,
    ProyectoPut,
    ProyectoResponse,
    ProyectoStartResponse,
    ProyectoUpdate,
)
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


@router.put(
    "/projects/{project_id}",
    response_model=ProyectoResponse,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        403: OWNERSHIP_RESPONSES[403],
        404: OWNERSHIP_RESPONSES[404],
        422: {
            "model": ValidationErrorDetail,
            "description": "Validation Error - Invalid replacement data",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "titulo"],
                                "msg": "ensure this value has at least 5 characters",
                                "type": "value_error.any_str.min_length",
                            }
                        ]
                    }
                }
            },
        },
    },
)
async def replace_project(
    project_id: UUID,
    replace_data: ProyectoPut,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProyectoResponse:
    """
    Reemplazo completo de un proyecto (PUT).

    **Requisitos:**
    - Solo el dueño del proyecto puede reemplazarlo (o Bonita via X-API-Key)
    - Todos los campos principales son obligatorios

    **Campos obligatorios:**
    - titulo: str
    - descripcion: str
    - tipo: str
    - pais: str
    - provincia: str
    - ciudad: str

    **Campos opcionales:**
    - barrio: str
    - estado: str
    - bonita_case_id: str
    - bonita_process_instance_id: int
    """
    logger.info(f"User {current_user.id} replacing proyecto {project_id}")
    db_proyecto = await ProyectoService.replace(db, project_id, replace_data, current_user)

    if not db_proyecto:
        logger.warning(f"Proyecto {project_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proyecto with id {project_id} not found",
        )

    logger.info(f"Successfully replaced proyecto {project_id}")
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


@router.post(
    "/projects/{project_id}/start",
    response_model=ProyectoStartResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        403: {
            "model": ErrorDetail,
            "description": "Forbidden - User is not the owner of this project",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Only the project owner can perform this action"
                    }
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
        400: {
            "description": "Bad Request - Project cannot be started (invalid state or incomplete pedidos)",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_state": {
                            "summary": "Invalid project state",
                            "value": {
                                "detail": "Project can only be started from 'pendiente' state. Current state: en_ejecucion"
                            },
                        },
                        "incomplete_pedidos": {
                            "summary": "Incomplete pedidos",
                            "value": {
                                "detail": {
                                    "message": "No se puede iniciar el proyecto. 3 pedidos no están completados",
                                    "pedidos_pendientes": [
                                        {
                                            "pedido_id": "123e4567-e89b-12d3-a456-426614174000",
                                            "etapa_nombre": "Etapa 1 - Preparación",
                                            "tipo": "materiales",
                                            "estado": "COMPROMETIDO",
                                            "descripcion": "Cemento 50 bolsas",
                                        },
                                        {
                                            "pedido_id": "223e4567-e89b-12d3-a456-426614174111",
                                            "etapa_nombre": "Etapa 2 - Construcción",
                                            "tipo": "economico",
                                            "estado": "PENDIENTE",
                                            "descripcion": "Pago de mano de obra",
                                        },
                                    ],
                                }
                            },
                        },
                    }
                }
            },
        },
    },
)
async def start_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProyectoStartResponse:
    """
    Iniciar un proyecto (transición de PENDIENTE a EN_EJECUCION).

    Solo puede ser iniciado por el dueño del proyecto.
    Requiere que TODAS las etapas estén financiadas (sin pedidos pendientes).

    Si hay pedidos sin financiamiento, retorna error 400 con lista detallada.
    """
    logger.info(f"User {current_user.id} attempting to start proyecto {project_id}")

    result = await ProyectoService.start_project(db, project_id, current_user)

    logger.info(f"Successfully started proyecto {project_id}")
    return ProyectoStartResponse(**result)


@router.post(
    "/projects/{project_id}/complete",
    response_model=ProyectoCompleteResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        403: OWNERSHIP_RESPONSES[403],
        404: OWNERSHIP_RESPONSES[404],
        400: {
            "description": "Bad Request - Project cannot be finalized (invalid state or etapas pendientes)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "message": "Todas las etapas deben estar completadas antes de finalizar el proyecto.",
                            "etapas_pendientes": [
                                {
                                    "etapa_id": "123e4567-e89b-12d3-a456-426614174000",
                                    "nombre": "Etapa 1 - Preparación",
                                    "estado": "en_ejecucion",
                                }
                            ],
                        }
                    }
                }
            },
        },
    },
)
async def complete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProyectoCompleteResponse:
    """
    Finalizar un proyecto (transición de EN_EJECUCION a FINALIZADO).

    Solo el dueño del proyecto puede finalizarlo.
    Requiere que TODAS las etapas estén marcadas como completadas.
    """
    logger.info(f"User {current_user.id} attempting to complete proyecto {project_id}")

    result = await ProyectoService.complete_project(db, project_id, current_user)

    logger.info(f"Successfully completed proyecto {project_id}")
    return ProyectoCompleteResponse(**result)


@router.get(
    "/projects",
    response_model=PaginatedProyectoResponse,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        422: {
            "model": ValidationErrorDetail,
            "description": "Validation Error - Invalid query parameters",
        },
    },
)
async def list_projects(
    # Pagination
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (1-100)"),
    # Filtering
    estado: Optional[str] = Query(
        None,
        pattern="^(pendiente|en_ejecucion|finalizado)$",
        description="Filter by project status",
    ),
    tipo: Optional[str] = Query(None, max_length=100, description="Filter by project type (partial match, case-insensitive)"),
    pais: Optional[str] = Query(None, max_length=100, description="Filter by country (partial match, case-insensitive)"),
    provincia: Optional[str] = Query(None, max_length=100, description="Filter by province (partial match, case-insensitive)"),
    ciudad: Optional[str] = Query(None, max_length=100, description="Filter by city (partial match, case-insensitive)"),
    search: Optional[str] = Query(None, description="Search in title and description (case-insensitive)"),
    user_id: Optional[UUID] = Query(None, description="Filter by project owner (user ID)"),
    my_projects: bool = Query(False, description="Only show current user's projects (overrides user_id)"),
    # Sorting
    sort_by: str = Query(
        "created_at",
        pattern="^(created_at|updated_at|titulo)$",
        description="Field to sort by",
    ),
    sort_order: str = Query(
        "desc",
        pattern="^(asc|desc)$",
        description="Sort direction (asc or desc)",
    ),
    # Dependencies
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedProyectoResponse:
    """
    Listar todos los proyectos con paginación, filtros y ordenamiento.

    **Casos de Uso:**
    - **Descubrir proyectos para colaborar**: Ver todos los proyectos disponibles
    - **Ver mis propios proyectos**: `?my_projects=true`
    - **Buscar proyectos**: `?search=centro comunitario`
    - **Filtrar por ubicación**: `?pais=Argentina&provincia=Buenos Aires`
    - **Filtrar por estado**: `?estado=en_ejecucion`
    - **Filtrar por tipo**: `?tipo=Infraestructura`
    - **Combinar filtros**: Todos los filtros son combinables

    **Permisos:**
    - Todos los usuarios autenticados pueden ver todos los proyectos
    - Útil para descubrir proyectos en los que colaborar

    **Paginación:**
    - Por defecto: página 1, 20 items por página
    - Máximo: 100 items por página

    **Ordenamiento:**
    - Por defecto: ordenado por `created_at desc` (más recientes primero)
    - Campos disponibles: `created_at`, `updated_at`, `titulo`

    **Filtros:**
    - Todos los filtros de texto usan búsqueda case-insensitive y partial match
    - Los filtros se pueden combinar para búsquedas más específicas

    **Ejemplos:**
    ```
    # Listar todos los proyectos (página 1, 20 items)
    GET /api/v1/projects

    # Mis proyectos solamente
    GET /api/v1/projects?my_projects=true

    # Buscar proyectos
    GET /api/v1/projects?search=centro comunitario

    # Proyectos en ejecución en Buenos Aires
    GET /api/v1/projects?estado=en_ejecucion&provincia=Buenos Aires

    # Página 2, ordenados por título
    GET /api/v1/projects?page=2&page_size=10&sort_by=titulo&sort_order=asc

    # Combinar filtros
    GET /api/v1/projects?estado=pendiente&pais=Argentina&search=huerta
    ```
    """
    logger.info(
        f"User {current_user.id} listing projects (page={page}, page_size={page_size}, "
        f"filters: estado={estado}, tipo={tipo}, search={search}, my_projects={my_projects})"
    )

    # Override user_id if my_projects is True
    filter_user_id = current_user.id if my_projects else user_id

    # Convert estado string to enum if provided
    estado_filter = None
    if estado:
        try:
            estado_filter = EstadoProyecto(estado)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid estado value: {estado}. Must be one of: pendiente, en_ejecucion, finalizado",
            )

    # Call service layer
    projects, total = await ProyectoService.list_with_filters(
        db=db,
        page=page,
        page_size=page_size,
        estado=estado_filter,
        tipo=tipo,
        pais=pais,
        provincia=provincia,
        ciudad=ciudad,
        search=search,
        user_id=filter_user_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Convert to response schema
    items = [ProyectoListItem.model_validate(p) for p in projects]

    logger.info(
        f"Returning {len(items)} projects (total={total}, page={page}/{total_pages})"
    )

    return PaginatedProyectoResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
