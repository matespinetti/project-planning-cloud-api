"""Observacion service - Business logic for observation operations."""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.observacion import EstadoObservacion, Observacion
from app.models.proyecto import EstadoProyecto, Proyecto
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


class ObservacionService:
    """Service for observacion-related operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
        proyecto_id: UUID,
        descripcion: str,
        council_user: User,
        bonita_case_id: Optional[str] = None,
        bonita_process_instance_id: Optional[int] = None,
    ) -> Observacion:
        """
        Create a new observacion for a project.

        Only council members can create observations.
        Only for projects in EN_EJECUCION state.
        Deadline is automatically set to 5 days from creation.

        Args:
            db: Database session
            proyecto_id: ID of the project to observe
            descripcion: Observation description
            council_user: Council member creating the observation
            bonita_case_id: Optional Bonita case ID for workflow tracking
            bonita_process_instance_id: Optional Bonita process instance ID

        Returns:
            Created Observacion instance

        Raises:
            HTTPException: If user is not council, project not found, or project not in execution
        """
        # Verify user is council member
        if council_user.role != UserRole.COUNCIL:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only council members can create observations",
            )

        # Verify proyecto exists
        proyecto = await db.get(Proyecto, proyecto_id)
        if not proyecto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proyecto with id {proyecto_id} not found",
            )

        # Verify proyecto is in en_ejecucion state
        if proyecto.estado != EstadoProyecto.en_ejecucion.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Observations can only be created for projects in 'en_ejecucion' state. "
                f"Current state: {proyecto.estado}",
            )

        # Calculate deadline (5 days from today)
        fecha_limite = date.today() + timedelta(days=5)

        # Create observacion
        db_observacion = Observacion(
            proyecto_id=proyecto_id,
            council_user_id=council_user.id,
            descripcion=descripcion,
            estado=EstadoObservacion.pendiente,
            fecha_limite=fecha_limite,
            bonita_case_id=bonita_case_id,
            bonita_process_instance_id=bonita_process_instance_id,
        )

        db.add(db_observacion)
        await db.commit()
        await db.refresh(db_observacion)

        logger.info(
            f"Observacion {db_observacion.id} created by council user {council_user.id} "
            f"for project {proyecto_id} with deadline {fecha_limite}"
        )
        return db_observacion

    @staticmethod
    async def get_by_id(db: AsyncSession, observacion_id: UUID) -> Optional[Observacion]:
        """
        Get an observacion by ID with relationships.

        Automatically checks and updates status if overdue.

        Args:
            db: Database session
            observacion_id: ID of the observacion

        Returns:
            Observacion instance or None if not found
        """
        stmt = (
            select(Observacion)
            .where(Observacion.id == observacion_id)
            .options(
                joinedload(Observacion.proyecto),
                joinedload(Observacion.council_user),
            )
        )
        result = await db.execute(stmt)
        observacion = result.unique().scalar_one_or_none()

        if observacion:
            if ObservacionService._check_and_update_overdue(observacion):
                await db.commit()
                await db.refresh(observacion)
            return observacion
        return None

    @staticmethod
    async def list_by_proyecto(
        db: AsyncSession,
        proyecto_id: UUID,
        estado_filter: Optional[str] = None,
    ) -> List[Observacion]:
        """
        List all observaciones for a project.

        Automatically updates overdue observations before returning.

        Args:
            db: Database session
            proyecto_id: ID of the project
            estado_filter: Optional filter by estado (pendiente, resuelta, vencida)

        Returns:
            List of Observacion instances

        Raises:
            HTTPException: If project not found or invalid estado filter
        """
        # Verify proyecto exists
        proyecto = await db.get(Proyecto, proyecto_id)
        if not proyecto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proyecto with id {proyecto_id} not found",
            )

        # Build query
        stmt = (
            select(Observacion)
            .where(Observacion.proyecto_id == proyecto_id)
            .options(joinedload(Observacion.council_user))
            .order_by(Observacion.created_at.desc())
        )

        # Apply estado filter if provided
        if estado_filter:
            valid_estados = ["pendiente", "resuelta", "vencida"]
            if estado_filter not in valid_estados:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid estado filter. Must be one of: {valid_estados}",
                )
            stmt = stmt.where(Observacion.estado == EstadoObservacion(estado_filter))

        result = await db.execute(stmt)
        observaciones = list(result.unique().scalars().all())

        # Check and update overdue observations
        updated = False
        for obs in observaciones:
            if ObservacionService._check_and_update_overdue(obs):
                updated = True

        if updated:
            await db.commit()
            # Refresh all observations
            for obs in observaciones:
                await db.refresh(obs)

        logger.info(
            f"Listed {len(observaciones)} observaciones for project {proyecto_id} "
            f"with estado filter: {estado_filter}"
        )
        return observaciones

    @staticmethod
    async def update(
        db: AsyncSession,
        observacion_id: UUID,
        update_data: dict,
        current_user: User,
    ) -> Observacion:
        """
        Update an observacion (PATCH).

        Only the council member who created the observation or the project owner can update it.
        Deadline, resolution info, and estado cannot be modified.

        Args:
            db: Database session
            observacion_id: ID of the observacion to update
            update_data: Dictionary with fields to update (descripcion, bonita_case_id, bonita_process_instance_id)
            current_user: User performing the update

        Returns:
            Updated Observacion instance

        Raises:
            HTTPException: If not found or insufficient permissions
        """
        # Get observacion with proyecto relationship
        stmt = (
            select(Observacion)
            .where(Observacion.id == observacion_id)
            .options(joinedload(Observacion.proyecto))
        )
        result = await db.execute(stmt)
        observacion = result.unique().scalar_one_or_none()

        if not observacion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Observacion with id {observacion_id} not found",
            )

        # Check and update if overdue
        ObservacionService._check_and_update_overdue(observacion)

        # Verify authorization: council member who created it or project owner
        is_creator = observacion.council_user_id == current_user.id
        is_project_owner = observacion.proyecto.user_id == current_user.id

        if not (is_creator or is_project_owner):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the council member who created the observation or the project owner can update it",
            )

        # Update only provided fields
        for key, value in update_data.items():
            if value is not None and hasattr(observacion, key):
                setattr(observacion, key, value)

        await db.commit()
        await db.refresh(observacion)

        logger.info(f"Observacion {observacion_id} updated by user {current_user.id}")
        return observacion

    @staticmethod
    async def resolve(
        db: AsyncSession,
        observacion_id: UUID,
        respuesta: str,
        executor_user: User,
    ) -> Observacion:
        """
        Resolve an observacion.

        Only the project executor (owner) can resolve observations.
        Can resolve even if observation is overdue (vencida).
        Bonita system actor can bypass ownership check.

        Args:
            db: Database session
            observacion_id: ID of the observacion to resolve
            respuesta: Response from project executor
            executor_user: User resolving the observation

        Returns:
            Resolved Observacion instance

        Raises:
            HTTPException: If not found, not project owner, or already resolved
        """
        # Get observacion with proyecto relationship
        stmt = (
            select(Observacion)
            .where(Observacion.id == observacion_id)
            .options(joinedload(Observacion.proyecto))
        )
        result = await db.execute(stmt)
        observacion = result.unique().scalar_one_or_none()

        if not observacion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Observacion with id {observacion_id} not found",
            )

        # Check and update if overdue
        ObservacionService._check_and_update_overdue(observacion)

        # Verify user is the project owner or is Bonita system actor
        is_bonita_actor = getattr(executor_user, "is_bonita_actor", False)
        if not (observacion.proyecto.user_id == executor_user.id or is_bonita_actor):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project executor (owner) can resolve observations",
            )

        # Check if already resolved
        if observacion.estado == EstadoObservacion.resuelta:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Observacion is already resolved",
            )

        # Resolve the observacion
        observacion.estado = EstadoObservacion.resuelta
        observacion.respuesta = respuesta
        observacion.fecha_resolucion = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(observacion)

        logger.info(
            f"Observacion {observacion_id} resolved by user {executor_user.id}. "
            f"Was {'overdue' if observacion.estado == EstadoObservacion.vencida else 'on time'}"
        )
        return observacion

    @staticmethod
    async def expire(
        db: AsyncSession,
        observacion_id: UUID,
        executor_user: User,
    ) -> Observacion:
        """
        Expire an observacion (mark as vencida).

        Only the project executor (owner) or Bonita system actor can expire observations.
        Used when an observation passes its deadline without being resolved.

        Args:
            db: Database session
            observacion_id: ID of the observacion to expire
            executor_user: User expiring the observation

        Returns:
            Expired Observacion instance

        Raises:
            HTTPException: If not found, not project owner, or already expired/resolved
        """
        # Get observacion with proyecto relationship
        stmt = (
            select(Observacion)
            .where(Observacion.id == observacion_id)
            .options(joinedload(Observacion.proyecto))
        )
        result = await db.execute(stmt)
        observacion = result.unique().scalar_one_or_none()

        if not observacion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Observacion with id {observacion_id} not found",
            )

        # Verify user is the project owner or is Bonita system actor
        is_bonita_actor = getattr(executor_user, "is_bonita_actor", False)
        if not (observacion.proyecto.user_id == executor_user.id or is_bonita_actor):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project executor (owner) or Bonita can expire observations",
            )

        # Check if already resolved
        if observacion.estado == EstadoObservacion.resuelta:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot expire an already resolved observation",
            )

        # Check if already expired
        if observacion.estado == EstadoObservacion.vencida:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Observacion is already expired",
            )

        # Expire the observacion
        observacion.estado = EstadoObservacion.vencida

        await db.commit()
        await db.refresh(observacion)

        logger.info(
            f"Observacion {observacion_id} expired by user {executor_user.id}. "
            f"Deadline was {observacion.fecha_limite}"
        )
        return observacion

    @staticmethod
    async def get_all_observaciones(
        db: AsyncSession,
        current_user: User,
        estado_filter: Optional[str] = None,
        proyecto_id: Optional[UUID] = None,
        council_user_id: Optional[UUID] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Observacion], int]:
        """
        Get all observaciones with advanced filtering, searching, sorting, and pagination.

        Authorization:
        - COUNCIL users: See all observaciones they created
        - MEMBER users: See only observaciones for their own projects (as executor)

        Args:
            db: Database session
            current_user: Currently authenticated user
            estado_filter: Optional filter by estado (pendiente, resuelta, vencida)
            proyecto_id: Optional filter by specific project
            council_user_id: Optional filter by council member who created
            search: Optional search string in descripcion and respuesta
            sort_by: Field to sort by (created_at, fecha_limite, fecha_resolucion, updated_at)
            sort_order: Sort order (asc, desc)
            fecha_desde: Optional filter - created after this date
            fecha_hasta: Optional filter - created before this date
            page: Page number (1-indexed)
            page_size: Results per page

        Returns:
            Tuple of (list of Observacion instances, total count)

        Raises:
            HTTPException: If invalid filter values provided
        """
        from sqlalchemy import and_, or_

        # Start with base query
        stmt = (
            select(Observacion)
            .options(
                joinedload(Observacion.proyecto),
                joinedload(Observacion.council_user),
            )
        )

        # Authorization: MEMBER users can only see observations for their projects
        if current_user.role == UserRole.MEMBER:
            # Only show observations where current_user is the project executor (owner)
            stmt = stmt.where(Observacion.proyecto.has(Proyecto.user_id == current_user.id))
        # COUNCIL users see all observations they created

        # Apply filters
        filters = []

        # Estado filter
        if estado_filter:
            valid_estados = ["pendiente", "resuelta", "vencida"]
            if estado_filter not in valid_estados:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid estado filter. Must be one of: {valid_estados}",
                )
            filters.append(Observacion.estado == EstadoObservacion(estado_filter))

        # Proyecto filter
        if proyecto_id:
            filters.append(Observacion.proyecto_id == proyecto_id)

        # Council user filter (only applies if user has permission to see those observations)
        if council_user_id:
            filters.append(Observacion.council_user_id == council_user_id)

        # Date range filters
        if fecha_desde:
            filters.append(Observacion.created_at >= datetime.combine(fecha_desde, datetime.min.time()))
        if fecha_hasta:
            filters.append(
                Observacion.created_at < datetime.combine(fecha_hasta + timedelta(days=1), datetime.min.time())
            )

        # Search filter (full-text search on descripcion and respuesta)
        if search:
            search_term = f"%{search}%"
            filters.append(
                or_(
                    Observacion.descripcion.ilike(search_term),
                    Observacion.respuesta.ilike(search_term),
                )
            )

        # Apply all filters
        if filters:
            stmt = stmt.where(and_(*filters))

        # Get total count before pagination
        count_stmt = select(Observacion).where(stmt.whereclause)
        count_result = await db.execute(count_stmt)
        total_count = len(count_result.scalars().all())

        # Apply sorting
        valid_sort_fields = {
            "created_at": Observacion.created_at,
            "fecha_limite": Observacion.fecha_limite,
            "fecha_resolucion": Observacion.fecha_resolucion,
            "updated_at": Observacion.updated_at,
        }
        if sort_by not in valid_sort_fields:
            sort_by = "created_at"
        
        sort_column = valid_sort_fields[sort_by]
        if sort_order.lower() == "asc":
            stmt = stmt.order_by(sort_column.asc())
        else:
            stmt = stmt.order_by(sort_column.desc())

        # Apply pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        # Execute query
        result = await db.execute(stmt)
        observaciones = list(result.unique().scalars().all())

        # Check and update overdue observations
        updated = False
        for obs in observaciones:
            if ObservacionService._check_and_update_overdue(obs):
                updated = True

        if updated:
            await db.commit()
            for obs in observaciones:
                await db.refresh(obs)

        logger.info(
            f"Retrieved {len(observaciones)} observaciones for user {current_user.id} "
            f"(total: {total_count}, page: {page}, page_size: {page_size})"
        )
        return observaciones, total_count

    @staticmethod
    def _check_and_update_overdue(observacion: Observacion) -> bool:
        """
        Check if an observacion is overdue and update status if needed.

        An observation is overdue if it's still PENDIENTE and the deadline has passed.

        Args:
            observacion: Observacion instance to check

        Returns:
            True if status was changed to VENCIDA, False otherwise
        """
        if (
            observacion.estado == EstadoObservacion.pendiente
            and date.today() > observacion.fecha_limite
        ):
            observacion.estado = EstadoObservacion.vencida
            logger.info(
                f"Observacion {observacion.id} marked as vencida (overdue). "
                f"Deadline was {observacion.fecha_limite}"
            )
            return True
        return False
