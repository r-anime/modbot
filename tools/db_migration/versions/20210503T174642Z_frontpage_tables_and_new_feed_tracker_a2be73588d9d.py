"""Frontpage tables and new feed tracker

Revision ID: a2be73588d9d
Revises: 02533d88ffd0
Create Date: 2021-05-03 17:46:42.655713+00:00

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "a2be73588d9d"
down_revision = "02533d88ffd0"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
    ALTER TABLE posts ADD COLUMN IF NOT EXISTS sent_to_feed BOOLEAN NOT NULL DEFAULT false;
    
    CREATE TABLE IF NOT EXISTS snapshots (
        id serial primary key,
        created_time timestamp with time zone not null default now(),
        date date not null,
        hour int not null,
        subscribers int,
        UNIQUE (date, hour)
    );
    
    CREATE TABLE IF NOT EXISTS snapshot_frontpage (
        post_id bigint not null references posts(id),
        snapshot_id int not null references snapshots(id),
        rank int,
        score int,
        PRIMARY KEY (snapshot_id, rank)
    );
    """
    )


def downgrade():
    op.execute(
        """
    DROP TABLE IF EXISTS snapshot_frontpage;
    DROP TABLE IF EXISTS snapshots;
    ALTER TABLE posts DROP COLUMN IF EXISTS sent_to_feed;
    """
    )
