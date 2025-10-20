"""Pedido SQLAlchemy model."""

from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

import enum as py_enum
from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.etapa import Etapa


class TipoPedido(str, py_enum.Enum):
    """Coverage request type enumeration."""
    ECONOMICO = "economico"
    MATERIALES = "materiales"
    MANO_OBRA = "mano_obra"
    TRANSPORTE = "transporte"
    EQUIPAMIENTO = "equipamiento"


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

    # Financial (for economico type)
    monto: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    moneda: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Quantity (for materiales, mano_obra, etc.)
    cantidad: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    unidad: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    etapa: Mapped["Etapa"] = relationship(back_populates="pedidos")
