from typing import Optional

from sqlalchemy.sql import text

from data.base_data import BaseModel, BaseData


class RabbitmqPendingMessageModel(BaseModel):
    _table = "rabbitmq_pending_messages"
    _pk_field = "id"
    _columns = ["id", "type", "exchange_name", "queue_name", "json_body", "created_time"]


class RabbitmqPendingMessageData(BaseData):
    def get_rabbitmq_pending_message_by_id(self, id: int) -> Optional[RabbitmqPendingMessageModel]:
        sql = text("""
        SELECT * FROM rabbitmq_pending_messages
        WHERE id = :id;
        """)

        result_rows = self.execute(sql, id=id)
        if not result_rows:
            return None

        return RabbitmqPendingMessageModel(result_rows[0])

    def get_rabbitmq_pending_messages(self) -> list[RabbitmqPendingMessageModel]:
        sql = text("""
            SELECT * FROM rabbitmq_pending_messages
            ORDER BY created_time ASC;
            """)

        result_rows = self.execute(sql)
        return [RabbitmqPendingMessageModel(row) for row in result_rows]
