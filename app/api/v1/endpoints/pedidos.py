"""Pedido endpoints."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.pedido import EstadoPedido
from app.models.user import User
from app.schemas.errors import OWNERSHIP_RESPONSES, ErrorDetail, ValidationErrorDetail
from app.schemas.pedido import PedidoCreate, PedidoUpdate, PedidoResponse
from app.services.pedido_service import PedidoService

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post(
    "/projects/{project_id}/etapas/{etapa_id}/pedidos",
    response_model=PedidoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        403: {
            "model": ErrorDetail,
            "description": "Forbidden - User is not the owner of the project",
            "content": {
                "application/json": {
                    "example": {"detail": "You are not the owner of this project"}
                }
            },
        },
        404: {
            "model": ErrorDetail,
            "description": "Not Found - Project or Etapa does not exist",
            "content": {
                "application/json": {
                    "examples": {
                        "project_not_found": {
                            "summary": "Project not found",
                            "value": {
                                "detail": "Proyecto with id 123e4567-e89b-12d3-a456-426614174000 not found"
                            },
                        },
                        "etapa_not_found": {
                            "summary": "Etapa not found",
                            "value": {
                                "detail": "Etapa with id 123e4567-e89b-12d3-a456-426614174000 not found in proyecto"
                            },
                        },
                    }
                }
            },
        },
        422: {
            "model": ValidationErrorDetail,
            "description": "Validation Error - Invalid pedido data",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "tipo"],
                                "msg": "value is not a valid enumeration member",
                                "type": "type_error.enum",
                            }
                        ]
                    }
                }
            },
        },
    },
)
async def create_pedido(
    project_id: UUID,
    etapa_id: UUID,
    pedido_data: PedidoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PedidoResponse:
    """
    Crear un nuevo pedido para una etapa existente.
    Solo el dueño del proyecto puede crear pedidos.
    """
    logger.info(
        f"User {current_user.id} creating pedido for etapa {etapa_id} in project {project_id}"
    )

    pedido = await PedidoService.create_for_etapa(
        db, project_id, etapa_id, pedido_data, current_user
    )

    logger.info(f"Successfully created pedido {pedido.id}")
    return PedidoResponse.model_validate(pedido)


@router.get(
    "/projects/{project_id}/pedidos",
    response_model=List[PedidoResponse],
    responses={
        401: OWNERSHIP_RESPONSES[401],
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
        422: {
            "model": ValidationErrorDetail,
            "description": "Validation Error - Invalid estado filter value",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["query", "estado"],
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
async def list_project_pedidos(
    project_id: UUID,
    estado: Optional[str] = Query(
        None,
        description="Filter by estado (PENDIENTE, COMPROMETIDO, or COMPLETADO)",
        pattern="^(PENDIENTE|COMPROMETIDO|COMPLETADO)$",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PedidoResponse]:
    """
    Listar todos los pedidos de un proyecto específico, opcionalmente filtrados por estado.
    Cualquier usuario autenticado puede ver pedidos.
    """
    logger.info(f"Fetching pedidos for project {project_id} with estado filter: {estado}")

    # Convert estado string to enum if provided
    estado_filter = None
    if estado:
        estado_filter = EstadoPedido(estado)

    pedidos = await PedidoService.list_by_proyecto(
        db, project_id, estado_filter, current_user.id
    )

    return [PedidoResponse.model_validate(pedido) for pedido in pedidos]


@router.delete(
    "/pedidos/{pedido_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        403: {
            "model": ErrorDetail,
            "description": "Forbidden - User is not the owner of the project",
            "content": {
                "application/json": {
                    "example": {"detail": "You are not the owner of this project"}
                }
            },
        },
        404: {
            "model": ErrorDetail,
            "description": "Not Found - Pedido does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Pedido with id 123e4567-e89b-12d3-a456-426614174000 not found"
                    }
                }
            },
        },
    },
)
async def delete_pedido(
    pedido_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Eliminar un pedido (en cascada a ofertas).
    Solo el dueño del proyecto puede eliminar pedidos.
    """
    logger.info(f"User {current_user.id} deleting pedido {pedido_id}")

    deleted = await PedidoService.delete(db, pedido_id, current_user)

    if not deleted:
        logger.warning(f"Pedido {pedido_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido with id {pedido_id} not found",
        )

    logger.info(f"Successfully deleted pedido {pedido_id}")


@router.get(
    "/pedidos/{pedido_id}",
    response_model=PedidoResponse,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        404: {
            "model": ErrorDetail,
            "description": "Not Found - Pedido does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Pedido with id 123e4567-e89b-12d3-a456-426614174000 not found"
                    }
                }
            },
        },
    },
)
async def get_pedido(
    pedido_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PedidoResponse:
    """
    Obtener detalles de un pedido específico.
    """
    logger.info(f"User {current_user.id} fetching pedido {pedido_id}")

    pedido = await PedidoService.get_by_id(db, pedido_id)

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido with id {pedido_id} not found",
        )

    return PedidoResponse.model_validate(pedido)


@router.patch(
    "/pedidos/{pedido_id}",
    response_model=PedidoResponse,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        403: {
            "model": ErrorDetail,
            "description": "Forbidden - User is not the owner of the project",
            "content": {
                "application/json": {
                    "example": {"detail": "Only the project owner can update pedidos"}
                }
            },
        },
        404: {
            "model": ErrorDetail,
            "description": "Not Found - Pedido does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Pedido with id 123e4567-e89b-12d3-a456-426614174000 not found"
                    }
                }
            },
        },
        400: {
            "model": ErrorDetail,
            "description": "Bad Request - Pedido cannot be updated in current state",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Cannot update pedido in state 'COMPROMETIDO'. Pedidos can only be updated while in PENDIENTE state."
                    }
                }
            },
        },
    },
)
async def update_pedido(
    pedido_id: UUID,
    pedido_data: PedidoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PedidoResponse:
    """
    Actualizar un pedido.
    Solo el dueño del proyecto puede actualizar pedidos.
    Los pedidos solo pueden actualizarse si están en estado PENDIENTE.

    Campos que se pueden actualizar:
    - tipo: Tipo de pedido (economico, materiales, mano_obra, transporte, equipamiento)
    - descripcion: Descripción del pedido
    - monto: Monto del presupuesto
    - moneda: Código de moneda (ej: ARS, USD)
    - cantidad: Cantidad requerida
    - unidad: Unidad de medida
    """
    logger.info(f"User {current_user.id} updating pedido {pedido_id}")

    pedido = await PedidoService.update(db, pedido_id, pedido_data, current_user)

    return PedidoResponse.model_validate(pedido)
