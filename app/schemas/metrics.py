"""Metrics Pydantic schemas."""

from datetime import date
from typing import Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.etapa import EstadoEtapa
from app.models.proyecto import EstadoProyecto


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
    proyectos_en_riesgo: int = Field(
        ..., description="Projects with etapas past their due date"
    )
    velocidad_completacion: float = Field(
        ..., description="Average projects completed per week"
    )
    observaciones_vencidas_total: int = Field(
        ..., description="Total overdue observations in the system"
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
    estado: EstadoEtapa = Field(..., description="Etapa lifecycle state")
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
    estado_salud: Literal["en_tiempo", "retrasado", "completado"] = Field(
        ..., description="Health status: on-time, overdue, or completed"
    )
    dias_restantes: Optional[int] = Field(
        None, description="Days remaining until due date (negative if overdue)"
    )


class ProyectoTrackingMetrics(BaseModel):
    """Detailed tracking metrics for a specific project."""

    proyecto_id: UUID
    titulo: str
    estado: EstadoProyecto
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
    tasa_aceptacion: float = Field(..., description="Acceptance rate percentage")


class CommitmentMetrics(BaseModel):
    """Metrics about network commitments (ofertas)."""

    total_pedidos: int = Field(..., description="Total number of pedidos in the system")
    pedidos_con_ofertas: int = Field(
        ..., description="Pedidos that have at least one oferta"
    )
    cobertura_ofertas_porcentaje: float = Field(
        ..., description="% of pedidos that have at least one oferta"
    )
    tasa_aceptacion_porcentaje: float = Field(
        ..., description="% of ofertas that were accepted"
    )
    tiempo_respuesta_promedio_dias: Optional[float] = Field(
        None, description="Average days from pedido creation to first oferta"
    )
    top_contribuidores: List[TopContribuidor] = Field(
        [], description="Top 5 contributors by acceptance rate"
    )
    pedidos_por_tipo: Dict[str, int] = Field(
        ..., description="Distribution of pedidos by type (economico, materiales, etc)"
    )
    cobertura_por_tipo: Dict[str, float] = Field(
        ..., description="Coverage percentage for each pedido type"
    )


# ============================================================================
# Performance Metrics
# ============================================================================


class PerformanceMetrics(BaseModel):
    """Performance and efficiency metrics."""

    tiempo_promedio_etapa_dias: Optional[float] = Field(
        None, description="Average duration of etapas in days"
    )
    semanas_promedio_etapa: Optional[float] = Field(
        None, description="Average duration of etapas in weeks"
    )
    tiempo_inicio_promedio_dias: Optional[float] = Field(
        None,
        description="Average days from project creation to en_ejecucion transition",
    )
    proyectos_pendientes_mas_30_dias: int = Field(
        ..., description="Projects stuck in pending (sin ejecución) for more than 30 days"
    )
    observaciones_total: int = Field(..., description="Total observations in the system")
    observaciones_resueltas: int = Field(..., description="Resolved observations")
    observaciones_pendientes: int = Field(..., description="Pending observations")
    observaciones_vencidas: int = Field(..., description="Overdue observations")
    tiempo_resolucion_observaciones_promedio_dias: Optional[float] = Field(
        None, description="Average days to resolve an observacion"
    )
    tasa_cumplimiento_observaciones: float = Field(
        ..., description="Percentage of observations that were resolved"
    )
    tiempo_respuesta_promedio_pedido_dias: Optional[float] = Field(
        None, description="Average days from pedido creation to completion"
    )
    distribucion_pedidos_por_tipo: Dict[str, int] = Field(
        ..., description="Count of pedidos by type"
    )
