"""Etapa SQLAlchemy model."""

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import StrEnum

if TYPE_CHECKING:
    from app.models.proyecto import Proyecto
    from app.models.pedido import Pedido


class EstadoEtapa(StrEnum):
    """Etapa lifecycle: pending funding → financed → awaiting execution → executing → completed."""

    pendiente = "pendiente"
    financiada = "financiada"
    esperando_ejecucion = "esperando_ejecucion"
    en_ejecucion = "en_ejecucion"
    completada = "completada"


class Etapa(Base):
    """Project stages/phases with date ranges."""

    __tablename__ = "etapas"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Foreign Key
    proyecto_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False
    )

    # Etapa Info
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)

    # Status
    estado: Mapped[EstadoEtapa] = mapped_column(
        Enum(EstadoEtapa), nullable=False, default=EstadoEtapa.pendiente
    )

    # Completion tracking
    fecha_completitud: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

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
    fecha_en_ejecucion: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fecha_financiada: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Bonita Integration
    bonita_case_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bonita_process_instance_id: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Relationships
    proyecto: Mapped["Proyecto"] = relationship(back_populates="etapas")
    pedidos: Mapped[List["Pedido"]] = relationship(
        back_populates="etapa", cascade="all, delete-orphan", lazy="joined"
    )
