"""Metrics endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.proyecto import Proyecto
from app.models.user import User
from app.schemas.errors import OWNERSHIP_RESPONSES, ErrorDetail
from app.schemas.metrics import (
    CommitmentMetrics,
    DashboardMetrics,
    PerformanceMetrics,
    ProyectoTrackingMetrics,
)
from app.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get(
    "/metrics/dashboard",
    response_model=DashboardMetrics,
    status_code=status.HTTP_200_OK,
    responses={
        401: OWNERSHIP_RESPONSES[401],
    },
)
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardMetrics:
    """
    Obtener métricas generales del dashboard.

    **Métricas incluidas:**
    - Distribución de proyectos por estado (pendiente, en_ejecucion, finalizado)
    - Total de proyectos en el sistema
    - Proyectos activos (en ejecución)
    - Proyectos listos para iniciar (en planificación con todos los pedidos completados)
    - Tasa de éxito (% de proyectos completados vs total)

    **Permisos:**
    - Todos los usuarios autenticados pueden ver estas métricas

    **Ejemplo de respuesta:**
    ```json
    {
      "proyectos_por_estado": {
        "pendiente": 2,
        "en_ejecucion": 2,
        "finalizado": 1
      },
      "total_proyectos": 8,
      "proyectos_activos": 2,
      "proyectos_listos_para_iniciar": 1,
      "tasa_exito": 14.29
    }
    ```
    """
    logger.info(f"User {current_user.id} requesting dashboard metrics")
    metrics = await MetricsService.get_dashboard_metrics(db)
    logger.info("Dashboard metrics calculated successfully")
    return metrics


@router.get(
    "/metrics/projects/{project_id}/tracking",
    response_model=ProyectoTrackingMetrics,
    status_code=status.HTTP_200_OK,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        404: {
            "model": ErrorDetail,
            "description": "Not Found - Proyecto does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Proyecto with id 123e4567-e89b-12d3-a456-426614174000 not found"
                    }
                }
            },
        },
    },
)
async def get_project_tracking_metrics(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProyectoTrackingMetrics:
    """
    Obtener métricas detalladas de tracking para un proyecto específico.

    **Métricas incluidas:**
    - Progreso por etapa (% de pedidos completados)
    - Tiempos planificados vs transcurridos por etapa
    - Estado de pedidos (total, completados, pendientes)
    - Estado de observaciones (pendientes, resueltas, vencidas)
    - Indicador de si el proyecto puede ser iniciado
    - Estado de salud de etapas (en_tiempo, retrasado, completado)
    - Días restantes hasta vencimiento

    **Permisos:**
    - Todos los usuarios autenticados pueden ver las métricas de cualquier proyecto
    - Útil para miembros del council y dueños del proyecto

    **Casos de uso:**
    - Panel de control de proyecto individual
    - Identificar bloqueos y cuellos de botella
    - Monitorear progreso de etapas
    - Ver estado de observaciones del consejo
    - Análisis por parte del council

    **Ejemplo de respuesta:**
    ```json
    {
      "proyecto_id": "...",
      "titulo": "Centro Comunitario Barrio Norte",
      "estado": "en_ejecucion",
      "etapas": [
        {
          "etapa_id": "...",
          "nombre": "Fundaciones y Estructura Base",
          "descripcion": "...",
          "fecha_inicio": "2024-10-01",
          "fecha_fin": "2024-11-30",
          "total_pedidos": 3,
          "pedidos_completados": 2,
          "pedidos_pendientes": 1,
          "progreso_porcentaje": 66.67,
          "dias_planificados": 60,
          "dias_transcurridos": 15,
          "estado_salud": "en_tiempo",
          "dias_restantes": 20
        }
      ],
      "total_pedidos": 3,
      "pedidos_completados": 2,
      "pedidos_pendientes": 1,
      "progreso_global_porcentaje": 66.67,
      "observaciones_pendientes": 2,
      "observaciones_resueltas": 2,
      "observaciones_vencidas": 1,
      "puede_iniciar": false
    }
    ```
    """
    logger.info(
        f"User {current_user.id} requesting tracking metrics for project {project_id}"
    )

    # Verify project exists
    ownership_stmt = select(Proyecto.id).where(Proyecto.id == project_id)
    result = await db.execute(ownership_stmt)
    project_exists = result.scalar_one_or_none()

    if not project_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proyecto with id {project_id} not found",
        )

    metrics = await MetricsService.get_project_tracking(db, project_id)
    logger.info(f"Tracking metrics calculated for project {project_id}")
    return metrics


@router.get(
    "/metrics/commitments",
    response_model=CommitmentMetrics,
    status_code=status.HTTP_200_OK,
    responses={
        401: OWNERSHIP_RESPONSES[401],
    },
)
async def get_commitment_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommitmentMetrics:
    """
    Obtener métricas sobre compromisos de la red (ofertas).

    **Métricas incluidas:**
    - Cobertura de ofertas (% de pedidos que tienen al menos una oferta)
    - Tasa de aceptación de ofertas
    - Distribución de ofertas por estado (pendiente, aceptada, rechazada)
    - Top 5 contribuidores (usuarios con más ofertas)
    - Tiempo promedio de respuesta (desde creación de pedido hasta primera oferta)
    - Valores monetarios (total solicitado vs comprometido para pedidos económicos)

    **Permisos:**
    - Todos los usuarios autenticados pueden ver estas métricas

    **Casos de uso:**
    - Evaluar participación de la red
    - Identificar miembros más activos
    - Medir eficiencia de la red en cubrir necesidades
    - Análisis de compromisos financieros

    **Ejemplo de respuesta:**
    ```json
    {
      "total_pedidos": 10,
      "pedidos_con_ofertas": 8,
      "cobertura_ofertas_porcentaje": 80.0,
      "total_ofertas": 15,
      "ofertas_aceptadas": 5,
      "ofertas_rechazadas": 2,
      "ofertas_pendientes": 8,
      "tasa_aceptacion_porcentaje": 33.33,
      "tiempo_respuesta_promedio_dias": 2.5,
      "top_contribuidores": [
        {
          "user_id": "...",
          "nombre": "Juan",
          "apellido": "Pérez",
          "ong": "Construcciones JP",
          "ofertas_realizadas": 10,
          "ofertas_aceptadas": 4,
          "tasa_aceptacion": 40.0
        }
      ],
      "valor_total_solicitado": 500000.0,
      "valor_total_comprometido": 350000.0
    }
    ```
    """
    logger.info(f"User {current_user.id} requesting commitment metrics")
    metrics = await MetricsService.get_commitment_metrics(db)
    logger.info("Commitment metrics calculated successfully")
    return metrics


@router.get(
    "/metrics/performance",
    response_model=PerformanceMetrics,
    status_code=status.HTTP_200_OK,
    responses={
        401: OWNERSHIP_RESPONSES[401],
    },
)
async def get_performance_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PerformanceMetrics:
    """
    Obtener métricas de rendimiento y eficiencia del sistema.

    **Métricas incluidas:**
    - Tiempo promedio por etapa (en días)
    - Tiempo promedio desde creación hasta inicio de proyecto
    - Proyectos atascados en planificación (más de 30 días)
    - Estado de observaciones (total, resueltas, pendientes, vencidas)
    - Tiempo promedio de resolución de observaciones

    **Permisos:**
    - Todos los usuarios autenticados pueden ver estas métricas

    **Casos de uso:**
    - Identificar cuellos de botella en el sistema
    - Evaluar eficiencia del proceso de aprobación
    - Monitorear cumplimiento de plazos de observaciones
    - KPIs para el consejo directivo

    **Ejemplo de respuesta:**
    ```json
    {
      "tiempo_promedio_etapa_dias": 45.5,
      "tiempo_inicio_promedio_dias": 12.3,
      "proyectos_pendientes_mas_30_dias": 3,
      "observaciones_total": 20,
      "observaciones_resueltas": 12,
      "observaciones_pendientes": 6,
      "observaciones_vencidas": 2,
      "tiempo_resolucion_observaciones_promedio_dias": 3.8
    }
    ```
    """
    logger.info(f"User {current_user.id} requesting performance metrics")
    metrics = await MetricsService.get_performance_metrics(db)
    logger.info("Performance metrics calculated successfully")
    return metrics
