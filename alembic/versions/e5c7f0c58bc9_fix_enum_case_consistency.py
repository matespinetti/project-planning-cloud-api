"""fix_enum_case_consistency

Revision ID: e5c7f0c58bc9
Revises: 9e0ce1dc0ff0
Create Date: 2025-11-13 19:12:55.835267

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5c7f0c58bc9'
down_revision = '9e0ce1dc0ff0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Fix enum case consistency for EstadoProyecto and EstadoEtapa.

    The Python enums use lowercase attribute names (pendiente, en_ejecucion, finalizado)
    but the database already has lowercase values, so no database changes needed.

    This migration is a no-op because the database enum values are already correct.
    The fix was only needed in the Python code (enum attribute names).
    """
    pass


def downgrade() -> None:
    """No changes needed in database."""
    pass
