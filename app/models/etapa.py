"""Etapa SQLAlchemy model."""

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

import enum as py_enum

if TYPE_CHECKING:
    from app.models.proyecto import Proyecto
    from app.models.pedido import Pedido


class EstadoEtapa(str, py_enum.Enum):
    """Etapa status enumeration."""

    EN_PROGRESO = "en_progreso"
    COMPLETADA = "completada"


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
        Enum(EstadoEtapa), nullable=False, default=EstadoEtapa.EN_PROGRESO
    )

    # Completion tracking
    fecha_completitud: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    proyecto: Mapped["Proyecto"] = relationship(back_populates="etapas")
    pedidos: Mapped[List["Pedido"]] = relationship(
        back_populates="etapa", cascade="all, delete-orphan", lazy="joined"
    )
