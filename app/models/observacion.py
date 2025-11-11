"""Observacion SQLAlchemy model."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

import enum as py_enum
from sqlalchemy import Date, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.proyecto import Proyecto
    from app.models.user import User


class EstadoObservacion(str, py_enum.Enum):
    """Observation status enumeration."""

    PENDIENTE = "pendiente"
    RESUELTA = "resuelta"
    VENCIDA = "vencida"


class Observacion(Base):
    """
    Observations made by council members on projects in execution.

    Council members can create observations during monitoring sessions.
    Project executors must resolve observations within 5 days.
    Observations automatically become 'vencida' (overdue) if not resolved in time.
    """

    __tablename__ = "observaciones"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Foreign Keys
    proyecto_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("proyectos.id", ondelete="CASCADE"),
        nullable=False,
    )
    council_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Observation Content
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[EstadoObservacion] = mapped_column(
        Enum(EstadoObservacion),
        nullable=False,
        default=EstadoObservacion.PENDIENTE,
    )

    # Deadlines (5 days from creation)
    fecha_limite: Mapped[date] = mapped_column(Date, nullable=False)

    # Resolution Information
    respuesta: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    proyecto: Mapped["Proyecto"] = relationship(back_populates="observaciones")
    council_user: Mapped["User"] = relationship(
        back_populates="observaciones", foreign_keys=[council_user_id]
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"Observacion(id={self.id}, proyecto_id={self.proyecto_id}, estado={self.estado})"
