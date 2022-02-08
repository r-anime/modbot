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
        "edited",
        "distinguished",
        "deleted",
        "removed",
        "sent_to_feed",
    ]

    def set_id(self, id_base36: str):
        """Sets both base 10 and base 36 forms of the id field."""
        self.id = base36decode(id_base36)
        self.id36 = id_base36

    def __str__(self):
        return f'<{self.__class__.__name__}: {getattr(self, "id36", None)} by {getattr(self, "author", None)}>'


class PostData(BaseData):
    def get_post_by_id(self, post_id: int) -> Optional[PostModel]:
        sql = text(
            """
        SELECT * FROM posts
        WHERE id = :post_id;
        """
        )

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

        sql = text(
            f"""
        SELECT * FROM posts
        WHERE {where_str};
        """
        )

        result_rows = self.execute(sql, **sql_kwargs)
        return [PostModel(row) for row in result_rows]
