"""update_enum_values_to_lowercase

Revision ID: 0ec59ed902de
Revises: e5c7f0c58bc9
Create Date: 2025-11-13 19:46:31.272793

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0ec59ed902de'
down_revision = 'e5c7f0c58bc9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Update enum values from UPPERCASE to lowercase for EstadoOferta and EstadoObservacion.

    The database enum types were created with UPPERCASE values (PENDIENTE, ACEPTADA, etc.)
    but Python code now uses lowercase attribute names that map to lowercase values.

    Since we can't remove enum values and PostgreSQL requires new enum values to be
    committed before use, we'll recreate the enum types completely.
    """

    # ESTADOOFERTA: Recreate with lowercase values
    # Step 1: Rename old enum
    op.execute("ALTER TYPE estadooferta RENAME TO estadooferta_old")

    # Step 2: Create new enum with lowercase values
    op.execute("CREATE TYPE estadooferta AS ENUM ('pendiente', 'aceptada', 'rechazada')")

    # Step 3: Update column to use new enum, converting uppercase to lowercase
    op.execute("""
        ALTER TABLE ofertas
        ALTER COLUMN estado TYPE estadooferta
        USING (
            CASE estado::text
                WHEN 'PENDIENTE' THEN 'pendiente'
                WHEN 'ACEPTADA' THEN 'aceptada'
                WHEN 'RECHAZADA' THEN 'rechazada'
                ELSE estado::text
            END
        )::estadooferta
    """)

    # Step 4: Drop old enum
    op.execute("DROP TYPE estadooferta_old")

    # ESTADOOBSERVACION: Recreate with lowercase values
    # Step 1: Rename old enum
    op.execute("ALTER TYPE estadoobservacion RENAME TO estadoobservacion_old")

    # Step 2: Create new enum with lowercase values
    op.execute("CREATE TYPE estadoobservacion AS ENUM ('pendiente', 'resuelta', 'vencida')")

    # Step 3: Update column to use new enum, converting uppercase to lowercase
    op.execute("""
        ALTER TABLE observaciones
        ALTER COLUMN estado TYPE estadoobservacion
        USING (
            CASE estado::text
                WHEN 'PENDIENTE' THEN 'pendiente'
                WHEN 'RESUELTA' THEN 'resuelta'
                WHEN 'VENCIDA' THEN 'vencida'
                ELSE estado::text
            END
        )::estadoobservacion
    """)

    # Step 4: Drop old enum
    op.execute("DROP TYPE estadoobservacion_old")


def downgrade() -> None:
    """
    Revert enum values from lowercase to UPPERCASE.
    """
    # Rename current enums
    op.execute("ALTER TYPE estadooferta RENAME TO estadooferta_old")
    op.execute("ALTER TYPE estadoobservacion RENAME TO estadoobservacion_old")

    # Create old uppercase enums
    op.execute("CREATE TYPE estadooferta AS ENUM ('PENDIENTE', 'ACEPTADA', 'RECHAZADA')")
    op.execute("CREATE TYPE estadoobservacion AS ENUM ('PENDIENTE', 'RESUELTA', 'VENCIDA')")

    # Update data to uppercase
    op.execute("""
        UPDATE ofertas
        SET estado = CASE
            WHEN estado::text = 'pendiente' THEN 'PENDIENTE'
            WHEN estado::text = 'aceptada' THEN 'ACEPTADA'
            WHEN estado::text = 'rechazada' THEN 'RECHAZADA'
            ELSE estado::text
        END::text
    """)

    op.execute("""
        UPDATE observaciones
        SET estado = CASE
            WHEN estado::text = 'pendiente' THEN 'PENDIENTE'
            WHEN estado::text = 'resuelta' THEN 'RESUELTA'
            WHEN estado::text = 'vencida' THEN 'VENCIDA'
            ELSE estado::text
        END::text
    """)

    # Update columns to use old enum types
    op.execute("""
        ALTER TABLE ofertas
        ALTER COLUMN estado TYPE estadooferta
        USING estado::text::estadooferta
    """)

    op.execute("""
        ALTER TABLE observaciones
        ALTER COLUMN estado TYPE estadoobservacion
        USING estado::text::estadoobservacion
    """)

    # Drop lowercase enum types
    op.execute("DROP TYPE estadooferta_old")
    op.execute("DROP TYPE estadoobservacion_old")
