"""add projects and ai tables

Revision ID: 20251107_0003
Revises: 20251106_0002
Create Date: 2025-11-07 00:03:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251107_0003'
down_revision = '20251106_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_table(
		'projects',
		sa.Column('id', sa.String(length=36), nullable=False),
		sa.Column('created_at', sa.String(length=64), nullable=False),
		sa.Column('updated_at', sa.String(length=64), nullable=False),
		sa.Column('owner', sa.String(length=120), nullable=False),
		sa.Column('title', sa.String(length=200), nullable=False),
		sa.Column('summary', sa.String(length=280), nullable=True),
		sa.Column('description', sa.Text(), nullable=False),
		sa.Column('repo_url', sa.String(length=400), nullable=True),
		sa.Column('tags', sa.Text(), nullable=True),
		sa.Column('ai_summary', sa.Text(), nullable=True),
		sa.Column('visibility', sa.String(length=32), nullable=False, server_default='public'),
		sa.Column('metadata', sa.Text(), nullable=True),
		sa.PrimaryKeyConstraint('id')
	)

	op.create_table(
		'project_snippets',
		sa.Column('id', sa.Integer(), nullable=False),
		sa.Column('project_id', sa.String(length=36), nullable=False),
		sa.Column('language', sa.String(length=64), nullable=True),
		sa.Column('title', sa.String(length=200), nullable=True),
		sa.Column('code', sa.Text(), nullable=False),
		sa.Column('notes', sa.Text(), nullable=True),
		sa.Column('created_at', sa.String(length=64), nullable=False),
		sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
		sa.PrimaryKeyConstraint('id')
	)

	op.create_table(
		'doubt_responses',
		sa.Column('id', sa.Integer(), nullable=False),
		sa.Column('doubt_id', sa.Integer(), nullable=False),
		sa.Column('created_at', sa.String(length=64), nullable=False),
		sa.Column('responder', sa.String(length=120), nullable=False),
		sa.Column('message', sa.Text(), nullable=False),
	sa.Column('is_ai', sa.Boolean(), nullable=False, server_default=sa.text('0')),
		sa.ForeignKeyConstraint(['doubt_id'], ['doubts.id'], ondelete='CASCADE'),
		sa.PrimaryKeyConstraint('id')
	)


def downgrade() -> None:
	op.drop_table('doubt_responses')
	op.drop_table('project_snippets')
	op.drop_table('projects')
