"""
Test script to verify etapa completion flow works correctly.
Tests that etapas marked as 'completada' stay completada when completing project.
"""

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.etapa import Etapa, EstadoEtapa
from app.models.proyecto import Proyecto, EstadoProyecto
from app.models.user import User
from app.services.proyecto_service import ProyectoService


async def test_complete_project_with_completed_etapas():
    """Test that completing a project doesn't reset etapa states."""

    async with AsyncSessionLocal() as db:
        print("🧪 Test: Completing project with completed etapas\n")
        print("=" * 70)

        # 1. Find a project in execution
        stmt = select(Proyecto).where(
            Proyecto.estado == EstadoProyecto.en_ejecucion
        ).limit(1)
        result = await db.execute(stmt)
        proyecto = result.scalar_one_or_none()

        if not proyecto:
            print("❌ No project in execution found. Run seed_data.py first.")
            return False

        print(f"✅ Found project: {proyecto.titulo}")
        print(f"   Estado: {proyecto.estado}")
        print(f"   ID: {proyecto.id}\n")

        # 2. Get the project owner
        stmt = select(User).where(User.id == proyecto.user_id)
        result = await db.execute(stmt)
        user = result.scalar_one()
        print(f"✅ Project owner: {user.email}\n")

        # 3. Load etapas
        stmt = (
            select(Etapa)
            .where(Etapa.proyecto_id == proyecto.id)
            .order_by(Etapa.fecha_inicio)
        )
        result = await db.execute(stmt)
        etapas = list(result.scalars().all())

        print(f"📋 Etapas before completion:\n")
        for i, etapa in enumerate(etapas, 1):
            print(f"   {i}. {etapa.nombre}")
            print(f"      Estado: {etapa.estado.value}")
            print(f"      ID: {etapa.id}")

        # 4. Mark all etapas as completada manually
        print(f"\n🔄 Marking all etapas as completada...\n")
        for etapa in etapas:
            if etapa.estado != EstadoEtapa.completada:
                etapa.estado = EstadoEtapa.completada
                from datetime import datetime, timezone
                if not etapa.fecha_completitud:
                    etapa.fecha_completitud = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(proyecto)

        # Verify all etapas are completada
        stmt = (
            select(Etapa)
            .where(Etapa.proyecto_id == proyecto.id)
        )
        result = await db.execute(stmt)
        etapas = list(result.scalars().all())

        print(f"✅ All etapas marked as completada:\n")
        for i, etapa in enumerate(etapas, 1):
            print(f"   {i}. {etapa.nombre} → {etapa.estado.value}")
            if etapa.estado != EstadoEtapa.completada:
                print(f"      ❌ ERROR: Expected completada, got {etapa.estado.value}")
                return False

        # 5. Try to complete the project
        print(f"\n🎯 Attempting to complete project...\n")

        try:
            result = await ProyectoService.complete_project(db, proyecto.id, user)
            print(f"✅ Project completed successfully!")
            print(f"   Message: {result['message']}")
            print(f"   Estado: {result['estado']}\n")
        except Exception as e:
            print(f"❌ Failed to complete project: {e}\n")
            return False

        # 6. Verify etapas are STILL completada (not reset)
        stmt = (
            select(Etapa)
            .where(Etapa.proyecto_id == proyecto.id)
        )
        result = await db.execute(stmt)
        etapas_after = list(result.scalars().all())

        print(f"🔍 Verifying etapas after project completion:\n")
        all_good = True
        for i, etapa in enumerate(etapas_after, 1):
            status_icon = "✅" if etapa.estado == EstadoEtapa.completada else "❌"
            print(f"   {status_icon} {etapa.nombre} → {etapa.estado.value}")
            if etapa.estado != EstadoEtapa.completada:
                print(f"      ❌ ERROR: Estado changed from completada!")
                all_good = False

        print("\n" + "=" * 70)
        if all_good:
            print("✅ TEST PASSED: Etapas stayed completada after project completion!")
            return True
        else:
            print("❌ TEST FAILED: Some etapas were reset!")
            return False


if __name__ == "__main__":
    success = asyncio.run(test_complete_project_with_completed_etapas())
    exit(0 if success else 1)
