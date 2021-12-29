"""Add traffic tables

Revision ID: ef9e7017d686
Revises: a2be73588d9d
Create Date: 2021-11-09 02:22:38.435818+00:00

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "ef9e7017d686"
down_revision = "a2be73588d9d"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
    CREATE TABLE IF NOT EXISTS traffic_monthly (
        id serial primary key,
        date date not null UNIQUE,
        unique_pageviews int,
        total_pageviews int
    );
    CREATE TABLE IF NOT EXISTS traffic_daily (
        id serial primary key,
        date date not null UNIQUE,
        unique_pageviews int,
        total_pageviews int,
        net_subscribers int
    );

    ALTER TABLE snapshots ADD COLUMN IF NOT EXISTS unique_pageviews int;
    ALTER TABLE snapshots ADD COLUMN IF NOT EXISTS total_pageviews int;
    """
    )


def downgrade():
    op.execute(
        """
    ALTER TABLE snapshots DROP COLUMN IF EXISTS total_pageviews;
    ALTER TABLE snapshots DROP COLUMN IF EXISTS unique_pageviews;

    DROP TABLE IF EXISTS traffic_daily;
    DROP TABLE IF EXISTS traffic_monthly;
    """
    )
