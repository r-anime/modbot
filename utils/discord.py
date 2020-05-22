"""Utilities focused around Discord, including sending messages."""

import re
import time

import requests

import config
from utils.logger import logger


MESSAGE_LIMIT = 2000

# Use these to escape characters that would become formatting.
_UNESCAPE_RE = re.compile(r'\\')
_ESCAPE_RE = re.compile(r'([*_~`|\\])')


def escape_formatting(string):
    """
    Escapes any Discord formatting characters.
    """
    unescaped = _UNESCAPE_RE.sub('', string)
    escaped = _ESCAPE_RE.sub(r'\\\g<1>', unescaped)

    return escaped


def send_webhook_message(json_content, channel_webhook_url=config.DISCORD["webhook_notifications"], retries=3):
    """
    Send a message to the specified channel via a webhook.

    :param json_content: dictionary containing data to send (usually "content" or "embed" keys)
    :param channel_webhook_url: full URL for the receiving webhook
    :param retries: number of times to attempt to send message again if it fails
    :return: True if message was successfully sent, False otherwise
    """

    attempt = 0
    while attempt <= retries:
        try:
            response = requests.post(channel_webhook_url, json=json_content)

            if response.status_code in (200, 204):
                return True

            logger.warning(f"Webhook response {response.status_code}: {response.text}")
        except Exception:
            logger.exception("Unexpected error while attempting to send webhook message.")

        time.sleep(5)
        attempt += 1

    logger.error(f"Unable to send webhook message, content: {json_content}")
    return False
