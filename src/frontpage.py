"""
Gathers a snapshot of the front page of a subreddit, designed to be run at the top of each hour (currently via cron).
Saves posts and their rank in a database to provide changes from the previous hour and how long a post has been there.
"""

from collections import Counter
from datetime import datetime, timezone, timedelta

import praw

import config
from utils import discord, reddit as reddit_utils
from utils.logger import logger
from data.db import session_scope
from data.models import PostModel, SnapshotModel, SnapshotFrontpageModel


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

    line += " {:>24}".format(f"[{submission.link_flair_text}]({submission.id})")

    line += f" <{submission.author.name}>"

    line += f" <{reddit_utils.slug(submission)}>"

    return line


def check_front_page(subreddit):
    """Gathers information about the front page, saves it to a database, and sends a summary to Discord."""

    # Grab the date/hour that this is for. Less accurate the later in the hour this is executed.
    current_datetime = datetime.utcnow()
    previous_time = current_datetime - timedelta(hours=1)

    snapshot = SnapshotModel()
    snapshot.datetime = current_datetime
    snapshot.date = current_datetime.date()
    snapshot.hour = current_datetime.hour
    snapshot.subscribers = subreddit.subscribers

    # Index, keeps track of front page ranking.
    post_rank = 0

    # Get more than we need for a few different reasons:
    # 1. The first one or two items may be stickied and should be ignored.
    # 2. To track what position something is in if it fell off the front page.
    hot_list = subreddit.hot(limit=75)
    lines = []
    flairs = Counter()

    with session_scope() as session:
        session.add(snapshot)

        for post_praw in hot_list:
            if post_praw.stickied:
                continue
            post_rank += 1

            # Get post if it exists in the database, create it otherwise.
            post_model = session.query(PostModel).filter(PostModel.id == post_praw.id).one_or_none()
            if not post_model:
                post_model = PostModel(
                    id=post_praw.id,
                    title=post_praw.title,
                    created_time=datetime.fromtimestamp(post_praw.created_utc, tz=timezone.utc))
                session.add(post_model)
            post_model.flair = post_praw.link_flair_text  # flair may have changed, so update it

            # Add rest of relevant data to the join table.
            frontpage = SnapshotFrontpageModel(
                rank=post_rank,
                score=post_praw.score,
                post=post_model,
                snapshot=snapshot)
            session.add(frontpage)
            snapshot.frontpage.append(frontpage)

            # Once we have 25 we don't need to do more calculations for the summary, but keep recording in the database
            # for the top 50 to track decay over time and possible later returns to the front page.
            if post_rank >= 50:
                break
            elif post_rank > 25:
                continue

            # For reporting to Discord, get where the post was previously ranked (if at all).
            previous_frontpage = session.query(SnapshotFrontpageModel)\
                .join(SnapshotModel)\
                .filter(SnapshotModel.hour == previous_time.hour, SnapshotModel.date == previous_time.date())\
                .filter(SnapshotFrontpageModel.post_psk == post_model.psk)\
                .one_or_none()

            rank_change = None
            if previous_frontpage:
                rank_change = previous_frontpage.rank - post_rank

            # How many hours the post has been on the front page in total.
            total_hours = session.query(SnapshotFrontpageModel)\
                .filter(SnapshotFrontpageModel.post_psk == post_model.psk, SnapshotFrontpageModel.rank < 26)\
                .count()

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
        discord.send_webhook_message({"content": message})


if __name__ == "__main__":
    logger.info("Connecting to Reddit...")
    reddit = praw.Reddit(**config.REDDIT["auth"])
    subreddit = reddit.subreddit(config.REDDIT["subreddit"])
    check_front_page(subreddit)
