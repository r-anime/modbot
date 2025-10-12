import json
import pika
import praw
from collections import deque
from json import JSONEncoder
from praw.models.mod_action import ModAction
from praw.models.reddit.comment import Comment
from praw.models.reddit.submission import Submission
from types import FunctionType
from typing import Deque
from uuid import UUID

from data.comment_data import CommentModel
from data.mod_action_data import ModActionModel
from data.post_data import PostModel
from utils.logger import logger


class PRAWJSONEncoder(JSONEncoder):
    """Class to encode PRAW objects to JSON."""

    def default(self, obj):
        if isinstance(obj, praw.models.base.PRAWBase):
            obj_dict = {}
            for key, value in obj.__dict__.items():
                if key.startswith("_") or isinstance(value, FunctionType):
                    continue
                obj_dict[key] = value
            return obj_dict
        elif isinstance(obj, UUID):
            return str(obj)
        else:
            return super().default(obj)


class RabbitService:
    messages_to_retry: Deque[dict] = deque()

    def __init__(self, config_dict: dict):
        self.config = config_dict
        self.connection = None
        self.channel = None
        self.init_connection(False)

        self.queues = {}
        for exchange in self.config["exchanges"]:
            logger.info(f"Declaring RabbitMQ Exchange {exchange["name"]}")
            self.channel.exchange_declare(exchange=exchange["name"], exchange_type="direct", durable=True)
            for key, queue in exchange["queues"].items():
                logger.info(f"Declaring RabbitMQ Queue {queue["name"]}")
                self.channel.queue_declare(queue=queue["name"], durable=True)
                self.channel.queue_bind(exchange=exchange["name"], queue=queue["name"], routing_key=queue["name"])
                self.queues[key] = {"exchange": exchange["name"], "queue": queue["name"]}

        if self.messages_to_retry:
            logger.info(f"Retrying {len(self.messages_to_retry)} RabbitMQ messages")
        while self.messages_to_retry:
            exchange_name, queue_name, json_body = self.messages_to_retry.popleft()
            self._publish_message(exchange_name, queue_name, json_body)

    def init_connection(self, reconnect: bool = True):
        logger.info(f"{"Rec" if reconnect else "C"}onnecting to RabbitMQ...")
        self.connection = pika.BlockingConnection(pika.URLParameters(self.config["connection"]))
        self.channel = self.connection.channel()
        self.channel.confirm_delivery()

    def publish_post(self, reddit_post: Submission, post: PostModel, status: str = "new"):
        logger.info(f"Publishing post to RabbitMQ: {reddit_post.id} ({status})")
        queue = self.queues["post"]
        body = {"status": status, "reddit": reddit_post, "db": post.to_dict()}
        self._publish_message(queue["exchange"], queue["queue"], json.dumps(body, cls=PRAWJSONEncoder))

    def publish_comment(self, reddit_comment: Comment, comment: CommentModel, status: str = "new"):
        logger.info(f"Publishing comment to RabbitMQ: {reddit_comment.id} ({status})")
        queue = self.queues["comment"]
        body = {"status": status, "reddit": reddit_comment, "db": comment.to_dict()}
        self._publish_message(queue["exchange"], queue["queue"], json.dumps(body, cls=PRAWJSONEncoder))

    def publish_mod_action(self, reddit_mod_action: ModAction, mod_action: ModActionModel, status: str = "new"):
        logger.info(f"Publishing mod action to RabbitMQ: {reddit_mod_action.id} ({status})")
        queue = self.queues["mod_action"]
        body = {"status": status, "reddit": reddit_mod_action, "db": mod_action.to_dict()}
        self._publish_message(queue["exchange"], queue["queue"], json.dumps(body, cls=PRAWJSONEncoder))

    def _publish_message(self, exchange_name: str, queue_name: str, json_body: str):
        try:
            self.channel.basic_publish(
                exchange=exchange_name,
                routing_key=queue_name,
                body=json_body,
                properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
            )
        except Exception:
            try:
                self.init_connection(True)
                self.channel.basic_publish(
                    exchange=exchange_name,
                    routing_key=queue_name,
                    body=json_body,
                    properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
                )
                logger.info("Successfully send message after reconnect")
            except Exception:
                logger.error("Still couldn't connect to RabbitMQ. Saving message to retry memory list")
                self.messages_to_retry.append((exchange_name, queue_name, json_body))
                raise
