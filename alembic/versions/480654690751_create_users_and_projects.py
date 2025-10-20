"""Add user profile fields and role enum.

Revision ID: 480654690751
Revises: 22d7d5e154ae
Create Date: 2025-10-20 15:44:19.986344

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '480654690751'
down_revision = '22d7d5e154ae'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add ONG profile information and role enum to users."""
    role_enum = sa.Enum('COUNCIL', 'MEMBER', name='userrole')
    role_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('users', sa.Column('ong', sa.String(length=255), server_default='', nullable=False))
    op.add_column('users', sa.Column('nombre', sa.String(length=255), server_default='', nullable=False))
    op.add_column('users', sa.Column('apellido', sa.String(length=255), server_default='', nullable=False))
    op.add_column(
        'users',
        sa.Column('role', role_enum, server_default='MEMBER', nullable=False),
    )

    # Remove temporary defaults after column creation
    op.alter_column('users', 'ong', server_default=None)
    op.alter_column('users', 'nombre', server_default=None)
    op.alter_column('users', 'apellido', server_default=None)
    op.alter_column('users', 'role', server_default=None)


def downgrade() -> None:
    """Remove user profile information and enum."""
    op.drop_column('users', 'role')
    op.drop_column('users', 'apellido')
    op.drop_column('users', 'nombre')
    op.drop_column('users', 'ong')

    role_enum = sa.Enum('COUNCIL', 'MEMBER', name='userrole')
    role_enum.drop(op.get_bind(), checkfirst=True)
