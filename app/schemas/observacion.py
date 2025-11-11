"""Observacion Pydantic schemas."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ObservacionCreate(BaseModel):
    """Schema for creating an observacion (council members only)."""

    descripcion: str = Field(
        ..., min_length=10, description="Observation description from council member"
    )


class ObservacionResolve(BaseModel):
    """Schema for resolving an observacion (project executor)."""

    respuesta: str = Field(
        ..., min_length=10, description="Response to the observation from project executor"
    )


class ObservacionResponse(BaseModel):
    """Schema for observacion response."""

    model_config = {"from_attributes": True}

    id: UUID
    proyecto_id: UUID
    council_user_id: UUID
    descripcion: str
    estado: str
    fecha_limite: date
    respuesta: Optional[str] = None
    fecha_resolucion: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ObservacionWithUserResponse(BaseModel):
    """Schema for observacion response with council user information."""

    model_config = {"from_attributes": True}

    id: UUID
    proyecto_id: UUID
    council_user_id: UUID
    descripcion: str
    estado: str
    fecha_limite: date
    respuesta: Optional[str] = None
    fecha_resolucion: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Council user information
    council_user_email: Optional[str] = None
    council_user_ong: Optional[str] = None
    council_user_nombre: Optional[str] = None
