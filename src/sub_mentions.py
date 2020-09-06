import re
import time

import praw

import config
from utils import discord
from utils.logger import logger


def listen(reddit):
    colour_switcher = 0

    for message in reddit.inbox.unread(limit=5):
        if message.author != "Sub_Mentions":
            message.mark_read()
            continue

        title = message.subject
        desc = message.body
        desc = desc[:-279]  # removes info at the end of the message
        desc = re.sub(r"\(/r/", "(https://www.reddit.com/r/", desc)  # hyperlinks reddit links
        if len(desc) >= 2000:  # message length (max for webhook is 2000)
            desc = desc[:1997] + "..."

        colour_switcher = colour_switcher + 1  # breaks up the flow so its easier on the eye, delete if it's not
        if colour_switcher % 2 == 1:
            colour = 242424
        else:
            colour = 22135

        embed_json = {
            "title": title,
            "description": desc,
            "color": colour  # yeah the Australia
        }

        logger.debug(embed_json)
        discord.send_webhook_message(
            {"embeds": [embed_json]},
            channel_webhook_url=config.DISCORD["webhook_sub_mentions"]
        )

        message.mark_read()
        time.sleep(5)  # wait between messages to not flood Discord

    logger.debug("waiting...")
    time.sleep(30)  # wait between inbox retrievals because it's not necessary to be realtime


if __name__ == "__main__":
    while True:
        try:
            logger.info("Connecting to Reddit...")
            reddit = praw.Reddit(**config.SUB_MENTIONS["auth"])  # Requires an account linked to /u/Sub_Mentions
            while True:
                listen(reddit)
        except Exception:
            delay_time = 30
            logger.exception(f"Encountered an unexpected error, restarting in {delay_time} seconds...")
            time.sleep(delay_time)
