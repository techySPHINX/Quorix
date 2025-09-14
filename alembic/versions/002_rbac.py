"""add role based access control

Revision ID: 002_rbac
Revises: 001_initial
Create Date: 2024-09-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_rbac'
down_revision = '001_initial'  # Update this to match your last migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type
    user_role_enum = postgresql.ENUM('user', 'admin', 'super_admin', name='userrole')
    user_role_enum.create(op.get_bind())

    # Add new columns
    op.add_column('users', sa.Column('full_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('role', user_role_enum, nullable=False, server_default='user'))
    op.add_column('users', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
    op.add_column('users', sa.Column('last_login', sa.DateTime(timezone=True), nullable=True))

    # Update existing superusers to have super_admin role
    op.execute("UPDATE users SET role = 'super_admin' WHERE is_superuser = true")


def downgrade() -> None:
    # Remove columns
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'created_at')
    op.drop_column('users', 'role')
    op.drop_column('users', 'full_name')

    # Drop enum type
    user_role_enum = postgresql.ENUM('user', 'admin', 'super_admin', name='userrole')
    user_role_enum.drop(op.get_bind())
