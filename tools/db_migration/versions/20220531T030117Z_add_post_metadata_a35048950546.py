"""Add post metadata and Discord message id columns

Revision ID: a35048950546
Revises: ef9e7017d686
Create Date: 2022-05-31 03:01:17.890458+00:00

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "a35048950546"
down_revision = "ef9e7017d686"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE posts ADD COLUMN IF NOT EXISTS metadata jsonb;
        ALTER TABLE posts ADD COLUMN IF NOT EXISTS discord_message_id varchar(64);
        """
    )


def downgrade():
    op.execute(
        """
        ALTER TABLE posts DROP COLUMN IF EXISTS discord_message_id;
        ALTER TABLE posts DROP COLUMN IF EXISTS metadata;
        """
    )
