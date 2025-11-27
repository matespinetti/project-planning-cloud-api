"""Merge heads c3d4e5f6a7b8 and f9a1b2c3d4e5.

This merge resolves the diverging branches created by the project
execution timestamps migration and the oferta fecha_resolucion migration.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "merge_c3d4e5f6a7b8_f9a1b2c3d4e5"
down_revision = ("c3d4e5f6a7b8", "f9a1b2c3d4e5")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No schema changes; this migration only merges heads.
    pass


def downgrade() -> None:
    # No schema changes to undo.
    pass
