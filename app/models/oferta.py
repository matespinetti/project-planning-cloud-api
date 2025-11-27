"""Oferta SQLAlchemy model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import StrEnum

if TYPE_CHECKING:
    from app.models.pedido import Pedido
    from app.models.user import User


class EstadoOferta(StrEnum):
    """Offer status enumeration."""
    pendiente = "pendiente"
    aceptada = "aceptada"
    rechazada = "rechazada"


class Oferta(Base):
    """Offers submitted by users to cover specific pedidos."""

    __tablename__ = "ofertas"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Foreign Keys
    pedido_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Offer Info
    monto_ofrecido: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[EstadoOferta] = mapped_column(
        Enum(EstadoOferta), nullable=False, default=EstadoOferta.pendiente
    )
    fecha_resolucion: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps (auto-managed)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    pedido: Mapped["Pedido"] = relationship(back_populates="ofertas")
    user: Mapped["User"] = relationship(back_populates="ofertas")

    def __repr__(self) -> str:
        return f"Oferta(id={self.id}, pedido_id={self.pedido_id}, user_id={self.user_id}, estado={self.estado})"
