"""Add indexes for proyecto filtering and sorting

Revision ID: 26e1c5debbec
Revises: 7a84d4a6d23b
Create Date: 2025-11-11 17:50:03.943273

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '26e1c5debbec'
down_revision = '7a84d4a6d23b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create indexes for common filter and sort columns
    op.create_index('idx_proyectos_estado', 'proyectos', ['estado'])
    op.create_index('idx_proyectos_tipo', 'proyectos', ['tipo'])
    op.create_index('idx_proyectos_pais', 'proyectos', ['pais'])
    op.create_index('idx_proyectos_provincia', 'proyectos', ['provincia'])
    op.create_index('idx_proyectos_ciudad', 'proyectos', ['ciudad'])
    op.create_index('idx_proyectos_created_at', 'proyectos', ['created_at'])
    op.create_index('idx_proyectos_updated_at', 'proyectos', ['updated_at'])
    op.create_index('idx_proyectos_user_id', 'proyectos', ['user_id'])


def downgrade() -> None:
    # Drop indexes in reverse order
    op.drop_index('idx_proyectos_user_id', table_name='proyectos')
    op.drop_index('idx_proyectos_updated_at', table_name='proyectos')
    op.drop_index('idx_proyectos_created_at', table_name='proyectos')
    op.drop_index('idx_proyectos_ciudad', table_name='proyectos')
    op.drop_index('idx_proyectos_provincia', table_name='proyectos')
    op.drop_index('idx_proyectos_pais', table_name='proyectos')
    op.drop_index('idx_proyectos_tipo', table_name='proyectos')
    op.drop_index('idx_proyectos_estado', table_name='proyectos')
