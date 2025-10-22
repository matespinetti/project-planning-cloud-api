"""Fix comprometido enum value to uppercase

Revision ID: e88571dbba0e
Revises: 839f5ca1b315
Create Date: 2025-10-22 15:18:00.691173

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e88571dbba0e'
down_revision = '839f5ca1b315'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Add the COMPROMETIDO value in uppercase
    # Note: ALTER TYPE ... ADD VALUE cannot run inside a transaction block
    # We need to use execute with execution_options
    connection = op.get_bind()

    # Check if the value already exists
    result = connection.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'COMPROMETIDO' "
        "AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'estadopedido'))"
    ))
    value_exists = result.scalar()

    if not value_exists:
        # Add the new enum value outside of a transaction
        connection.execute(sa.text("COMMIT"))
        connection.execute(sa.text("ALTER TYPE estadopedido ADD VALUE 'COMPROMETIDO'"))
        connection.execute(sa.text("BEGIN"))

    # Step 2: Update any existing records that have 'comprometido' (lowercase) to 'COMPROMETIDO' (uppercase)
    op.execute("UPDATE pedidos SET estado = 'COMPROMETIDO' WHERE estado = 'comprometido'")

    # Note: We cannot easily remove the 'comprometido' value from the enum in PostgreSQL
    # without recreating the entire enum type. For now, both values will exist in the enum,
    # but the application will only use 'COMPROMETIDO' (uppercase).


def downgrade() -> None:
    # Revert any COMPROMETIDO values back to comprometido
    op.execute("UPDATE pedidos SET estado = 'comprometido' WHERE estado = 'COMPROMETIDO'")

    # Note: We leave the enum value as-is since removing enum values is complex in PostgreSQL
