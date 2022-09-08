"""Utilities focused around Discord, including sending messages."""

import re
import time

import requests

import config_loader
from utils.logger import logger


MESSAGE_LIMIT = 2000

# Use these to escape characters that would become formatting.
_UNESCAPE_RE = re.compile(r"\\")
_ESCAPE_RE = re.compile(r"([*_~`|\\])")


def escape_formatting(string):
    """
    Escapes any Discord formatting characters.
    """
    unescaped = _UNESCAPE_RE.sub("", string)
    escaped = _ESCAPE_RE.sub(r"\\\g<1>", unescaped)

    return escaped


def send_webhook_message(channel_webhook_url, json_content, return_message_id=False, retries=3):
    """
    Send a message to the specified channel via a webhook.

    :param channel_webhook_url: full URL for the receiving webhook
    :param json_content: dictionary containing data to send (usually "content" or "embed" keys)
    :param retries: number of times to attempt to send message again if it fails
    :param return_message_id: whether or not to get the Discord message id and return it
    :return: Discord message id if return_message_id is True and message was successfully sent,
     True if return_message_id is False and message was successfully sent,
     False otherwise
    """

    if not config_loader.DISCORD["enabled"]:
        return True

    attempt = 0
    while attempt <= retries:
        try:
            params = {"wait": "true"} if return_message_id else {}
            response = requests.post(channel_webhook_url, json=json_content, params=params)

            if response.status_code in (200, 204) and not return_message_id:
                return True
            if response.status_code == 200 and return_message_id:
                response_json = response.json()
                return response_json.get("id")

            logger.warning(f"Webhook response {response.status_code}: {response.text}")
        except Exception:
            logger.exception("Unexpected error while attempting to send webhook message.")

        time.sleep(5)
        attempt += 1

    logger.error(f"Unable to send webhook message, content: {json_content}")
    return False


def update_webhook_message(channel_webhook_url, message_id, json_content, retries=3):
    if not config_loader.DISCORD["enabled"]:
        return True

    if message_id is None:
        return False

    attempt = 0
    while attempt <= retries:
        try:
            message_edit_url = f"{channel_webhook_url.rstrip('/')}/messages/{message_id}"
            response = requests.patch(message_edit_url, json=json_content)

            if response.status_code in (200, 204):
                return True

            logger.warning(f"Webhook response {response.status_code}: {response.text}")
        except Exception:
            logger.exception("Unexpected error while attempting to send webhook message.")

        time.sleep(5)
        attempt += 1

    logger.error(f"Unable to send webhook message, content: {json_content}")
    return False
