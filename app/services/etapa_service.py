"""Etapa service - Business logic for etapa operations."""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.etapa import Etapa, EstadoEtapa
from app.models.pedido import EstadoPedido, Pedido
from app.models.proyecto import EstadoProyecto, Proyecto
from app.models.user import User
from app.services.state_machine import etapa_pedidos_pendientes

logger = logging.getLogger(__name__)


class EtapaService:
    """Service for etapa-related operations."""

    @staticmethod
    async def get_by_id(db: AsyncSession, etapa_id: UUID) -> Optional[Etapa]:
        """
        Get an etapa by ID with all nested data (eager loading).
        """
        stmt = (
            select(Etapa)
            .where(Etapa.id == etapa_id)
            .options(joinedload(Etapa.pedidos), joinedload(Etapa.proyecto))
        )
        result = await db.execute(stmt)
        return result.unique().scalar_one_or_none()

    @staticmethod
    async def list_by_project(
        db: AsyncSession,
        proyecto_id: UUID,
        estado: Optional[EstadoEtapa] = None,
    ) -> List[Etapa]:
        """
        List all etapas for a specific project, optionally filtered by estado.

        Args:
            db: Database session
            proyecto_id: Project ID
            estado: Optional filter by etapa status

        Returns:
            List of etapas with pedidos loaded
        """
        stmt = (
            select(Etapa)
            .where(Etapa.proyecto_id == proyecto_id)
            .options(joinedload(Etapa.pedidos))
            .order_by(Etapa.fecha_inicio)
        )

        if estado:
            stmt = stmt.where(Etapa.estado == estado.value)

        result = await db.execute(stmt)
        etapas = list(result.unique().scalars().all())

        logger.info(
            f"Listed {len(etapas)} etapas for project {proyecto_id}"
            + (f" with estado={estado.value}" if estado else "")
        )

        return etapas

    @staticmethod
    async def start_etapa(
        db: AsyncSession, etapa_id: UUID, user: User
    ) -> Dict[str, any]:
        """
        Start an etapa by transitioning from financiada to en_ejecucion.

        Validations:
        - Only the project owner can start etapas
        - Project must be en_ejecucion
        - Etapa must be financiada (all pedidos completed)
        - Cannot start if already started or completed

        Returns:
            Dict with etapa data and success message
        """
        # Fetch etapa with project
        db_etapa = await EtapaService.get_by_id(db, etapa_id)
        if not db_etapa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Etapa with id {etapa_id} not found",
            )

        # Verify project ownership
        if db_etapa.proyecto.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project owner can start etapas",
            )

        # Check project is in execution
        if db_etapa.proyecto.estado != EstadoProyecto.en_ejecucion.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project must be 'en_ejecucion' to start etapas. Current state: {db_etapa.proyecto.estado}",
            )

        # Check etapa current state
        if db_etapa.estado == EstadoEtapa.en_ejecucion:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Etapa is already in execution",
            )

        if db_etapa.estado == EstadoEtapa.completada:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot start a completed etapa",
            )

        if db_etapa.estado == EstadoEtapa.pendiente:
            # Check if has pending pedidos
            pending_pedidos = etapa_pedidos_pendientes(db_etapa)
            if pending_pedidos:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": f"Cannot start etapa with {len(pending_pedidos)} pending pedidos. All pedidos must be completed first.",
                        "pending_pedidos": [
                            {
                                "id": str(p.id),
                                "tipo": p.tipo.value,
                                "estado": p.estado.value,
                                "descripcion": p.descripcion,
                            }
                            for p in pending_pedidos
                        ],
                    },
                )

        # Transition to en_ejecucion
        db_etapa.estado = EstadoEtapa.en_ejecucion
        await db.commit()
        await db.refresh(db_etapa)

        logger.info(
            f"Etapa {etapa_id} started by user {user.id}. Transitioned to en_ejecucion"
        )

        return {
            "id": db_etapa.id,
            "nombre": db_etapa.nombre,
            "estado": db_etapa.estado.value,
            "message": "Etapa iniciada exitosamente",
        }

    @staticmethod
    async def complete_etapa(
        db: AsyncSession, etapa_id: UUID, user: User
    ) -> Dict[str, any]:
        """
        Complete an etapa by transitioning from en_ejecucion to completada.

        Validations:
        - Only the project owner can complete etapas
        - Project must be en_ejecucion
        - Etapa must be en_ejecucion

        Returns:
            Dict with etapa data and success message
        """
        # Fetch etapa with project
        db_etapa = await EtapaService.get_by_id(db, etapa_id)
        if not db_etapa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Etapa with id {etapa_id} not found",
            )

        # Verify project ownership
        if db_etapa.proyecto.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project owner can complete etapas",
            )

        # Check project is in execution
        if db_etapa.proyecto.estado != EstadoProyecto.en_ejecucion.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project must be 'en_ejecucion' to complete etapas. Current state: {db_etapa.proyecto.estado}",
            )

        # Check etapa current state
        if db_etapa.estado != EstadoEtapa.en_ejecucion:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Etapa can only be completed from 'en_ejecucion' state. Current state: {db_etapa.estado.value}",
            )

        # Transition to completada and set completion timestamp
        db_etapa.estado = EstadoEtapa.completada
        db_etapa.fecha_completitud = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(db_etapa)

        logger.info(
            f"Etapa {etapa_id} completed by user {user.id}. Transitioned to completada"
        )

        return {
            "id": db_etapa.id,
            "nombre": db_etapa.nombre,
            "estado": db_etapa.estado.value,
            "fecha_completitud": db_etapa.fecha_completitud,
            "message": "Etapa completada exitosamente",
        }
