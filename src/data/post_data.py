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
    ]

    def set_id(self, id_base36: str):
        """Sets both base 10 and base 36 forms of the id field."""
        self.id = base36decode(id_base36)
        self.id36 = id_base36


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
