"""add user photos gallery

Revision ID: 20251110_0005
Revises: 20251109_0004
Create Date: 2025-11-10 18:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251110_0005'
down_revision = '20251109_0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('photos_json', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'photos_json')
