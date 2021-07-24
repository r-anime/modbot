"""
Migrates user flairs from old CSS system to new emoji system.
"""

import re
import time

import praw

import config_loader
from utils.logger import logger


# TODO: verified flairs?
CSS_EMOJI = {
    "a-amq": ":AMQ:",
    "a-1milquiz": ":star:",
    "a-WT2020": ":TopWT:",
}

LIST_SITE_TEMPLATES = {
    "mal": {
        "regex": re.compile(r"myanimelist\.net/(profile|animelist|mangalist)/(?P<username>[\w-]+)"),
        "text": "{awards}:MAL:https://myanimelist.net/animelist/{username}",
    },
    "anilist": {
        "regex": re.compile(r"anilist\.co/(user|animelist)/(?P<username>[\w-]+)"),
        "text": "{awards}:ANI:https://anilist.co/user/{username}/animelist",
    },
    "kitsu": {
        "regex": re.compile(r"kitsu\.io/users/(?P<username>[\w-]+)"),
        "text": "{awards}:Kitsu:https://kitsu.io/users/{username}/library",
    },
    "hummingbird": {
        # Note: this does *not* include - as a username character because a lot of old URLs have number-username
        # where either is valid under Kitsu but not both together. Since the number still works, can pull that alone.
        "regex": re.compile(r"hummingbird\.me/users/(?P<username>\w+)"),
        "text": "{awards}:Kitsu:https://kitsu.io/users/{username}/library",
    },
    "ap": {
        "regex": re.compile(r"anime-planet\.com/users/(?P<username>[\w-]+)"),
        "text": "{awards}:AP:https://www.anime-planet.com/users/{username}",
    },
    "anidb": {
        "regex": re.compile(r"anidb\.net/(user/|up)(?P<username>[\w-]+)"),
        "text": "{awards}:AniDB:https://anidb.net/user/{username}/mylist",
    },
    "mal_old": {
        "regex": re.compile(r"(?P<username>[\w-]+)\.myanimelist\.net"),
        "text": "{awards}:MAL:https://myanimelist.net/animelist/{username}",
    },
}


reddit = None
subreddit = None


def migrate_flairs():
    """
    Fetch all users with flairs in the subreddit and convert them to the emoji format.
    """

    global reddit, subreddit

    users_to_update = []
    total_users = 0
    users_with_flair = 0

    while True:
        try:
            logger.info("Connecting to Reddit...")
            reddit = praw.Reddit(**config_loader.REDDIT["auth"])
            subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])
            logger.info("Loading flairs...")
            # Generator will load in batches of 1000 from Reddit, this covers the entire sub.
            for user_flair in subreddit.flair(limit=None):
                new_flair_text = _parse_flair(user_flair)

                if new_flair_text:
                    users_with_flair += 1

                # TODO: add flair template ID for each?
                users_to_update.append({"user": user_flair["user"], "flair_text": new_flair_text})
                # Update users in a batch
                if len(users_to_update) >= 100:
                    # subreddit.flair.update(flair_list=users_to_update)
                    total_users += len(users_to_update)
                    logger.info(f"Updated {len(users_to_update)} users, {total_users} total")
                    users_to_update = []
            if users_to_update:
                # subreddit.flair.update(flair_list=users_to_update)
                total_users += len(users_to_update)
                logger.info(f"Updated {len(users_to_update)} users, {total_users} total")
            logger.info(f"{users_with_flair} users successfully migrated!")
            break
        except Exception:
            delay_time = 30
            logger.exception(f"Encountered an unexpected error, restarting in {delay_time} seconds...")
            time.sleep(delay_time)


def _parse_flair(user_flair):
    user = user_flair["user"]
    current_classes = user_flair["flair_css_class"].split() if user_flair["flair_css_class"] is not None else []
    current_text = user_flair["flair_text"]

    awards_list = [CSS_EMOJI[css_class] for css_class in current_classes if css_class in CSS_EMOJI]
    awards_str = "".join(awards_list)

    new_flair_text = awards_str

    if current_text is None:
        logger.warning(f"{user.name} - Old: {current_classes} {current_text} - {new_flair_text}")
        return new_flair_text

    # For each list site, see if the user's flair text matches.
    for _, template in LIST_SITE_TEMPLATES.items():
        match = template["regex"].search(current_text)
        if not match:
            continue
        site_username = match.groupdict()["username"]
        new_flair_text = template["text"].format(awards=awards_str, username=site_username)
        logger.info(f"{user.name} - Old: {current_classes} {current_text} - {new_flair_text}")
        break
    # No matches because it didn't break above.
    else:
        logger.warning(f"{user.name} - Old: {current_classes} {current_text} - {new_flair_text}")

    return new_flair_text


if __name__ == "__main__":
    migrate_flairs()
