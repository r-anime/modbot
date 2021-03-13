"""Create initial tables

Revision ID: 02533d88ffd0
Revises:
Create Date: 2021-03-04 04:28:47.138468+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "02533d88ffd0"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        username varchar(40) primary key,
        created_time timestamptz,
        flair text,
        flair_class text,
        moderator boolean not null default false,
        suspended boolean not null default false,
        deleted boolean not null default false,
        banned_until timestamptz
    );
    CREATE UNIQUE INDEX IF NOT EXISTS users_username_lower_key ON users (lower(username));

    CREATE TABLE IF NOT EXISTS posts (
        id bigint primary key,
        id36 varchar(15) unique not null,
        author varchar(40) references users(username),
        title text not null,
        flair_id uuid,
        flair_text text,
        created_time timestamptz not null,
        edited timestamptz,
        score integer not null default 0,
        url text,
        body text,
        distinguished boolean not null default false,
        deleted boolean not null default false,
        removed boolean not null default false
    );
    CREATE INDEX IF NOT EXISTS posts_author_lower_key ON posts (lower(author));

    CREATE TABLE IF NOT EXISTS comments (
        id bigint primary key,
        id36 varchar(15) unique not null,
        author varchar(40) references users(username),
        post_id bigint not null references posts(id),
        parent_id bigint references comments(id),
        created_time timestamptz not null,
        edited timestamptz,
        score integer not null default 0,
        body text,
        distinguished boolean not null default false,
        deleted boolean not null default false,
        removed boolean not null default false
    );
    CREATE INDEX IF NOT EXISTS comments_author_lower_key ON comments (lower(author));

    CREATE TABLE IF NOT EXISTS mod_actions (
        id uuid primary key,
        action text not null,
        mod varchar(40) not null references users(username),
        details text,
        description text,
        created_time timestamptz not null,
        target_user varchar(40) references users(username),
        target_post_id bigint references posts(id),
        target_comment_id bigint references comments(id)
    );
    CREATE INDEX IF NOT EXISTS mod_actions_mod_lower_key ON mod_actions (lower(mod));
    """
    )


def downgrade():
    op.execute(
        """
    DROP TABLE IF EXISTS mod_actions;
    DROP TABLE IF EXISTS comments;
    DROP TABLE IF EXISTS posts;
    DROP TABLE IF EXISTS users;
    """
    )
