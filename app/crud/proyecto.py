"""CRUD operations for Proyecto."""

from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.etapa import Etapa
from app.models.pedido import Pedido
from app.models.proyecto import Proyecto
from app.schemas.proyecto import ProyectoCreate, ProyectoUpdate


async def create_proyecto(
    db: AsyncSession, proyecto_data: ProyectoCreate
) -> Proyecto:
    """
    Create a proyecto with nested etapas and pedidos in a single transaction.
    """
    # Create Proyecto instance
    db_proyecto = Proyecto(
        titulo=proyecto_data.titulo,
        descripcion=proyecto_data.descripcion,
        tipo=proyecto_data.tipo,
        pais=proyecto_data.pais,
        provincia=proyecto_data.provincia,
        ciudad=proyecto_data.ciudad,
        barrio=proyecto_data.barrio,
        estado=proyecto_data.estado,
        bonita_case_id=proyecto_data.bonita_case_id,
        bonita_process_instance_id=proyecto_data.bonita_process_instance_id,
    )

    # Create Etapas with Pedidos
    for etapa_data in proyecto_data.etapas:
        db_etapa = Etapa(
            nombre=etapa_data.nombre,
            descripcion=etapa_data.descripcion,
            fecha_inicio=date.fromisoformat(etapa_data.fecha_inicio),
            fecha_fin=date.fromisoformat(etapa_data.fecha_fin),
        )

        # Create Pedidos for this Etapa
        for pedido_data in etapa_data.pedidos:
            db_pedido = Pedido(
                tipo=pedido_data.tipo,
                descripcion=pedido_data.descripcion,
                monto=pedido_data.monto,
                moneda=pedido_data.moneda,
                cantidad=pedido_data.cantidad,
                unidad=pedido_data.unidad,
            )
            db_etapa.pedidos.append(db_pedido)

        db_proyecto.etapas.append(db_etapa)

    db.add(db_proyecto)
    await db.commit()
    await db.refresh(db_proyecto)

    return db_proyecto


async def get_proyecto(db: AsyncSession, proyecto_id: UUID) -> Optional[Proyecto]:
    """
    Get a proyecto by ID with all nested data (eager loading).
    """
    stmt = (
        select(Proyecto)
        .where(Proyecto.id == proyecto_id)
        .options(
            joinedload(Proyecto.etapas).joinedload(Etapa.pedidos)
        )
    )
    result = await db.execute(stmt)
    return result.unique().scalar_one_or_none()


async def update_proyecto(
    db: AsyncSession, proyecto_id: UUID, update_data: ProyectoUpdate
) -> Optional[Proyecto]:
    """
    Partial update of a proyecto (PATCH).
    """
    db_proyecto = await get_proyecto(db, proyecto_id)
    if not db_proyecto:
        return None

    # Update only provided fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_proyecto, key, value)

    await db.commit()
    await db.refresh(db_proyecto)

    return db_proyecto


async def delete_proyecto(db: AsyncSession, proyecto_id: UUID) -> bool:
    """
    Delete a proyecto (cascades to etapas and pedidos).
    """
    db_proyecto = await get_proyecto(db, proyecto_id)
    if not db_proyecto:
        return False

    await db.delete(db_proyecto)
    await db.commit()

    return True
