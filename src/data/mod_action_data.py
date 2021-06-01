from typing import Optional

from sqlalchemy.sql import text

from data.base_data import BaseModel, BaseData


class ModActionModel(BaseModel):
    _table = "mod_actions"
    _pk_field = "id"
    _columns = [
        "id",
        "action",
        "mod",
        "details",
        "description",
        "created_time",
        "target_user",
        "target_comment_id",
        "target_post_id",
    ]


class ModActionData(BaseData):
    def get_mod_action_by_id(self, mod_action_id: str) -> Optional[ModActionModel]:
        sql = text(
            """
        SELECT * FROM mod_actions
        WHERE id = :mod_action_id;
        """
        )

        result_rows = self.execute(sql, mod_action_id=mod_action_id)
        if not result_rows:
            return None

        return ModActionModel(result_rows[0])
