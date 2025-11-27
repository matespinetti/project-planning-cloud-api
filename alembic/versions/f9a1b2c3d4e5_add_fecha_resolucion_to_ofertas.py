"""add fecha_resolucion to ofertas

Revision ID: f9a1b2c3d4e5
Revises: e88571dbba0e
Create Date: 2025-01-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f9a1b2c3d4e5"
down_revision = "e88571dbba0e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ofertas",
        sa.Column(
            "fecha_resolucion",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("ofertas", "fecha_resolucion")
