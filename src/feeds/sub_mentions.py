import time

import config_loader
from utils import discord, reddit as reddit_utils
from utils.logger import logger


colour = 22135


def check_inbox(reddit):
    for message in reddit.inbox.unread(limit=5):
        if message.author != "Sub_Mentions":
            message.mark_read()
            continue

        author, desc = message.body.split("\n\n", 1)

        title = message.subject.replace("[Notification] Your subreddit has been mentioned in ", "")
        title = title.replace("!", " - ")
        title += author.replace("Author: ", "")
        logger.info(f"Processing message {title}")

        desc = desc[:-279]  # removes info at the end of the message
        desc = desc.replace("(/r/", "(https://www.reddit.com/r/")  # hyperlinks reddit links
        desc = desc.replace("\n___\n", "")
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
