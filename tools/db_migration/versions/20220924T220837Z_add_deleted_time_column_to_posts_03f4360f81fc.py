"""Add deleted_time column to posts

Revision ID: 03f4360f81fc
Revises: d36823f77b1f
Create Date: 2022-09-24 22:08:37.600621+00:00

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "03f4360f81fc"
down_revision = "d36823f77b1f"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE posts ADD COLUMN IF NOT EXISTS deleted_time timestamptz DEFAULT NULL;
        """
    )


def downgrade():
    op.execute(
        """
        ALTER TABLE posts DROP COLUMN IF EXISTS deleted_time;
        """
    )
