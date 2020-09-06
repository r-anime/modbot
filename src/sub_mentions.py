import re
import time

import praw

import config
from utils import discord


reddit = praw.Reddit(**config.SUB_MENTIONS["auth"])  # Requires an account linked to /u/Sub_Mentions
colour_switcher = 0


while True:
    for message in reddit.inbox.unread(limit=1):
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

        discord.send_webhook_message(
            {"embeds": [embed_json]},
            channel_webhook_url=config.DISCORD["webhook_sub_mentions"]
        )
        message.mark_read()

    time.sleep(2.1)
