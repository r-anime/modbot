from typing import Optional

from data.rabbitmq_pending_message_data import RabbitmqPendingMessageData, RabbitmqPendingMessageModel

_rabbitmq_pending_message_data = RabbitmqPendingMessageData()


def get_pending_message_by_id(id: int) -> Optional[RabbitmqPendingMessageModel]:
    """
    Gets a single rabbitmq_pending_message from the database.
    """

    return _rabbitmq_pending_message_data.get_rabbitmq_pending_message_by_id(id)


def get_pending_messages() -> list[RabbitmqPendingMessageModel]:
    """
    Get all rabbitmq_pending_messages in the DB. Ordered by created_time ascending
    """

    return _rabbitmq_pending_message_data.get_rabbitmq_pending_messages()


def insert_pending_message(
    exchange_name: str, queue_name: str, json_body: str, type: str
) -> RabbitmqPendingMessageModel:
    """Adds a new pending rabbitmq message to the database."""

    db_model = RabbitmqPendingMessageModel()
    db_model.exchange_name = exchange_name
    db_model.queue_name = queue_name
    db_model.json_body = json_body
    db_model.type = type

    saved_db_model = _rabbitmq_pending_message_data.insert(db_model)
    return saved_db_model


def delete_pending_message(pending_message: RabbitmqPendingMessageModel):
    return _rabbitmq_pending_message_data.delete(pending_message)
