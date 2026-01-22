"""Add indexes for comments.post_id, comments.created_time, posts.created_time

Revision ID: d36823f77b1f
Revises: a35048950546
Create Date: 2022-09-24 21:00:09.062636+00:00

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d36823f77b1f"
down_revision = "a35048950546"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("COMMIT;")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comments_created_time ON comments(created_time);")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comments_post_id ON comments(post_id);")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_created_time ON posts(created_time);")


def downgrade():
    op.execute("COMMIT;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_posts_created_time;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_comments_post_id;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_comments_created_time;")
