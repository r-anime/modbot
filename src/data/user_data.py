from typing import Optional

from sqlalchemy.sql import text

from data.base_data import BaseModel, BaseData


class UserModel(BaseModel):
    # Originally users were supposed to have an int/base36 id field just like posts/comments,
    # but turns out suspended users DON'T HAVE A VISIBLE ID. Thanks Reddit!
    _table = "users"
    _pk_field = "username"  # Case-sensitive, use lower(username) when searching.
    _columns = ["username", "moderator", "flair", "flair_class", "created_time", "suspended", "deleted", "banned_until"]


class UserData(BaseData):
    def get_user(self, username: str) -> Optional[UserModel]:
        sql = text(
            """
        SELECT * FROM users
        WHERE username = :username;
        """
        )

        result_rows = self.execute(sql, username=username)
        if not result_rows:
            return None

        return UserModel(result_rows[0])

    def get_moderators(self) -> list[UserModel]:
        sql = text(
            """
        SELECT * FROM users
        WHERE moderator = TRUE;
        """
        )

        result_rows = self.execute(sql)

        user_list = []
        for row in result_rows:
            user_list.append(UserModel(row))

        return user_list
