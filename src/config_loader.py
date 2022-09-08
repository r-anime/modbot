"""
Loads environment values as application config, all config should be routed through here.
"""

import os

from dotenv import load_dotenv

# Loads .env file's settings in when outside of container
load_dotenv()


DEBUG_MODE = (os.environ.get("DEBUG_MODE", "False").lower() in ["true", "t", "1", "yes", "y"],)  # load as bool

REDDIT = {
    "subreddit": os.environ.get("SUBREDDIT_NAME_TO_ACT_ON"),
    "auth": {
        "client_id": os.environ.get("REDDIT_CLIENT_ID"),
        "client_secret": os.environ.get("REDDIT_SECRET"),
        "user_agent": os.environ.get("REDDIT_USER_AGENT"),
        "username": os.environ.get("REDDIT_USERNAME"),
        "password": os.environ.get("REDDIT_USER_PASSWORD"),
        "totp_secret": os.environ.get("REDDIT_TOTP_SECRET"),
    },
}

DB_CONNECTION = (
    f'postgresql+psycopg2://{os.environ.get("DB_USER")}:{os.environ.get("DB_PASSWORD")}@'
    f'{os.environ.get("DB_HOST")}:{os.environ.get("DB_PORT")}/{os.environ.get("DB_NAME")}'
)

REDIS_CONNECTION = f'redis://{os.environ.get("REDIS_HOST")}:{os.environ.get("REDIS_PORT")}/0'

DISCORD = {
    "enabled": os.environ.get("DISCORD_ENABLED", "False").lower() in ["true", "t", "1", "yes", "y"],  # load as bool
    "webhook_url": os.environ.get("DISCORD_WEBHOOK_URL"),
    "post_webhook_url": os.environ.get("DISCORD_POST_WEBHOOK_URL", os.environ.get("DISCORD_WEBHOOK_URL")),
}

LOGGING = {
    "file_path": os.environ.get("LOG_FILE_PATH"),
    "log_level_file": os.environ.get("LOG_LEVEL_FILE"),
    "log_level_console": os.environ.get("LOG_LEVEL_CONSOLE"),
}
