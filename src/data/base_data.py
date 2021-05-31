from copy import copy
from typing import Union

from sqlalchemy import create_engine
from sqlalchemy.sql import text
from sqlalchemy.engine.result import RowProxy

import config_loader
from data.session import session_scope


_engine = create_engine(config_loader.DB_CONNECTION)


class BaseModel:
    """
    A thin wrapper around SQLAlchemy's RowProxy object. Tables are defined manually with alembic.
    """

    _row = None

    _table = ""
    _pk_field = ""

    _columns = []
    # Columns that have been modified, with new values.
    _modified = {}

    def __init__(self, row: RowProxy = None, lazy: bool = True):
        self._row = row

        # If we're not lazy loading, load all columns at once.
        if not lazy and self._row:
            for column in self._columns:
                getattr(self, column)

        self._modified = {}

    def __getattr__(self, item):
        # Loads column from row if it exists.
        if self._row and item in self._columns:
            object.__setattr__(self, item, self._row[item])
            return self._row[item]

        raise AttributeError(f"Could not locate column named {item}")

    def __setattr__(self, key, value):
        # Only set as modified if it's a database column *and* it's changed compared to the previous value.
        if key in self._columns:
            # New model, not from database.
            if self._row is None:
                self._modified[key] = value
            # Model from database. Column gets loaded when hasattr is called.
            elif hasattr(self, key) and self.__getattribute__(key) != value:
                self._modified[key] = value

        object.__setattr__(self, key, value)

    def __str__(self):
        return f"<{self.__class__.__name__}: {self._pk_field}={getattr(self, self._pk_field, None)}>"

    @property
    def table(self):
        return self._table

    @property
    def modified_fields(self):
        return self._modified

    @property
    def pk_field(self):
        return self._pk_field

    @property
    def columns(self):
        return self._columns

    def load(self):
        """
        Sets all columns as the model's attributes from the saved row.
        Similar to passing lazy=False when creating the model.
        """

        if not self._row:
            return

        for column in self._columns:
            getattr(self, column)


class BaseData:
    _model = None
    _model_table = ""

    def insert(self, model: BaseModel, error_on_conflict: bool = True):
        # sql_params is a copy of modified_fields with every key replaced as ":key".
        # This avoids SQL injection attacks by forcing every set value to be sent parameterized.
        sql_params = dict(zip([f":{key}" for key in model.modified_fields.keys()], model.modified_fields.values()))
        sql_param_str = ", ".join(sql_params.keys())
        sql_column_str = ", ".join(model.modified_fields.keys())

        # If error_on_conflict is false, will still return existing row.
        conflict_sql = "ON CONFLICT DO NOTHING" if not error_on_conflict else ""

        sql = text(
            f"""
            INSERT INTO {model.table}
            ({sql_column_str})
            VALUES
            ({sql_param_str})
            {conflict_sql}
            RETURNING *;
        """
        )

        with session_scope() as session:
            result_row = session.execute(sql, model.modified_fields).fetchone()

            # ON CONFLICT DO NOTHING doesn't return an existing row, so fetch it if necessary.
            if result_row is None and not error_on_conflict and hasattr(model, model.pk_field):
                sql = text(f"SELECT * FROM {model.table} WHERE {model.pk_field} = :pk;")
                result_row = session.execute(sql, {"pk": getattr(model, model.pk_field)}).fetchone()

            new_model = model.__class__(result_row)

        return new_model

    def update(self, model: BaseModel):

        if model.pk_field in model.modified_fields:
            raise NotImplementedError(f"Can't update the primary key of model {model}!")

        if not model.modified_fields:
            return model

        # sql_params is a copy of modified_fields with every key replaced as ":key".
        # This avoids SQL injection attacks by forcing every set value to be sent parameterized.
        sql_params = dict(zip([f":{key}" for key in model.modified_fields.keys()], model.modified_fields.values()))
        sql_param_str = ", ".join(sql_params.keys())
        sql_column_str = ", ".join(model.modified_fields.keys())

        # Weird SQL(/Postgres?) thing: if only a single column is being updated, can't use () around the column list.
        # Multiple columns still need it though. Values are fine with just one.
        if len(model.modified_fields) > 1:
            sql_column_str = f"({sql_column_str})"

        sql = text(
            f"""
            UPDATE {model.table} SET
            {sql_column_str}
            =
            ({sql_param_str})
            WHERE {model.pk_field} = :pk
            RETURNING *;
        """
        )

        sql_parameterized = copy(model.modified_fields)
        sql_parameterized["pk"] = getattr(model, model.pk_field)

        with session_scope() as session:
            result_row = session.execute(sql, sql_parameterized).fetchone()
            new_model = model.__class__(result_row)

        return new_model

    def delete(self, model: BaseModel):
        sql = text(
            f"""DELETE FROM {model.table}
            WHERE {model.pk_field} = :pk"""
        )

        return self.execute(sql, pk=getattr(model, model.pk_field))

    def execute(self, sql: Union[str, text], **kwargs):
        if isinstance(sql, str):
            sql = text(sql)

        with session_scope() as session:
            result = session.execute(sql, kwargs).fetchall()

        return result
