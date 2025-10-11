import json
import pika
import praw
from json import JSONEncoder
from praw.models.mod_action import ModAction
from praw.models.reddit.comment import Comment
from praw.models.reddit.submission import Submission
from types import FunctionType
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
    def __init__(self, config_dict: dict):
        logger.info("Connecting to RabbitMQ...")
        connection = pika.BlockingConnection(pika.URLParameters(config_dict["connection"]))
        self.channel = connection.channel()
        self.queues = {}

        for exchange in config_dict["exchanges"]:
            logger.info(f"Declaring RabbitMQ Exchange {exchange["name"]}")
            self.channel.exchange_declare(exchange=exchange["name"], exchange_type="direct", durable=True)
            for key, queue in exchange["queues"].items():
                logger.info(f"Declaring RabbitMQ Queue {queue["name"]}")
                self.channel.queue_declare(queue=queue["name"], durable=True)
                self.channel.queue_bind(exchange=exchange["name"], queue=queue["name"], routing_key=queue["name"])
                self.queues[key] = {"exchange": exchange["name"], "queue": queue["name"]}

    def publish_post(self, reddit_post: Submission, post: PostModel, status: str = "new"):
        logger.info(f"Publishing post to RabbitMQ: {reddit_post.id} ({status})")
        queue = self.queues["post"]
        body = {"status": status, "reddit": reddit_post, "db": post.to_dict()}
        self.channel.basic_publish(
            exchange=queue["exchange"], routing_key=queue["queue"], body=json.dumps(body, cls=PRAWJSONEncoder)
        )

    def publish_comment(self, reddit_comment: Comment, comment: CommentModel, status: str = "new"):
        logger.info(f"Publishing comment to RabbitMQ: {reddit_comment.id} ({status})")
        queue = self.queues["comment"]
        body = {"status": status, "reddit": reddit_comment, "db": comment.to_dict()}
        self.channel.basic_publish(
            exchange=queue["exchange"], routing_key=queue["queue"], body=json.dumps(body, cls=PRAWJSONEncoder)
        )

    def publish_mod_action(self, reddit_mod_action: ModAction, mod_action: ModActionModel, status: str = "new"):
        logger.info(f"Publishing mod action to RabbitMQ: {reddit_mod_action.id} ({status})")
        queue = self.queues["mod_action"]
        body = {"status": status, "reddit": reddit_mod_action, "db": mod_action.to_dict()}
        self.channel.basic_publish(
            exchange=queue["exchange"], routing_key=queue["queue"], body=json.dumps(body, cls=PRAWJSONEncoder)
        )
