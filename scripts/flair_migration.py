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
    "a-1milquiz": ":STAR:",
    "a-WT2020": ":TWT:",
}

_counters = {"MAL": 0, "AniList": 0, "Kitsu": 0, "Anime-Planet": 0, "AniDB": 0}

LIST_SITE_TEMPLATES = {
    "mal": {
        "regex": re.compile(r"myanimelist\.net/(profile|animelist|mangalist)/(?P<username>[\w-]+)"),
        "text": "{awards}:MAL:https://myanimelist.net/profile/{username}",
        "counter_key": "MAL",
        "template_id": "6b1b36f0-f1e1-11eb-a927-e2ecbed958f2",
    },
    "anilist": {
        "regex": re.compile(r"anilist\.co/(user|animelist)/(?P<username>[\w-]+)"),
        "text": "{awards}:AL:https://anilist.co/user/{username}",
        "counter_key": "AniList",
        "template_id": "2079d5d4-f263-11eb-be34-468722fad2fe",
    },
    "kitsu": {
        "regex": re.compile(r"kitsu\.io/users/(?P<username>[\w-]+)"),
        "text": "{awards}:K:https://kitsu.io/users/{username}",
        "counter_key": "Kitsu",
        "template_id": "13f64ad6-f263-11eb-8f8c-8a434363e2e3",
    },
    "hummingbird": {
        # Note: this does *not* include - as a username character because a lot of old URLs have number-username
        # where either is valid under Kitsu but not both together. Since the number still works, can pull that alone.
        "regex": re.compile(r"hummingbird\.me/users/(?P<username>\w+)"),
        "text": "{awards}:K:https://kitsu.io/users/{username}",
        "counter_key": "Kitsu",
        "template_id": "13f64ad6-f263-11eb-8f8c-8a434363e2e3",
    },
    "ap": {
        "regex": re.compile(r"anime-planet\.com/users/(?P<username>[\w-]+)"),
        "text": "{awards}:AP:https://www.anime-planet.com/users/{username}",
        "counter_key": "Anime-Planet",
        "template_id": "0b3ddca6-f263-11eb-8e80-9eff306c8673",
    },
    "anidb": {
        "regex": re.compile(r"anidb\.net/(user/|up)(?P<username>[\w-]+)"),
        "text": "{awards}:ADB:https://anidb.net/user/{username}",
        "counter_key": "AniDB",
        "template_id": "2c0afaae-f263-11eb-8288-eabdc06583fc",
    },
    "mal_old": {
        "regex": re.compile(r"(?P<username>[\w-]+)\.myanimelist\.net"),
        "text": "{awards}:MAL:https://myanimelist.net/animelist/{username}",
        "counter_key": "MAL",
        "template_id": "6b1b36f0-f1e1-11eb-a927-e2ecbed958f2",
    },
}

verified_users = []

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
                new_flair_text, template_id = _parse_flair(user_flair)
                if user_flair["flair_css_class"] is not None and user_flair["flair_css_class"].startswith("v-"):
                    verified_users.append(user_flair["user"].name)

                if new_flair_text:
                    users_with_flair += 1

                users_to_update.append(
                    {"user": user_flair["user"], "flair_text": new_flair_text, "flair_template_id": template_id}
                )
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
            logger.info(f"{users_with_flair} / {total_users} users successfully migrated!")
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
    new_template_id = None

    if current_text is None:
        logger.warning(f"{user.name} - Old: {current_classes} {current_text} - {new_flair_text}")
        return new_flair_text, new_template_id

    # For each list site, see if the user's flair text matches.
    for _, template in LIST_SITE_TEMPLATES.items():
        match = template["regex"].search(current_text)
        if not match:
            continue
        site_username = match.groupdict()["username"]
        new_flair_text = template["text"].format(awards=awards_str, username=site_username)
        new_template_id = template["template_id"]
        _counters[template["counter_key"]] += 1
        logger.info(f"{user.name} - Old: {current_classes} {current_text} - {new_flair_text}")
        break
    # No matches because it didn't break above.
    else:
        logger.warning(f"{user.name} - Old: {current_classes} {current_text} - {new_flair_text}")

    return new_flair_text, new_template_id


if __name__ == "__main__":
    migrate_flairs()
    logger.info(f"Verified users: {verified_users}")
    for key, value in _counters.items():
        logger.info(f"{key} total successful: {value}")
