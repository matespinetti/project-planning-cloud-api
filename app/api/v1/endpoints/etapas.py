"""Etapa API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.etapa import EstadoEtapa
from app.models.pedido import EstadoPedido
from app.models.user import User
from app.schemas.etapa import (
    EtapaCompleteResponse,
    EtapaListItem,
    EtapasListResponse,
    EtapaStartResponse,
)
from app.services.etapa_service import EtapaService
from app.services.state_machine import etapa_pedidos_pendientes

router = APIRouter()


@router.get(
    "/projects/{project_id}/etapas",
    response_model=EtapasListResponse,
    status_code=status.HTTP_200_OK,
    summary="List project etapas",
    description="Get all etapas for a specific project with optional estado filter",
)
async def list_project_etapas(
    project_id: UUID,
    estado: Optional[EstadoEtapa] = Query(
        None, description="Filter by etapa estado (pendiente, financiada, en_ejecucion, completada)"
    ),
    db: AsyncSession = Depends(get_db),
) -> EtapasListResponse:
    """
    List all etapas for a project.

    - **project_id**: UUID of the project
    - **estado**: Optional filter by etapa estado
    - Returns list of etapas with pedido counts
    """
    etapas = await EtapaService.list_by_project(db, project_id, estado)

    # Build response with pedido counts
    etapa_items = []
    for etapa in etapas:
        pending_pedidos = etapa_pedidos_pendientes(etapa)
        etapa_item = EtapaListItem(
            id=etapa.id,
            proyecto_id=etapa.proyecto_id,
            nombre=etapa.nombre,
            descripcion=etapa.descripcion,
            fecha_inicio=etapa.fecha_inicio,
            fecha_fin=etapa.fecha_fin,
            estado=etapa.estado.value,
            fecha_completitud=etapa.fecha_completitud,
            pedidos=etapa.pedidos,
            pedidos_pendientes_count=len(pending_pedidos),
            pedidos_total_count=len(etapa.pedidos),
        )
        etapa_items.append(etapa_item)

    return EtapasListResponse(etapas=etapa_items, total=len(etapa_items))


@router.post(
    "/etapas/{etapa_id}/start",
    response_model=EtapaStartResponse,
    status_code=status.HTTP_200_OK,
    summary="Start an etapa",
    description="Mark an etapa as started (transition from financiada to en_ejecucion)",
)
async def start_etapa(
    etapa_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EtapaStartResponse:
    """
    Start an etapa (mark as en_ejecucion).

    **Requirements:**
    - Only project owner can start etapas
    - Project must be en_ejecucion
    - Etapa must be financiada (all pedidos completed)

    - **etapa_id**: UUID of the etapa to start
    - Returns success message with updated etapa data
    """
    result = await EtapaService.start_etapa(db, etapa_id, current_user)
    return EtapaStartResponse(**result)


@router.post(
    "/etapas/{etapa_id}/complete",
    response_model=EtapaCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete an etapa",
    description="Mark an etapa as completed (transition from en_ejecucion to completada)",
)
async def complete_etapa(
    etapa_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EtapaCompleteResponse:
    """
    Complete an etapa (mark as completada).

    **Requirements:**
    - Only project owner can complete etapas
    - Project must be en_ejecucion
    - Etapa must be en_ejecucion

    - **etapa_id**: UUID of the etapa to complete
    - Returns success message with updated etapa data including completion timestamp
    """
    result = await EtapaService.complete_etapa(db, etapa_id, current_user)
    return EtapaCompleteResponse(**result)
