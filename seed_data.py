"""
Seed script for populating the database with sample data for testing.

This script creates:
- 2 users (1 COUNCIL, 1 MEMBER)
- 2 projects (1 in EN_EJECUCION, 1 in EN_PLANIFICACION)
- Etapas and pedidos for projects
- Ofertas for pedidos
- Observaciones for the project in execution

Run with: uv run python seed_data.py
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.etapa import Etapa
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
    """Create sample users."""
    print("\n👥 Creating users...")

    # Council user (can create observations)
    council_user = User(
        id=uuid4(),
        email="consejo@ong.org",
        password=get_password_hash("Password123"),
        nombre="Carlos",
        apellido="Rodríguez",
        ong="Consejo Directivo Red ONGs",
        role=UserRole.COUNCIL,
    )

    # Member user (project owner/executor)
    member_user = User(
        id=uuid4(),
        email="maria@ong.org",
        password=get_password_hash("Password123"),
        nombre="María",
        apellido="González",
        ong="ONG Barrio Norte",
        role=UserRole.MEMBER,
    )

    # Oferente user
    oferente_user = User(
        id=uuid4(),
        email="juan@construcciones.com",
        password=get_password_hash("Password123"),
        nombre="Juan",
        apellido="Pérez",
        ong="Construcciones JP",
        role=UserRole.MEMBER,
    )

    db.add_all([council_user, member_user, oferente_user])
    await db.commit()

    print(f"  ✅ Council user: {council_user.email} (ID: {council_user.id})")
    print(f"  ✅ Member user: {member_user.email} (ID: {member_user.id})")
    print(f"  ✅ Oferente user: {oferente_user.email} (ID: {oferente_user.id})")

    return {
        "council": council_user,
        "member": member_user,
        "oferente": oferente_user,
    }


async def create_projects(db: AsyncSession, users: dict) -> dict:
    """Create sample projects with diverse states, types, and locations."""
    print("\n📋 Creating projects...")

    projects_list = []

    # Project 1: In execution (can receive observations)
    proyecto_ejecucion = Proyecto(
        id=uuid4(),
        user_id=users["member"].id,
        titulo="Centro Comunitario Barrio Norte",
        descripcion="Construcción de un centro comunitario para actividades educativas y recreativas. Incluye salón principal, cocina comunitaria, y área verde.",
        tipo="Infraestructura Social",
        pais="Argentina",
        provincia="Buenos Aires",
        ciudad="La Plata",
        barrio="Barrio Norte",
        estado=EstadoProyecto.EN_EJECUCION,
        bonita_case_id="CASE-2024-001",
        bonita_process_instance_id=12345,
    )
    projects_list.append(proyecto_ejecucion)

    # Project 2: In planning
    proyecto_planificacion = Proyecto(
        id=uuid4(),
        user_id=users["member"].id,
        titulo="Huerta Comunitaria Villa Elvira",
        descripcion="Creación de una huerta comunitaria orgánica para abastecer a las familias del barrio con verduras frescas y saludables.",
        tipo="Desarrollo Sustentable",
        pais="Argentina",
        provincia="Buenos Aires",
        ciudad="La Plata",
        barrio="Villa Elvira",
        estado=EstadoProyecto.EN_PLANIFICACION,
    )
    projects_list.append(proyecto_planificacion)

    # Project 3: Seeking funding
    proyecto_financiamiento = Proyecto(
        id=uuid4(),
        user_id=users["oferente"].id,
        titulo="Biblioteca Popular San Martín",
        descripcion="Renovación y ampliación de biblioteca popular con acceso a computadoras e internet para la comunidad. Incluye sala de lectura, área infantil y espacio de coworking.",
        tipo="Educación",
        pais="Argentina",
        provincia="Buenos Aires",
        ciudad="Mar del Plata",
        barrio="San Martín",
        estado=EstadoProyecto.BUSCANDO_FINANCIAMIENTO,
    )
    projects_list.append(proyecto_financiamiento)

    # Project 4: In execution (different location)
    proyecto_ejecucion2 = Proyecto(
        id=uuid4(),
        user_id=users["oferente"].id,
        titulo="Comedor Infantil Rosario Norte",
        descripcion="Construcción de comedor escolar para 200 niños con cocina equipada, comedor y depósito. Incluye instalaciones sanitarias y área de recreación.",
        tipo="Infraestructura Social",
        pais="Argentina",
        provincia="Santa Fe",
        ciudad="Rosario",
        barrio="Norte",
        estado=EstadoProyecto.EN_EJECUCION,
    )
    projects_list.append(proyecto_ejecucion2)

    # Project 5: Draft
    proyecto_borrador = Proyecto(
        id=uuid4(),
        user_id=users["member"].id,
        titulo="Taller de Carpintería Comunitaria",
        descripcion="Espacio equipado para enseñar oficios a jóvenes de la comunidad. Taller de carpintería con herramientas y maquinaria básica.",
        tipo="Capacitación Laboral",
        pais="Argentina",
        provincia="Córdoba",
        ciudad="Córdoba Capital",
        barrio="Alta Córdoba",
        estado=EstadoProyecto.BORRADOR,
    )
    projects_list.append(proyecto_borrador)

    # Project 6: Complete
    proyecto_completo = Proyecto(
        id=uuid4(),
        user_id=users["oferente"].id,
        titulo="Merendero Comunitario Quilmes",
        descripcion="Merendero para niños y adolescentes del barrio. Proyecto completado exitosamente, actualmente funciona atendiendo a 150 niños diariamente.",
        tipo="Asistencia Alimentaria",
        pais="Argentina",
        provincia="Buenos Aires",
        ciudad="Quilmes",
        barrio="La Matera",
        estado=EstadoProyecto.COMPLETO,
    )
    projects_list.append(proyecto_completo)

    # Project 7: In planning (different type and location)
    proyecto_salud = Proyecto(
        id=uuid4(),
        user_id=users["member"].id,
        titulo="Centro de Salud Barrial Mendoza",
        descripcion="Centro de atención primaria de salud con consultorio médico, odontológico y farmacia comunitaria para atender a 500 familias.",
        tipo="Salud Comunitaria",
        pais="Argentina",
        provincia="Mendoza",
        ciudad="Mendoza Capital",
        barrio="Las Heras",
        estado=EstadoProyecto.EN_PLANIFICACION,
    )
    projects_list.append(proyecto_salud)

    # Project 8: Seeking funding (education)
    proyecto_escuela = Proyecto(
        id=uuid4(),
        user_id=users["oferente"].id,
        titulo="Escuela de Oficios Tucumán",
        descripcion="Centro de formación profesional en oficios técnicos: electricidad, plomería, soldadura y refrigeración. Incluye aulas teóricas y talleres prácticos.",
        tipo="Educación",
        pais="Argentina",
        provincia="Tucumán",
        ciudad="San Miguel de Tucumán",
        barrio="Centro",
        estado=EstadoProyecto.BUSCANDO_FINANCIAMIENTO,
    )
    projects_list.append(proyecto_escuela)

    db.add_all(projects_list)
    await db.commit()

    print(f"  ✅ {len(projects_list)} projects created:")
    for p in projects_list:
        print(f"    - [{p.estado}] {p.titulo} ({p.ciudad}, {p.provincia})")

    return {
        "ejecucion": proyecto_ejecucion,
        "planificacion": proyecto_planificacion,
        "all": projects_list,
    }


async def create_etapas_and_pedidos(db: AsyncSession, projects: dict, users: dict) -> dict:
    """Create etapas, pedidos, and ofertas with realistic test data."""
    print("\n📅 Creating etapas, pedidos, and ofertas...")

    proyecto = projects["ejecucion"]

    # Etapa 1: Fundaciones
    etapa1 = Etapa(
        id=uuid4(),
        proyecto_id=proyecto.id,
        nombre="Fundaciones y Estructura Base",
        descripcion="Excavación, cimientos y estructura de hormigón armado",
        fecha_inicio=date(2024, 10, 1),
        fecha_fin=date(2024, 11, 30),
    )

    # Pedidos para etapa 1
    pedido1 = Pedido(
        id=uuid4(),
        etapa_id=etapa1.id,
        tipo=TipoPedido.ECONOMICO,
        descripcion="Presupuesto para materiales de construcción (cemento, hierro, arena)",
        estado=EstadoPedido.COMPLETADO,  # Marked as completed (has accepted oferta)
        monto=150000.0,
        moneda="ARS",
    )

    pedido2 = Pedido(
        id=uuid4(),
        etapa_id=etapa1.id,
        tipo=TipoPedido.MANO_OBRA,
        descripcion="Albañiles especializados en fundaciones",
        estado=EstadoPedido.PENDIENTE,
        cantidad=5,
        unidad="trabajadores",
    )

    pedido3 = Pedido(
        id=uuid4(),
        etapa_id=etapa1.id,
        tipo=TipoPedido.TRANSPORTE,
        descripcion="Camiones para transporte de materiales",
        estado=EstadoPedido.COMPLETADO,  # Completed
        cantidad=2,
        unidad="camiones",
    )

    # Etapa 2: Construcción
    etapa2 = Etapa(
        id=uuid4(),
        proyecto_id=proyecto.id,
        nombre="Construcción de Paredes y Techo",
        descripcion="Levantamiento de paredes, instalación de techo",
        fecha_inicio=date(2024, 12, 1),
        fecha_fin=date(2025, 2, 28),
    )

    pedido4 = Pedido(
        id=uuid4(),
        etapa_id=etapa2.id,
        tipo=TipoPedido.MATERIALES,
        descripcion="Ladrillos cerámicos para construcción",
        estado=EstadoPedido.PENDIENTE,
        cantidad=15000,
        unidad="ladrillos",
    )

    pedido5 = Pedido(
        id=uuid4(),
        etapa_id=etapa2.id,
        tipo=TipoPedido.ECONOMICO,
        descripcion="Presupuesto para instalación eléctrica",
        estado=EstadoPedido.PENDIENTE,
        monto=75000.0,
        moneda="ARS",
    )

    pedido6 = Pedido(
        id=uuid4(),
        etapa_id=etapa2.id,
        tipo=TipoPedido.EQUIPAMIENTO,
        descripcion="Herramientas de construcción especializadas",
        estado=EstadoPedido.PENDIENTE,
        cantidad=1,
        unidad="set",
    )

    db.add_all([etapa1, etapa2, pedido1, pedido2, pedido3, pedido4, pedido5, pedido6])
    await db.commit()

    print(f"  ✅ Etapa 1: {etapa1.nombre} (3 pedidos)")
    print(f"  ✅ Etapa 2: {etapa2.nombre} (3 pedidos)")

    # =========================================================================
    # CREATE OFERTAS (multiple ofertas per pedido for realistic testing)
    # =========================================================================

    ofertas = []

    # Ofertas for pedido1 (economico - COMPLETADO)
    oferta1_accepted = Oferta(
        id=uuid4(),
        pedido_id=pedido1.id,
        user_id=users["oferente"].id,
        descripcion="Puedo proveer todos los materiales de construcción especificados. Tengo experiencia en obras similares y garantizo calidad certificada.",
        monto_ofrecido=145000.0,
        estado=EstadoOferta.ACEPTADA,  # This is why pedido1 is COMPLETADO
    )
    ofertas.append(oferta1_accepted)

    oferta1_rejected = Oferta(
        id=uuid4(),
        pedido_id=pedido1.id,
        user_id=users["council"].id,
        descripcion="Ofrezco materiales de buena calidad a buen precio.",
        monto_ofrecido=155000.0,
        estado=EstadoOferta.RECHAZADA,
    )
    ofertas.append(oferta1_rejected)

    # Ofertas for pedido2 (mano obra - PENDIENTE)
    oferta2_pending1 = Oferta(
        id=uuid4(),
        pedido_id=pedido2.id,
        user_id=users["oferente"].id,
        descripcion="Cuento con equipo de 5 albañiles con 10 años de experiencia en fundaciones.",
        monto_ofrecido=None,
        estado=EstadoOferta.PENDIENTE,
    )
    ofertas.append(oferta2_pending1)

    oferta2_pending2 = Oferta(
        id=uuid4(),
        pedido_id=pedido2.id,
        user_id=users["council"].id,
        descripcion="Tengo contactos con albañiles de la zona que pueden trabajar en el proyecto.",
        monto_ofrecido=None,
        estado=EstadoOferta.PENDIENTE,
    )
    ofertas.append(oferta2_pending2)

    # Oferta for pedido3 (transporte - COMPLETADO)
    oferta3_accepted = Oferta(
        id=uuid4(),
        pedido_id=pedido3.id,
        user_id=users["oferente"].id,
        descripcion="Disponemos de 2 camiones para el transporte de materiales durante toda la obra.",
        monto_ofrecido=None,
        estado=EstadoOferta.ACEPTADA,
    )
    ofertas.append(oferta3_accepted)

    # Ofertas for pedido4 (ladrillos - PENDIENTE)
    oferta4_pending = Oferta(
        id=uuid4(),
        pedido_id=pedido4.id,
        user_id=users["oferente"].id,
        descripcion="Puedo conseguir 15,000 ladrillos de primera calidad a buen precio.",
        monto_ofrecido=None,
        estado=EstadoOferta.PENDIENTE,
    )
    ofertas.append(oferta4_pending)

    # Ofertas for pedido5 (electricidad - PENDIENTE, multiple ofertas)
    oferta5_pending1 = Oferta(
        id=uuid4(),
        pedido_id=pedido5.id,
        user_id=users["oferente"].id,
        descripcion="Presupuesto completo para instalación eléctrica con materiales incluidos.",
        monto_ofrecido=72000.0,
        estado=EstadoOferta.PENDIENTE,
    )
    ofertas.append(oferta5_pending1)

    oferta5_pending2 = Oferta(
        id=uuid4(),
        pedido_id=pedido5.id,
        user_id=users["council"].id,
        descripcion="Puedo conseguir electricistas matriculados a buen precio.",
        monto_ofrecido=78000.0,
        estado=EstadoOferta.PENDIENTE,
    )
    ofertas.append(oferta5_pending2)

    # No ofertas for pedido6 (equipamiento) - to test 0% coverage

    db.add_all(ofertas)
    await db.commit()

    print(f"  ✅ Created {len(ofertas)} ofertas:")
    print(f"    - Pedido 1 (economico): 1 aceptada, 1 rechazada")
    print(f"    - Pedido 2 (mano obra): 2 pendientes")
    print(f"    - Pedido 3 (transporte): 1 aceptada")
    print(f"    - Pedido 4 (materiales): 1 pendiente")
    print(f"    - Pedido 5 (electricidad): 2 pendientes")
    print(f"    - Pedido 6 (equipamiento): sin ofertas")

    return {
        "etapa1": etapa1,
        "etapa2": etapa2,
        "pedido1": pedido1,
        "pedido2": pedido2,
        "pedido3": pedido3,
        "pedido4": pedido4,
        "pedido5": pedido5,
        "pedido6": pedido6,
    }


async def create_observaciones(db: AsyncSession, projects: dict, users: dict):
    """Create sample observations."""
    print("\n🔍 Creating observaciones...")

    proyecto = projects["ejecucion"]
    council = users["council"]

    # Observación 1: Pendiente (fecha límite futura)
    obs1 = Observacion(
        id=uuid4(),
        proyecto_id=proyecto.id,
        council_user_id=council.id,
        descripcion="Se observa que el presupuesto para materiales de construcción no incluye costos de transporte. Según las actas de la reunión del consejo del día 20/10, es necesario contemplar este gasto adicional estimado en 15% del total de materiales.",
        estado=EstadoObservacion.PENDIENTE,
        fecha_limite=date.today() + timedelta(days=3),  # Vence en 3 días
    )

    # Observación 2: Pendiente próxima a vencer (fecha límite mañana)
    obs2 = Observacion(
        id=uuid4(),
        proyecto_id=proyecto.id,
        council_user_id=council.id,
        descripcion="El cronograma de la Etapa 2 parece muy ajustado considerando la cantidad de trabajadores disponibles. Recomendamos ampliar el plazo en 2-3 semanas para evitar retrasos y garantizar la calidad del trabajo.",
        estado=EstadoObservacion.PENDIENTE,
        fecha_limite=date.today() + timedelta(days=1),  # Vence mañana
    )

    # Observación 3: Vencida (fecha límite en el pasado)
    obs3 = Observacion(
        id=uuid4(),
        proyecto_id=proyecto.id,
        council_user_id=council.id,
        descripcion="Falta documentación sobre los permisos municipales de construcción. Es imprescindible adjuntar estos documentos antes de continuar con la siguiente etapa del proyecto.",
        estado=EstadoObservacion.PENDIENTE,  # Se marcará como vencida automáticamente
        fecha_limite=date.today() - timedelta(days=3),  # Vencida hace 3 días
    )

    # Observación 4: Resuelta
    obs4 = Observacion(
        id=uuid4(),
        proyecto_id=proyecto.id,
        council_user_id=council.id,
        descripcion="En la descripción del proyecto falta especificar las medidas de seguridad e higiene que se implementarán durante la obra. Por favor, detallar el plan de seguridad.",
        estado=EstadoObservacion.RESUELTA,
        fecha_limite=date.today() - timedelta(days=10),
        respuesta="Gracias por la observación. Hemos elaborado un plan de seguridad completo que incluye: 1) Señalización de obra, 2) Equipamiento de protección personal para todos los trabajadores, 3) Vallado perimetral, 4) Botiquín de primeros auxilios, 5) Capacitación en seguridad. El documento completo está disponible en la carpeta 'Documentación' del proyecto.",
        fecha_resolucion=datetime.now(timezone.utc) - timedelta(days=8),
    )

    # Observación 5: Resuelta (otra)
    obs5 = Observacion(
        id=uuid4(),
        proyecto_id=proyecto.id,
        council_user_id=council.id,
        descripcion="Se requiere un plan de gestión de residuos de construcción para cumplir con las normativas ambientales locales.",
        estado=EstadoObservacion.RESUELTA,
        fecha_limite=date.today() - timedelta(days=15),
        respuesta="Plan de gestión de residuos implementado. Hemos contratado a la empresa EcoResiduos para el retiro y tratamiento de escombros. Se separarán materiales reciclables (hierro, madera) y se dispondrá correctamente de residuos no reutilizables en vertederos autorizados.",
        fecha_resolucion=datetime.now(timezone.utc) - timedelta(days=13),
    )

    db.add_all([obs1, obs2, obs3, obs4, obs5])
    await db.commit()

    print(f"  ✅ Observación 1 (PENDIENTE - vence en 3 días): {obs1.descripcion[:60]}...")
    print(f"  ✅ Observación 2 (PENDIENTE - vence mañana): {obs2.descripcion[:60]}...")
    print(f"  ✅ Observación 3 (VENCIDA - hace 3 días): {obs3.descripcion[:60]}...")
    print(f"  ✅ Observación 4 (RESUELTA): {obs4.descripcion[:60]}...")
    print(f"  ✅ Observación 5 (RESUELTA): {obs5.descripcion[:60]}...")


async def seed_database():
    """Main seed function."""
    print("🌱 Starting database seed...")
    print("=" * 80)

    async with AsyncSessionLocal() as db:
        try:
            # Clear existing data
            await clear_database(db)

            # Create data
            users = await create_users(db)
            projects = await create_projects(db, users)
            await create_etapas_and_pedidos(db, projects, users)
            await create_observaciones(db, projects, users)

            print("\n" + "=" * 80)
            print("✅ Database seeded successfully!")
            print("\n📝 LOGIN CREDENTIALS:")
            print("-" * 80)
            print("COUNCIL USER (can create observations):")
            print(f"  Email:    consejo@ong.org")
            print(f"  Password: Password123")
            print(f"  Role:     COUNCIL")
            print()
            print("MEMBER USER (project owner):")
            print(f"  Email:    maria@ong.org")
            print(f"  Password: Password123")
            print(f"  Role:     MEMBER")
            print()
            print("OFERENTE USER:")
            print(f"  Email:    juan@construcciones.com")
            print(f"  Password: Password123")
            print(f"  Role:     MEMBER")
            print("-" * 80)
            print("\n📊 SUMMARY:")
            print(f"  - 3 users created")
            print(f"  - 2 projects created (1 in EN_EJECUCION, 1 in EN_PLANIFICACION)")
            print(f"  - 2 etapas created")
            print(f"  - 3 pedidos created")
            print(f"  - 1 oferta created")
            print(f"  - 5 observaciones created:")
            print(f"    • 2 pendientes (1 vence en 3 días, 1 vence mañana)")
            print(f"    • 1 vencida (se marcará automáticamente al listar)")
            print(f"    • 2 resueltas")
            print("\n🚀 Ready to test from frontend!")
            print("=" * 80)

        except Exception as e:
            print(f"\n❌ Error seeding database: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_database())
