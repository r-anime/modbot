from datetime import datetime, timezone, timedelta
import sys
import time

import config_loader
from old.menuupdater import SubredditMenuUpdater
from utils import reddit as reddit_utils
from utils.logger import logger

name = "Casual Discussion Fridays"
short_name = "Casual Disc Fridays"
author = "AutoModerator"

# First wait for new thread to go up and update links (standard)
SubredditMenuUpdater(name=name, short_name=short_name, author=author)

# Then the CDF-specific stuff
reddit = reddit_utils.get_reddit_instance(config_loader.REDDIT["auth"])
subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])

# Step 0: get new and old CDF
search_str = f"{name.lower()} author:{author}"
logger.debug(f"Search query: {search_str}")
cdfs = subreddit.search(search_str, sort="new")

while True:
    cdf = next(cdfs)
    created_ts = datetime.fromtimestamp(cdf.created_utc, timezone.utc)
    if created_ts > datetime.now(timezone.utc) - timedelta(days=1):  # today
        new_cdf = cdf
    elif created_ts < datetime.now(timezone.utc) - timedelta(days=6):  # last week
        old_cdf = cdf
        break

logger.debug(f'Found new CDF id {new_cdf.id} "{new_cdf.title}"')
logger.debug(f'Found old CDF id {old_cdf.id} "{old_cdf.title}"')


# Step 1: Notify old CDF that the new CDF is up
notify_comment = old_cdf.reply(f"""
Hello CDF users! Since it is Friday, the new CDF is now live. Please follow
[this link]({new_cdf.permalink}) to move on to the new thread.

[](#heartbot "And don't forget to be nice to new users!")

A quick note: this thread will remain open for one hour so that you can finish
your conversations. Please **do not** use this thread for spamming or other
undesirable behavior. Excessive violations will result in sanctions.
""")
notify_comment.disable_inbox_replies()
notify_comment.mod.distinguish()

# Step 1.5 Sort new CDF by new
logger.debug("Setting new CDF thread sorting to 'new'")
logger.info(f"Posted notify comment {notify_comment.id} in old CDF")
new_cdf.mod.suggested_sort(sort="new")

# Step 2: Lock old CDF
logger.debug("Going to sleep for 3600 seconds...")
sys.stdout.flush()
time.sleep(3600)
logger.debug("Waking up. Locking old CDF")

old_cdf.mod.lock()
logger.info("Old CDF thread has been locked")
last_comment = old_cdf.reply(f"""
This thread has been locked.
We will see you all in the new Casual Discussion Fridays thread,
which you can find [here]({new_cdf.permalink}).

Reminder to keep the new discussion *welcoming* and be mindful of new users.
Don't take the shitpost too far — but have fun!

[](#bot-chan)
""")
last_comment.disable_inbox_replies()
last_comment.mod.distinguish(sticky=True)

logger.debug(f"Last comment {last_comment.id} posted")
logger.info("CDF job complete.")
