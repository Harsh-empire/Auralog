"""add progress updates and doubts"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251106_0002'
down_revision = '20251103_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'progress_updates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.String(length=64), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('blockers', sa.Text(), nullable=True),
        sa.Column('errors', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'doubts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.String(length=64), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('topic', sa.String(length=200), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('doubts')
    op.drop_table('progress_updates')
