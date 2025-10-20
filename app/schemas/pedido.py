"""Pedido Pydantic schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PedidoCreate(BaseModel):
    """Schema for creating a pedido."""

    tipo: str = Field(..., min_length=1)
    descripcion: str = Field(..., min_length=5)
    monto: Optional[float] = Field(None, gt=0)
    moneda: Optional[str] = Field(None, max_length=10)
    cantidad: Optional[int] = Field(None, gt=0)
    unidad: Optional[str] = Field(None, max_length=50)

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: str) -> str:
        """Validate tipo is one of the allowed values."""
        allowed = ["economico", "materiales", "mano_obra", "transporte", "equipamiento"]
        if v not in allowed:
            raise ValueError(f"tipo must be one of {allowed}")
        return v


class PedidoResponse(BaseModel):
    """Schema for pedido response."""

    model_config = {"from_attributes": True}

    id: UUID
    etapa_id: UUID
    tipo: str
    descripcion: str
    monto: Optional[float] = None
    moneda: Optional[str] = None
    cantidad: Optional[int] = None
    unidad: Optional[str] = None
