"""
Seed script for populating the database with consistent, realistic sample data.

This script creates a complete test environment with:
- 5 users (Bonita system + 2 COUNCIL + 2 MEMBER)
- 3 FINALIZADO projects with realistic timelines
- 5 etapas with proper state consistency
- 9 pedidos (all COMPLETADO)
- 9 ofertas (all aceptada)
- 4 observaciones (RESUELTA/VENCIDA only)

KEY BUSINESS RULE: Para que un Proyecto esté EN_EJECUCION, TODAS sus etapas
deben estar financiadas (todos sus pedidos deben estar COMPLETADO).

Run with: uv run python seed_data.py
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.etapa import Etapa, EstadoEtapa
from app.models.observacion import EstadoObservacion, Observacion
from app.models.oferta import EstadoOferta, Oferta
from app.models.pedido import EstadoPedido, Pedido, TipoPedido
from app.models.proyecto import EstadoProyecto, Proyecto
from app.models.user import User, UserRole
from app.schemas.etapa import EtapaCreate
from app.schemas.oferta import OfertaCreate
from app.schemas.pedido import PedidoCreate
from app.schemas.proyecto import ProyectoCreate
from app.services.oferta_service import OfertaService
from app.services.proyecto_service import ProyectoService

# Deterministic UUID for the Bonita integration user so it can be referenced via env vars
BONITA_SYSTEM_USER_ID = UUID("11111111-1111-1111-1111-111111111111")


async def clear_database(db: AsyncSession):
    """Clear all data from tables (in correct order due to foreign keys)."""
    print("🗑️  Clearing existing data...")

    # Delete in order to respect foreign keys
    await db.execute(delete(Observacion))
    await db.execute(delete(Oferta))
    await db.execute(delete(Pedido))
    await db.execute(delete(Etapa))
    await db.execute(delete(Proyecto))
    await db.execute(delete(User))

    await db.commit()
    print("✅ Database cleared")


async def create_users(db: AsyncSession) -> dict:
    """Create users: Bonita system + 2 COUNCIL + 2 MEMBER."""
    print("\n👥 Creating users...")

    users_list = []

    # ===== SYSTEM USER FOR BONITA INTEGRATION =====
    bonita_system_user = User(
        id=BONITA_SYSTEM_USER_ID,
        email="bonita.integration@projectplanning.org",
        password=get_password_hash("BonitaSystem#2024"),
        nombre="Bonita",
        apellido="System",
        ong="ProjectPlanning Automation",
        role=UserRole.COUNCIL,
    )
    users_list.append(bonita_system_user)

    # ===== COUNCIL USERS =====
    council1 = User(
        id=uuid4(),
        email="consejo@rednacional.org",
        password=get_password_hash("Password123"),
        nombre="Carlos",
        apellido="Rodríguez",
        ong="Consejo Directivo Red Nacional ONGs",
        role=UserRole.COUNCIL,
    )
    users_list.append(council1)

    council2 = User(
        id=uuid4(),
        email="auditoria@rednacional.org",
        password=get_password_hash("Password123"),
        nombre="Ana",
        apellido="Martínez",
        ong="Auditoría Red Nacional ONGs",
        role=UserRole.COUNCIL,
    )
    users_list.append(council2)

    # ===== MEMBER USERS (Project Owners + Oferentes) =====
    member1 = User(
        id=uuid4(),
        email="maria@barrionorte.org",
        password=get_password_hash("Password123"),
        nombre="María",
        apellido="González",
        ong="Fundación Barrio Norte",
        role=UserRole.MEMBER,
    )
    users_list.append(member1)

    member2 = User(
        id=uuid4(),
        email="pedro@desarrollo.org",
        password=get_password_hash("Password123"),
        nombre="Pedro",
        apellido="López",
        ong="ONG Desarrollo Comunitario",
        role=UserRole.MEMBER,
    )
    users_list.append(member2)

    # Add all users to database
    db.add_all(users_list)
    await db.commit()

    print(f"✅ Created {len(users_list)} users (including Bonita system account)")
    print(f"   • Bonita system user id: {BONITA_SYSTEM_USER_ID}")
    print("     Configure BONITA_SYSTEM_USER_ID in .env with this UUID to enable API key auth.")

    return {
        "bonita_system_user": bonita_system_user,
        "council1": council1,
        "council2": council2,
        "member1": member1,
        "member2": member2,
    }


async def create_projects(db: AsyncSession, users: dict) -> list:
    """Create 3 FINALIZADO projects with realistic completion timelines."""
    print("\n📋 Creating projects...")

    projects = []

    # =========================================================================
    # PROJECT A: FINALIZADO - Antiguo (4 meses atrás)
    # =========================================================================
    p_a = Proyecto(
        id=uuid4(),
        user_id=users["member1"].id,
        titulo="Huerta Orgánica Comunitaria",
        descripcion="Huerta comunitaria de 2000m² con sistema de riego, invernadero y herramientas.",
        tipo="Desarrollo Sustentable",
        pais="Argentina",
        provincia="Buenos Aires",
        ciudad="La Plata",
        barrio="Villa Elvira",
        estado=EstadoProyecto.finalizado,
        created_at=datetime(2025, 7, 26, tzinfo=timezone.utc),
        fecha_en_ejecucion=datetime(2025, 8, 20, tzinfo=timezone.utc),
        fecha_finalizado=datetime(2025, 9, 10, tzinfo=timezone.utc),
    )
    projects.append(p_a)

    # =========================================================================
    # PROJECT B: FINALIZADO - Completo (3 meses atrás)
    # =========================================================================
    p_b = Proyecto(
        id=uuid4(),
        user_id=users["member2"].id,
        titulo="Comedor Escolar Rosario Norte",
        descripcion="Comedor para 200 niños con cocina industrial, comedor y depósito de alimentos.",
        tipo="Infraestructura Social",
        pais="Argentina",
        provincia="Santa Fe",
        ciudad="Rosario",
        barrio="Norte",
        estado=EstadoProyecto.finalizado,
        created_at=datetime(2025, 8, 26, tzinfo=timezone.utc),
        fecha_en_ejecucion=datetime(2025, 9, 15, tzinfo=timezone.utc),
        fecha_finalizado=datetime(2025, 10, 15, tzinfo=timezone.utc),
    )
    projects.append(p_b)

    # =========================================================================
    # PROJECT C: FINALIZADO - Reciente (1 mes atrás)
    # =========================================================================
    p_c = Proyecto(
        id=uuid4(),
        user_id=users["member1"].id,
        titulo="Biblioteca Popular San Martín",
        descripcion="Renovación de biblioteca con 5000 libros, computadoras y conexión a internet.",
        tipo="Educación",
        pais="Argentina",
        provincia="Buenos Aires",
        ciudad="Mar del Plata",
        barrio="San Martín",
        estado=EstadoProyecto.finalizado,
        created_at=datetime(2025, 10, 26, tzinfo=timezone.utc),
        fecha_en_ejecucion=datetime(2025, 10, 28, tzinfo=timezone.utc),
        fecha_finalizado=datetime(2025, 11, 15, tzinfo=timezone.utc),
    )
    projects.append(p_c)

    db.add_all(projects)
    await db.commit()

    print(f"✅ Created {len(projects)} FINALIZADO projects with realistic timelines")
    return projects


async def create_etapas_pedidos_ofertas(db: AsyncSession, projects: list, users: dict):
    """Create etapas, pedidos and ofertas for 3 FINALIZADO projects with realistic timestamps."""
    print("\n📅 Creating etapas, pedidos and ofertas...")

    all_etapas = []
    all_pedidos = []
    all_ofertas = []

    # =========================================================================
    # PROJECT A: FINALIZADO - Antiguo (4 meses atrás)
    # Huerta Orgánica - 1 etapa, 2 pedidos
    # =========================================================================
    p_a = next(p for p in projects if "Huerta Orgánica" in p.titulo)

    etapa_a_1 = Etapa(
        id=uuid4(),
        proyecto_id=p_a.id,
        nombre="Preparación y Construcción",
        descripcion="Preparación del terreno y construcción de camas de cultivo",
        fecha_inicio=date(2025, 7, 26),
        fecha_fin=date(2025, 8, 31),
        estado=EstadoEtapa.completada,
        created_at=datetime(2025, 7, 26, tzinfo=timezone.utc),
        fecha_en_ejecucion=datetime(2025, 7, 28, tzinfo=timezone.utc),
        fecha_financiada=datetime(2025, 8, 5, tzinfo=timezone.utc),
    )

    ped_a_1_1 = Pedido(
        id=uuid4(),
        etapa_id=etapa_a_1.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="Madera, tierra y abono de calidad",
        estado=EstadoPedido.COMPLETADO,
        cantidad=3000,
        unidad="kg",
        created_at=datetime(2025, 7, 27, tzinfo=timezone.utc),
        fecha_comprometido=datetime(2025, 7, 29, tzinfo=timezone.utc),
        fecha_completado=datetime(2025, 8, 3, tzinfo=timezone.utc),
    )

    ped_a_1_2 = Pedido(
        id=uuid4(),
        etapa_id=etapa_a_1.id,
        tipo=TipoPedido.MANO_OBRA,
        descripcion="Operarios para construcción",
        estado=EstadoPedido.COMPLETADO,
        cantidad=2,
        unidad="trabajadores",
        created_at=datetime(2025, 7, 27, tzinfo=timezone.utc),
        fecha_comprometido=datetime(2025, 7, 30, tzinfo=timezone.utc),
        fecha_completado=datetime(2025, 8, 4, tzinfo=timezone.utc),
    )

    all_etapas.extend([etapa_a_1])
    all_pedidos.extend([ped_a_1_1, ped_a_1_2])

    ofertas_a = [
        Oferta(
            id=uuid4(),
            pedido_id=ped_a_1_1.id,
            user_id=users["member2"].id,
            estado=EstadoOferta.aceptada,
            descripcion="Materiales de huerta de calidad premium",
        ),
        Oferta(
            id=uuid4(),
            pedido_id=ped_a_1_2.id,
            user_id=users["member1"].id,
            estado=EstadoOferta.aceptada,
            descripcion="Equipo de 2 operarios especializados",
        ),
    ]
    all_ofertas.extend(ofertas_a)

    # =========================================================================
    # PROJECT B: FINALIZADO - Completo (3 meses atrás)
    # Comedor Escolar - 2 etapas, 4 pedidos
    # =========================================================================
    p_b = next(p for p in projects if "Comedor Escolar" in p.titulo)

    etapa_b_1 = Etapa(
        id=uuid4(),
        proyecto_id=p_b.id,
        nombre="Infraestructura Base",
        descripcion="Preparación del terreno y cimientos",
        fecha_inicio=date(2025, 8, 26),
        fecha_fin=date(2025, 9, 30),
        estado=EstadoEtapa.completada,
        created_at=datetime(2025, 8, 26, tzinfo=timezone.utc),
        fecha_en_ejecucion=datetime(2025, 8, 28, tzinfo=timezone.utc),
        fecha_financiada=datetime(2025, 9, 5, tzinfo=timezone.utc),
    )

    ped_b_1_1 = Pedido(
        id=uuid4(),
        etapa_id=etapa_b_1.id,
        tipo=TipoPedido.ECONOMICO,
        descripcion="Materiales de cimentación",
        estado=EstadoPedido.COMPLETADO,
        monto=150000.0,
        moneda="ARS",
        created_at=datetime(2025, 8, 27, tzinfo=timezone.utc),
        fecha_comprometido=datetime(2025, 8, 29, tzinfo=timezone.utc),
        fecha_completado=datetime(2025, 9, 3, tzinfo=timezone.utc),
    )

    ped_b_1_2 = Pedido(
        id=uuid4(),
        etapa_id=etapa_b_1.id,
        tipo=TipoPedido.MANO_OBRA,
        descripcion="Obreros especializados",
        estado=EstadoPedido.COMPLETADO,
        cantidad=4,
        unidad="trabajadores",
        created_at=datetime(2025, 8, 27, tzinfo=timezone.utc),
        fecha_comprometido=datetime(2025, 8, 30, tzinfo=timezone.utc),
        fecha_completado=datetime(2025, 9, 4, tzinfo=timezone.utc),
    )

    etapa_b_2 = Etapa(
        id=uuid4(),
        proyecto_id=p_b.id,
        nombre="Construcción y Equipamiento",
        descripcion="Construcción del comedor e instalación de equipos",
        fecha_inicio=date(2025, 10, 1),
        fecha_fin=date(2025, 10, 30),
        estado=EstadoEtapa.completada,
        created_at=datetime(2025, 9, 1, tzinfo=timezone.utc),
        fecha_en_ejecucion=datetime(2025, 10, 1, tzinfo=timezone.utc),
        fecha_financiada=datetime(2025, 10, 8, tzinfo=timezone.utc),
    )

    ped_b_2_1 = Pedido(
        id=uuid4(),
        etapa_id=etapa_b_2.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="Materiales de construcción",
        estado=EstadoPedido.COMPLETADO,
        cantidad=5000,
        unidad="kg",
        created_at=datetime(2025, 9, 2, tzinfo=timezone.utc),
        fecha_comprometido=datetime(2025, 9, 4, tzinfo=timezone.utc),
        fecha_completado=datetime(2025, 10, 3, tzinfo=timezone.utc),
    )

    ped_b_2_2 = Pedido(
        id=uuid4(),
        etapa_id=etapa_b_2.id,
        tipo=TipoPedido.EQUIPAMIENTO,
        descripcion="Cocina industrial y equipamiento",
        estado=EstadoPedido.COMPLETADO,
        monto=200000.0,
        moneda="ARS",
        created_at=datetime(2025, 9, 2, tzinfo=timezone.utc),
        fecha_comprometido=datetime(2025, 9, 5, tzinfo=timezone.utc),
        fecha_completado=datetime(2025, 10, 5, tzinfo=timezone.utc),
    )

    all_etapas.extend([etapa_b_1, etapa_b_2])
    all_pedidos.extend([ped_b_1_1, ped_b_1_2, ped_b_2_1, ped_b_2_2])

    ofertas_b = [
        Oferta(
            id=uuid4(),
            pedido_id=ped_b_1_1.id,
            user_id=users["member1"].id,
            monto_ofrecido=145000.0,
            estado=EstadoOferta.aceptada,
            descripcion="Materiales de cimentación de calidad",
        ),
        Oferta(
            id=uuid4(),
            pedido_id=ped_b_1_2.id,
            user_id=users["member2"].id,
            estado=EstadoOferta.aceptada,
            descripcion="Equipo de obreros experimentados",
        ),
        Oferta(
            id=uuid4(),
            pedido_id=ped_b_2_1.id,
            user_id=users["member1"].id,
            estado=EstadoOferta.aceptada,
            descripcion="Materiales de construcción certificados",
        ),
        Oferta(
            id=uuid4(),
            pedido_id=ped_b_2_2.id,
            user_id=users["member2"].id,
            monto_ofrecido=195000.0,
            estado=EstadoOferta.aceptada,
            descripcion="Cocina industrial con instalación",
        ),
    ]
    all_ofertas.extend(ofertas_b)

    # =========================================================================
    # PROJECT C: FINALIZADO - Reciente (1 mes atrás)
    # Biblioteca Popular - 2 etapas, 3 pedidos
    # =========================================================================
    p_c = next(p for p in projects if "Biblioteca" in p.titulo)

    etapa_c_1 = Etapa(
        id=uuid4(),
        proyecto_id=p_c.id,
        nombre="Renovación Estructural",
        descripcion="Renovación de estructura y reparaciones",
        fecha_inicio=date(2025, 10, 26),
        fecha_fin=date(2025, 11, 5),
        estado=EstadoEtapa.completada,
        created_at=datetime(2025, 10, 26, tzinfo=timezone.utc),
        fecha_en_ejecucion=datetime(2025, 10, 27, tzinfo=timezone.utc),
        fecha_financiada=datetime(2025, 10, 30, tzinfo=timezone.utc),
    )

    ped_c_1_1 = Pedido(
        id=uuid4(),
        etapa_id=etapa_c_1.id,
        tipo=TipoPedido.ECONOMICO,
        descripcion="Reparaciones estructurales",
        estado=EstadoPedido.COMPLETADO,
        monto=100000.0,
        moneda="ARS",
        created_at=datetime(2025, 10, 27, tzinfo=timezone.utc),
        fecha_comprometido=datetime(2025, 10, 28, tzinfo=timezone.utc),
        fecha_completado=datetime(2025, 11, 1, tzinfo=timezone.utc),
    )

    etapa_c_2 = Etapa(
        id=uuid4(),
        proyecto_id=p_c.id,
        nombre="Equipamiento y Libros",
        descripcion="Instalación de computadoras y adquisición de libros",
        fecha_inicio=date(2025, 11, 6),
        fecha_fin=date(2025, 11, 15),
        estado=EstadoEtapa.completada,
        created_at=datetime(2025, 10, 26, tzinfo=timezone.utc),
        fecha_en_ejecucion=datetime(2025, 11, 6, tzinfo=timezone.utc),
        fecha_financiada=datetime(2025, 11, 10, tzinfo=timezone.utc),
    )

    ped_c_2_1 = Pedido(
        id=uuid4(),
        etapa_id=etapa_c_2.id,
        tipo=TipoPedido.EQUIPAMIENTO,
        descripcion="Computadoras e instalación",
        estado=EstadoPedido.COMPLETADO,
        cantidad=15,
        unidad="computadoras",
        created_at=datetime(2025, 10, 28, tzinfo=timezone.utc),
        fecha_comprometido=datetime(2025, 10, 30, tzinfo=timezone.utc),
        fecha_completado=datetime(2025, 11, 8, tzinfo=timezone.utc),
    )

    ped_c_2_2 = Pedido(
        id=uuid4(),
        etapa_id=etapa_c_2.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="4500 libros variados",
        estado=EstadoPedido.COMPLETADO,
        cantidad=4500,
        unidad="libros",
        created_at=datetime(2025, 10, 28, tzinfo=timezone.utc),
        fecha_comprometido=datetime(2025, 10, 31, tzinfo=timezone.utc),
        fecha_completado=datetime(2025, 11, 12, tzinfo=timezone.utc),
    )

    all_etapas.extend([etapa_c_1, etapa_c_2])
    all_pedidos.extend([ped_c_1_1, ped_c_2_1, ped_c_2_2])

    ofertas_c = [
        Oferta(
            id=uuid4(),
            pedido_id=ped_c_1_1.id,
            user_id=users["member2"].id,
            monto_ofrecido=98000.0,
            estado=EstadoOferta.aceptada,
            descripcion="Reparaciones de calidad",
        ),
        Oferta(
            id=uuid4(),
            pedido_id=ped_c_2_1.id,
            user_id=users["member1"].id,
            estado=EstadoOferta.aceptada,
            descripcion="Computadoras e instalación profesional",
        ),
        Oferta(
            id=uuid4(),
            pedido_id=ped_c_2_2.id,
            user_id=users["member2"].id,
            estado=EstadoOferta.aceptada,
            descripcion="Colección diversa de libros",
        ),
    ]
    all_ofertas.extend(ofertas_c)

    # Add all to database
    db.add_all(all_etapas)
    db.add_all(all_pedidos)
    db.add_all(all_ofertas)
    await db.commit()

    print(f"✅ Created {len(all_etapas)} etapas with {len(all_pedidos)} pedidos and {len(all_ofertas)} ofertas")


async def create_observaciones(db: AsyncSession, projects: list, users: dict):
    """Create RESOLVED and EXPIRED observaciones only (no pending)."""
    print("\n📝 Creating observaciones...")

    # Projects for observaciones
    p_b = next(p for p in projects if "Comedor Escolar" in p.titulo)
    p_c = next(p for p in projects if "Biblioteca" in p.titulo)

    observaciones = [
        # RESUELTA - from Project B (Comedor)
        # Created 2025-09-10, vence en 5 días (2025-09-15), resuelto en 2 días (2025-09-12)
        Observacion(
            id=uuid4(),
            proyecto_id=p_b.id,
            council_user_id=users["council1"].id,
            descripcion="Verificar que los materiales utilizados cumplan con las normas de construcción establecidas. Se solicita certificado de conformidad.",
            estado=EstadoObservacion.resuelta,
            fecha_limite=date(2025, 9, 15),
            respuesta="Certificado de conformidad recibido y aprobado. Todos los materiales cumplen con las normas vigentes.",
            created_at=datetime(2025, 9, 10, tzinfo=timezone.utc),
            fecha_resolucion=datetime(2025, 9, 12, tzinfo=timezone.utc),
        ),
        # RESUELTA - from Project B (Comedor)
        # Created 2025-09-15, vence en 5 días (2025-09-20), resuelto en 3 días (2025-09-18)
        Observacion(
            id=uuid4(),
            proyecto_id=p_b.id,
            council_user_id=users["council2"].id,
            descripcion="Documentación de avance debe ser presentada semanalmente en la plataforma.",
            estado=EstadoObservacion.resuelta,
            fecha_limite=date(2025, 9, 20),
            respuesta="Se ha establecido un sistema de reportes semanales automáticos en la plataforma.",
            created_at=datetime(2025, 9, 15, tzinfo=timezone.utc),
            fecha_resolucion=datetime(2025, 9, 18, tzinfo=timezone.utc),
        ),
        # RESUELTA - from Project C (Biblioteca)
        # Created 2025-11-06, vence en 5 días (2025-11-11), resuelto en 3 días (2025-11-09)
        Observacion(
            id=uuid4(),
            proyecto_id=p_c.id,
            council_user_id=users["council1"].id,
            descripcion="Se requiere inspección final de seguridad antes de inauguración.",
            estado=EstadoObservacion.resuelta,
            fecha_limite=date(2025, 11, 11),
            respuesta="Inspección de seguridad completada exitosamente. Todas las normas de seguridad cumplidas.",
            created_at=datetime(2025, 11, 6, tzinfo=timezone.utc),
            fecha_resolucion=datetime(2025, 11, 9, tzinfo=timezone.utc),
        ),
        # VENCIDA - from Project C (Biblioteca)
        # Created 2025-11-08, vence en 5 días (2025-11-13), pero no se resolvió (vencida)
        Observacion(
            id=uuid4(),
            proyecto_id=p_c.id,
            council_user_id=users["council2"].id,
            descripcion="Aplicar etiquetado de libros según norma de biblioteca.",
            estado=EstadoObservacion.vencida,
            fecha_limite=date(2025, 11, 13),
            created_at=datetime(2025, 11, 8, tzinfo=timezone.utc),
        ),
    ]

    db.add_all(observaciones)
    await db.commit()
    print(f"✅ Created {len(observaciones)} observaciones (all RESUELTA or VENCIDA)")


async def seed_database():
    """Main seed function."""
    print("=" * 70)
    print("🌱 SEEDING DATABASE WITH CONSISTENT FINALIZADO DATA")
    print("=" * 70)

    async with AsyncSessionLocal() as db:
        await clear_database(db)
        users = await create_users(db)
        projects = await create_projects(db, users)
        await create_etapas_pedidos_ofertas(db, projects, users)
        await create_observaciones(db, projects, users)

    print("\n" + "=" * 70)
    print("✅ DATABASE SEEDING COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print("\n📊 Summary of Created Data:")
    print("  • 5 users (1 Bonita system + 2 COUNCIL + 2 MEMBER)")
    print("  • 3 FINALIZADO projects with realistic timelines:")
    print("    - Huerta Orgánica (owner: member1, antiguo - 4 meses)")
    print("    - Comedor Escolar (owner: member2, completo - 3 meses)")
    print("    - Biblioteca Popular (owner: member1, reciente - 1 mes)")
    print("  • 5 etapas with all timestamps set")
    print("  • 9 pedidos (all COMPLETADO with fecha_comprometido & fecha_completado)")
    print("  • 9 ofertas (all aceptada, distributed between member1 & member2)")
    print("  • 4 observaciones (3 RESUELTA + 1 VENCIDA, no PENDIENTE)")
    print("\n✨ Key Features for Metrics:")
    print("  ✅ All timestamps properly set for metric calculations")
    print("  ✅ Complete pedido lifecycle (created → comprometido → completado)")
    print("  ✅ Complete etapa lifecycle with estado transitions")
    print("  ✅ Complete proyecto lifecycle with fecha_en_ejecucion & fecha_finalizado")
    print("  ✅ Both MEMBER users active as project owners and oferentes")
    print("  ✅ Metrics will show non-null values for:")
    print("     - tiempo_inicio_promedio_dias")
    print("     - tiempo_resolucion_observaciones_promedio_dias")
    print("     - tiempo_promedio_etapa_dias")
    print("     - All performance metrics properly calculated")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(seed_database())
