"""Shared helpers to keep proyecto/etapa state transitions consistent."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from app.models.etapa import Etapa, EstadoEtapa
from app.models.pedido import EstadoPedido, Pedido


def etapa_pedidos_pendientes(etapa: Etapa) -> List[Pedido]:
    """Return pedidos that are still pending funding (EstadoPedido.PENDIENTE)."""
    return [pedido for pedido in etapa.pedidos if pedido.estado == EstadoPedido.PENDIENTE]


def etapa_all_pedidos_financed(etapa: Etapa) -> bool:
    """True when the etapa has pedidos and all are COMPLETADO (fully financed)."""
    pedidos = etapa.pedidos
    return bool(pedidos) and all(pedido.estado == EstadoPedido.COMPLETADO for pedido in pedidos)


def etapa_all_pedidos_completed(etapa: Etapa) -> bool:
    """True when every pedido within the etapa is completed."""
    pedidos = etapa.pedidos
    return bool(pedidos) and all(pedido.estado == EstadoPedido.COMPLETADO for pedido in pedidos)


def can_auto_calculate_state(etapa: Etapa) -> bool:
    """
    Returns True if etapa state can be auto-calculated based on pedidos.
    Returns False if etapa is in a manual state that should NEVER be touched.

    AUTO-CALCULATED STATES (based on pedidos):
    - pendiente: Has pedidos without completed status
    - financiada: All pedidos are COMPLETADO

    MANUAL STATES (user-controlled via endpoints):
    - en_ejecucion: User explicitly started etapa
    - completada: User explicitly finished etapa
    """
    return etapa.estado in [EstadoEtapa.pendiente, EstadoEtapa.financiada]


def refresh_etapa_state(etapa: Etapa) -> EstadoEtapa:
    """
    Auto-calculate etapa state ONLY for pendiente/financiada states.

    This function is SAFE to call anytime because:
    - It NEVER touches en_ejecucion or completada (manual states)
    - It only updates pendiente ↔ financiada based on pedidos
    - Manual state transitions are protected from auto-calculation

    State logic:
    - If all pedidos COMPLETADO → financiada
    - If any pedidos not COMPLETADO → pendiente
    - If en_ejecucion or completada → NO CHANGE (return immediately)
    """
    # IMMUTABLE RULE: Never touch manual states
    if not can_auto_calculate_state(etapa):
        return etapa.estado

    # Auto-calculate state based on pedidos (only for pendiente/financiada)
    if etapa_all_pedidos_financed(etapa):
        etapa.estado = EstadoEtapa.financiada
        etapa.fecha_financiada = datetime.now(timezone.utc)
    else:
        etapa.estado = EstadoEtapa.pendiente
        # Clear completion timestamp if reverting to pendiente
        etapa.fecha_completitud = None
        # Clear financiada timestamp if reverting to pendiente
        etapa.fecha_financiada = None

    return etapa.estado
