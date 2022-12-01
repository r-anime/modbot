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

    def get_mod_actions_targeting_post(
        self, post_id: int, actions: list[str] = None, limit: int = None, order: str = "DESC"
    ):

        where_clauses = ["target_post_id = :post_id"]
        sql_kwargs = {"post_id": post_id}

        if actions:
            action_params = [f":action{i}" for i, _ in enumerate(actions)]
            action_param_str = ", ".join(action_params)
            where_clauses.append(f"action in ({action_param_str})")
            for param, action in zip(action_params, actions):
                sql_kwargs[param.lstrip(":")] = action

        if limit:
            limit_str = "LIMIT :limit"
            sql_kwargs["limit"] = limit
        else:
            limit_str = ""

        where_str = " AND ".join(where_clauses)
        order_str = "ORDER BY created_time DESC" if order == "DESC" else ""

        sql = text(
            f"""
            SELECT * FROM mod_actions
            WHERE {where_str}
            {order_str}
            {limit_str};
            """
        )

        result_rows = self.execute(sql, **sql_kwargs)
        result_models = [ModActionModel(row) for row in result_rows]
        return result_models

    def get_mod_actions_targeting_username(
        self, username: str, actions: list[str] = None, start_date: str = None, end_date: str = None
    ) -> list[ModActionModel]:
        where_clauses = ["lower(target_user) = :username"]
        sql_kwargs = {"username": username.lower()}

        if actions:
            action_params = [f":action{i}" for i, _ in enumerate(actions)]
            action_param_str = ", ".join(action_params)
            where_clauses.append(f"action in ({action_param_str})")
            for param, action in zip(action_params, actions):
                sql_kwargs[param.lstrip(":")] = action

        if start_date:
            where_clauses.append("created_time >= :start_date")
            sql_kwargs["start_date"] = start_date

        if end_date:
            where_clauses.append("created_time < :end_date")
            sql_kwargs["end_date"] = end_date

        where_str = " AND ".join(where_clauses)

        sql = text(
            f"""
        SELECT * FROM mod_actions
        WHERE {where_str};
        """
        )

        result_rows = self.execute(sql, **sql_kwargs)
        return [ModActionModel(row) for row in result_rows]

    def count_mod_actions(
        self,
        action: str,
        start_time: str,
        end_time: str,
        distinct_target: str = "",
        details: str = "",
        description: str = "",
        include_mods: list = None,
        exclude_mods: list = None,
    ) -> int:
        """

        :param action:
        :param start_time:
        :param end_time:
        :param distinct_target:
        :param details:
        :param description:
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

        if description:
            where_clauses.append("description = :description")
            sql_kwargs["description"] = description

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
