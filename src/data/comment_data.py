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

    def set_id(self, id_base36: str):
        """Sets both base 10 and base 36 forms of the id field."""
        self.id = base36decode(id_base36)
        self.id36 = id_base36


class CommentData(BaseData):
    def get_comment_by_id(self, comment_id: int) -> Optional[CommentModel]:
        sql = text(
            """
        SELECT * FROM comments
        WHERE id = :comment_id;
        """
        )

        result_rows = self.execute(sql, comment_id=comment_id)
        if not result_rows:
            return None

        return CommentModel(result_rows[0])
