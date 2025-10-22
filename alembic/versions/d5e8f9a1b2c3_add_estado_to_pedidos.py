"""Add estado column to pedidos table

Revision ID: d5e8f9a1b2c3
Revises: c4cd300b3a8d
Create Date: 2025-10-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5e8f9a1b2c3'
down_revision = 'c4cd300b3a8d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create EstadoPedido enum type
    estado_pedido_enum = sa.Enum('PENDIENTE', 'COMPLETADO', name='estadopedido')
    estado_pedido_enum.create(op.get_bind(), checkfirst=True)

    # Add estado column to pedidos table with default PENDIENTE
    op.add_column('pedidos',
        sa.Column('estado',
                  sa.Enum('PENDIENTE', 'COMPLETADO', name='estadopedido'),
                  nullable=False,
                  server_default='PENDIENTE')
    )


def downgrade() -> None:
    # Drop estado column
    op.drop_column('pedidos', 'estado')

    # Drop enum type
    sa.Enum(name='estadopedido').drop(op.get_bind(), checkfirst=True)
