"""Proyecto Pydantic schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.etapa import EtapaCreate, EtapaResponse


class ProyectoCreate(BaseModel):
    """Schema for creating a proyecto (no IDs, server-generated).

    Note: user_id is automatically set from the authenticated user, not from the request body.
    """

    titulo: str = Field(..., min_length=5, max_length=200)
    descripcion: str = Field(..., min_length=20)
    tipo: str = Field(..., min_length=1, max_length=100)
    pais: str = Field(..., max_length=100)
    provincia: str = Field(..., max_length=100)
    ciudad: str = Field(..., max_length=100)
    barrio: Optional[str] = Field(None, max_length=100)
    estado: str = Field(default="en_planificacion")
    bonita_case_id: Optional[str] = Field(None, max_length=100)
    bonita_process_instance_id: Optional[int] = None
    etapas: List[EtapaCreate] = Field(..., min_length=1)

    @field_validator("etapas")
    @classmethod
    def validate_etapas_not_empty(cls, v: List[EtapaCreate]) -> List[EtapaCreate]:
        """Validate at least one etapa is provided and dates are valid."""
        if not v or len(v) == 0:
            raise ValueError("At least one etapa is required")
        # Validate dates for each etapa
        for etapa in v:
            etapa.validate_dates()
        return v


class ProyectoUpdate(BaseModel):
    """Schema for partial update (PATCH) - all fields optional."""

    titulo: Optional[str] = Field(None, min_length=5, max_length=200)
    descripcion: Optional[str] = Field(None, min_length=20)
    tipo: Optional[str] = Field(None, min_length=1, max_length=100)
    pais: Optional[str] = Field(None, max_length=100)
    provincia: Optional[str] = Field(None, max_length=100)
    ciudad: Optional[str] = Field(None, max_length=100)
    barrio: Optional[str] = Field(None, max_length=100)
    estado: Optional[str] = None
    bonita_case_id: Optional[str] = Field(None, max_length=100)
    bonita_process_instance_id: Optional[int] = None


class ProyectoResponse(BaseModel):
    """Schema for proyecto response with all nested data."""

    model_config = {"from_attributes": True}

    id: UUID
    user_id: UUID
    titulo: str
    descripcion: str
    tipo: str
    pais: str
    provincia: str
    ciudad: str
    barrio: Optional[str] = None
    estado: str
    bonita_case_id: Optional[str] = None
    bonita_process_instance_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    etapas: List[EtapaResponse] = []
