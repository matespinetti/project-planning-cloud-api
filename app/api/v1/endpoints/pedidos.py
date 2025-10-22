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
from app.schemas.pedido import PedidoCreate, PedidoResponse
from app.services.pedido_service import PedidoService

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post(
    "/projects/{project_id}/etapas/{etapa_id}/pedidos",
    response_model=PedidoResponse,
    status_code=status.HTTP_201_CREATED,
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
)
async def list_project_pedidos(
    project_id: UUID,
    estado: Optional[str] = Query(
        None,
        description="Filter by estado (pendiente or completado)",
        pattern="^(pendiente|completado)$",
    ),
    db: AsyncSession = Depends(get_db),
) -> List[PedidoResponse]:
    """
    Listar todos los pedidos de un proyecto específico, opcionalmente filtrados por estado.
    Cualquier usuario autenticado puede ver pedidos.
    """
    logger.info(f"Fetching pedidos for project {project_id} with estado filter: {estado}")

    # Convert estado string to enum if provided
    estado_filter = None
    if estado:
        estado_filter = EstadoPedido.PENDIENTE if estado == "pendiente" else EstadoPedido.COMPLETADO

    pedidos = await PedidoService.list_by_proyecto(db, project_id, estado_filter)

    return [PedidoResponse.model_validate(pedido) for pedido in pedidos]


@router.delete(
    "/pedidos/{pedido_id}",
    status_code=status.HTTP_204_NO_CONTENT,
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
