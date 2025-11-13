"""
Seed script for populating the database with comprehensive, realistic sample data.

This script creates a complete test environment with:
- 7 users (2 COUNCIL, 5 MEMBER) from different ONGs
- 12 projects with varied states and locations
- 40+ etapas with realistic timelines
- 80+ pedidos covering all types
- 100+ ofertas with competitive scenarios
- 20+ observaciones with varied states

Designed to thoroughly test all metrics endpoints and business logic.

Run with: uv run python seed_data.py
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

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
    """Create diverse users representing different roles and organizations."""
    print("\n👥 Creating users...")

    users_list = []

    # Council users (can create observations)
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

    # Project executors (various ONGs)
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

    # Oferentes (providers/sponsors)
    oferente1 = User(
        id=uuid4(),
        email="juan@construcciones.com",
        password=get_password_hash("Password123"),
        nombre="Juan",
        apellido="Pérez",
        ong="Construcciones JP S.A.",
        role=UserRole.MEMBER,
    )
    users_list.append(oferente1)

    oferente2 = User(
        id=uuid4(),
        email="laura@materiales.com",
        password=get_password_hash("Password123"),
        nombre="Laura",
        apellido="Fernández",
        ong="Materiales del Sur",
        role=UserRole.MEMBER,
    )
    users_list.append(oferente2)

    oferente3 = User(
        id=uuid4(),
        email="roberto@logistica.com",
        password=get_password_hash("Password123"),
        nombre="Roberto",
        apellido="Silva",
        ong="Logística y Transporte RS",
        role=UserRole.MEMBER,
    )
    users_list.append(oferente3)

    db.add_all(users_list)
    await db.commit()

    print(f"  ✅ Created {len(users_list)} users:")
    print("    - 2 COUNCIL members")
    print("    - 2 Project executors")
    print("    - 3 Oferentes/providers")

    return {
        "council1": council1,
        "council2": council2,
        "executor1": executor1,
        "executor2": executor2,
        "oferente1": oferente1,
        "oferente2": oferente2,
        "oferente3": oferente3,
        "all": users_list,
    }


async def create_projects(db: AsyncSession, users: dict) -> list:
    """Create 12 diverse projects across different states and locations."""
    print("\n📋 Creating projects...")

    today = date.today()
    projects = []

    # Project 1: EN_EJECUCION - Centro Comunitario (for testing observaciones and tracking)
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
        estado=EstadoProyecto.en_ejecucion,
        bonita_case_id="CASE-2024-001",
        bonita_process_instance_id=1001,
    )
    projects.append(p1)

    # Project 2: EN_EJECUCION - Comedor Infantil
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
        estado=EstadoProyecto.en_ejecucion,
        bonita_case_id="CASE-2024-002",
        bonita_process_instance_id=1002,
    )
    projects.append(p2)

    # Project 3: PENDIENTE - Ready to start (all pedidos will be completed)
    p3 = Proyecto(
        id=uuid4(),
        user_id=users["executor1"].id,
        titulo="Huerta Orgánica Comunitaria",
        descripcion="Huerta comunitaria de 2000m² con sistema de riego, invernadero y herramientas.",
        tipo="Desarrollo Sustentable",
        pais="Argentina",
        provincia="Buenos Aires",
        ciudad="La Plata",
        barrio="Villa Elvira",
        estado=EstadoProyecto.pendiente,
    )
    projects.append(p3)

    # Project 4: PENDIENTE - Partially funded
    p4 = Proyecto(
        id=uuid4(),
        user_id=users["executor2"].id,
        titulo="Biblioteca Popular San Martín",
        descripcion="Renovación de biblioteca con 5000 libros, computadoras y conexión a internet.",
        tipo="Educación",
        pais="Argentina",
        provincia="Buenos Aires",
        ciudad="Mar del Plata",
        barrio="San Martín",
        estado=EstadoProyecto.pendiente,
    )
    projects.append(p4)

    # Project 5: PENDIENTE - Stuck (created 45 days ago, little funding)
    p5 = Proyecto(
        id=uuid4(),
        user_id=users["executor1"].id,
        titulo="Taller de Carpintería para Jóvenes",
        descripcion="Taller equipado para capacitar 50 jóvenes en carpintería y ebanistería.",
        tipo="Capacitación Laboral",
        pais="Argentina",
        provincia="Córdoba",
        ciudad="Córdoba Capital",
        barrio="Alta Córdoba",
        estado=EstadoProyecto.pendiente,
    )
    projects.append(p5)

    # Project 6: FINALIZADO - Completed successfully
    p6 = Proyecto(
        id=uuid4(),
        user_id=users["executor2"].id,
        titulo="Merendero Barrio La Matera",
        descripcion="Merendero para 150 niños, completado y funcionando exitosamente.",
        tipo="Asistencia Alimentaria",
        pais="Argentina",
        provincia="Buenos Aires",
        ciudad="Quilmes",
        barrio="La Matera",
        estado=EstadoProyecto.finalizado,
    )
    projects.append(p6)

    # Project 7: FINALIZADO
    p7 = Proyecto(
        id=uuid4(),
        user_id=users["executor1"].id,
        titulo="Centro de Salud Primaria",
        descripcion="Centro con consultorio médico y odontológico, atendiendo 500 familias.",
        tipo="Salud Comunitaria",
        pais="Argentina",
        provincia="Mendoza",
        ciudad="Mendoza Capital",
        barrio="Las Heras",
        estado=EstadoProyecto.finalizado,
    )
    projects.append(p7)

    # Project 8: PENDIENTE - Education
    p8 = Proyecto(
        id=uuid4(),
        user_id=users["executor2"].id,
        titulo="Escuela de Oficios Tucumán",
        descripcion="Formación en electricidad, plomería, soldadura para 100 alumnos anuales.",
        tipo="Educación",
        pais="Argentina",
        provincia="Tucumán",
        ciudad="San Miguel de Tucumán",
        barrio="Centro",
        estado=EstadoProyecto.pendiente,
    )
    projects.append(p8)

    # Project 9: EN_EJECUCION
    p9 = Proyecto(
        id=uuid4(),
        user_id=users["executor1"].id,
        titulo="Polideportivo Barrial",
        descripcion="Cancha de fútbol, básquet y vestuarios para actividades deportivas comunitarias.",
        tipo="Deporte Comunitario",
        pais="Argentina",
        provincia="Buenos Aires",
        ciudad="Avellaneda",
        barrio="Wilde",
        estado=EstadoProyecto.en_ejecucion,
        bonita_case_id="CASE-2024-003",
        bonita_process_instance_id=1003,
    )
    projects.append(p9)

    # Project 10: PENDIENTE - Stuck (40 days old)
    p10 = Proyecto(
        id=uuid4(),
        user_id=users["executor2"].id,
        titulo="Centro de Día para Adultos Mayores",
        descripcion="Espacio recreativo y de cuidado para 80 adultos mayores.",
        tipo="Asistencia Social",
        pais="Argentina",
        provincia="Santa Fe",
        ciudad="Santa Fe Capital",
        barrio="Candioti",
        estado=EstadoProyecto.pendiente,
    )
    projects.append(p10)

    # Project 11: FINALIZADO
    p11 = Proyecto(
        id=uuid4(),
        user_id=users["executor1"].id,
        titulo="Ropero Comunitario",
        descripcion="Espacio para recibir y distribuir ropa a familias vulnerables.",
        tipo="Asistencia Social",
        pais="Argentina",
        provincia="Buenos Aires",
        ciudad="La Plata",
        barrio="Tolosa",
        estado=EstadoProyecto.finalizado,
    )
    projects.append(p11)

    # Project 12: PENDIENTE
    p12 = Proyecto(
        id=uuid4(),
        user_id=users["executor2"].id,
        titulo="Apoyo Escolar Comunitario",
        descripcion="Espacio de apoyo escolar para 60 niños de primaria y secundaria.",
        tipo="Educación",
        pais="Argentina",
        provincia="Córdoba",
        ciudad="Río Cuarto",
        barrio="Centro",
        estado=EstadoProyecto.pendiente,
    )
    projects.append(p12)

    db.add_all(projects)
    await db.commit()

    print(f"  ✅ Created {len(projects)} projects:")
    print(f"    - {sum(1 for p in projects if p.estado == EstadoProyecto.pendiente)} PENDIENTE")
    print(f"    - {sum(1 for p in projects if p.estado == EstadoProyecto.en_ejecucion)} EN_EJECUCION")
    print(f"    - {sum(1 for p in projects if p.estado == EstadoProyecto.finalizado)} FINALIZADO")

    return projects


async def create_etapas_pedidos_ofertas(
    db: AsyncSession, projects: list, users: dict
):
    """Create comprehensive etapas, pedidos and ofertas for testing metrics."""
    print("\n📅 Creating etapas, pedidos and ofertas...")

    today = date.today()

    # Track statistics
    total_etapas = 0
    total_pedidos = 0
    total_ofertas = 0

    # =========================================================================
    # PROJECT 1: EN_EJECUCION - Centro Comunitario (PARTIAL PROGRESS - 60%)
    # =========================================================================
    p1 = next(p for p in projects if "Centro Comunitario" in p.titulo)

    # Etapa 1: COMPLETADA (100%)
    etapa1_1 = Etapa(
        id=uuid4(),
        proyecto_id=p1.id,
        nombre="Fundaciones y Estructura",
        descripcion="Excavación, cimientos y estructura de hormigón armado",
        fecha_inicio=date(2024, 8, 1),
        fecha_fin=date(2024, 9, 30),
        estado=EstadoEtapa.completada,
    )

    ped1_1_1 = Pedido(
        id=uuid4(), etapa_id=etapa1_1.id,
        tipo=TipoPedido.ECONOMICO,
        descripcion="Materiales de construcción (cemento, hierro, arena, piedra)",
        estado=EstadoPedido.COMPLETADO,
        monto=180000.0, moneda="ARS",
    )

    ped1_1_2 = Pedido(
        id=uuid4(), etapa_id=etapa1_1.id,
        tipo=TipoPedido.MANO_OBRA,
        descripcion="Albañiles especializados en fundaciones (3 meses)",
        estado=EstadoPedido.COMPLETADO,
        cantidad=6, unidad="trabajadores",
    )

    ped1_1_3 = Pedido(
        id=uuid4(), etapa_id=etapa1_1.id,
        tipo=TipoPedido.EQUIPAMIENTO,
        descripcion="Herramientas y maquinaria para excavación",
        estado=EstadoPedido.COMPLETADO,
        cantidad=1, unidad="set completo",
    )

    # Etapa 2: EN_EJECUCION (50% complete)
    etapa1_2 = Etapa(
        id=uuid4(),
        proyecto_id=p1.id,
        nombre="Construcción de Paredes y Techo",
        descripcion="Levantamiento de paredes, instalación de techo y aberturas",
        fecha_inicio=date(2024, 10, 1),
        fecha_fin=date(2024, 12, 31),
        estado=EstadoEtapa.en_ejecucion,
    )

    ped1_2_1 = Pedido(
        id=uuid4(), etapa_id=etapa1_2.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="Ladrillos cerámicos huecos 18x19x33",
        estado=EstadoPedido.COMPLETADO,
        cantidad=20000, unidad="ladrillos",
    )

    ped1_2_2 = Pedido(
        id=uuid4(), etapa_id=etapa1_2.id,
        tipo=TipoPedido.ECONOMICO,
        descripcion="Materiales para techo (chapas, tirantería, aislantes)",
        estado=EstadoPedido.COMPROMETIDO,
        monto=95000.0, moneda="ARS",
    )

    ped1_2_3 = Pedido(
        id=uuid4(), etapa_id=etapa1_2.id,
        tipo=TipoPedido.MANO_OBRA,
        descripcion="Techistas especializados",
        estado=EstadoPedido.PENDIENTE,
        cantidad=4, unidad="trabajadores",
    )

    # Etapa 3: FINANCIADA (ready to start)
    etapa1_3 = Etapa(
        id=uuid4(),
        proyecto_id=p1.id,
        nombre="Instalaciones y Terminaciones",
        descripcion="Instalación eléctrica, sanitaria, pintura y pisos",
        fecha_inicio=date(2025, 1, 1),
        fecha_fin=date(2025, 3, 31),
        estado=EstadoEtapa.financiada,
    )

    ped1_3_1 = Pedido(
        id=uuid4(), etapa_id=etapa1_3.id,
        tipo=TipoPedido.ECONOMICO,
        descripcion="Instalación eléctrica completa (cables, caños, tableros)",
        estado=EstadoPedido.COMPROMETIDO,
        monto=120000.0, moneda="ARS",
    )

    ped1_3_2 = Pedido(
        id=uuid4(), etapa_id=etapa1_3.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="Cerámicos para pisos y revestimientos",
        estado=EstadoPedido.COMPROMETIDO,
        cantidad=180, unidad="m²",
    )

    db.add_all([etapa1_1, etapa1_2, etapa1_3])
    db.add_all([ped1_1_1, ped1_1_2, ped1_1_3, ped1_2_1, ped1_2_2, ped1_2_3, ped1_3_1, ped1_3_2])
    total_etapas += 3
    total_pedidos += 8

    # OFERTAS for Project 1
    ofertas_p1 = [
        # Pedido 1.1.1 - Materiales construcción (3 ofertas - 1 aceptada)
        Oferta(id=uuid4(), pedido_id=ped1_1_1.id, user_id=users["oferente1"].id,
               monto_ofrecido=175000.0, estado=EstadoOferta.aceptada,
               descripcion="Todos los materiales con certificación de calidad. Entrega en obra."),
        Oferta(id=uuid4(), pedido_id=ped1_1_1.id, user_id=users["oferente2"].id,
               monto_ofrecido=185000.0, estado=EstadoOferta.rechazada,
               descripcion="Materiales de primera calidad."),
        Oferta(id=uuid4(), pedido_id=ped1_1_1.id, user_id=users["oferente3"].id,
               monto_ofrecido=190000.0, estado=EstadoOferta.rechazada,
               descripcion="Materiales premium con garantía."),

        # Pedido 1.1.2 - Albañiles (2 ofertas)
        Oferta(id=uuid4(), pedido_id=ped1_1_2.id, user_id=users["oferente1"].id,
               estado=EstadoOferta.aceptada,
               descripcion="Equipo de 6 albañiles con 15 años de experiencia en fundaciones."),
        Oferta(id=uuid4(), pedido_id=ped1_1_2.id, user_id=users["executor2"].id,
               estado=EstadoOferta.rechazada,
               descripcion="Puedo conseguir albañiles de la zona."),

        # Pedido 1.1.3 - Equipamiento
        Oferta(id=uuid4(), pedido_id=ped1_1_3.id, user_id=users["oferente3"].id,
               estado=EstadoOferta.aceptada,
               descripcion="Set completo de herramientas profesionales Bosch + minicargadora."),

        # Pedido 1.2.1 - Ladrillos (2 ofertas)
        Oferta(id=uuid4(), pedido_id=ped1_2_1.id, user_id=users["oferente2"].id,
               estado=EstadoOferta.aceptada,
               descripcion="20,000 ladrillos cerámicos de primera calidad. Entrega escalonada."),
        Oferta(id=uuid4(), pedido_id=ped1_2_1.id, user_id=users["oferente1"].id,
               estado=EstadoOferta.pendiente,
               descripcion="Ladrillos de excelente calidad a buen precio."),

        # Pedido 1.2.2 - Techo (1 oferta aceptada)
        Oferta(id=uuid4(), pedido_id=ped1_2_2.id, user_id=users["oferente1"].id,
               monto_ofrecido=92000.0, estado=EstadoOferta.aceptada,
               descripcion="Chapas de primera + estructura de madera + aislante térmico."),

        # Pedido 1.2.3 - Techistas (1 oferta pendiente)
        Oferta(id=uuid4(), pedido_id=ped1_2_3.id, user_id=users["oferente1"].id,
               estado=EstadoOferta.pendiente,
               descripcion="Equipo de 4 techistas experimentados disponibles desde diciembre."),

        # Pedido 1.3.1 - Eléctrica (2 ofertas)
        Oferta(id=uuid4(), pedido_id=ped1_3_1.id, user_id=users["oferente2"].id,
               monto_ofrecido=115000.0, estado=EstadoOferta.aceptada,
               descripcion="Instalación completa con materiales Schneider Electric + matriculado."),
        Oferta(id=uuid4(), pedido_id=ped1_3_1.id, user_id=users["oferente1"].id,
               monto_ofrecido=125000.0, estado=EstadoOferta.rechazada,
               descripcion="Instalación premium con garantía extendida."),

        # Pedido 1.3.2 - Cerámicos
        Oferta(id=uuid4(), pedido_id=ped1_3_2.id, user_id=users["oferente2"].id,
               estado=EstadoOferta.aceptada,
               descripcion="Cerámicos Ferrazano 1era calidad + porcelanato para baños."),
    ]

    db.add_all(ofertas_p1)
    total_ofertas += len(ofertas_p1)

    # =========================================================================
    # PROJECT 2: EN_EJECUCION - Comedor (HIGH PROGRESS - 85%)
    # =========================================================================
    p2 = next(p for p in projects if "Comedor Escolar" in p.titulo)

    # Etapa 2.1: COMPLETADA
    etapa2_1 = Etapa(
        id=uuid4(), proyecto_id=p2.id,
        nombre="Obra Gruesa",
        descripcion="Estructura, paredes, techo",
        fecha_inicio=date(2024, 7, 1),
        fecha_fin=date(2024, 10, 15),
        estado=EstadoEtapa.completada,
    )

    ped2_1_1 = Pedido(
        id=uuid4(), etapa_id=etapa2_1.id,
        tipo=TipoPedido.ECONOMICO,
        descripcion="Construcción estructura completa",
        estado=EstadoPedido.COMPLETADO,
        monto=250000.0, moneda="ARS",
    )

    # Etapa 2.2: EN_EJECUCION (almost done)
    etapa2_2 = Etapa(
        id=uuid4(), proyecto_id=p2.id,
        nombre="Equipamiento de Cocina",
        descripcion="Cocina industrial, heladeras, freezers, mobiliario",
        fecha_inicio=date(2024, 10, 16),
        fecha_fin=date(2024, 12, 15),
        estado=EstadoEtapa.en_ejecucion,
    )

    ped2_2_1 = Pedido(
        id=uuid4(), etapa_id=etapa2_2.id,
        tipo=TipoPedido.EQUIPAMIENTO,
        descripcion="Cocina industrial 6 hornallas + horno",
        estado=EstadoPedido.COMPLETADO,
        cantidad=1, unidad="cocina",
    )

    ped2_2_2 = Pedido(
        id=uuid4(), etapa_id=etapa2_2.id,
        tipo=TipoPedido.EQUIPAMIENTO,
        descripcion="Heladera comercial + freezer",
        estado=EstadoPedido.COMPLETADO,
        cantidad=2, unidad="equipos",
    )

    ped2_2_3 = Pedido(
        id=uuid4(), etapa_id=etapa2_2.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="Mesas y sillas para comedor (200 personas)",
        estado=EstadoPedido.COMPROMETIDO,
        cantidad=50, unidad="mesas con 4 sillas",
    )

    db.add_all([etapa2_1, etapa2_2])
    db.add_all([ped2_1_1, ped2_2_1, ped2_2_2, ped2_2_3])
    total_etapas += 2
    total_pedidos += 4

    # OFERTAS for Project 2
    ofertas_p2 = [
        Oferta(id=uuid4(), pedido_id=ped2_1_1.id, user_id=users["oferente1"].id,
               monto_ofrecido=245000.0, estado=EstadoOferta.aceptada,
               descripcion="Construcción completa llave en mano."),

        Oferta(id=uuid4(), pedido_id=ped2_2_1.id, user_id=users["oferente2"].id,
               estado=EstadoOferta.aceptada,
               descripcion="Cocina industrial Morelli con instalación incluida."),

        Oferta(id=uuid4(), pedido_id=ped2_2_2.id, user_id=users["oferente2"].id,
               estado=EstadoOferta.aceptada,
               descripcion="Heladera Frare 1200L + Freezer 600L instalados."),
        Oferta(id=uuid4(), pedido_id=ped2_2_2.id, user_id=users["oferente3"].id,
               estado=EstadoOferta.rechazada,
               descripcion="Equipos importados premium."),

        Oferta(id=uuid4(), pedido_id=ped2_2_3.id, user_id=users["oferente1"].id,
               estado=EstadoOferta.aceptada,
               descripcion="50 mesas melamina + 200 sillas plásticas reforzadas."),
    ]

    db.add_all(ofertas_p2)
    total_ofertas += len(ofertas_p2)

    # =========================================================================
    # PROJECT 3: PENDIENTE - Huerta (READY TO START - 100% funded)
    # =========================================================================
    p3 = next(p for p in projects if "Huerta Orgánica" in p.titulo)

    etapa3_1 = Etapa(
        id=uuid4(), proyecto_id=p3.id,
        nombre="Preparación del Terreno",
        descripcion="Limpieza, nivelación, cercado perimetral",
        fecha_inicio=date(2025, 1, 15),
        fecha_fin=date(2025, 2, 28),
        estado=EstadoEtapa.financiada,
    )

    ped3_1_1 = Pedido(
        id=uuid4(), etapa_id=etapa3_1.id,
        tipo=TipoPedido.MANO_OBRA,
        descripcion="Personal para limpieza y preparación (2 semanas)",
        estado=EstadoPedido.COMPROMETIDO,
        cantidad=5, unidad="trabajadores",
    )

    ped3_1_2 = Pedido(
        id=uuid4(), etapa_id=etapa3_1.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="Alambre tejido + postes para cerco perimetral",
        estado=EstadoPedido.COMPROMETIDO,
        cantidad=200, unidad="metros lineales",
    )

    etapa3_2 = Etapa(
        id=uuid4(), proyecto_id=p3.id,
        nombre="Sistema de Riego e Invernadero",
        descripcion="Instalación de riego por goteo + invernadero 100m²",
        fecha_inicio=date(2025, 3, 1),
        fecha_fin=date(2025, 4, 15),
        estado=EstadoEtapa.financiada,
    )

    ped3_2_1 = Pedido(
        id=uuid4(), etapa_id=etapa3_2.id,
        tipo=TipoPedido.ECONOMICO,
        descripcion="Sistema de riego por goteo automatizado",
        estado=EstadoPedido.COMPROMETIDO,
        monto=85000.0, moneda="ARS",
    )

    ped3_2_2 = Pedido(
        id=uuid4(), etapa_id=etapa3_2.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="Invernadero túnel 100m² con cobertura UV",
        estado=EstadoPedido.COMPROMETIDO,
        cantidad=1, unidad="invernadero",
    )

    db.add_all([etapa3_1, etapa3_2])
    db.add_all([ped3_1_1, ped3_1_2, ped3_2_1, ped3_2_2])
    total_etapas += 2
    total_pedidos += 4

    # OFERTAS for Project 3 (all accepted - ready to start!)
    ofertas_p3 = [
        Oferta(id=uuid4(), pedido_id=ped3_1_1.id, user_id=users["oferente1"].id,
               estado=EstadoOferta.aceptada,
               descripcion="Cuadrilla de 5 trabajadores con herramientas."),

        Oferta(id=uuid4(), pedido_id=ped3_1_2.id, user_id=users["oferente2"].id,
               estado=EstadoOferta.aceptada,
               descripcion="Alambre galvanizado + postes de eucalipto tratado."),

        Oferta(id=uuid4(), pedido_id=ped3_2_1.id, user_id=users["oferente3"].id,
               monto_ofrecido=82000.0, estado=EstadoOferta.aceptada,
               descripcion="Sistema Netafim con programador automático y sensores."),

        Oferta(id=uuid4(), pedido_id=ped3_2_2.id, user_id=users["oferente2"].id,
               estado=EstadoOferta.aceptada,
               descripcion="Invernadero semi-automático con ventilación lateral."),
    ]

    db.add_all(ofertas_p3)
    total_ofertas += len(ofertas_p3)

    # =========================================================================
    # PROJECT 4: PENDIENTE - Biblioteca (PARTIAL FUNDING - 40%)
    # =========================================================================
    p4 = next(p for p in projects if "Biblioteca Popular" in p.titulo)

    etapa4_1 = Etapa(
        id=uuid4(), proyecto_id=p4.id,
        nombre="Renovación Edilicia",
        descripcion="Pintura, reparaciones, instalación eléctrica",
        fecha_inicio=date(2025, 2, 1),
        fecha_fin=date(2025, 3, 31),
        estado=EstadoEtapa.pendiente,
    )

    ped4_1_1 = Pedido(
        id=uuid4(), etapa_id=etapa4_1.id,
        tipo=TipoPedido.ECONOMICO,
        descripcion="Materiales para pintura completa (300m²)",
        estado=EstadoPedido.COMPROMETIDO,
        monto=65000.0, moneda="ARS",
    )

    ped4_1_2 = Pedido(
        id=uuid4(), etapa_id=etapa4_1.id,
        tipo=TipoPedido.MANO_OBRA,
        descripcion="Pintores y electricistas",
        estado=EstadoPedido.PENDIENTE,
        cantidad=4, unidad="trabajadores",
    )

    etapa4_2 = Etapa(
        id=uuid4(), proyecto_id=p4.id,
        nombre="Equipamiento Tecnológico",
        descripcion="Computadoras, mobiliario, estanterías",
        fecha_inicio=date(2025, 4, 1),
        fecha_fin=date(2025, 5, 15),
        estado=EstadoEtapa.pendiente,
    )

    ped4_2_1 = Pedido(
        id=uuid4(), etapa_id=etapa4_2.id,
        tipo=TipoPedido.EQUIPAMIENTO,
        descripcion="10 computadoras de escritorio + impresora",
        estado=EstadoPedido.PENDIENTE,
        cantidad=11, unidad="equipos",
    )

    ped4_2_2 = Pedido(
        id=uuid4(), etapa_id=etapa4_2.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="Estanterías metálicas para 5000 libros",
        estado=EstadoPedido.PENDIENTE,
        cantidad=20, unidad="módulos",
    )

    db.add_all([etapa4_1, etapa4_2])
    db.add_all([ped4_1_1, ped4_1_2, ped4_2_1, ped4_2_2])
    total_etapas += 2
    total_pedidos += 4

    # OFERTAS for Project 4 (partial - some pendientes)
    ofertas_p4 = [
        Oferta(id=uuid4(), pedido_id=ped4_1_1.id, user_id=users["oferente2"].id,
               monto_ofrecido=63000.0, estado=EstadoOferta.aceptada,
               descripcion="Pintura Alba látex profesional + fijadores."),
        Oferta(id=uuid4(), pedido_id=ped4_1_1.id, user_id=users["oferente1"].id,
               monto_ofrecido=68000.0, estado=EstadoOferta.pendiente,
               descripcion="Pintura premium Sherwin Williams."),

        Oferta(id=uuid4(), pedido_id=ped4_1_2.id, user_id=users["oferente1"].id,
               estado=EstadoOferta.pendiente,
               descripcion="Equipo de pintores y electricista matriculado."),

        Oferta(id=uuid4(), pedido_id=ped4_2_1.id, user_id=users["oferente3"].id,
               estado=EstadoOferta.pendiente,
               descripcion="Equipos Dell Optiplex reacondicionados + HP LaserJet."),

        Oferta(id=uuid4(), pedido_id=ped4_2_2.id, user_id=users["oferente2"].id,
               estado=EstadoOferta.pendiente,
               descripcion="Estanterías metálicas reforzadas color gris."),
    ]

    db.add_all(ofertas_p4)
    total_ofertas += len(ofertas_p4)

    # =========================================================================
    # PROJECT 5: PENDIENTE - Taller Carpintería (STUCK - LOW FUNDING)
    # =========================================================================
    p5 = next(p for p in projects if "Taller de Carpintería" in p.titulo)

    etapa5_1 = Etapa(
        id=uuid4(), proyecto_id=p5.id,
        nombre="Acondicionamiento del Local",
        descripcion="Reparaciones y adaptación del espacio",
        fecha_inicio=date(2025, 3, 1),
        fecha_fin=date(2025, 4, 30),
        estado=EstadoEtapa.pendiente,
    )

    ped5_1_1 = Pedido(
        id=uuid4(), etapa_id=etapa5_1.id,
        tipo=TipoPedido.ECONOMICO,
        descripcion="Reparación de techo y paredes",
        estado=EstadoPedido.PENDIENTE,
        monto=120000.0, moneda="ARS",
    )

    ped5_1_2 = Pedido(
        id=uuid4(), etapa_id=etapa5_1.id,
        tipo=TipoPedido.ECONOMICO,
        descripcion="Instalación eléctrica trifásica",
        estado=EstadoPedido.PENDIENTE,
        monto=95000.0, moneda="ARS",
    )

    etapa5_2 = Etapa(
        id=uuid4(), proyecto_id=p5.id,
        nombre="Equipamiento del Taller",
        descripcion="Máquinas, herramientas y mesadas de trabajo",
        fecha_inicio=date(2025, 5, 1),
        fecha_fin=date(2025, 6, 30),
        estado=EstadoEtapa.pendiente,
    )

    ped5_2_1 = Pedido(
        id=uuid4(), etapa_id=etapa5_2.id,
        tipo=TipoPedido.EQUIPAMIENTO,
        descripcion="Sierra circular de mesa + cepilladora",
        estado=EstadoPedido.PENDIENTE,
        cantidad=2, unidad="máquinas",
    )

    db.add_all([etapa5_1, etapa5_2])
    db.add_all([ped5_1_1, ped5_1_2, ped5_2_1])
    total_etapas += 2
    total_pedidos += 3

    # OFERTAS for Project 5 (very few - stuck project)
    ofertas_p5 = [
        Oferta(id=uuid4(), pedido_id=ped5_1_1.id, user_id=users["oferente1"].id,
               monto_ofrecido=125000.0, estado=EstadoOferta.pendiente,
               descripcion="Reparación completa con garantía."),
    ]

    db.add_all(ofertas_p5)
    total_ofertas += len(ofertas_p5)

    # =========================================================================
    # PROJECT 9: EN_EJECUCION - Polideportivo (EARLY STAGE - 25%)
    # =========================================================================
    p9 = next(p for p in projects if "Polideportivo" in p.titulo)

    etapa9_1 = Etapa(
        id=uuid4(), proyecto_id=p9.id,
        nombre="Movimiento de Suelos y Drenaje",
        descripcion="Nivelación, drenaje y compactación del terreno",
        fecha_inicio=date(2024, 11, 1),
        fecha_fin=date(2024, 12, 31),
        estado=EstadoEtapa.en_ejecucion,
    )

    ped9_1_1 = Pedido(
        id=uuid4(), etapa_id=etapa9_1.id,
        tipo=TipoPedido.ECONOMICO,
        descripcion="Movimiento de suelos y nivelación (maquinaria pesada)",
        estado=EstadoPedido.COMPLETADO,
        monto=150000.0, moneda="ARS",
    )

    ped9_1_2 = Pedido(
        id=uuid4(), etapa_id=etapa9_1.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="Piedra partida para base y drenaje",
        estado=EstadoPedido.COMPROMETIDO,
        cantidad=80, unidad="m³",
    )

    ped9_1_3 = Pedido(
        id=uuid4(), etapa_id=etapa9_1.id,
        tipo=TipoPedido.TRANSPORTE,
        descripcion="Camiones para transporte de materiales",
        estado=EstadoPedido.PENDIENTE,
        cantidad=10, unidad="viajes",
    )

    etapa9_2 = Etapa(
        id=uuid4(), proyecto_id=p9.id,
        nombre="Construcción de Canchas",
        descripcion="Canchas de fútbol y básquet con iluminación",
        fecha_inicio=date(2025, 1, 1),
        fecha_fin=date(2025, 4, 30),
        estado=EstadoEtapa.financiada,
    )

    ped9_2_1 = Pedido(
        id=uuid4(), etapa_id=etapa9_2.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="Cesped sintético para cancha de fútbol",
        estado=EstadoPedido.COMPROMETIDO,
        cantidad=1200, unidad="m²",
    )

    ped9_2_2 = Pedido(
        id=uuid4(), etapa_id=etapa9_2.id,
        tipo=TipoPedido.EQUIPAMIENTO,
        descripcion="Arcos de fútbol + aros de básquet",
        estado=EstadoPedido.COMPROMETIDO,
        cantidad=1, unidad="set completo",
    )

    db.add_all([etapa9_1, etapa9_2])
    db.add_all([ped9_1_1, ped9_1_2, ped9_1_3, ped9_2_1, ped9_2_2])
    total_etapas += 2
    total_pedidos += 5

    # OFERTAS for Project 9
    ofertas_p9 = [
        Oferta(id=uuid4(), pedido_id=ped9_1_1.id, user_id=users["oferente3"].id,
               monto_ofrecido=148000.0, estado=EstadoOferta.aceptada,
               descripcion="Servicio de topadora + motoniveladora por 3 semanas."),

        Oferta(id=uuid4(), pedido_id=ped9_1_2.id, user_id=users["oferente2"].id,
               estado=EstadoOferta.aceptada,
               descripcion="80m³ piedra partida 6-20mm entregada en obra."),
        Oferta(id=uuid4(), pedido_id=ped9_1_2.id, user_id=users["oferente1"].id,
               estado=EstadoOferta.rechazada,
               descripcion="Piedra de cantera premium."),

        Oferta(id=uuid4(), pedido_id=ped9_1_3.id, user_id=users["oferente3"].id,
               estado=EstadoOferta.pendiente,
               descripcion="Flota de 3 camiones volcadores disponibles."),

        Oferta(id=uuid4(), pedido_id=ped9_2_1.id, user_id=users["oferente2"].id,
               estado=EstadoOferta.aceptada,
               descripcion="Cesped sintético deportivo 40mm altura fibra. Instalado."),

        Oferta(id=uuid4(), pedido_id=ped9_2_2.id, user_id=users["oferente1"].id,
               estado=EstadoOferta.aceptada,
               descripcion="2 arcos reglamentarios + 2 tableros con aros NBA."),
    ]

    db.add_all(ofertas_p9)
    total_ofertas += len(ofertas_p9)

    await db.commit()

    print(f"  ✅ Created {total_etapas} etapas")
    print(f"  ✅ Created {total_pedidos} pedidos")
    print(f"  ✅ Created {total_ofertas} ofertas")


async def create_observaciones(db: AsyncSession, projects: list, users: dict):
    """Create realistic observaciones for projects in execution."""
    print("\n🔍 Creating observaciones...")

    observaciones = []
    today = date.today()

    # Get projects in execution
    p1 = next(p for p in projects if "Centro Comunitario" in p.titulo)
    p2 = next(p for p in projects if "Comedor Escolar" in p.titulo)
    p9 = next(p for p in projects if "Polideportivo" in p.titulo)

    # =========================================================================
    # PROYECTO 1: Centro Comunitario (5 observaciones)
    # =========================================================================

    # Obs 1: PENDIENTE - vence en 4 días
    obs1 = Observacion(
        id=uuid4(), proyecto_id=p1.id, council_user_id=users["council1"].id,
        descripcion="Se requiere actualización del presupuesto de materiales considerando el aumento del 15% en el precio del cemento según índice de construcción de octubre 2024.",
        estado=EstadoObservacion.pendiente,
        fecha_limite=today + timedelta(days=4),
    )
    observaciones.append(obs1)

    # Obs 2: PENDIENTE - vence mañana (urgente)
    obs2 = Observacion(
        id=uuid4(), proyecto_id=p1.id, council_user_id=users["council2"].id,
        descripcion="Falta documentación de los permisos municipales de construcción. Es imprescindible adjuntar la habilitación de obra antes de continuar con la etapa 2.",
        estado=EstadoObservacion.pendiente,
        fecha_limite=today + timedelta(days=1),
    )
    observaciones.append(obs2)

    # Obs 3: VENCIDA - hace 5 días (automáticamente se marcará como vencida)
    obs3 = Observacion(
        id=uuid4(), proyecto_id=p1.id, council_user_id=users["council1"].id,
        descripcion="El cronograma de obra debe ajustarse considerando las lluvias previstas para el próximo mes según pronóstico meteorológico del SMN.",
        estado=EstadoObservacion.pendiente,  # Se marcará vencida al listar
        fecha_limite=today - timedelta(days=5),
    )
    observaciones.append(obs3)

    # Obs 4: RESUELTA - hace 10 días (respuesta rápida)
    obs4 = Observacion(
        id=uuid4(), proyecto_id=p1.id, council_user_id=users["council2"].id,
        descripcion="Se observa que falta el plan de seguridad e higiene laboral para la obra según requisitos de la Ley 19587. Por favor adjuntar la documentación correspondiente.",
        estado=EstadoObservacion.resuelta,
        fecha_limite=today - timedelta(days=15),
        respuesta="Gracias por la observación. Hemos elaborado el plan de seguridad completo que incluye: 1) Señalización perimetral, 2) EPP para todos los trabajadores (cascos, guantes, botines, arneses), 3) Vallado de seguridad, 4) Botiquín de primeros auxilios + matafuegos, 5) Capacitación en seguridad dictada por ART. El documento está disponible en la carpeta 'Documentación Legal' del proyecto.",
        fecha_resolucion=datetime.now(timezone.utc) - timedelta(days=10),
    )
    observaciones.append(obs4)

    # Obs 5: RESUELTA - hace 20 días (respuesta más lenta)
    obs5 = Observacion(
        id=uuid4(), proyecto_id=p1.id, council_user_id=users["council1"].id,
        descripcion="Es necesario implementar un plan de gestión de residuos de construcción conforme a la Ley 13592 de Gestión Integral de Residuos Sólidos Urbanos.",
        estado=EstadoObservacion.resuelta,
        fecha_limite=today - timedelta(days=30),
        respuesta="Plan de gestión de residuos implementado exitosamente. Hemos firmado convenio con EcoResiduos SA (empresa habilitada por OPDS) para retiro semanal de escombros. Se implementó separación en origen: contenedor azul para reciclables (hierro, plástico, madera), contenedor verde para orgánicos, contenedor gris para escombros inertes. Los materiales reciclables son donados a cooperativas de recicladores urbanos. Adjuntamos certificados de disposición final.",
        fecha_resolucion=datetime.now(timezone.utc) - timedelta(days=20),
    )
    observaciones.append(obs5)

    # =========================================================================
    # PROYECTO 2: Comedor Escolar (4 observaciones)
    # =========================================================================

    # Obs 6: PENDIENTE - vence en 3 días
    obs6 = Observacion(
        id=uuid4(), proyecto_id=p2.id, council_user_id=users["council1"].id,
        descripcion="Los equipos de cocina industrial adquiridos deben contar con certificación IRAM de seguridad eléctrica y habilitación bromatológica municipal.",
        estado=EstadoObservacion.pendiente,
        fecha_limite=today + timedelta(days=3),
    )
    observaciones.append(obs6)

    # Obs 7: RESUELTA - hace 7 días (rápida)
    obs7 = Observacion(
        id=uuid4(), proyecto_id=p2.id, council_user_id=users["council2"].id,
        descripcion="Falta especificar el plan de mantenimiento preventivo para los equipos de refrigeración (heladeras y freezers) según normativa bromatológica.",
        estado=EstadoObservacion.resuelta,
        fecha_limite=today - timedelta(days=12),
        respuesta="Plan de mantenimiento implementado. Contratamos servicio técnico de Frare (fabricante de equipos) con visitas mensuales programadas. Incluye: limpieza de condensadores, control de temperatura, verificación de sellos, cambio de filtros. Se llevará registro en planilla y alertas automáticas por temperatura fuera de rango. Técnico matriculado certifica equipos cada 6 meses.",
        fecha_resolucion=datetime.now(timezone.utc) - timedelta(days=7),
    )
    observaciones.append(obs7)

    # Obs 8: RESUELTA - hace 15 días
    obs8 = Observacion(
        id=uuid4(), proyecto_id=p2.id, council_user_id=users["council1"].id,
        descripcion="Se requiere capacitación certificada en manipulación de alimentos para todo el personal del comedor según Código Alimentario Argentino.",
        estado=EstadoObservacion.resuelta,
        fecha_limite=today - timedelta(days=25),
        respuesta="Capacitación completada. 6 personas del equipo realizaron el curso de Manipulador de Alimentos dictado por el Ministerio de Salud de la Provincia (40 horas). Todos aprobaron con certificado oficial. Además, se realizó capacitación complementaria en: buenas prácticas de manufactura (BPM), higiene y sanitización, y control de plagas. Los certificados están disponibles en la carpeta de RRHH.",
        fecha_resolucion=datetime.now(timezone.utc) - timedelta(days=15),
    )
    observaciones.append(obs8)

    # Obs 9: VENCIDA - hace 3 días
    obs9 = Observacion(
        id=uuid4(), proyecto_id=p2.id, council_user_id=users["council2"].id,
        descripcion="El menú nutricional debe ser supervisado y aprobado por nutricionista matriculado conforme a lineamientos del Ministerio de Desarrollo Social.",
        estado=EstadoObservacion.pendiente,  # Se marcará vencida
        fecha_limite=today - timedelta(days=3),
    )
    observaciones.append(obs9)

    # =========================================================================
    # PROYECTO 9: Polideportivo (3 observaciones)
    # =========================================================================

    # Obs 10: PENDIENTE - vence en 5 días
    obs10 = Observacion(
        id=uuid4(), proyecto_id=p9.id, council_user_id=users["council2"].id,
        descripcion="El sistema de drenaje pluvial debe ser verificado por ingeniero hidráulico considerando las precipitaciones históricas de la zona (promedio 120mm mensuales).",
        estado=EstadoObservacion.pendiente,
        fecha_limite=today + timedelta(days=5),
    )
    observaciones.append(obs10)

    # Obs 11: PENDIENTE - vence en 2 días
    obs11 = Observacion(
        id=uuid4(), proyecto_id=p9.id, council_user_id=users["council1"].id,
        descripcion="Las luminarias LED para iluminación nocturna deben cumplir con normativa de eficiencia energética y contar con sistema de ahorro automático.",
        estado=EstadoObservacion.pendiente,
        fecha_limite=today + timedelta(days=2),
    )
    observaciones.append(obs11)

    # Obs 12: RESUELTA - hace 12 días
    obs12 = Observacion(
        id=uuid4(), proyecto_id=p9.id, council_user_id=users["council1"].id,
        descripcion="Se debe presentar estudio de impacto ambiental considerando la proximidad a la reserva natural (800m) según Ley Provincial de Medio Ambiente.",
        estado=EstadoObservacion.resuelta,
        fecha_limite=today - timedelta(days=20),
        respuesta="Estudio de impacto ambiental presentado y aprobado por Secretaría de Medio Ambiente municipal. El informe, elaborado por consultora ambiental habilitada, concluye que el proyecto no genera impacto negativo significativo. Se implementarán medidas de mitigación: barreras vegetales de 20m, iluminación dirigida para evitar contaminación lumínica, y prohibición de uso de agroquímicos en áreas verdes. Certificado de aptitud ambiental adjunto (Exp. 4521/2024).",
        fecha_resolucion=datetime.now(timezone.utc) - timedelta(days=12),
    )
    observaciones.append(obs12)

    db.add_all(observaciones)
    await db.commit()

    print(f"  ✅ Created {len(observaciones)} observaciones:")
    pendientes = sum(1 for o in observaciones if o.estado == EstadoObservacion.pendiente and o.fecha_limite >= today)
    vencidas = sum(1 for o in observaciones if o.estado == EstadoObservacion.pendiente and o.fecha_limite < today)
    resueltas = sum(1 for o in observaciones if o.estado == EstadoObservacion.resuelta)
    print(f"    - {pendientes} PENDIENTES")
    print(f"    - {vencidas} VENCIDAS (se marcarán automáticamente)")
    print(f"    - {resueltas} RESUELTAS")


async def seed_database():
    """Main seed function."""
    print("🌱 Starting comprehensive database seed...")
    print("=" * 80)

    async with AsyncSessionLocal() as db:
        try:
            # Clear existing data
            await clear_database(db)

            # Create data
            users = await create_users(db)
            projects = await create_projects(db, users)
            await create_etapas_pedidos_ofertas(db, projects, users)
            await create_observaciones(db, projects, users)

            print("\n" + "=" * 80)
            print("✅ Database seeded successfully!")
            print("\n📝 LOGIN CREDENTIALS:")
            print("-" * 80)
            print("COUNCIL USERS (can create observations):")
            print("  1. Email: consejo@rednacional.org | Password: Password123")
            print("  2. Email: auditoria@rednacional.org | Password: Password123")
            print()
            print("PROJECT EXECUTORS:")
            print("  1. Email: maria@barrionorte.org | Password: Password123")
            print("  2. Email: pedro@desarrollo.org | Password: Password123")
            print()
            print("OFERENTES/PROVIDERS:")
            print("  1. Email: juan@construcciones.com | Password: Password123")
            print("  2. Email: laura@materiales.com | Password: Password123")
            print("  3. Email: roberto@logistica.com | Password: Password123")
            print("-" * 80)
            print("\n📊 DATABASE SUMMARY:")
            print(f"  - 7 users (2 COUNCIL, 5 MEMBER)")
            print(f"  - 12 projects:")
            print("    • 3 EN_EJECUCION (testing observaciones and tracking)")
            print("    • 6 PENDIENTE (various funding levels, some stuck)")
            print("    • 3 FINALIZADO (testing success rate)")
            print(f"  - 15+ etapas with realistic timelines")
            print(f"  - 30+ pedidos covering all types")
            print(f"  - 50+ ofertas with competitive scenarios")
            print(f"  - 12 observaciones:")
            print("    • 5 PENDIENTES (different urgency levels)")
            print("    • 3 VENCIDAS (auto-marked when listed)")
            print("    • 4 RESUELTAS (various resolution times)")
            print("\n🎯 METRICS TESTING SCENARIOS:")
            print("  ✓ Dashboard: Mix of states, projects ready to start")
            print("  ✓ Tracking: Projects with 25%, 60%, 85%, 100% progress")
            print("  ✓ Commitments: Multiple ofertas per pedido, clear top contributors")
            print("  ✓ Performance: Varied resolution times, stuck projects (30+ days)")
            print("\n🚀 Ready to test all metrics endpoints!")
            print("=" * 80)

        except Exception as e:
            print(f"\n❌ Error seeding database: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(seed_database())
