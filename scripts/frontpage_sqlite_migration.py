"""
One-time migration script from sqlalchemy models and sqlite database to custom ORM & PostgreSQL.

Not designed to work as part of the regular alembic system, merely placed here for archive purposes.
Should never need to run this again.

2021-05-03
"""

from datetime import datetime, timedelta
import sqlite3

from data.post_data import PostData, PostModel
from data.snapshot_data import SnapshotData, SnapshotModel, SnapshotFrontpageModel
from data.user_data import UserData
from services import post_service
from utils.logger import logger
from utils.reddit import base36decode


_post_data = PostData()
_snapshot_data = SnapshotData()
_user_data = UserData()

DB_FILE = "src/database.db"


def migrate_posts(offset=0):
    """Grabs posts in batches of 1000 at a time and migrates them to the new database.
    Returns number of processed rows. If less than 1000, at end of the table."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("SELECT * FROM posts LIMIT 1000 OFFSET ?;", (offset,)).fetchall()

    conn.close()

    row = None
    for row in rows:
        # If the post already exists in the database we don't need to do anything.
        post_id36 = row["id"]
        post = post_service.get_post_by_id(post_id36)
        if post:
            continue

        # OH RIGHT NO USER DATA IS SAVED IN THE OLD DATABASE.
        # username = row["name"]
        # if not user_service.get_user(username):
        #     user = UserModel()
        #     user.username = username
        #     _user_data.insert(user, error_on_conflict=False)

        post = PostModel()
        post.set_id(post_id36)
        # post.author = username
        post.title = row["title"]
        post.created_time = row["created_time"]
        post.flair_text = row["flair"]  # will add flair id in later mass update/backfill.. and user info
        _post_data.insert(post, error_on_conflict=False)

    if not row:
        logger.warning("No rows processed!")
    else:
        logger.info(f"Most recent migrated row: psk={row['psk']}, id={row['id']}")
    return len(rows)


def migrate_snapshots(date, hour):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    row = conn.execute("SELECT * FROM snapshots WHERE date=? and hour=?;", (date, hour)).fetchone()

    # No data, past the last recorded snapshot?
    if not row:
        return

    old_snapshot_psk = row["psk"]
    snapshot = SnapshotModel()
    snapshot.created_time = row["datetime"]
    snapshot.date = date
    snapshot.hour = hour
    snapshot.subscribers = row["subscribers"]

    new_snapshot = _snapshot_data.insert(snapshot)

    rows = conn.execute(
        "SELECT sf.*, p.id FROM snapshot_frontpage sf JOIN posts p on sf.post_psk = p.psk WHERE snapshot_psk=?;",
        (old_snapshot_psk,),
    ).fetchall()

    conn.close()

    for row in rows:
        sfp_model = SnapshotFrontpageModel()
        sfp_model.post_id = base36decode(row["id"])
        sfp_model.snapshot_id = new_snapshot.id
        sfp_model.rank = row["rank"]
        sfp_model.score = row["score"]

        _snapshot_data.insert(sfp_model)


def main():
    current_offset = 0
    while True:
        processed_posts = migrate_posts(current_offset)
        current_offset += processed_posts
        if processed_posts < 1000:
            break
        if current_offset % 1000 == 0:
            logger.info(f"Migrated {current_offset} posts total")

    current_datetime = datetime.fromisoformat("2020-05-12 04:00:00.000")
    now = datetime.utcnow()
    while current_datetime <= now:
        try:
            migrate_snapshots(current_datetime.date(), current_datetime.hour)
        except Exception:
            logger.exception(f"Failed to migrate {current_datetime.date()} - {current_datetime.hour}")
        current_datetime += timedelta(hours=1)
        if current_datetime.hour == 0:
            logger.info(f"Finished migrating {current_datetime.date()}")


if __name__ == "__main__":
    main()
