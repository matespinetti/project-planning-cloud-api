"""Add comprometido state to EstadoPedido enum

Revision ID: 839f5ca1b315
Revises: d5e8f9a1b2c3
Create Date: 2025-10-22 14:50:58.208245

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '839f5ca1b315'
down_revision = 'd5e8f9a1b2c3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'comprometido' value to EstadoPedido enum
    op.execute("ALTER TYPE estadopedido ADD VALUE IF NOT EXISTS 'comprometido'")


def downgrade() -> None:
    # Note: PostgreSQL does not support removing enum values directly.
    # You would need to recreate the enum type to remove the value.
    # For safety, we'll leave this as a no-op.
    pass
