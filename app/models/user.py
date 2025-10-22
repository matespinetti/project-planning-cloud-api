"""User SQLAlchemy model."""

from datetime import datetime
from typing import TYPE_CHECKING, List
from uuid import UUID, uuid4
import enum as py_enum

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.proyecto import Proyecto
    from app.models.oferta import Oferta


class UserRole(str, py_enum.Enum):
    """Available user roles."""

    COUNCIL = "COUNCIL"
    MEMBER = "MEMBER"


class User(Base):
    """User account used for authentication."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    ong: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    apellido: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole"),
        nullable=False,
        default=UserRole.MEMBER,
        server_default=UserRole.MEMBER.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    proyectos: Mapped[List["Proyecto"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    ofertas: Mapped[List["Oferta"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - string helper
        return f"User(id={self.id}, email={self.email}, role={self.role})"
