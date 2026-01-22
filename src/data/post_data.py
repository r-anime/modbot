from typing import Optional

from sqlalchemy.sql import text

from data.base_data import BaseModel, BaseData
from utils.reddit import base36decode


class PostModel(BaseModel):
    _table = "posts"
    _pk_field = "id"
    _columns = [
        "id",
        "id36",
        "author",
        "title",
        "flair_id",
        "flair_text",
        "created_time",
        "score",
        "url",
        "body",
        "metadata",
        "edited",
        "distinguished",
        "deleted",
        "deleted_time",
        "removed",
        "sent_to_feed",
        "discord_message_id",
    ]

    @property
    def fullname(self):
        return f"t3_{self.id36}"

    def set_id(self, id_base36: str):
        """Sets both base 10 and base 36 forms of the id field."""
        self.id = base36decode(id_base36)
        self.id36 = id_base36


class PostData(BaseData):
    def get_post_by_id(self, post_id: int) -> Optional[PostModel]:
        sql = text("""
        SELECT * FROM posts
        WHERE id = :post_id;
        """)

        result_rows = self.execute(sql, post_id=post_id)
        if not result_rows:
            return None

        return PostModel(result_rows[0])

    def get_posts_by_username(self, username: str, start_date: str = None, end_date: str = None) -> list[PostModel]:
        where_clauses = ["lower(author) = :username"]
        sql_kwargs = {"username": username.lower()}

        if start_date:
            where_clauses.append("created_time >= :start_date")
            sql_kwargs["start_date"] = start_date

        if end_date:
            where_clauses.append("created_time < :end_date")
            sql_kwargs["end_date"] = end_date

        where_str = " AND ".join(where_clauses)

        sql = text(f"""
        SELECT * FROM posts
        WHERE {where_str};
        """)

        result_rows = self.execute(sql, **sql_kwargs)
        return [PostModel(row) for row in result_rows]

    def get_post_count_by_username(self, username: str, start_date: str = None, end_date: str = None) -> int:
        where_clauses = ["lower(author) = :username"]
        sql_kwargs = {"username": username.lower()}

        if start_date:
            where_clauses.append("created_time >= :start_date")
            sql_kwargs["start_date"] = start_date

        if end_date:
            where_clauses.append("created_time < :end_date")
            sql_kwargs["end_date"] = end_date

        where_str = " AND ".join(where_clauses)

        sql = text(f"""
        SELECT COUNT(*) FROM posts
        WHERE {where_str};
        """)

        return self.execute(sql, **sql_kwargs)[0][0]

    def get_flaired_posts_by_username(
        self,
        username: str,
        flairs: list[str],
        exclude_reddit_ids: list[str] = None,
        include_removed: bool = False,
        start_date: str = None,
        end_date: str = None,
    ) -> list[PostModel]:
        where_clauses = ["lower(author) = :username", "lower(flair_text) IN :flairs"]
        sql_kwargs = {"username": username.lower(), "flairs": tuple([f.lower() for f in flairs])}

        if exclude_reddit_ids:
            where_clauses.append("id36 NOT IN :excluded_ids")
            sql_kwargs["excluded_ids"] = tuple(exclude_reddit_ids)

        if not include_removed:
            where_clauses.append("removed != :removed")
            sql_kwargs["removed"] = str(not include_removed)

        if start_date:
            where_clauses.append("created_time >= :start_date")
            sql_kwargs["start_date"] = start_date

        if end_date:
            where_clauses.append("created_time < :end_date")
            sql_kwargs["end_date"] = end_date

        where_str = " AND ".join(where_clauses)

        sql = text(f"""
        SELECT * FROM posts
        WHERE {where_str}
        ORDER BY created_time ASC;
        """)

        result_rows = self.execute(sql, **sql_kwargs)
        return [PostModel(row) for row in result_rows]

    def get_post_count(self, start_date: str = None, end_date: str = None, exclude_authors: list = None) -> int:
        where_clauses = []
        sql_kwargs = {}

        if start_date:
            where_clauses.append("created_time >= :start_date")
            sql_kwargs["start_date"] = start_date

        if end_date:
            where_clauses.append("created_time < :end_date")
            sql_kwargs["end_date"] = end_date

        if exclude_authors is not None:
            where_clauses.append("author not in :exclude_authors")
            sql_kwargs["exclude_authors"] = tuple(exclude_authors)

        where_str = " AND ".join(where_clauses)
        sql = text(f"""
        SELECT COUNT(*) FROM posts
        WHERE {where_str};
        """)

        # Will return a list of tuples with only one item in each, e.g. [(2910,)]
        result = self.execute(sql, **sql_kwargs)
        return result[0][0]

    def get_post_author_count(self, start_date: str = None, end_date: str = None, exclude_authors: list = None) -> int:
        where_clauses = []
        sql_kwargs = {}

        if start_date:
            where_clauses.append("created_time >= :start_date")
            sql_kwargs["start_date"] = start_date

        if end_date:
            where_clauses.append("created_time < :end_date")
            sql_kwargs["end_date"] = end_date

        if exclude_authors is not None:
            where_clauses.append("author not in :exclude_authors")
            sql_kwargs["exclude_authors"] = tuple(exclude_authors)

        where_str = " AND ".join(where_clauses)
        sql = text(f"""
        SELECT COUNT(DISTINCT author) FROM posts
        WHERE {where_str};
        """)

        # Will return a list of tuples with only one item in each, e.g. [(2910,)]
        result = self.execute(sql, **sql_kwargs)
        return result[0][0]
