"""add flair_frequency_exemption table

Revision ID: 18a156c604fd
Revises: 03f4360f81fc
Create Date: 2026-07-02 05:17:13.461166+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '18a156c604fd'
down_revision = '03f4360f81fc'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE flair_frequency_exemptions (
            id BIGSERIAL PRIMARY KEY,
            post_id BIGINT UNIQUE NOT NULL REFERENCES posts(id),
            is_exempt BOOLEAN NOT NULL,
            created_time TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """)


def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS flair_frequency_exemptions;
        """)
