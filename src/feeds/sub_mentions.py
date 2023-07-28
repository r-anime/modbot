import re
import time

import config_loader
from utils import discord, reddit as reddit_utils
from utils.logger import logger


colour = 22135


def check_inbox(reddit):
    for message in reddit.inbox.unread(limit=5):
        logger.info(f"Checking message from {message.author}")
        if message.author != "Sub_Mentions" and not message.author.name.startswith("feedcomber-"):
            message.mark_read()
            continue

        message_body = re.sub("\n\n___\n\n", "\n\n____\n\n", message.body)  # standardize template
        header, body = message_body.split("\n\n____\n\n", 1)
        body, footer = body.rsplit("\n\n____\n\n", 1)
        header_parts = header.split("\n\n")
        link = header_parts[-1]
        author = header_parts[-2]

        # Check to see that it's actually a reference to /r/anime and not something else.
        if not re.search(r"\br/anime\b", body):
            message.mark_read()
            continue

        title = re.sub(r"^.*/(r/\w+)!?$", r"/\1 - ", message.subject)
        title += author.replace("Author: ", "")
        logger.info(f"Processing message {title}")

        desc = link.replace("(/r/", "(https://www.reddit.com/r/")  # hyperlink to reference
        desc += "\n\n" + body

        if len(desc) >= 2000:  # message length (max for webhook is 2000)
            desc = desc[:1997] + "..."

        global colour
        colour = 242424 if colour == 22135 else 22135  # switches colors to break up messages

        embed_json = {"title": title, "description": desc, "color": colour}  # yeah the Australia

        logger.debug(embed_json)
        discord.send_webhook_message(config_loader.DISCORD["webhook_url"], {"embeds": [embed_json]})

        message.mark_read()
        time.sleep(5)  # wait between messages to not flood Discord


if __name__ == "__main__":
    while True:
        try:
            logger.info("Connecting to Reddit...")
            # Requires an account linked to /u/Sub_Mentions
            reddit = reddit_utils.get_reddit_instance(config_loader.REDDIT["auth"])
            while True:
                check_inbox(reddit)
                logger.debug("waiting...")
                time.sleep(30)  # wait between inbox retrievals because it's not necessary to be realtime
        except Exception:
            delay_time = 30
            logger.exception(f"Encountered an unexpected error, restarting in {delay_time} seconds...")
            time.sleep(delay_time)
