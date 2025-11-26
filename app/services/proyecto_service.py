"""Proyecto service - Business logic for project operations."""

import logging
from datetime import date, datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.etapa import Etapa, EstadoEtapa
from app.models.pedido import Pedido
from app.models.proyecto import EstadoProyecto, Proyecto
from app.models.user import User
from app.schemas.proyecto import PedidoPendienteInfo, ProyectoCreate, ProyectoPut, ProyectoUpdate
from app.services.state_machine import (
    etapa_all_pedidos_financed,
    etapa_pedidos_pendientes,
    refresh_etapa_state,
)

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
        # Create Proyecto instance (estado defaults to 'pendiente')
        db_proyecto = Proyecto(
            user_id=user.id,
            titulo=proyecto_data.titulo,
            descripcion=proyecto_data.descripcion,
            tipo=proyecto_data.tipo,
            pais=proyecto_data.pais,
            provincia=proyecto_data.provincia,
            ciudad=proyecto_data.ciudad,
            barrio=proyecto_data.barrio,
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
    async def replace(
        db: AsyncSession, proyecto_id: UUID, replace_data: ProyectoPut, user: User
    ) -> Optional[Proyecto]:
        """
        Complete replacement of a proyecto (PUT).
        Only the project owner can replace the project.
        Bonita can also replace using X-API-Key bypass.
        """
        db_proyecto = await ProyectoService.get_by_id(db, proyecto_id)
        if not db_proyecto:
            return None

        # Check ownership (skip for Bonita system actor)
        if not getattr(user, "is_bonita_actor", False):
            if db_proyecto.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the project owner can replace this project",
                )
        else:
            logger.info(
                f"Skipping ownership verification for project {db_proyecto.id} because request comes from Bonita"
            )

        # Update all provided fields
        db_proyecto.titulo = replace_data.titulo
        db_proyecto.descripcion = replace_data.descripcion
        db_proyecto.tipo = replace_data.tipo
        db_proyecto.pais = replace_data.pais
        db_proyecto.provincia = replace_data.provincia
        db_proyecto.ciudad = replace_data.ciudad
        db_proyecto.barrio = replace_data.barrio
        if replace_data.estado:
            db_proyecto.estado = replace_data.estado
        if replace_data.bonita_case_id:
            db_proyecto.bonita_case_id = replace_data.bonita_case_id
        if replace_data.bonita_process_instance_id:
            db_proyecto.bonita_process_instance_id = replace_data.bonita_process_instance_id

        await db.commit()
        await db.refresh(db_proyecto)

        logger.info(f"Proyecto {proyecto_id} replaced by user {user.id}")

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

    @staticmethod
    async def start_project(
        db: AsyncSession, proyecto_id: UUID, user: User
    ) -> Dict[str, any]:
        """
        Start a project by transitioning from PENDIENTE to EN_EJECUCION.
        Only allowed when ALL etapas are financed (no pedidos pendientes).
        Only the project owner can start the project.

        Returns:
            Dict with proyecto data and success message, or raises HTTPException with
            list of incomplete pedidos.
        """
        # Fetch project with all nested data
        db_proyecto = await ProyectoService.get_by_id(db, proyecto_id)
        if not db_proyecto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proyecto with id {proyecto_id} not found",
            )

        # Verify ownership (skip for Bonita system actor)
        if not getattr(user, "is_bonita_actor", False):
            ProyectoService.verify_ownership(db_proyecto, user)
        else:
            logger.info(
                f"Skipping ownership verification for project {proyecto_id} because request comes from Bonita"
            )

        # Check current state
        if db_proyecto.estado != EstadoProyecto.pendiente.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project can only be started from 'pendiente' state. Current state: {db_proyecto.estado}",
            )

        # Re-evaluate etapa states before validating financing
        for etapa in db_proyecto.etapas:
            refresh_etapa_state(etapa)

        pedidos_sin_financiar: List[PedidoPendienteInfo] = []

        for etapa in db_proyecto.etapas:
            pending_pedidos = etapa_pedidos_pendientes(etapa)
            for pedido in pending_pedidos:
                pedidos_sin_financiar.append(
                    PedidoPendienteInfo(
                        pedido_id=pedido.id,
                        etapa_nombre=etapa.nombre,
                        tipo=pedido.tipo.value,
                        estado=pedido.estado.value,
                        descripcion=pedido.descripcion,
                    )
                )

        if pedidos_sin_financiar:
            count = len(pedidos_sin_financiar)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": f"No se puede iniciar el proyecto. {count} pedido{'s' if count != 1 else ''} no {'están' if count != 1 else 'está'} financiado{'s' if count != 1 else ''}",
                    "pedidos_pendientes": [p.model_dump() for p in pedidos_sin_financiar],
                },
            )

        # All etapas financed, advance project and etapas
        db_proyecto.estado = EstadoProyecto.en_ejecucion.value
        db_proyecto.fecha_en_ejecucion = datetime.now(timezone.utc)
        # Transition etapas to esperando_ejecucion (awaiting manual start)
        for etapa in db_proyecto.etapas:
            if etapa.estado != EstadoEtapa.completada:
                etapa.estado = EstadoEtapa.esperando_ejecucion
                etapa.fecha_completitud = None

        await db.commit()
        await db.refresh(db_proyecto)

        logger.info(
            f"Project {proyecto_id} started by user {user.id}. Transitioned to EN_EJECUCION"
        )

        return {
            "id": db_proyecto.id,
            "titulo": db_proyecto.titulo,
            "estado": db_proyecto.estado,
            "message": "Proyecto iniciado exitosamente",
        }

    @staticmethod
    async def complete_project(
        db: AsyncSession, proyecto_id: UUID, user: User
    ) -> Dict[str, any]:
        """
        Complete a project by transitioning from EN_EJECUCION to FINALIZADO.
        Only allowed when ALL etapas are marked as COMPLETADA.
        """
        db_proyecto = await ProyectoService.get_by_id(db, proyecto_id)
        if not db_proyecto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proyecto with id {proyecto_id} not found",
            )

        logger.info(
            f"Attempting to complete project {proyecto_id}. Current estado: {db_proyecto.estado}"
        )

        # Verify project ownership (skip for Bonita system actor)
        if not getattr(user, "is_bonita_actor", False):
            ProyectoService.verify_ownership(db_proyecto, user)
        else:
            logger.info(
                f"Skipping ownership verification for project {db_proyecto.id} because request comes from Bonita"
            )

        if db_proyecto.estado != EstadoProyecto.en_ejecucion.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project can only be completed from 'en_ejecucion' state. Current state: {db_proyecto.estado}",
            )

        # Validate all etapas are completed (no state modification)
        etapas_incompletas: List[Dict[str, str]] = []
        for etapa in db_proyecto.etapas:
            if etapa.estado != EstadoEtapa.completada:
                etapas_incompletas.append(
                    {
                        "etapa_id": str(etapa.id),
                        "nombre": etapa.nombre,
                        "estado": etapa.estado.value,
                    }
                )

        if etapas_incompletas:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Todas las etapas deben estar completadas antes de finalizar el proyecto.",
                    "etapas_pendientes": etapas_incompletas,
                },
            )

        db_proyecto.estado = EstadoProyecto.finalizado.value
        db_proyecto.fecha_finalizado = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(db_proyecto)

        logger.info(
            f"Project {proyecto_id} finalized by user {user.id}. Transitioned to FINALIZADO"
        )

        return {
            "id": db_proyecto.id,
            "titulo": db_proyecto.titulo,
            "estado": db_proyecto.estado,
            "message": "Proyecto finalizado exitosamente",
        }

    @staticmethod
    async def list_with_filters(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        estado: Optional[EstadoProyecto] = None,
        tipo: Optional[str] = None,
        pais: Optional[str] = None,
        provincia: Optional[str] = None,
        ciudad: Optional[str] = None,
        search: Optional[str] = None,
        user_id: Optional[UUID] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[List[Proyecto], int]:
        """
        List projects with filtering, sorting, and pagination.

        Args:
            db: Database session
            page: Page number (1-indexed)
            page_size: Number of items per page
            estado: Filter by project status
            tipo: Filter by project type (case-insensitive partial match)
            pais: Filter by country (case-insensitive partial match)
            provincia: Filter by province (case-insensitive partial match)
            ciudad: Filter by city (case-insensitive partial match)
            search: Search in titulo and descripcion (case-insensitive)
            user_id: Filter by project owner
            sort_by: Field to sort by (created_at, updated_at, titulo)
            sort_order: Sort direction (asc or desc)

        Returns:
            Tuple of (list of projects, total count)
        """
        # Build base query (no eager loading for list view - performance optimization)
        stmt = select(Proyecto)

        # Apply filters
        if estado:
            stmt = stmt.where(Proyecto.estado == estado.value)

        if tipo:
            stmt = stmt.where(Proyecto.tipo.ilike(f"%{tipo}%"))

        if pais:
            stmt = stmt.where(Proyecto.pais.ilike(f"%{pais}%"))

        if provincia:
            stmt = stmt.where(Proyecto.provincia.ilike(f"%{provincia}%"))

        if ciudad:
            stmt = stmt.where(Proyecto.ciudad.ilike(f"%{ciudad}%"))

        if search:
            # Search in both titulo and descripcion
            search_pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Proyecto.titulo.ilike(search_pattern),
                    Proyecto.descripcion.ilike(search_pattern),
                )
            )

        if user_id:
            stmt = stmt.where(Proyecto.user_id == user_id)

        # Get total count BEFORE pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # Apply sorting
        sort_column = getattr(Proyecto, sort_by)
        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        # Execute query
        result = await db.execute(stmt)
        projects = list(result.unique().scalars().all())

        logger.info(
            f"Listed {len(projects)} projects (page {page}, total={total}) with filters: "
            f"estado={estado}, tipo={tipo}, pais={pais}, search={search}, user_id={user_id}"
        )

        return projects, total
