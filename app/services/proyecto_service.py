"""Proyecto service - Business logic for project operations."""

import logging
from datetime import date
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.etapa import Etapa
from app.models.pedido import EstadoPedido, Pedido
from app.models.proyecto import EstadoProyecto, Proyecto
from app.models.user import User
from app.schemas.proyecto import PedidoPendienteInfo, ProyectoCreate, ProyectoUpdate

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

    @staticmethod
    async def start_project(
        db: AsyncSession, proyecto_id: UUID, user: User
    ) -> Dict[str, any]:
        """
        Start a project by transitioning from EN_PLANIFICACION to EN_EJECUCION.
        Only allowed when ALL pedidos from ALL etapas are in COMPLETADO state.
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

        # Verify ownership
        ProyectoService.verify_ownership(db_proyecto, user)

        # Check current state
        if db_proyecto.estado != EstadoProyecto.EN_PLANIFICACION.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project can only be started from 'en_planificacion' state. Current state: {db_proyecto.estado}",
            )

        # Check if all pedidos are COMPLETADO
        pedidos_pendientes: List[PedidoPendienteInfo] = []

        for etapa in db_proyecto.etapas:
            for pedido in etapa.pedidos:
                if pedido.estado != EstadoPedido.COMPLETADO:
                    pedidos_pendientes.append(
                        PedidoPendienteInfo(
                            pedido_id=pedido.id,
                            etapa_nombre=etapa.nombre,
                            tipo=pedido.tipo.value,
                            estado=pedido.estado.value,
                            descripcion=pedido.descripcion,
                        )
                    )

        # If there are incomplete pedidos, raise error with details
        if pedidos_pendientes:
            count = len(pedidos_pendientes)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": f"No se puede iniciar el proyecto. {count} pedido{'s' if count > 1 else ''} no {'están' if count > 1 else 'está'} completado{'s' if count > 1 else ''}",
                    "pedidos_pendientes": [p.model_dump() for p in pedidos_pendientes],
                },
            )

        # All pedidos are completed, update state
        db_proyecto.estado = EstadoProyecto.EN_EJECUCION.value
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
