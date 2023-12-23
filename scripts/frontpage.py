"""
Gathers a snapshot of the front page of a subreddit, designed to be run at the top of each hour (currently via cron).
Saves posts and their rank in a database to provide changes from the previous hour and how long a post has been there.
Also collects traffic for the sub provided by the API.
"""

from collections import Counter
from datetime import datetime, timezone, timedelta

import config_loader
from utils import discord, reddit as reddit_utils
from utils.logger import logger
from services import snapshot_service, traffic_service


def _format_line(submission, position, rank_change, total_hours):
    """
    Formats info about a single post on the front page for logging/messaging. A single post will look like this:
    Rank Change Duration Score  Flair    Id       User          Slug
    13.  +1     10h      188   [Episode](gkvlja) <AutoLovepon> <arte_episode_7_discussion>
    """

    line = "{:3}".format(f"{position}.")

    if rank_change is None:
        line += "  (new) "
    elif rank_change != 0:
        line += " {:7}".format(f"{rank_change:+d} {total_hours}h")
    else:
        line += " {:7}".format(f"-- {total_hours}h")

    line += f" {submission.score:>5}"

    line += " {:>25}".format(f"[{submission.link_flair_text}]({submission.id})")

    line += f" <{submission.author.name}>" if submission.author is not None else " <[deleted]>"

    line += f" <{reddit_utils.slug(submission)}>"

    return line


def update_traffic(subreddit):
    traffic = subreddit.traffic()

    if "month" in traffic:
        traffic_service.update_monthly_traffic(traffic["month"])
    if "day" in traffic:
        traffic_service.update_daily_traffic(traffic["day"])
    if "hour" in traffic:
        snapshot_service.update_hourly_traffic(traffic["hour"])


def check_front_page(subreddit):
    """Gathers information about the front page, saves it to a database, and sends a summary to Discord."""

    # Grab the date/hour that this is for. Less accurate the later in the hour this is executed.
    current_datetime = datetime.now(timezone.utc)
    previous_time = current_datetime - timedelta(hours=1)

    snapshot = snapshot_service.add_snapshot(current_datetime, subreddit.subscribers)

    # Index, keeps track of front page ranking.
    post_rank = 0

    # Get more than we need for a few different reasons:
    # 1. The first one or two items may be stickied and should be ignored.
    # 2. To track what position something is in if it fell off the front page.
    hot_list = subreddit.hot(limit=75)
    lines = []
    flairs = Counter()

    for post_praw in hot_list:
        if post_praw.stickied:
            continue
        post_rank += 1

        frontpage = snapshot_service.add_frontpage_post(post_praw, snapshot, post_rank)

        # Once we have 25 we don't need to do more calculations for the summary, but keep recording in the database
        # for the top 50 to track decay over time and possible later returns to the front page.
        if post_rank >= 50:
            break
        elif post_rank > 25:
            continue

        # For reporting to Discord, get where the post was previously ranked (if at all).
        previous_rank = snapshot_service.get_frontpage_rank(frontpage.post_id, previous_time)

        rank_change = None
        if previous_rank:
            rank_change = previous_rank - post_rank

        # How many hours the post has been on the front page in total.
        total_hours = snapshot_service.get_post_hours_ranked(frontpage.post_id)

        # Count flairs, as this goes by text any manually modified flairs will be saved separately.
        if post_praw.link_flair_text in flairs:
            flairs[post_praw.link_flair_text] += 1
        else:
            flairs[post_praw.link_flair_text] = 1

        lines.append(_format_line(post_praw, post_rank, rank_change, total_hours))
        logger.debug(lines[-1])

    message_list = []
    message_body = f"Front page as of {current_datetime.isoformat()}:\n```md\n"

    # Summary with count of each flair.
    message_body += " | ".join(f"[{key}][{value}]" for key, value in flairs.most_common()) + "\n"

    for line in lines:
        # If the current message will run over the character limit with the next line, end and start the next message.
        if len(message_body + line) > discord.MESSAGE_LIMIT - 5:  # small buffer since we need to close the code block.
            message_body += "\n```"
            message_list.append(message_body)
            message_body = "```md\n"

        message_body += line + "\n"

    message_body += "\n```"
    message_list.append(message_body)

    message_body += "\n```"
    for message in message_list:
        discord.send_webhook_message(config_loader.DISCORD["webhook_url"], {"content": message})


if __name__ == "__main__":
    logger.info("Connecting to Reddit...")
    reddit = reddit_utils.get_reddit_instance(config_loader.REDDIT["auth"])
    subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])
    check_front_page(subreddit)
    update_traffic(subreddit)
