"""Etapa Pydantic schemas."""

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer, field_validator

from app.schemas.pedido import PedidoCreate, PedidoResponse


class EtapaCreate(BaseModel):
    """Schema for creating an etapa."""

    nombre: str = Field(..., min_length=3, max_length=200)
    descripcion: str = Field(..., min_length=10)
    fecha_inicio: str = Field(...)  # ISO date string from frontend
    fecha_fin: str = Field(...)  # ISO date string from frontend
    pedidos: List[PedidoCreate] = Field(..., min_length=1)

    @field_validator("fecha_inicio", "fecha_fin")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date is in ISO format (YYYY-MM-DD)."""
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("Date must be in ISO format (YYYY-MM-DD)")
        return v

    @field_validator("pedidos")
    @classmethod
    def validate_pedidos_not_empty(cls, v: List[PedidoCreate]) -> List[PedidoCreate]:
        """Validate at least one pedido is provided."""
        if not v or len(v) == 0:
            raise ValueError("At least one pedido is required")
        return v

    def validate_dates(self) -> None:
        """Validate fecha_fin >= fecha_inicio."""
        fecha_inicio_date = date.fromisoformat(self.fecha_inicio)
        fecha_fin_date = date.fromisoformat(self.fecha_fin)
        if fecha_fin_date < fecha_inicio_date:
            raise ValueError("fecha_fin must be >= fecha_inicio")


class EtapaUpdate(BaseModel):
    """Schema for partial update (PATCH) - all fields optional."""

    nombre: Optional[str] = Field(None, min_length=3, max_length=200)
    descripcion: Optional[str] = Field(None, min_length=10)
    fecha_inicio: Optional[str] = None  # ISO date string
    fecha_fin: Optional[str] = None  # ISO date string
    bonita_case_id: Optional[str] = Field(None, max_length=100)
    bonita_process_instance_id: Optional[int] = None

    @field_validator("fecha_inicio", "fecha_fin")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate date is in ISO format (YYYY-MM-DD) if provided."""
        if v is None:
            return v
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("Date must be in ISO format (YYYY-MM-DD)")
        return v


class EtapaPut(BaseModel):
    """Schema for complete update (PUT) - core fields required, Bonita fields optional."""

    nombre: str = Field(..., min_length=3, max_length=200)
    descripcion: str = Field(..., min_length=10)
    fecha_inicio: str = Field(...)  # ISO date string
    fecha_fin: str = Field(...)  # ISO date string
    bonita_case_id: Optional[str] = Field(None, max_length=100)
    bonita_process_instance_id: Optional[int] = None

    @field_validator("fecha_inicio", "fecha_fin")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date is in ISO format (YYYY-MM-DD)."""
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("Date must be in ISO format (YYYY-MM-DD)")
        return v

    @field_validator("fecha_fin")
    @classmethod
    def validate_date_range(cls, v: str, info) -> str:
        """Validate fecha_fin >= fecha_inicio."""
        if "fecha_inicio" in info.data:
            fecha_inicio = date.fromisoformat(info.data["fecha_inicio"])
            fecha_fin = date.fromisoformat(v)
            if fecha_fin < fecha_inicio:
                raise ValueError("fecha_fin must be >= fecha_inicio")
        return v


class EtapaResponse(BaseModel):
    """Schema for etapa response."""

    model_config = {"from_attributes": True}

    id: UUID
    proyecto_id: UUID
    nombre: str
    descripcion: str
    fecha_inicio: date
    fecha_fin: date
    estado: str
    fecha_completitud: Optional[datetime] = None
    bonita_case_id: Optional[str] = None
    bonita_process_instance_id: Optional[int] = None
    pedidos: List[PedidoResponse] = []

    @field_serializer("estado")
    def serialize_estado(self, value) -> str:
        """Serialize estado enum to its string value."""
        if hasattr(value, "value"):
            return value.value
        return str(value)


class EtapaListItem(BaseModel):
    """Schema for etapa list item with pedido counts."""

    model_config = {"from_attributes": True}

    id: UUID
    proyecto_id: UUID
    nombre: str
    descripcion: str
    fecha_inicio: date
    fecha_fin: date
    estado: str
    fecha_completitud: Optional[datetime] = None
    bonita_case_id: Optional[str] = None
    bonita_process_instance_id: Optional[int] = None
    pedidos: List[PedidoResponse] = []
    pedidos_pendientes_count: int = 0
    pedidos_total_count: int = 0

    @field_serializer("estado")
    def serialize_estado(self, value) -> str:
        """Serialize estado enum to its string value."""
        if hasattr(value, "value"):
            return value.value
        return str(value)


class EtapasListResponse(BaseModel):
    """Schema for list of etapas."""

    etapas: List[EtapaListItem]
    total: int


class EtapaStartResponse(BaseModel):
    """Schema for successful etapa start response."""

    id: UUID
    nombre: str
    estado: str
    message: str


class EtapaCompleteResponse(BaseModel):
    """Schema for successful etapa completion response."""

    id: UUID
    nombre: str
    estado: str
    fecha_completitud: datetime
    message: str
