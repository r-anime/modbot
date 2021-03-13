"""
Generic methods for handling model CRUD in the database.
"""

from data.base_data import BaseData, BaseModel


_base_data = BaseData()


def insert(model: BaseModel) -> BaseModel:
    return _base_data.insert(model)


def update(model: BaseModel) -> BaseModel:
    return _base_data.update(model)


def delete(model: BaseModel):
    return _base_data.delete(model)
