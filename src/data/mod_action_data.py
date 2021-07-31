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

    def count_mod_actions(
            self,
            action: str,
            start_time: str,
            end_time: str,
            distinct_target: str = "",
            details: str = "",
            include_mods: list = None,
            exclude_mods: list = None
    ) -> int:
        """

        :param action:
        :param start_time:
        :param end_time:
        :param distinct_target:
        :param details:
        :param include_mods:
        :param exclude_mods:
        :return:
        """

        if distinct_target == "user":
            distinct = "DISTINCT target_user"
        elif distinct_target == "post":
            distinct = "DISTINCT target_post_id"
        elif distinct_target == "comment":
            distinct = "DISTINCT target_Comment_id"
        else:
            distinct = "*"

        where_clauses = ["action = :action", "created_time >= :start_time", "created_time < :end_time"]
        sql_kwargs = {"action": action, "start_time": start_time, "end_time": end_time}

        if details:
            where_clauses.append("details = :details")
            sql_kwargs["details"] = details

        if include_mods is not None:
            where_clauses.append("mod in :include_mods")
            sql_kwargs["include_mods"] = tuple(include_mods)

        if exclude_mods is not None:
            where_clauses.append("mod not in :exclude_mods")
            sql_kwargs["exclude_mods"] = tuple(exclude_mods)

        where_str = " AND ".join(where_clauses)

        sql = text(
            f"""
        SELECT COUNT({distinct}) FROM mod_actions
        WHERE {where_str};
        """
        )

        # Will return a list of tuples with only one item in each, e.g. [(2910,)]
        result = self.execute(sql, **sql_kwargs)

        return result[0][0]
