"""Metrics service - Business logic for calculating system metrics."""

import logging
from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.etapa import Etapa
from app.models.observacion import EstadoObservacion, Observacion
from app.models.oferta import EstadoOferta, Oferta
from app.models.pedido import EstadoPedido, Pedido, TipoPedido
from app.models.proyecto import EstadoProyecto, Proyecto
from app.models.user import User
from app.schemas.metrics import (
    CommitmentMetrics,
    DashboardMetrics,
    EtapaTracking,
    PerformanceMetrics,
    ProyectosPorEstado,
    ProyectoTrackingMetrics,
    TopContribuidor,
)
from app.services.state_machine import etapa_all_pedidos_financed

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for calculating system metrics."""

    @staticmethod
    async def get_dashboard_metrics(db: AsyncSession) -> DashboardMetrics:
        """
        Calculate global dashboard metrics.

        Returns:
            DashboardMetrics with project counts and success rate
        """
        logger.info("Calculating dashboard metrics")

        # Count projects by estado
        estado_counts = {}
        for estado in EstadoProyecto:
            count_stmt = select(func.count()).where(Proyecto.estado == estado.value)
            count = (await db.execute(count_stmt)).scalar_one()
            estado_counts[estado.value] = count

        # Total projects
        total_proyectos = sum(estado_counts.values())

        # Projects in execution
        proyectos_activos = estado_counts.get(EstadoProyecto.en_ejecucion.value, 0)

        # Projects ready to start (pendiente with all etapas financed)
        # First, get all projects in pending state
        planning_stmt = (
            select(Proyecto)
            .options(joinedload(Proyecto.etapas).joinedload(Etapa.pedidos))
            .where(Proyecto.estado == EstadoProyecto.pendiente.value)
        )
        result = await db.execute(planning_stmt)
        planning_projects = list(result.unique().scalars().all())

        # Check which ones have all etapas financed
        ready_to_start = 0
        for proyecto in planning_projects:
            if proyecto.etapas and all(
                etapa_all_pedidos_financed(etapa) for etapa in proyecto.etapas
            ):
                ready_to_start += 1

        # Success rate (completed / total, excluding pending)
        completed_count = estado_counts.get(EstadoProyecto.finalizado.value, 0)
        non_pending_total = total_proyectos - estado_counts.get(
            EstadoProyecto.pendiente.value, 0
        )
        tasa_exito = (
            (completed_count / non_pending_total * 100) if non_pending_total > 0 else 0.0
        )

        return DashboardMetrics(
            proyectos_por_estado=ProyectosPorEstado(
                pendiente=estado_counts.get(EstadoProyecto.pendiente.value, 0),
                en_ejecucion=estado_counts.get(EstadoProyecto.en_ejecucion.value, 0),
                finalizado=estado_counts.get(EstadoProyecto.finalizado.value, 0),
            ),
            total_proyectos=total_proyectos,
            proyectos_activos=proyectos_activos,
            proyectos_listos_para_iniciar=ready_to_start,
            tasa_exito=round(tasa_exito, 2),
        )

    @staticmethod
    async def get_project_tracking(
        db: AsyncSession, project_id: UUID
    ) -> ProyectoTrackingMetrics:
        """
        Calculate detailed tracking metrics for a specific project.

        Args:
            db: Database session
            project_id: Project ID to track

        Returns:
            ProyectoTrackingMetrics with detailed progress information

        Raises:
            HTTPException: 404 if project not found
        """
        logger.info(f"Calculating tracking metrics for project {project_id}")

        # Get project with all relationships
        stmt = (
            select(Proyecto)
            .options(
                joinedload(Proyecto.etapas).joinedload(Etapa.pedidos),
                joinedload(Proyecto.observaciones),
            )
            .where(Proyecto.id == project_id)
        )
        result = await db.execute(stmt)
        proyecto = result.unique().scalar_one_or_none()

        if not proyecto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proyecto with id {project_id} not found",
            )

        # Calculate etapa tracking
        etapas_tracking: List[EtapaTracking] = []
        total_pedidos = 0
        pedidos_completados = 0

        for etapa in proyecto.etapas:
            etapa_total = len(etapa.pedidos)
            etapa_completados = sum(
                1
                for p in etapa.pedidos
                if p.estado == EstadoPedido.COMPLETADO.value
            )
            etapa_pendientes = etapa_total - etapa_completados

            # Calculate progress percentage
            progreso = (
                (etapa_completados / etapa_total * 100) if etapa_total > 0 else 0.0
            )

            # Calculate time metrics
            dias_planificados = (etapa.fecha_fin - etapa.fecha_inicio).days
            dias_transcurridos = None
            if proyecto.estado == EstadoProyecto.en_ejecucion.value:
                # Only calculate if project is in execution
                dias_transcurridos = (date.today() - etapa.fecha_inicio).days
                if dias_transcurridos < 0:
                    dias_transcurridos = 0

            etapas_tracking.append(
                EtapaTracking(
                    etapa_id=etapa.id,
                    nombre=etapa.nombre,
                    descripcion=etapa.descripcion,
                    fecha_inicio=etapa.fecha_inicio,
                    fecha_fin=etapa.fecha_fin,
                    estado=etapa.estado.value,
                    total_pedidos=etapa_total,
                    pedidos_completados=etapa_completados,
                    pedidos_pendientes=etapa_pendientes,
                    progreso_porcentaje=round(progreso, 2),
                    dias_planificados=dias_planificados,
                    dias_transcurridos=dias_transcurridos,
                )
            )

            total_pedidos += etapa_total
            pedidos_completados += etapa_completados

        pedidos_pendientes = total_pedidos - pedidos_completados
        progreso_global = (
            (pedidos_completados / total_pedidos * 100) if total_pedidos > 0 else 0.0
        )

        # Check if can start
        puede_iniciar = (
            proyecto.estado == EstadoProyecto.pendiente.value
            and proyecto.etapas
            and all(etapa_all_pedidos_financed(etapa) for etapa in proyecto.etapas)
        )

        # Count observaciones by status
        obs_pendientes = sum(
            1
            for obs in proyecto.observaciones
            if obs.estado == EstadoObservacion.pendiente.value
        )
        obs_resueltas = sum(
            1
            for obs in proyecto.observaciones
            if obs.estado == EstadoObservacion.resuelta.value
        )
        # Vencidas are those pendientes with fecha_limite in the past
        today = date.today()
        obs_vencidas = sum(
            1
            for obs in proyecto.observaciones
            if obs.estado == EstadoObservacion.pendiente.value
            and obs.fecha_limite < today
        )

        return ProyectoTrackingMetrics(
            proyecto_id=proyecto.id,
            titulo=proyecto.titulo,
            estado=proyecto.estado,
            etapas=etapas_tracking,
            total_pedidos=total_pedidos,
            pedidos_completados=pedidos_completados,
            pedidos_pendientes=pedidos_pendientes,
            progreso_global_porcentaje=round(progreso_global, 2),
            observaciones_pendientes=obs_pendientes,
            observaciones_resueltas=obs_resueltas,
            observaciones_vencidas=obs_vencidas,
            puede_iniciar=puede_iniciar,
        )

    @staticmethod
    async def get_commitment_metrics(db: AsyncSession) -> CommitmentMetrics:
        """
        Calculate metrics about network commitments (ofertas).

        Returns:
            CommitmentMetrics with oferta coverage and acceptance rates
        """
        logger.info("Calculating commitment metrics")

        # Total pedidos
        total_pedidos_stmt = select(func.count(Pedido.id))
        total_pedidos = (await db.execute(total_pedidos_stmt)).scalar_one()

        # Pedidos with at least one oferta
        pedidos_con_ofertas_stmt = select(func.count(func.distinct(Oferta.pedido_id)))
        pedidos_con_ofertas = (await db.execute(pedidos_con_ofertas_stmt)).scalar_one()

        # Coverage percentage
        cobertura = (
            (pedidos_con_ofertas / total_pedidos * 100) if total_pedidos > 0 else 0.0
        )

        # Total ofertas by estado
        total_ofertas_stmt = select(func.count(Oferta.id))
        total_ofertas = (await db.execute(total_ofertas_stmt)).scalar_one()

        ofertas_aceptadas_stmt = select(func.count(Oferta.id)).where(
            Oferta.estado == EstadoOferta.aceptada.value
        )
        ofertas_aceptadas = (await db.execute(ofertas_aceptadas_stmt)).scalar_one()

        ofertas_rechazadas_stmt = select(func.count(Oferta.id)).where(
            Oferta.estado == EstadoOferta.rechazada.value
        )
        ofertas_rechazadas = (await db.execute(ofertas_rechazadas_stmt)).scalar_one()

        ofertas_pendientes_stmt = select(func.count(Oferta.id)).where(
            Oferta.estado == EstadoOferta.pendiente.value
        )
        ofertas_pendientes = (await db.execute(ofertas_pendientes_stmt)).scalar_one()

        # Acceptance rate
        tasa_aceptacion = (
            (ofertas_aceptadas / total_ofertas * 100) if total_ofertas > 0 else 0.0
        )

        # Note: Average response time cannot be calculated because Pedido model
        # has no timestamp fields. This metric is set to None.

        # Top contributors (users with most ofertas)
        top_stmt = (
            select(
                User,
                func.count(Oferta.id).label("ofertas_count"),
                func.sum(
                    case((Oferta.estado == EstadoOferta.aceptada.value, 1), else_=0)
                ).label("aceptadas_count"),
            )
            .join(Oferta, User.id == Oferta.user_id)
            .group_by(User.id)
            .order_by(func.count(Oferta.id).desc())
            .limit(5)
        )
        result = await db.execute(top_stmt)
        top_rows = result.all()

        top_contribuidores = [
            TopContribuidor(
                user_id=user.id,
                nombre=user.nombre,
                apellido=user.apellido,
                ong=user.ong,
                ofertas_realizadas=ofertas_count,
                ofertas_aceptadas=aceptadas_count,
                tasa_aceptacion=round(
                    (aceptadas_count / ofertas_count * 100) if ofertas_count > 0 else 0.0,
                    2,
                ),
            )
            for user, ofertas_count, aceptadas_count in top_rows
        ]

        # Total monetary values (only economico pedidos)
        valor_solicitado_stmt = select(
            func.coalesce(func.sum(Pedido.monto), 0)
        ).where(Pedido.tipo == TipoPedido.ECONOMICO.value)
        valor_solicitado = (await db.execute(valor_solicitado_stmt)).scalar_one()

        # Valor comprometido (accepted ofertas for economico pedidos)
        valor_comprometido_stmt = (
            select(func.coalesce(func.sum(Oferta.monto_ofrecido), 0))
            .join(Oferta.pedido)
            .where(
                Oferta.estado == EstadoOferta.aceptada.value,
                Pedido.tipo == TipoPedido.ECONOMICO.value,
            )
        )
        valor_comprometido = (await db.execute(valor_comprometido_stmt)).scalar_one()

        return CommitmentMetrics(
            total_pedidos=total_pedidos,
            pedidos_con_ofertas=pedidos_con_ofertas,
            cobertura_ofertas_porcentaje=round(cobertura, 2),
            total_ofertas=total_ofertas,
            ofertas_aceptadas=ofertas_aceptadas,
            ofertas_rechazadas=ofertas_rechazadas,
            ofertas_pendientes=ofertas_pendientes,
            tasa_aceptacion_porcentaje=round(tasa_aceptacion, 2),
            tiempo_respuesta_promedio_dias=None,
            top_contribuidores=top_contribuidores,
            valor_total_solicitado=float(valor_solicitado),
            valor_total_comprometido=float(valor_comprometido),
        )

    @staticmethod
    async def get_performance_metrics(db: AsyncSession) -> PerformanceMetrics:
        """
        Calculate performance and efficiency metrics.

        Returns:
            PerformanceMetrics with time-based KPIs
        """
        logger.info("Calculating performance metrics")

        # Average etapa duration (fecha_fin - fecha_inicio)
        # Note: fecha_fin and fecha_inicio are Date fields, so subtraction gives days directly
        avg_etapa_stmt = select(
            func.avg(Etapa.fecha_fin - Etapa.fecha_inicio)
        )
        avg_etapa_days = (await db.execute(avg_etapa_stmt)).scalar_one()

        # Average time from creation to en_ejecucion
        # This is approximate - we can only measure projects currently in execution
        # Assumption: created_at to updated_at when estado is en_ejecucion
        avg_inicio_stmt = select(
            func.avg(
                func.extract("epoch", Proyecto.updated_at - Proyecto.created_at) / 86400
            )
        ).where(Proyecto.estado == EstadoProyecto.en_ejecucion.value)
        avg_inicio_days = (await db.execute(avg_inicio_stmt)).scalar_one()

        # Projects stuck in planning for more than 30 days
        thirty_days_ago = datetime.now(timezone.utc).timestamp() - (30 * 86400)
        stuck_stmt = select(func.count(Proyecto.id)).where(
            Proyecto.estado == EstadoProyecto.pendiente.value,
            func.extract("epoch", Proyecto.created_at) < thirty_days_ago,
        )
        stuck_count = (await db.execute(stuck_stmt)).scalar_one()

        # Observaciones counts
        total_obs_stmt = select(func.count(Observacion.id))
        total_obs = (await db.execute(total_obs_stmt)).scalar_one()

        resueltas_stmt = select(func.count(Observacion.id)).where(
            Observacion.estado == EstadoObservacion.resuelta.value
        )
        resueltas = (await db.execute(resueltas_stmt)).scalar_one()

        pendientes_stmt = select(func.count(Observacion.id)).where(
            Observacion.estado == EstadoObservacion.pendiente.value
        )
        pendientes = (await db.execute(pendientes_stmt)).scalar_one()

        # Vencidas (pendientes with fecha_limite < today)
        today = date.today()
        vencidas_stmt = select(func.count(Observacion.id)).where(
            Observacion.estado == EstadoObservacion.pendiente.value,
            Observacion.fecha_limite < today,
        )
        vencidas = (await db.execute(vencidas_stmt)).scalar_one()

        # Average resolution time for observaciones
        # fecha_resolucion - created_at for resolved observaciones
        avg_resolucion_stmt = select(
            func.avg(
                func.extract(
                    "epoch", Observacion.fecha_resolucion - Observacion.created_at
                )
                / 86400
            )
        ).where(Observacion.estado == EstadoObservacion.resuelta.value)
        avg_resolucion_days = (await db.execute(avg_resolucion_stmt)).scalar_one()

        return PerformanceMetrics(
            tiempo_promedio_etapa_dias=round(avg_etapa_days, 2)
            if avg_etapa_days
            else None,
            tiempo_inicio_promedio_dias=round(avg_inicio_days, 2)
            if avg_inicio_days
            else None,
            proyectos_pendientes_mas_30_dias=stuck_count,
            observaciones_total=total_obs,
            observaciones_resueltas=resueltas,
            observaciones_pendientes=pendientes,
            observaciones_vencidas=vencidas,
            tiempo_resolucion_observaciones_promedio_dias=round(avg_resolucion_days, 2)
            if avg_resolucion_days
            else None,
        )
