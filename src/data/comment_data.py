from typing import Optional

from sqlalchemy.sql import text

from data.base_data import BaseModel, BaseData
from utils.reddit import base36decode


class CommentModel(BaseModel):
    _table = "comments"
    _pk_field = "id"
    _columns = [
        "id",
        "id36",
        "post_id",
        "parent_id",
        "author",
        "created_time",
        "score",
        "body",
        "edited",
        "distinguished",
        "deleted",
        "removed",
    ]

    @property
    def fullname(self):
        return f"t1_{self.id36}"

    def set_id(self, id_base36: str):
        """Sets both base 10 and base 36 forms of the id field."""
        self.id = base36decode(id_base36)
        self.id36 = id_base36


class CommentData(BaseData):
    def get_comment_by_id(self, comment_id: int) -> Optional[CommentModel]:
        sql = text("""
        SELECT * FROM comments
        WHERE id = :comment_id;
        """)

        result_rows = self.execute(sql, comment_id=comment_id)
        if not result_rows:
            return None

        return CommentModel(result_rows[0])

    def get_comments_by_post_id(self, post_id: int) -> list[CommentModel]:
        sql = text("""
            SELECT * FROM comments
            WHERE post_id = :post_id;
            """)

        result_rows = self.execute(sql, post_id=post_id)
        return [CommentModel(row) for row in result_rows]

    def get_comments_by_username(
        self, username: str, start_date: str = None, end_date: str = None, exclude_cdf: bool = False
    ) -> list[CommentModel]:
        where_clauses = ["lower(c.author) = :username"]
        sql_kwargs = {"username": username.lower()}

        if start_date:
            where_clauses.append("c.created_time >= :start_date")
            sql_kwargs["start_date"] = start_date

        if end_date:
            where_clauses.append("c.created_time < :end_date")
            sql_kwargs["end_date"] = end_date

        where_str = " AND ".join(where_clauses)

        if exclude_cdf:
            sql = text(f"""
                SELECT * FROM comments c JOIN posts p ON c.post_id = p.id
                WHERE {where_str} AND p.title not like 'Casual Discussion Fridays - Week of %'
                """)
        else:
            sql = text(f"""
                SELECT * FROM comments c
                WHERE {where_str};
                """)

        result_rows = self.execute(sql, **sql_kwargs)
        return [CommentModel(row) for row in result_rows]

    def get_comment_count_by_username(
        self, username: str, start_date: str = None, end_date: str = None, exclude_cdf: bool = False
    ) -> int:
        where_clauses = ["lower(c.author) = :username"]
        sql_kwargs = {"username": username.lower()}

        if start_date:
            where_clauses.append("c.created_time >= :start_date")
            sql_kwargs["start_date"] = start_date

        if end_date:
            where_clauses.append("c.created_time < :end_date")
            sql_kwargs["end_date"] = end_date

        where_str = " AND ".join(where_clauses)

        if exclude_cdf:
            sql = text(f"""
                SELECT COUNT(*) FROM comments c JOIN posts p ON c.post_id = p.id
                WHERE {where_str} AND p.title not like 'Casual Discussion Fridays - Week of %'
                """)
        else:
            sql = text(f"""
                SELECT COUNT(*) FROM comments c
                WHERE {where_str};
                """)

        return self.execute(sql, **sql_kwargs)[0][0]

    def get_comment_count(self, start_date: str = None, end_date: str = None, exclude_authors: list = None) -> int:
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
        SELECT COUNT(*) FROM comments
        WHERE {where_str};
        """)

        # Will return a list of tuples with only one item in each, e.g. [(2910,)]
        result = self.execute(sql, **sql_kwargs)
        return result[0][0]

    def get_comment_author_count(
        self, start_date: str = None, end_date: str = None, exclude_authors: list = None
    ) -> int:
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
        SELECT COUNT(DISTINCT author) FROM comments
        WHERE {where_str};
        """)

        # Will return a list of tuples with only one item in each, e.g. [(2910,)]
        result = self.execute(sql, **sql_kwargs)
        return result[0][0]
