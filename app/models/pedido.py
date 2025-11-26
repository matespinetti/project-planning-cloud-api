"""Pedido SQLAlchemy model."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import StrEnum

if TYPE_CHECKING:
    from app.models.etapa import Etapa
    from app.models.oferta import Oferta


class TipoPedido(StrEnum):
    """Coverage request type enumeration."""
    ECONOMICO = "economico"
    MATERIALES = "materiales"
    MANO_OBRA = "mano_obra"
    TRANSPORTE = "transporte"
    EQUIPAMIENTO = "equipamiento"


class EstadoPedido(StrEnum):
    """Pedido status enumeration."""
    PENDIENTE = "PENDIENTE"
    COMPROMETIDO = "COMPROMETIDO"
    COMPLETADO = "COMPLETADO"


class Pedido(Base):
    """Coverage requests (economic, materials, labor, transport, equipment)."""

    __tablename__ = "pedidos"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Foreign Key
    etapa_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("etapas.id", ondelete="CASCADE"), nullable=False
    )

    # Pedido Info
    tipo: Mapped[TipoPedido] = mapped_column(Enum(TipoPedido), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[EstadoPedido] = mapped_column(
        Enum(EstadoPedido), nullable=False, default=EstadoPedido.PENDIENTE
    )

    # Financial (for economico type)
    monto: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    moneda: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Quantity (for materiales, mano_obra, etc.)
    cantidad: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    unidad: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    # State transition timestamps
    fecha_comprometido: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fecha_completado: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    etapa: Mapped["Etapa"] = relationship(back_populates="pedidos")
    ofertas: Mapped[List["Oferta"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan"
    )
