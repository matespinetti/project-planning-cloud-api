"""Oferta service - Business logic for offer operations."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.etapa import Etapa
from app.models.oferta import EstadoOferta, Oferta
from app.models.pedido import Pedido
from app.models.proyecto import Proyecto
from app.models.user import User
from app.schemas.oferta import OfertaCreate
from app.services.pedido_service import PedidoService

logger = logging.getLogger(__name__)


class OfertaService:
    """Service for oferta-related operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
        pedido_id: UUID,
        oferta_data: OfertaCreate,
        user: User,
    ) -> Oferta:
        """
        Create a new oferta for a pedido.
        Any authenticated user can create an oferta.

        Restrictions:
        - Ofertas can only be submitted for pedidos in PENDIENTE state
        - Cannot create ofertas for pedidos that are COMPROMETIDO or COMPLETADO
        """
        # Verify pedido exists
        pedido = await db.get(Pedido, pedido_id)
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido with id {pedido_id} not found",
            )

        # Verify pedido is in PENDIENTE state (only pending pedidos can receive ofertas)
        from app.models.pedido import EstadoPedido
        if pedido.estado != EstadoPedido.PENDIENTE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot create oferta for pedido in state '{pedido.estado.value}'. "
                       f"Ofertas can only be submitted for pedidos in 'PENDIENTE' state.",
            )

        # Prevent duplicate offers from the same user on the same pedido
        existing_oferta_stmt = select(Oferta.id).where(
            Oferta.pedido_id == pedido_id, Oferta.user_id == user.id
        )
        existing_oferta_result = await db.execute(existing_oferta_stmt)
        if existing_oferta_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already submitted an oferta for this pedido.",
            )

        # Create oferta
        db_oferta = Oferta(
            pedido_id=pedido_id,
            user_id=user.id,
            descripcion=oferta_data.descripcion,
            monto_ofrecido=oferta_data.monto_ofrecido,
            estado=EstadoOferta.pendiente,
        )

        db.add(db_oferta)
        await db.commit()
        await db.refresh(db_oferta)

        return db_oferta

    @staticmethod
    async def get_by_id(db: AsyncSession, oferta_id: UUID) -> Optional[Oferta]:
        """Get an oferta by ID with user relationship loaded."""
        stmt = select(Oferta).where(Oferta.id == oferta_id).options(joinedload(Oferta.user))
        result = await db.execute(stmt)
        return result.unique().scalar_one_or_none()

    @staticmethod
    async def get_by_pedido(db: AsyncSession, pedido_id: UUID, user: User) -> List[Oferta]:
        """
        Get all ofertas for a specific pedido.
        Only the project owner can view ofertas for their pedidos.
        """
        # Get pedido and verify it exists
        pedido = await db.get(Pedido, pedido_id)
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido with id {pedido_id} not found",
            )

        # Get etapa to access proyecto
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

        # Verify user is the project owner
        if proyecto.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project owner can view ofertas for their pedidos",
            )

        # Fetch ofertas
        stmt = (
            select(Oferta)
            .where(Oferta.pedido_id == pedido_id)
            .options(joinedload(Oferta.user))
            .order_by(Oferta.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.unique().scalars().all())

    @staticmethod
    async def accept(db: AsyncSession, oferta_id: UUID, user: User) -> Oferta:
        """
        Accept an oferta.
        Only the project owner can accept ofertas.

        Restrictions:
        - Ofertas can only be accepted for pedidos in PENDIENTE state
        - Cannot accept ofertas for pedidos that are COMPROMETIDO or COMPLETADO

        When an oferta is accepted:
        - The oferta estado is set to ACEPTADA
        - All other pending ofertas for the same pedido are automatically rejected (RECHAZADA)
        - The pedido estado is set to COMPROMETIDO (pending confirmation from oferente)
        """
        # Get oferta with all relationships
        oferta = await OfertaService.get_by_id(db, oferta_id)
        if not oferta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Oferta with id {oferta_id} not found",
            )

        # Verify user is project owner
        await OfertaService._verify_project_ownership(db, oferta, user)

        # Check if oferta is already accepted or rejected
        if oferta.estado != EstadoOferta.pendiente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Oferta is already {oferta.estado.value}",
            )

        # Verify the pedido is in PENDIENTE state (can't accept ofertas for committed/completed pedidos)
        pedido = await db.get(Pedido, oferta.pedido_id)
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido not found",
            )

        from app.models.pedido import EstadoPedido
        if pedido.estado != EstadoPedido.PENDIENTE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot accept oferta for pedido in state '{pedido.estado.value}'. "
                       f"Ofertas can only be accepted for pedidos in 'PENDIENTE' state.",
            )

        # Accept the oferta
        oferta.estado = EstadoOferta.aceptada

        # Auto-reject all other pending ofertas for the same pedido
        stmt_other_ofertas = (
            select(Oferta)
            .where(Oferta.pedido_id == oferta.pedido_id)
            .where(Oferta.id != oferta.id)  # Exclude the accepted one
            .where(Oferta.estado == EstadoOferta.pendiente)
        )
        result = await db.execute(stmt_other_ofertas)
        other_ofertas = result.scalars().all()

        for other_oferta in other_ofertas:
            other_oferta.estado = EstadoOferta.rechazada
            logger.info(
                f"Auto-rejecting oferta {other_oferta.id} because oferta {oferta_id} "
                f"was accepted for pedido {oferta.pedido_id}"
            )

        # Commit all changes (accepted oferta + rejected ofertas)
        await db.commit()
        await db.refresh(oferta)

        # Mark the associated pedido as comprometido (pending confirmation from oferente)
        await PedidoService.mark_as_comprometido(db, oferta.pedido_id)

        logger.info(f"Oferta {oferta_id} accepted by user {user.id}")
        return oferta

    @staticmethod
    async def reject(db: AsyncSession, oferta_id: UUID, user: User) -> Oferta:
        """
        Reject an oferta.
        Only the project owner can reject ofertas.
        """
        # Get oferta with all relationships
        oferta = await OfertaService.get_by_id(db, oferta_id)
        if not oferta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Oferta with id {oferta_id} not found",
            )

        # Verify user is project owner
        await OfertaService._verify_project_ownership(db, oferta, user)

        # Check if oferta is already accepted or rejected
        if oferta.estado != EstadoOferta.pendiente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Oferta is already {oferta.estado.value}",
            )

        # Reject the oferta
        oferta.estado = EstadoOferta.rechazada
        await db.commit()
        await db.refresh(oferta)

        logger.info(f"Oferta {oferta_id} rejected by user {user.id}")
        return oferta

    @staticmethod
    async def confirm_realizacion(db: AsyncSession, oferta_id: UUID, user: User) -> Dict[str, Any]:
        """
        Confirm that the commitment has been fulfilled.
        Only the user who created the oferta can confirm it.
        The oferta must be in ACEPTADA state and the pedido must be COMPROMETIDO.
        """
        # Get oferta with pedido relationship
        stmt = (
            select(Oferta)
            .where(Oferta.id == oferta_id)
            .options(joinedload(Oferta.user), joinedload(Oferta.pedido))
        )
        result = await db.execute(stmt)
        oferta = result.unique().scalar_one_or_none()

        if not oferta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Oferta with id {oferta_id} not found",
            )

        # Verify user is the oferente (creator of the oferta)
        if oferta.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the user who created the oferta can confirm its realization",
            )

        # Check if oferta is in ACEPTADA state
        if oferta.estado != EstadoOferta.aceptada:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Oferta must be in aceptada state to confirm realization. Current state: {oferta.estado.value}",
            )

        # Check if pedido is already COMPLETADO (special case - more user-friendly error)
        from app.models.pedido import EstadoPedido

        if oferta.pedido.estado == EstadoPedido.COMPLETADO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This commitment has already been confirmed. The pedido was marked as 'COMPLETADO'. "
                       "No further action is needed.",
            )

        # Check if pedido is in COMPROMETIDO state
        if oferta.pedido.estado != EstadoPedido.COMPROMETIDO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot confirm realization. Pedido is in state '{oferta.pedido.estado.value}', "
                       f"but must be in 'COMPROMETIDO' state.",
            )

        # Capture estado anterior before marking as completed
        estado_anterior = oferta.pedido.estado.value

        # Mark the pedido as completed
        await PedidoService.mark_as_completed(db, oferta.pedido_id)

        # Refresh oferta to get updated relationships
        await db.refresh(oferta)

        logger.info(f"Oferta {oferta_id} realization confirmed by user {user.id}")

        # Return structured response with clear messaging
        return {
            "message": "Compromiso confirmado exitosamente. El pedido ha sido marcado como completado.",
            "success": True,
            "oferta_id": oferta.id,
            "oferta_estado": oferta.estado.value,
            "pedido_id": oferta.pedido_id,
            "pedido_estado_anterior": estado_anterior,
            "pedido_estado_nuevo": oferta.pedido.estado.value,
            "confirmed_at": datetime.now(timezone.utc),
        }

    @staticmethod
    async def get_my_commitments(
        db: AsyncSession,
        user: User,
        estado_pedido_filter: Optional[str] = None,
    ) -> List[Oferta]:
        """
        Get all accepted ofertas for the current user (their commitments).
        Optionally filter by pedido estado (comprometido or completado).
        """
        from app.models.pedido import EstadoPedido

        # Build query for ofertas with estado ACEPTADA belonging to the user
        stmt = (
            select(Oferta)
            .where(Oferta.user_id == user.id)
            .where(Oferta.estado == EstadoOferta.aceptada)
            .options(joinedload(Oferta.pedido), joinedload(Oferta.user))
            .order_by(Oferta.updated_at.desc())
        )

        # Apply pedido estado filter if provided
        if estado_pedido_filter:
            # Validate estado_pedido_filter
            valid_estados = ["comprometido", "completado"]
            if estado_pedido_filter not in valid_estados:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid estado_pedido filter. Must be one of: {valid_estados}",
                )

            # Join with Pedido and filter by its estado
            stmt = stmt.join(Pedido).where(Pedido.estado == EstadoPedido(estado_pedido_filter))

        result = await db.execute(stmt)
        return list(result.unique().scalars().all())

    @staticmethod
    async def get_all_user_ofertas(
        db: AsyncSession,
        user: User,
        estado_oferta_filter: Optional[str] = None,
    ) -> List[Oferta]:
        """
        Get all ofertas created by the current user (all states).
        Optionally filter by oferta estado (pendiente, aceptada, rechazada).
        """
        # Build query for all ofertas belonging to the user
        # Eager load pedido → etapa → proyecto to avoid lazy loading issues in async context
        stmt = (
            select(Oferta)
            .where(Oferta.user_id == user.id)
            .options(
                joinedload(Oferta.pedido)
                    .joinedload(Pedido.etapa)
                    .joinedload(Etapa.proyecto),
                joinedload(Oferta.user)
            )
            .order_by(Oferta.updated_at.desc())
        )

        # Apply oferta estado filter if provided
        if estado_oferta_filter:
            # Validate estado_oferta_filter
            valid_estados = ["pendiente", "aceptada", "rechazada"]
            if estado_oferta_filter not in valid_estados:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid estado_oferta filter. Must be one of: {valid_estados}",
                )

            # Filter by oferta estado
            stmt = stmt.where(Oferta.estado == EstadoOferta(estado_oferta_filter))

        result = await db.execute(stmt)
        return list(result.unique().scalars().all())


    @staticmethod
    async def get_oferta_by_id(db: AsyncSession, oferta_id: UUID) -> Optional[Oferta]:
        """Get an oferta by ID with relationships loaded."""
        stmt = (
            select(Oferta)
            .where(Oferta.id == oferta_id)
            .options(
                joinedload(Oferta.user),
                joinedload(Oferta.pedido)
                .joinedload(Pedido.etapa)
                .joinedload(Etapa.proyecto),
            )
        )
        result = await db.execute(stmt)
        return result.unique().scalar_one_or_none()

    @staticmethod
    async def update(
        db: AsyncSession,
        oferta_id: UUID,
        oferta_data: "OfertaUpdate",
        user: User,
    ) -> Oferta:
        """
        Update an oferta (descripcion and/or monto).
        Only the user who created the oferta can update it.
        Ofertas can only be updated if they are in PENDIENTE state.
        """
        from app.schemas.oferta import OfertaUpdate

        # Get oferta
        oferta = await OfertaService.get_oferta_by_id(db, oferta_id)
        if not oferta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Oferta with id {oferta_id} not found",
            )

        # Verify user is the creator
        if oferta.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the user who created the oferta can update it",
            )

        # Validate that oferta is in PENDIENTE state
        if oferta.estado != EstadoOferta.pendiente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update oferta in state '{oferta.estado.value}'. "
                       "Ofertas can only be updated while in PENDIENTE state.",
            )

        # Update fields that are provided
        if oferta_data.descripcion is not None:
            oferta.descripcion = oferta_data.descripcion
        if oferta_data.monto_ofrecido is not None:
            oferta.monto_ofrecido = oferta_data.monto_ofrecido

        await db.commit()
        await db.refresh(oferta)

        logger.info(f"Oferta {oferta_id} updated by user {user.id}")
        return oferta

    @staticmethod
    async def delete_oferta(db: AsyncSession, oferta_id: UUID, user: User) -> bool:
        """
        Delete an oferta.
        Only the user who created the oferta can delete it.
        Ofertas can only be deleted if they are in PENDIENTE state.
        """
        # Get oferta
        oferta = await OfertaService.get_oferta_by_id(db, oferta_id)
        if not oferta:
            return False

        # Verify user is the creator
        if oferta.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the user who created the oferta can delete it",
            )

        # Validate that oferta is in PENDIENTE state
        if oferta.estado != EstadoOferta.pendiente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete oferta in state '{oferta.estado.value}'. "
                       "Ofertas can only be deleted while in PENDIENTE state.",
            )

        # Delete the oferta
        await db.delete(oferta)
        await db.commit()

        logger.info(f"Oferta {oferta_id} deleted by user {user.id}")
        return True

    @staticmethod
    async def _verify_project_ownership(db: AsyncSession, oferta: Oferta, user: User) -> None:
        """Verify that the user owns the project that contains this oferta."""
        # Bonita system calls are pre-authorized through the proxy API, so skip
        # project ownership validation when requests carry the X-API-Key header.
        if getattr(user, "is_bonita_actor", False):
            logger.info(
                "Skipping ownership verification for oferta %s because request comes from Bonita",
                oferta.id,
            )
            return

        # Get pedido -> etapa -> proyecto chain
        pedido = await db.get(Pedido, oferta.pedido_id)
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido not found",
            )

        etapa = await db.get(Etapa, pedido.etapa_id)
        if not etapa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Etapa not found",
            )

        proyecto = await db.get(Proyecto, etapa.proyecto_id)
        if not proyecto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto not found",
            )

        # Verify ownership
        if proyecto.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project owner can accept or reject ofertas",
            )
