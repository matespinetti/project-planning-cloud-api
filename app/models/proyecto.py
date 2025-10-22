"""Proyecto SQLAlchemy model."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

import enum as py_enum

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.etapa import Etapa


class EstadoProyecto(str, py_enum.Enum):
    """Project status enumeration."""
    BORRADOR = "borrador"
    EN_PLANIFICACION = "en_planificacion"
    BUSCANDO_FINANCIAMIENTO = "buscando_financiamiento"
    EN_EJECUCION = "en_ejecucion"
    COMPLETO = "completo"


class Proyecto(Base):
    """Main project table with all project metadata and Bonita tracking."""

    __tablename__ = "proyectos"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Foreign Key - Project Owner/Creator
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Project Info
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(String(100), nullable=False)

    # Location
    pais: Mapped[str] = mapped_column(String(100), nullable=False)
    provincia: Mapped[str] = mapped_column(String(100), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(100), nullable=False)
    barrio: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status
    estado: Mapped[EstadoProyecto] = mapped_column(
        Enum(EstadoProyecto), nullable=False, default=EstadoProyecto.EN_PLANIFICACION
    )

    # Bonita BPM Integration (can be null initially)
    bonita_case_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bonita_process_instance_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
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
    user: Mapped["User"] = relationship(back_populates="proyectos")
    etapas: Mapped[List["Etapa"]] = relationship(
        back_populates="proyecto", cascade="all, delete-orphan", lazy="joined"
    )
