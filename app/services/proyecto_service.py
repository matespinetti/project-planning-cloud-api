"""Proyecto service - Business logic for project operations."""

import logging
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.etapa import Etapa
from app.models.pedido import Pedido
from app.models.proyecto import Proyecto
from app.models.user import User
from app.schemas.proyecto import ProyectoCreate, ProyectoUpdate

logger = logging.getLogger(__name__)


class ProyectoService:
    """Service for proyecto-related operations."""

    @staticmethod
    async def create(
        db: AsyncSession, proyecto_data: ProyectoCreate, user: User
    ) -> Proyecto:
        """
        Create a proyecto with nested etapas and pedidos in a single transaction.
        The user_id is automatically set from the authenticated user.
        """
        # Create Proyecto instance
        db_proyecto = Proyecto(
            user_id=user.id,
            titulo=proyecto_data.titulo,
            descripcion=proyecto_data.descripcion,
            tipo=proyecto_data.tipo,
            pais=proyecto_data.pais,
            provincia=proyecto_data.provincia,
            ciudad=proyecto_data.ciudad,
            barrio=proyecto_data.barrio,
            estado=proyecto_data.estado,
            bonita_case_id=proyecto_data.bonita_case_id,
            bonita_process_instance_id=proyecto_data.bonita_process_instance_id,
        )

        # Create Etapas with Pedidos
        for etapa_data in proyecto_data.etapas:
            db_etapa = Etapa(
                nombre=etapa_data.nombre,
                descripcion=etapa_data.descripcion,
                fecha_inicio=date.fromisoformat(etapa_data.fecha_inicio),
                fecha_fin=date.fromisoformat(etapa_data.fecha_fin),
            )

            # Create Pedidos for this Etapa
            for pedido_data in etapa_data.pedidos:
                db_pedido = Pedido(
                    tipo=pedido_data.tipo,
                    descripcion=pedido_data.descripcion,
                    monto=pedido_data.monto,
                    moneda=pedido_data.moneda,
                    cantidad=pedido_data.cantidad,
                    unidad=pedido_data.unidad,
                )
                db_etapa.pedidos.append(db_pedido)

            db_proyecto.etapas.append(db_etapa)

        db.add(db_proyecto)
        await db.commit()
        await db.refresh(db_proyecto)

        return db_proyecto

    @staticmethod
    async def get_by_id(db: AsyncSession, proyecto_id: UUID) -> Optional[Proyecto]:
        """
        Get a proyecto by ID with all nested data (eager loading).
        """
        stmt = (
            select(Proyecto)
            .where(Proyecto.id == proyecto_id)
            .options(joinedload(Proyecto.etapas).joinedload(Etapa.pedidos))
        )
        result = await db.execute(stmt)
        return result.unique().scalar_one_or_none()

    @staticmethod
    async def update(
        db: AsyncSession, proyecto_id: UUID, update_data: ProyectoUpdate, user: User
    ) -> Optional[Proyecto]:
        """
        Partial update of a proyecto (PATCH).
        Only the project owner can update the project.
        """
        db_proyecto = await ProyectoService.get_by_id(db, proyecto_id)
        if not db_proyecto:
            return None

        # Check ownership
        if db_proyecto.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project owner can update this project",
            )

        # Update only provided fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(db_proyecto, key, value)

        await db.commit()
        await db.refresh(db_proyecto)

        return db_proyecto

    @staticmethod
    async def delete(db: AsyncSession, proyecto_id: UUID, user: User) -> bool:
        """
        Delete a proyecto (cascades to etapas and pedidos).
        Only the project owner can delete the project.
        """
        db_proyecto = await ProyectoService.get_by_id(db, proyecto_id)
        if not db_proyecto:
            return False

        # Check ownership
        if db_proyecto.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project owner can delete this project",
            )

        await db.delete(db_proyecto)
        await db.commit()

        return True

    @staticmethod
    def verify_ownership(proyecto: Proyecto, user: User) -> None:
        """
        Verify that the user is the owner of the project.
        Raises HTTPException if not.
        """
        if proyecto.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project owner can perform this action",
            )
