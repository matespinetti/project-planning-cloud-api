"""Pedido service - Business logic for pedido operations."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.etapa import Etapa
from app.models.pedido import EstadoPedido, Pedido
from app.models.proyecto import Proyecto
from app.models.user import User
from app.schemas.pedido import PedidoCreate

logger = logging.getLogger(__name__)


class PedidoService:
    """Service for pedido-related operations."""

    @staticmethod
    async def create_for_etapa(
        db: AsyncSession,
        proyecto_id: UUID,
        etapa_id: UUID,
        pedido_data: PedidoCreate,
        user: User,
    ) -> Pedido:
        """
        Create a new pedido for an existing etapa.
        Only the project owner can create pedidos.
        """
        # Get the proyecto and verify ownership
        proyecto = await db.get(Proyecto, proyecto_id)
        if not proyecto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proyecto with id {proyecto_id} not found",
            )

        if proyecto.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project owner can create pedidos",
            )

        # Verify etapa exists and belongs to proyecto
        etapa = await db.get(Etapa, etapa_id)
        if not etapa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Etapa with id {etapa_id} not found",
            )

        if etapa.proyecto_id != proyecto_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Etapa {etapa_id} does not belong to proyecto {proyecto_id}",
            )

        # Create the pedido
        db_pedido = Pedido(
            etapa_id=etapa_id,
            tipo=pedido_data.tipo,
            descripcion=pedido_data.descripcion,
            monto=pedido_data.monto,
            moneda=pedido_data.moneda,
            cantidad=pedido_data.cantidad,
            unidad=pedido_data.unidad,
            estado=EstadoPedido.PENDIENTE,
        )

        db.add(db_pedido)
        await db.commit()
        await db.refresh(db_pedido)

        logger.info(f"Pedido {db_pedido.id} created for etapa {etapa_id} by user {user.id}")
        return db_pedido

    @staticmethod
    async def get_by_id(db: AsyncSession, pedido_id: UUID) -> Optional[Pedido]:
        """Get a pedido by ID."""
        return await db.get(Pedido, pedido_id)

    @staticmethod
    async def list_by_proyecto(
        db: AsyncSession,
        proyecto_id: UUID,
        estado_filter: Optional[EstadoPedido] = None,
    ) -> List[Pedido]:
        """
        List all pedidos for a proyecto, optionally filtered by estado.
        Returns pedidos with eager loading of etapa relationship.
        """
        # Verify proyecto exists
        proyecto = await db.get(Proyecto, proyecto_id)
        if not proyecto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proyecto with id {proyecto_id} not found",
            )

        # Build query to get all pedidos from all etapas of the proyecto
        stmt = (
            select(Pedido)
            .join(Etapa, Pedido.etapa_id == Etapa.id)
            .where(Etapa.proyecto_id == proyecto_id)
            .options(joinedload(Pedido.etapa))
            .order_by(Pedido.etapa_id, Pedido.tipo)
        )

        # Apply estado filter if provided
        if estado_filter:
            stmt = stmt.where(Pedido.estado == estado_filter)

        result = await db.execute(stmt)
        return list(result.unique().scalars().all())

    @staticmethod
    async def delete(db: AsyncSession, pedido_id: UUID, user: User) -> bool:
        """
        Delete a pedido (cascades to ofertas).
        Only the project owner can delete pedidos.
        """
        # Get pedido
        pedido = await db.get(Pedido, pedido_id)
        if not pedido:
            return False

        # Get etapa to verify proyecto ownership
        etapa = await db.get(Etapa, pedido.etapa_id)
        if not etapa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Etapa not found",
            )

        # Get proyecto to verify ownership
        proyecto = await db.get(Proyecto, etapa.proyecto_id)
        if not proyecto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto not found",
            )

        if proyecto.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project owner can delete pedidos",
            )

        # Delete the pedido (ofertas will be cascade deleted)
        await db.delete(pedido)
        await db.commit()

        logger.info(f"Pedido {pedido_id} deleted by user {user.id}")
        return True

    @staticmethod
    async def mark_as_comprometido(db: AsyncSession, pedido_id: UUID) -> Pedido:
        """
        Mark a pedido as comprometido (committed).
        This is called internally when an oferta is accepted by the project owner.
        """
        pedido = await db.get(Pedido, pedido_id)
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido with id {pedido_id} not found",
            )

        pedido.estado = EstadoPedido.COMPROMETIDO
        await db.commit()
        await db.refresh(pedido)

        logger.info(f"Pedido {pedido_id} marked as comprometido")
        return pedido

    @staticmethod
    async def mark_as_completed(db: AsyncSession, pedido_id: UUID) -> Pedido:
        """
        Mark a pedido as completed.
        This is called internally when the oferente confirms the commitment.
        """
        pedido = await db.get(Pedido, pedido_id)
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido with id {pedido_id} not found",
            )

        pedido.estado = EstadoPedido.COMPLETADO
        await db.commit()
        await db.refresh(pedido)

        logger.info(f"Pedido {pedido_id} marked as completed")
        return pedido
