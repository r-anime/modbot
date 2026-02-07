"""Add rabbitmq pending table

Revision ID: a5f2ff2c36f8
Revises: 03f4360f81fc
Create Date: 2025-12-20 02:24:58.431032+00:00

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "a5f2ff2c36f8"
down_revision = "03f4360f81fc"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE rabbitmq_pending_messages (
        id BIGSERIAL PRIMARY KEY,
        type TEXT NOT NULL,
        exchange_name TEXT NOT NULL,
        queue_name TEXT NOT NULL,
        json_body JSONB NOT NULL,
        created_time TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE UNIQUE INDEX IF NOT EXISTS
        idx_rabbitmq_pending_messages_created_time ON rabbitmq_pending_messages(created_time);
    """)


def downgrade():
    op.execute("""
    DROP TABLE IF EXISTS rabbitmq_pending_messages;
    """)
