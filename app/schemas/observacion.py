"""Observacion Pydantic schemas."""

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ObservacionCreate(BaseModel):
    """Schema for creating an observacion (council members only)."""

    descripcion: str = Field(
        ..., min_length=10, description="Observation description from council member"
    )
    bonita_case_id: Optional[str] = Field(None, max_length=100, description="Bonita case ID for workflow tracking")
    bonita_process_instance_id: Optional[int] = Field(None, description="Bonita process instance ID")


class ObservacionResolve(BaseModel):
    """Schema for resolving an observacion (project executor)."""

    respuesta: str = Field(
        ..., min_length=10, description="Response to the observation from project executor"
    )


class UserBasicInfo(BaseModel):
    """Basic user information for nested responses."""

    model_config = {"from_attributes": True}

    id: UUID
    email: str
    ong: str
    nombre: str


class ProyectoBasicInfo(BaseModel):
    """Basic project information for nested responses."""

    model_config = {"from_attributes": True}

    id: UUID
    titulo: str
    estado: str


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
    bonita_case_id: Optional[str] = None
    bonita_process_instance_id: Optional[int] = None
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
    bonita_case_id: Optional[str] = None
    bonita_process_instance_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    # Council user information
    council_user_email: Optional[str] = None
    council_user_ong: Optional[str] = None
    council_user_nombre: Optional[str] = None


class ObservacionDetailedResponse(BaseModel):
    """Schema for observacion with nested proyecto and council user information."""

    model_config = {"from_attributes": True}

    id: UUID
    proyecto_id: UUID
    council_user_id: UUID
    descripcion: str
    estado: str
    fecha_limite: date
    respuesta: Optional[str] = None
    fecha_resolucion: Optional[datetime] = None
    bonita_case_id: Optional[str] = None
    bonita_process_instance_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    # Nested objects
    proyecto: ProyectoBasicInfo
    council_user: UserBasicInfo
    # If available: executor user info (project owner)
    executor_user: Optional[UserBasicInfo] = None


class ObservacionListResponse(BaseModel):
    """Paginated response for list of observaciones."""

    items: List[ObservacionDetailedResponse]
    total: int
    page: int
    page_size: int
    pages: int
