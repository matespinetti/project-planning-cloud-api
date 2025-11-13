"""Metrics Pydantic schemas."""

from datetime import date
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Dashboard Metrics
# ============================================================================


class ProyectosPorEstado(BaseModel):
    """Count of projects by lifecycle state."""

    pendiente: int = Field(0, description="Created and seeking financing")
    en_ejecucion: int = Field(0, description="Currently being executed")
    finalizado: int = Field(0, description="Finished projects")


class DashboardMetrics(BaseModel):
    """Global dashboard metrics."""

    proyectos_por_estado: ProyectosPorEstado
    total_proyectos: int = Field(..., description="Total number of projects")
    proyectos_activos: int = Field(..., description="Projects in execution")
    proyectos_listos_para_iniciar: int = Field(
        ..., description="Projects in planning with all pedidos completed"
    )
    tasa_exito: float = Field(
        ..., description="Success rate: % of completed projects vs total"
    )


# ============================================================================
# Project Tracking Metrics
# ============================================================================


class EtapaTracking(BaseModel):
    """Tracking information for a single etapa."""

    etapa_id: UUID
    nombre: str
    descripcion: str
    fecha_inicio: date
    fecha_fin: date
    estado: str = Field(..., description="Etapa lifecycle state")
    total_pedidos: int
    pedidos_completados: int
    pedidos_pendientes: int
    progreso_porcentaje: float = Field(
        ..., description="Percentage of completed pedidos"
    )
    dias_planificados: int = Field(..., description="Planned duration in days")
    dias_transcurridos: Optional[int] = Field(
        None, description="Days since start date (if started)"
    )


class ProyectoTrackingMetrics(BaseModel):
    """Detailed tracking metrics for a specific project."""

    proyecto_id: UUID
    titulo: str
    estado: str
    etapas: List[EtapaTracking]
    total_pedidos: int
    pedidos_completados: int
    pedidos_pendientes: int
    progreso_global_porcentaje: float = Field(
        ..., description="Overall progress across all etapas"
    )
    observaciones_pendientes: int
    observaciones_resueltas: int
    observaciones_vencidas: int
    puede_iniciar: bool = Field(
        ..., description="Whether project can be started (all pedidos completed)"
    )


# ============================================================================
# Commitment Metrics
# ============================================================================


class TopContribuidor(BaseModel):
    """Top contributor information."""

    user_id: UUID
    nombre: str
    apellido: str
    ong: str
    ofertas_realizadas: int
    ofertas_aceptadas: int
    tasa_aceptacion: float = Field(..., description="Acceptance rate percentage")


class CommitmentMetrics(BaseModel):
    """Metrics about network commitments (ofertas)."""

    total_pedidos: int
    pedidos_con_ofertas: int
    cobertura_ofertas_porcentaje: float = Field(
        ..., description="% of pedidos that have at least one oferta"
    )
    total_ofertas: int
    ofertas_aceptadas: int
    ofertas_rechazadas: int
    ofertas_pendientes: int
    tasa_aceptacion_porcentaje: float = Field(
        ..., description="% of ofertas that were accepted"
    )
    tiempo_respuesta_promedio_dias: Optional[float] = Field(
        None, description="Average days from pedido creation to first oferta"
    )
    top_contribuidores: List[TopContribuidor] = Field(
        [], description="Top 5 contributors by number of ofertas"
    )
    valor_total_solicitado: float = Field(
        ..., description="Total monetary value requested (economico pedidos)"
    )
    valor_total_comprometido: float = Field(
        ..., description="Total value of accepted ofertas"
    )


# ============================================================================
# Performance Metrics
# ============================================================================


class PerformanceMetrics(BaseModel):
    """Performance and efficiency metrics."""

    tiempo_promedio_etapa_dias: Optional[float] = Field(
        None, description="Average duration of etapas in days"
    )
    tiempo_inicio_promedio_dias: Optional[float] = Field(
        None,
        description="Average days from project creation to en_ejecucion transition",
    )
    proyectos_pendientes_mas_30_dias: int = Field(
        ..., description="Projects stuck in pending (sin ejecución) for more than 30 days"
    )
    observaciones_total: int
    observaciones_resueltas: int
    observaciones_pendientes: int
    observaciones_vencidas: int
    tiempo_resolucion_observaciones_promedio_dias: Optional[float] = Field(
        None, description="Average days to resolve an observacion"
    )
