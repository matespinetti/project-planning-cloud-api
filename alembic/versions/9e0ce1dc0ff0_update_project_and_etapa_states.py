"""Update proyecto and etapa enums to new lifecycle states."""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9e0ce1dc0ff0"
down_revision = "c222f92ef84b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Proyecto estado enum: rename old type, create new, convert, and drop old
    # ------------------------------------------------------------------
    op.execute("ALTER TYPE estadoproyecto RENAME TO estadoproyecto_old")
    op.execute("CREATE TYPE estadoproyecto AS ENUM ('pendiente', 'en_ejecucion', 'finalizado')")

    op.alter_column("proyectos", "estado", server_default=None)

    op.alter_column(
        "proyectos",
        "estado",
        type_=sa.Text(),
        existing_type=sa.Enum(
            "en_planificacion", "en_ejecucion", "completo", name="estadoproyecto_old"
        ),
        existing_nullable=False,
        postgresql_using="estado::text",
    )

    op.execute("UPDATE proyectos SET estado = 'pendiente' WHERE estado = 'en_planificacion'")
    op.execute("UPDATE proyectos SET estado = 'finalizado' WHERE estado = 'completo'")

    op.alter_column(
        "proyectos",
        "estado",
        type_=sa.Enum("pendiente", "en_ejecucion", "finalizado", name="estadoproyecto"),
        existing_nullable=False,
        postgresql_using="estado::estadoproyecto",
    )

    op.alter_column(
        "proyectos",
        "estado",
        server_default=sa.text("'pendiente'::estadoproyecto"),
        existing_type=sa.Enum("pendiente", "en_ejecucion", "finalizado", name="estadoproyecto"),
        existing_nullable=False,
    )

    op.execute("DROP TYPE estadoproyecto_old")

    # ------------------------------------------------------------------
    # Etapa estado enum: introduce financiada/en_ejecucion states
    # ------------------------------------------------------------------
    op.execute("ALTER TYPE estadoetapa RENAME TO estadoetapa_old")
    op.execute(
        "CREATE TYPE estadoetapa AS ENUM ('pendiente', 'financiada', 'en_ejecucion', 'completada')"
    )

    op.alter_column("etapas", "estado", server_default=None)

    op.alter_column(
        "etapas",
        "estado",
        type_=sa.Text(),
        existing_type=sa.Enum("en_progreso", "completada", name="estadoetapa_old"),
        existing_nullable=False,
        postgresql_using="estado::text",
    )

    op.execute("UPDATE etapas SET estado = 'pendiente' WHERE estado = 'en_progreso'")

    op.alter_column(
        "etapas",
        "estado",
        type_=sa.Enum("pendiente", "financiada", "en_ejecucion", "completada", name="estadoetapa"),
        existing_nullable=False,
        postgresql_using="estado::estadoetapa",
    )

    op.alter_column(
        "etapas",
        "estado",
        server_default=sa.text("'pendiente'::estadoetapa"),
        existing_type=sa.Enum("pendiente", "financiada", "en_ejecucion", "completada", name="estadoetapa"),
        existing_nullable=False,
    )

    op.execute("DROP TYPE estadoetapa_old")


def downgrade() -> None:
    # Restore previous proyecto enum values
    op.execute("ALTER TYPE estadoproyecto RENAME TO estadoproyecto_new")
    op.alter_column("proyectos", "estado", server_default=None)

    op.execute(
        "CREATE TYPE estadoproyecto AS ENUM ('en_planificacion', 'en_ejecucion', 'completo')"
    )

    op.alter_column(
        "proyectos",
        "estado",
        type_=sa.Text(),
        existing_type=sa.Enum("pendiente", "en_ejecucion", "finalizado", name="estadoproyecto_new"),
        existing_nullable=False,
        postgresql_using="estado::text",
    )

    op.execute("UPDATE proyectos SET estado = 'completo' WHERE estado = 'finalizado'")
    op.execute("UPDATE proyectos SET estado = 'en_planificacion' WHERE estado = 'pendiente'")

    op.alter_column(
        "proyectos",
        "estado",
        type_=sa.Enum("en_planificacion", "en_ejecucion", "completo", name="estadoproyecto"),
        existing_nullable=False,
        postgresql_using="estado::estadoproyecto",
    )

    op.alter_column(
        "proyectos",
        "estado",
        server_default=sa.text("'en_planificacion'::estadoproyecto"),
        existing_type=sa.Enum("en_planificacion", "en_ejecucion", "completo", name="estadoproyecto"),
        existing_nullable=False,
    )

    op.execute("DROP TYPE estadoproyecto_new")

    # Restore previous etapa enum values
    op.execute("ALTER TYPE estadoetapa RENAME TO estadoetapa_new")
    op.alter_column("etapas", "estado", server_default=None)

    op.execute("CREATE TYPE estadoetapa AS ENUM ('en_progreso', 'completada')")

    op.alter_column(
        "etapas",
        "estado",
        type_=sa.Text(),
        existing_type=sa.Enum(
            "pendiente", "financiada", "en_ejecucion", "completada", name="estadoetapa_new"
        ),
        existing_nullable=False,
        postgresql_using="estado::text",
    )

    op.execute(
        "UPDATE etapas SET estado = 'en_progreso' WHERE estado IN ('pendiente', 'financiada', 'en_ejecucion')"
    )

    op.alter_column(
        "etapas",
        "estado",
        type_=sa.Enum("en_progreso", "completada", name="estadoetapa"),
        existing_nullable=False,
        postgresql_using="estado::estadoetapa",
    )

    op.alter_column(
        "etapas",
        "estado",
        server_default=sa.text("'en_progreso'::estadoetapa"),
        existing_type=sa.Enum("en_progreso", "completada", name="estadoetapa"),
        existing_nullable=False,
    )

    op.execute("DROP TYPE estadoetapa_new")
