"""Oferta Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class OfertaCreate(BaseModel):
    """Schema for creating an oferta."""

    descripcion: str = Field(..., min_length=10, description="Description of the offer")
    monto_ofrecido: Optional[float] = Field(None, gt=0, description="Amount offered (if applicable)")


class OfertaUpdate(BaseModel):
    """Schema for updating an oferta (mainly for accepting/rejecting)."""

    estado: str = Field(..., pattern="^(pendiente|aceptada|rechazada)$")


class OfertaResponse(BaseModel):
    """Schema for oferta response."""

    model_config = {"from_attributes": True}

    id: UUID
    pedido_id: UUID
    user_id: UUID
    descripcion: str
    monto_ofrecido: Optional[float] = None
    estado: str
    created_at: datetime
    updated_at: datetime


class OfertaWithUserResponse(BaseModel):
    """Schema for oferta response with user information."""

    model_config = {"from_attributes": True}

    id: UUID
    pedido_id: UUID
    user_id: UUID
    descripcion: str
    monto_ofrecido: Optional[float] = None
    estado: str
    created_at: datetime
    updated_at: datetime

    # User information (from relationship)
    user_email: Optional[str] = None
    user_ong: Optional[str] = None
    user_nombre: Optional[str] = None
    user_apellido: Optional[str] = None


class OfertaWithPedidoResponse(BaseModel):
    """Schema for oferta response with pedido information (for commitments)."""

    model_config = {"from_attributes": True}

    id: UUID
    pedido_id: UUID
    user_id: UUID
    descripcion: str
    monto_ofrecido: Optional[float] = None
    estado: str
    created_at: datetime
    updated_at: datetime

    # Pedido information (from relationship)
    pedido_tipo: Optional[str] = None
    pedido_descripcion: Optional[str] = None
    pedido_estado: Optional[str] = None
    pedido_monto: Optional[float] = None
    pedido_moneda: Optional[str] = None
    pedido_cantidad: Optional[int] = None
    pedido_unidad: Optional[str] = None


class OfertaConfirmacionResponse(BaseModel):
    """Schema for confirmation response with clear messaging and state transitions."""

    message: str = Field(..., description="Success message describing what happened")
    success: bool = Field(default=True, description="Operation success status")

    # Oferta information
    oferta_id: UUID = Field(..., description="ID of the confirmed oferta")
    oferta_estado: str = Field(..., description="Estado of the oferta (should be ACEPTADA)")

    # Pedido state transition
    pedido_id: UUID = Field(..., description="ID of the associated pedido")
    pedido_estado_anterior: str = Field(..., description="Previous estado of the pedido")
    pedido_estado_nuevo: str = Field(..., description="New estado of the pedido (should be COMPLETADO)")

    # Timestamp
    confirmed_at: datetime = Field(..., description="Timestamp when the confirmation was made")
