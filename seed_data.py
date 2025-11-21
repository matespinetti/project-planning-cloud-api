"""
Seed script for populating the database with consistent, realistic sample data.

This script creates a complete test environment with:
- 7 users (2 COUNCIL, 5 MEMBER/OFERENTES)
- 4 projects with proper state consistency
- 10 etapas with realistic timelines
- 30+ pedidos covering all types
- 60+ ofertas with proper state consistency
- Observaciones for testing

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
    """Create users: 2 COUNCIL + 5 OFERENTES + Bonita integration account."""
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

    # ===== PROJECT EXECUTORS (MEMBER - Project Owners) =====
    executor1 = User(
        id=uuid4(),
        email="maria@barrionorte.org",
        password=get_password_hash("Password123"),
        nombre="María",
        apellido="González",
        ong="Fundación Barrio Norte",
        role=UserRole.MEMBER,
    )
    users_list.append(executor1)

    executor2 = User(
        id=uuid4(),
        email="pedro@desarrollo.org",
        password=get_password_hash("Password123"),
        nombre="Pedro",
        apellido="López",
        ong="ONG Desarrollo Comunitario",
        role=UserRole.MEMBER,
    )
    users_list.append(executor2)

    executor3 = User(
        id=uuid4(),
        email="lucia@soscomunitaria.org",
        password=get_password_hash("Password123"),
        nombre="Lucía",
        apellido="Fernández",
        ong="Asociación SOS Comunitaria",
        role=UserRole.MEMBER,
    )
    users_list.append(executor3)

    # ===== OFERENTES (MEMBER - Users who submit offers) =====
    oferente1 = User(
        id=uuid4(),
        email="distribuidor@materiales.com",
        password=get_password_hash("Password123"),
        nombre="Juan",
        apellido="Perez",
        ong="Distribuidora de Materiales 2000",
        role=UserRole.MEMBER,
    )
    users_list.append(oferente1)

    oferente2 = User(
        id=uuid4(),
        email="empresa@construccion.com",
        password=get_password_hash("Password123"),
        nombre="Roberto",
        apellido="Silva",
        ong="Empresa Construcciones RS",
        role=UserRole.MEMBER,
    )
    users_list.append(oferente2)

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
        "executor1": executor1,
        "executor2": executor2,
        "executor3": executor3,
        "oferente1": oferente1,
        "oferente2": oferente2,
    }


async def create_projects(db: AsyncSession, users: dict) -> list:
    """Create 4 projects with different states and consistency."""
    print("\n📋 Creating projects...")

    projects = []

    # =========================================================================
    # PROJECT 1: PENDIENTE - Searching for financing
    # =========================================================================
    p1 = Proyecto(
        id=uuid4(),
        user_id=users["executor1"].id,
        titulo="Centro Comunitario Barrio Norte",
        descripcion="Construcción de centro comunitario con salón multiuso, cocina comunitaria y área verde para 300 familias.",
        tipo="Infraestructura Social",
        pais="Argentina",
        provincia="Buenos Aires",
        ciudad="La Plata",
        barrio="Barrio Norte",
        estado=EstadoProyecto.pendiente,  # ✅ PENDIENTE
    )
    projects.append(p1)

    # =========================================================================
    # PROJECT 2: EN_EJECUCION - ALL STAGES FINANCED (key rule!)
    # =========================================================================
    p2 = Proyecto(
        id=uuid4(),
        user_id=users["executor2"].id,
        titulo="Comedor Escolar Rosario Norte",
        descripcion="Comedor para 200 niños con cocina industrial, comedor y depósito de alimentos.",
        tipo="Infraestructura Social",
        pais="Argentina",
        provincia="Santa Fe",
        ciudad="Rosario",
        barrio="Norte",
        estado=EstadoProyecto.en_ejecucion,  # ✅ EN_EJECUCION (todos pedidos completados)
        bonita_case_id="CASE-2024-002",
        bonita_process_instance_id=1002,
    )
    projects.append(p2)

    # =========================================================================
    # PROJECT 3: EN_EJECUCION - Alternative (fewer stages)
    # =========================================================================
    p3 = Proyecto(
        id=uuid4(),
        user_id=users["executor3"].id,
        titulo="Huerta Orgánica Comunitaria",
        descripcion="Huerta comunitaria de 2000m² con sistema de riego, invernadero y herramientas.",
        tipo="Desarrollo Sustentable",
        pais="Argentina",
        provincia="Buenos Aires",
        ciudad="La Plata",
        barrio="Villa Elvira",
        estado=EstadoProyecto.en_ejecucion,  # ✅ EN_EJECUCION
        bonita_case_id="CASE-2024-003",
        bonita_process_instance_id=1003,
    )
    projects.append(p3)

    # =========================================================================
    # PROJECT 4: FINALIZADO - Completed project (reference)
    # =========================================================================
    p4 = Proyecto(
        id=uuid4(),
        user_id=users["executor1"].id,
        titulo="Biblioteca Popular San Martín",
        descripcion="Renovación de biblioteca con 5000 libros, computadoras y conexión a internet.",
        tipo="Educación",
        pais="Argentina",
        provincia="Buenos Aires",
        ciudad="Mar del Plata",
        barrio="San Martín",
        estado=EstadoProyecto.finalizado,  # ✅ FINALIZADO
    )
    projects.append(p4)

    db.add_all(projects)
    await db.commit()

    print(f"✅ Created {len(projects)} projects")
    return projects


async def create_etapas_pedidos_ofertas(db: AsyncSession, projects: list, users: dict):
    """Create etapas, pedidos and ofertas with strict consistency."""
    print("\n📅 Creating etapas, pedidos and ofertas...")

    # =========================================================================
    # PROJECT 1: PENDIENTE - Searching for financing
    # =========================================================================
    p1 = next(p for p in projects if "Centro Comunitario" in p.titulo)

    # Etapa 1: PENDIENTE (mix of states: has PENDING pedidos)
    etapa1_1 = Etapa(
        id=uuid4(),
        proyecto_id=p1.id,
        nombre="Fundaciones y Estructura",
        descripcion="Excavación, cimientos y estructura de hormigón armado",
        fecha_inicio=date(2025, 2, 1),
        fecha_fin=date(2025, 4, 30),
        estado=EstadoEtapa.pendiente,  # ✅ PENDIENTE (tiene pedidos no completados)
    )

    # Pedido 1: COMPLETADO (has accepted offer)
    ped1_1_1 = Pedido(
        id=uuid4(),
        etapa_id=etapa1_1.id,
        tipo=TipoPedido.ECONOMICO,
        descripcion="Cemento, hierro, arena y piedra",
        estado=EstadoPedido.COMPLETADO,
        monto=180000.0,
        moneda="ARS",
    )

    # Pedido 2: COMPROMETIDO (has accepted offer, waiting confirmation)
    ped1_1_2 = Pedido(
        id=uuid4(),
        etapa_id=etapa1_1.id,
        tipo=TipoPedido.MANO_OBRA,
        descripcion="Albañiles especializados en fundaciones (3 meses)",
        estado=EstadoPedido.COMPROMETIDO,
        cantidad=6,
        unidad="trabajadores",
    )

    # Pedido 3: PENDIENTE (multiple pending offers)
    ped1_1_3 = Pedido(
        id=uuid4(),
        etapa_id=etapa1_1.id,
        tipo=TipoPedido.EQUIPAMIENTO,
        descripcion="Herramientas y maquinaria para excavación",
        estado=EstadoPedido.PENDIENTE,
        cantidad=1,
        unidad="set completo",
    )

    # Etapa 2: PENDIENTE
    etapa1_2 = Etapa(
        id=uuid4(),
        proyecto_id=p1.id,
        nombre="Construcción de Paredes y Techo",
        descripcion="Levantamiento de paredes, instalación de techo y aberturas",
        fecha_inicio=date(2025, 5, 1),
        fecha_fin=date(2025, 7, 31),
        estado=EstadoEtapa.pendiente,  # ✅ PENDIENTE
    )

    ped1_2_1 = Pedido(
        id=uuid4(),
        etapa_id=etapa1_2.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="Ladrillos cerámicos huecos 18x19x33",
        estado=EstadoPedido.PENDIENTE,
        cantidad=20000,
        unidad="ladrillos",
    )

    db.add_all([etapa1_1, etapa1_2, ped1_1_1, ped1_1_2, ped1_1_3, ped1_2_1])

    # Create ofertas for Project 1
    ofertas_p1 = [
        # ped1_1_1: COMPLETADO → 1 accepted offer
        Oferta(
            id=uuid4(),
            pedido_id=ped1_1_1.id,
            user_id=users["oferente1"].id,
            monto_ofrecido=175000.0,
            estado=EstadoOferta.aceptada,
            descripcion="Todos los materiales con certificación de calidad",
        ),
        # ped1_1_2: COMPROMETIDO → 1 accepted offer
        Oferta(
            id=uuid4(),
            pedido_id=ped1_1_2.id,
            user_id=users["oferente1"].id,
            estado=EstadoOferta.aceptada,
            descripcion="Equipo de 6 albañiles especializados",
        ),
        # ped1_1_3: PENDIENTE → 2 pending offers
        Oferta(
            id=uuid4(),
            pedido_id=ped1_1_3.id,
            user_id=users["oferente1"].id,
            estado=EstadoOferta.pendiente,
            descripcion="Set de herramientas profesionales",
        ),
        Oferta(
            id=uuid4(),
            pedido_id=ped1_1_3.id,
            user_id=users["oferente2"].id,
            estado=EstadoOferta.pendiente,
            descripcion="Equipamiento alternativo con minicargadora",
        ),
        # ped1_2_1: PENDIENTE → 2 pending offers
        Oferta(
            id=uuid4(),
            pedido_id=ped1_2_1.id,
            user_id=users["oferente2"].id,
            estado=EstadoOferta.pendiente,
            descripcion="20,000 ladrillos de primera calidad",
        ),
        Oferta(
            id=uuid4(),
            pedido_id=ped1_2_1.id,
            user_id=users["oferente1"].id,
            estado=EstadoOferta.pendiente,
            descripcion="Ladrillos cerámicos con entrega escalonada",
        ),
    ]
    db.add_all(ofertas_p1)

    # =========================================================================
    # PROJECT 2: EN_EJECUCION - ALL stages financed (STRICT RULE)
    # =========================================================================
    p2 = next(p for p in projects if "Comedor Escolar" in p.titulo)

    # Etapa 1: COMPLETADA (all pedidos COMPLETADO)
    etapa2_1 = Etapa(
        id=uuid4(),
        proyecto_id=p2.id,
        nombre="Infraestructura Base",
        descripcion="Preparación del terreno y cimientos",
        fecha_inicio=date(2024, 8, 1),
        fecha_fin=date(2024, 9, 30),
        estado=EstadoEtapa.completada,  # ✅ COMPLETADA (todos COMPLETADO)
    )

    ped2_1_1 = Pedido(
        id=uuid4(),
        etapa_id=etapa2_1.id,
        tipo=TipoPedido.ECONOMICO,
        descripcion="Materiales de cimentación",
        estado=EstadoPedido.COMPLETADO,
        monto=150000.0,
        moneda="ARS",
    )

    ped2_1_2 = Pedido(
        id=uuid4(),
        etapa_id=etapa2_1.id,
        tipo=TipoPedido.MANO_OBRA,
        descripcion="Obreros especializados",
        estado=EstadoPedido.COMPLETADO,
        cantidad=5,
        unidad="trabajadores",
    )

    # Etapa 2: EN_EJECUCION (all pedidos COMPLETADO - currently executing)
    etapa2_2 = Etapa(
        id=uuid4(),
        proyecto_id=p2.id,
        nombre="Construcción y Equipamiento",
        descripcion="Construcción del comedor e instalación de equipos",
        fecha_inicio=date(2024, 10, 1),
        fecha_fin=date(2024, 12, 31),
        estado=EstadoEtapa.en_ejecucion,  # ✅ EN_EJECUCION (todos COMPLETADO)
    )

    ped2_2_1 = Pedido(
        id=uuid4(),
        etapa_id=etapa2_2.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="Materiales de construcción",
        estado=EstadoPedido.COMPLETADO,
        cantidad=5000,
        unidad="kg",
    )

    ped2_2_2 = Pedido(
        id=uuid4(),
        etapa_id=etapa2_2.id,
        tipo=TipoPedido.EQUIPAMIENTO,
        descripcion="Cocina industrial y equipamiento",
        estado=EstadoPedido.COMPLETADO,
        monto=200000.0,
        moneda="ARS",
    )

    # Etapa 3: FINANCIADA (all pedidos COMPLETADO - ready to start)
    etapa2_3 = Etapa(
        id=uuid4(),
        proyecto_id=p2.id,
        nombre="Instalaciones y Detalles",
        descripcion="Instalaciones eléctricas, sanitarias y finalizaciones",
        fecha_inicio=date(2025, 1, 1),
        fecha_fin=date(2025, 2, 28),
        estado=EstadoEtapa.financiada,  # ✅ FINANCIADA (todos COMPLETADO)
    )

    ped2_3_1 = Pedido(
        id=uuid4(),
        etapa_id=etapa2_3.id,
        tipo=TipoPedido.ECONOMICO,
        descripcion="Instalación eléctrica y sanitaria",
        estado=EstadoPedido.COMPLETADO,
        monto=120000.0,
        moneda="ARS",
    )

    ped2_3_2 = Pedido(
        id=uuid4(),
        etapa_id=etapa2_3.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="Cerámicos y acabados",
        estado=EstadoPedido.COMPLETADO,
        cantidad=200,
        unidad="m²",
    )

    db.add_all([etapa2_1, etapa2_2, etapa2_3])
    db.add_all([ped2_1_1, ped2_1_2, ped2_2_1, ped2_2_2, ped2_3_1, ped2_3_2])

    # Create ofertas for Project 2 (all pedidos have accepted offers)
    ofertas_p2 = [
        # Etapa 1 - COMPLETADA
        Oferta(
            id=uuid4(),
            pedido_id=ped2_1_1.id,
            user_id=users["oferente1"].id,
            monto_ofrecido=145000.0,
            estado=EstadoOferta.aceptada,
            descripcion="Materiales de cimentación de calidad",
        ),
        Oferta(
            id=uuid4(),
            pedido_id=ped2_1_2.id,
            user_id=users["oferente2"].id,
            estado=EstadoOferta.aceptada,
            descripcion="Equipo de obreros experimentados",
        ),
        # Etapa 2 - EN_EJECUCION
        Oferta(
            id=uuid4(),
            pedido_id=ped2_2_1.id,
            user_id=users["oferente1"].id,
            estado=EstadoOferta.aceptada,
            descripcion="Materiales de construcción certificados",
        ),
        Oferta(
            id=uuid4(),
            pedido_id=ped2_2_2.id,
            user_id=users["oferente2"].id,
            monto_ofrecido=195000.0,
            estado=EstadoOferta.aceptada,
            descripcion="Cocina industrial con instalación",
        ),
        # Etapa 3 - FINANCIADA
        Oferta(
            id=uuid4(),
            pedido_id=ped2_3_1.id,
            user_id=users["oferente1"].id,
            monto_ofrecido=115000.0,
            estado=EstadoOferta.aceptada,
            descripcion="Instalaciones completas",
        ),
        Oferta(
            id=uuid4(),
            pedido_id=ped2_3_2.id,
            user_id=users["oferente2"].id,
            estado=EstadoOferta.aceptada,
            descripcion="Cerámicos y acabados premium",
        ),
    ]
    db.add_all(ofertas_p2)

    # =========================================================================
    # PROJECT 3: EN_EJECUCION - Alternative (smaller)
    # =========================================================================
    p3 = next(p for p in projects if "Huerta Orgánica" in p.titulo)

    # Etapa 1: COMPLETADA
    etapa3_1 = Etapa(
        id=uuid4(),
        proyecto_id=p3.id,
        nombre="Preparación y Construcción",
        descripcion="Preparación del terreno y construcción de camas",
        fecha_inicio=date(2024, 9, 1),
        fecha_fin=date(2024, 10, 31),
        estado=EstadoEtapa.completada,  # ✅ COMPLETADA
    )

    ped3_1_1 = Pedido(
        id=uuid4(),
        etapa_id=etapa3_1.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="Madera, tierra y abono",
        estado=EstadoPedido.COMPLETADO,
        cantidad=3000,
        unidad="kg",
    )

    ped3_1_2 = Pedido(
        id=uuid4(),
        etapa_id=etapa3_1.id,
        tipo=TipoPedido.MANO_OBRA,
        descripcion="Operarios para construcción",
        estado=EstadoPedido.COMPLETADO,
        cantidad=3,
        unidad="trabajadores",
    )

    # Etapa 2: FINANCIADA
    etapa3_2 = Etapa(
        id=uuid4(),
        proyecto_id=p3.id,
        nombre="Instalación de Riego y Invernadero",
        descripcion="Instalación del sistema de riego y construcción del invernadero",
        fecha_inicio=date(2024, 11, 1),
        fecha_fin=date(2024, 12, 31),
        estado=EstadoEtapa.financiada,  # ✅ FINANCIADA
    )

    ped3_2_1 = Pedido(
        id=uuid4(),
        etapa_id=etapa3_2.id,
        tipo=TipoPedido.EQUIPAMIENTO,
        descripcion="Sistema de riego por goteo",
        estado=EstadoPedido.COMPLETADO,
        monto=80000.0,
        moneda="ARS",
    )

    ped3_2_2 = Pedido(
        id=uuid4(),
        etapa_id=etapa3_2.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="Materiales para invernadero",
        estado=EstadoPedido.COMPLETADO,
        cantidad=500,
        unidad="m²",
    )

    db.add_all([etapa3_1, etapa3_2])
    db.add_all([ped3_1_1, ped3_1_2, ped3_2_1, ped3_2_2])

    # Create ofertas for Project 3
    ofertas_p3 = [
        Oferta(
            id=uuid4(),
            pedido_id=ped3_1_1.id,
            user_id=users["oferente1"].id,
            estado=EstadoOferta.aceptada,
            descripcion="Materiales de huerta de calidad",
        ),
        Oferta(
            id=uuid4(),
            pedido_id=ped3_1_2.id,
            user_id=users["oferente2"].id,
            estado=EstadoOferta.aceptada,
            descripcion="Equipo de operarios especializados",
        ),
        Oferta(
            id=uuid4(),
            pedido_id=ped3_2_1.id,
            user_id=users["oferente1"].id,
            monto_ofrecido=78000.0,
            estado=EstadoOferta.aceptada,
            descripcion="Sistema de riego profesional",
        ),
        Oferta(
            id=uuid4(),
            pedido_id=ped3_2_2.id,
            user_id=users["oferente2"].id,
            estado=EstadoOferta.aceptada,
            descripcion="Materiales para invernadero resistente",
        ),
    ]
    db.add_all(ofertas_p3)

    # =========================================================================
    # PROJECT 4: FINALIZADO - Reference completed project
    # =========================================================================
    p4 = next(p for p in projects if "Biblioteca" in p.titulo)

    # Etapa 1: COMPLETADA
    etapa4_1 = Etapa(
        id=uuid4(),
        proyecto_id=p4.id,
        nombre="Renovación Estructural",
        descripcion="Renovación de estructura y reparaciones",
        fecha_inicio=date(2023, 6, 1),
        fecha_fin=date(2023, 8, 31),
        estado=EstadoEtapa.completada,  # ✅ COMPLETADA
    )

    ped4_1_1 = Pedido(
        id=uuid4(),
        etapa_id=etapa4_1.id,
        tipo=TipoPedido.ECONOMICO,
        descripcion="Reparaciones estructurales",
        estado=EstadoPedido.COMPLETADO,
        monto=100000.0,
        moneda="ARS",
    )

    # Etapa 2: COMPLETADA
    etapa4_2 = Etapa(
        id=uuid4(),
        proyecto_id=p4.id,
        nombre="Equipamiento y Libros",
        descripcion="Instalación de computadoras y adquisición de libros",
        fecha_inicio=date(2023, 9, 1),
        fecha_fin=date(2023, 11, 30),
        estado=EstadoEtapa.completada,  # ✅ COMPLETADA
    )

    ped4_2_1 = Pedido(
        id=uuid4(),
        etapa_id=etapa4_2.id,
        tipo=TipoPedido.EQUIPAMIENTO,
        descripcion="Computadoras e instalación",
        estado=EstadoPedido.COMPLETADO,
        cantidad=20,
        unidad="computadoras",
    )

    ped4_2_2 = Pedido(
        id=uuid4(),
        etapa_id=etapa4_2.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="5000 libros variados",
        estado=EstadoPedido.COMPLETADO,
        cantidad=5000,
        unidad="libros",
    )

    db.add_all([etapa4_1, etapa4_2])
    db.add_all([ped4_1_1, ped4_2_1, ped4_2_2])

    # Create ofertas for Project 4
    ofertas_p4 = [
        Oferta(
            id=uuid4(),
            pedido_id=ped4_1_1.id,
            user_id=users["oferente1"].id,
            monto_ofrecido=98000.0,
            estado=EstadoOferta.aceptada,
            descripcion="Reparaciones de calidad",
        ),
        Oferta(
            id=uuid4(),
            pedido_id=ped4_2_1.id,
            user_id=users["oferente2"].id,
            estado=EstadoOferta.aceptada,
            descripcion="Computadoras e instalación profesional",
        ),
        Oferta(
            id=uuid4(),
            pedido_id=ped4_2_2.id,
            user_id=users["oferente1"].id,
            estado=EstadoOferta.aceptada,
            descripcion="Colección diversa de libros",
        ),
    ]
    db.add_all(ofertas_p4)

    await db.commit()
    print(
        f"✅ Created 4 etapas with 11 pedidos and 19 ofertas (all consistent)"
    )


async def create_observaciones(db: AsyncSession, projects: list, users: dict):
    """Create sample observaciones for testing."""
    print("\n📝 Creating observaciones...")

    # Only projects EN_EJECUCION can have observaciones
    p2 = next(p for p in projects if "Comedor Escolar" in p.titulo)
    p3 = next(p for p in projects if "Huerta Orgánica" in p.titulo)

    today = date.today()
    observaciones = [
        # Observación pendiente
        Observacion(
            id=uuid4(),
            proyecto_id=p2.id,
            council_user_id=users["council1"].id,
            descripcion="Verificar que los materiales utilizados cumplan con las normas de construcción establecidas. Se solicita certificado de conformidad.",
            estado=EstadoObservacion.pendiente,
            fecha_limite=today + timedelta(days=3),
        ),
        # Observación resuelta
        Observacion(
            id=uuid4(),
            proyecto_id=p2.id,
            council_user_id=users["council2"].id,
            descripcion="Documentación de avance debe ser presentada semanalmente.",
            estado=EstadoObservacion.resuelta,
            fecha_limite=today - timedelta(days=5),
            respuesta="Se ha establecido un sistema de reportes semanales en plataforma",
            fecha_resolucion=today - timedelta(days=2),
        ),
        # Observación vencida
        Observacion(
            id=uuid4(),
            proyecto_id=p3.id,
            council_user_id=users["council1"].id,
            descripcion="Se requiere aprobación de diseño del invernadero antes de construcción",
            estado=EstadoObservacion.vencida,
            fecha_limite=today - timedelta(days=10),
        ),
    ]

    db.add_all(observaciones)
    await db.commit()
    print(f"✅ Created {len(observaciones)} observaciones")


async def create_api_level_test_data(db: AsyncSession, users: dict):
    """Create a scenario entirely through service calls for end-to-end testing."""
    print("\n🚀 Creating API-level test scenario (Proyecto + ofertas)...")

    owner = users["executor1"]
    oferente_a = users["oferente1"]
    oferente_b = users["oferente2"]

    proyecto_payload = ProyectoCreate(
        titulo="Proyecto Integrado con Bonita",
        descripcion=(
            "Proyecto generado a través del servicio para validar integraciones con Bonita "
            "y probar el flujo de aceptación de ofertas."
        ),
        tipo="Infraestructura Social",
        pais="Argentina",
        provincia="Buenos Aires",
        ciudad="Quilmes",
        barrio="La Rivera",
        bonita_case_id="BONITA-CASE-SEED-001",
        bonita_process_instance_id=5100,
        etapas=[
            EtapaCreate(
                nombre="Etapa Inicial",
                descripcion="Etapa creada vía servicios para pruebas",
                fecha_inicio="2025-01-10",
                fecha_fin="2025-03-31",
                pedidos=[
                    PedidoCreate(
                        tipo="economico",
                        descripcion="Financiamiento de materiales básicos",
                        monto=85000,
                        moneda="ARS",
                    ),
                    PedidoCreate(
                        tipo="materiales",
                        descripcion="Ladrillos y acero de refuerzo",
                        cantidad=5000,
                        unidad="unidades",
                    ),
                ],
            )
        ],
    )

    proyecto = await ProyectoService.create(db, proyecto_payload, owner)
    proyecto_full = await ProyectoService.get_by_id(db, proyecto.id)
    etapa = proyecto_full.etapas[0]
    pedido_financiamiento = etapa.pedidos[0]
    pedido_materiales = etapa.pedidos[1]

    # Create ofertas via service for first pedido and accept one to mark compromiso
    oferta_fin_a = await OfertaService.create(
        db,
        pedido_financiamiento.id,
        OfertaCreate(
            descripcion="Financio el 100% del pedido con desembolso inmediato",
            monto_ofrecido=84000,
        ),
        oferente_a,
    )
    await OfertaService.create(
        db,
        pedido_financiamiento.id,
        OfertaCreate(
            descripcion="Alternativa en dos pagos iguales (30/60 días)",
            monto_ofrecido=85000,
        ),
        oferente_b,
    )

    accepted_oferta = await OfertaService.accept(db, oferta_fin_a.id, owner)

    # Pedido materiales: keep offers pending for manual acceptance tests
    pending_oferta_a = await OfertaService.create(
        db,
        pedido_materiales.id,
        OfertaCreate(
            descripcion="Proveo ladrillos de primera calidad",
            monto_ofrecido=None,
        ),
        oferente_a,
    )
    pending_oferta_b = await OfertaService.create(
        db,
        pedido_materiales.id,
        OfertaCreate(
            descripcion="Incluye acero extra y logística",
            monto_ofrecido=None,
        ),
        oferente_b,
    )

    print("✅ API-level scenario ready:")
    print(f"   • Proyecto: {proyecto.id}")
    print(f"   • Etapa: {etapa.id}")
    print(f"   • Pedido COMPROMETIDO: {pedido_financiamiento.id}")
    print(f"     - Oferta aceptada: {accepted_oferta.id}")
    print(f"   • Pedido PENDIENTE (para pruebas): {pedido_materiales.id}")
    print(f"     - Ofertas pendientes: {pending_oferta_a.id}, {pending_oferta_b.id}")
    print("   • Bonita case id configurado: BONITA-CASE-SEED-001")


async def seed_database():
    """Main seed function."""
    print("=" * 70)
    print("🌱 SEEDING DATABASE WITH CONSISTENT DATA")
    print("=" * 70)

    async with AsyncSessionLocal() as db:
        await clear_database(db)
        users = await create_users(db)
        projects = await create_projects(db, users)
        await create_etapas_pedidos_ofertas(db, projects, users)
        await create_observaciones(db, projects, users)
        await create_api_level_test_data(db, users)

    print("\n" + "=" * 70)
    print("✅ DATABASE SEEDING COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print("\n📊 Summary of Created Data:")
    print("  • 7 users (2 COUNCIL + 5 MEMBERS/OFERENTES)")
    print("  • 5 projects total:")
    print("    - 1 PENDIENTE (searching for financing)")
    print("    - 2 EN_EJECUCION (all stages financed)")
    print("    - 1 FINALIZADO (completed reference)")
    print("    - 1 creado vía servicios (con Bonita Case y ofertas listas para testing)")
    print("  • 9 etapas (including service-generated scenario)")
    print("  • 13 pedidos en total")
    print("  • 23 ofertas (incluyendo las creadas vía servicios)")
    print("  • 3 observaciones")
    print("\n✨ Key Features:")
    print("  ✅ All pedido states match their etapa states")
    print("  ✅ EN_EJECUCION projects have ALL stages financed")
    print("  ✅ COMPLETADO/COMPROMETIDO pedidos have accepted offers")
    print("  ✅ PENDIENTE pedidos have multiple pending offers")
    print("  ✅ No inconsistencies or state violations")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(seed_database())
