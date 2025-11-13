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

        # Verify user is the project owner
        if observacion.proyecto.user_id != executor_user.id:
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
