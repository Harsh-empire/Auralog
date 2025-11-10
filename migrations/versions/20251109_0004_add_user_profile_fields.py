"""add user profile fields

Revision ID: 20251109_0004
Revises: 20251107_0003
Create Date: 2025-11-09 00:04:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251109_0004'
down_revision = '20251107_0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
	with op.batch_alter_table('users') as batch:
		batch.add_column(sa.Column('avatar', sa.String(length=400), nullable=True))
		batch.add_column(sa.Column('github', sa.String(length=300), nullable=True))
		batch.add_column(sa.Column('linkedin', sa.String(length=300), nullable=True))
		batch.add_column(sa.Column('website', sa.String(length=400), nullable=True))
		batch.add_column(sa.Column('public_profile', sa.Boolean(), server_default=sa.text('1'), nullable=False))
		batch.add_column(sa.Column('email_visible', sa.Boolean(), server_default=sa.text('0'), nullable=False))
		batch.add_column(sa.Column('theme', sa.String(length=64), nullable=True))
		batch.add_column(sa.Column('code_theme', sa.String(length=64), nullable=True))
		batch.add_column(sa.Column('notifications', sa.Text(), nullable=True))
		batch.add_column(sa.Column('deleted', sa.Boolean(), server_default=sa.text('0'), nullable=False))

	op.execute("UPDATE users SET theme = 'default' WHERE theme IS NULL")
	op.execute("UPDATE users SET code_theme = 'monokai' WHERE code_theme IS NULL")
	op.execute("UPDATE users SET notifications = '{}' WHERE notifications IS NULL")


def downgrade() -> None:
	with op.batch_alter_table('users') as batch:
		batch.drop_column('deleted')
		batch.drop_column('notifications')
		batch.drop_column('code_theme')
		batch.drop_column('theme')
		batch.drop_column('email_visible')
		batch.drop_column('public_profile')
		batch.drop_column('website')
		batch.drop_column('linkedin')
		batch.drop_column('github')
		batch.drop_column('avatar')
