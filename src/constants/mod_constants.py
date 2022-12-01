"""
Static values about mods and mod actions that generally shouldn't need to change.
"""

from enum import Enum

BOTS = ["AnimeMod", "AutoModerator", "BotDefense"]

ADMINS = ["reddit", "Reddit Legal", "Anti-Evil Operations"]


class ModActionEnum(Enum):
    approve_post = "approvelink"
    remove_post = "removelink"
    spam_post = "spamlink"


# There are more types of actions that can be set here, currently used in selecting distinct posts/comments/users.
MOD_ACTIONS_POSTS = [
    "approvelink",
    "editflair",
    "removelink",
    "spamlink",
    "spoiler",
    "unspoiler",
]

# Actions denoting a change in post status that warrants an update in the post feed.
MOD_ACTIONS_POST_FEED_UPDATE = [
    "approvelink",
    "removelink",
    "spamlink",
    "editflair",
    "spoiler",
    "unspoiler",
    "marknsfw",
]

MOD_ACTIONS_COMMENTS = [
    "approvecomment",
    "distinguish",  # Posts can be distinguished too but we aren't counting those right now.
    "removecomment",
    "spamcomment",
]

MOD_ACTIONS_USERS = ["acceptmoderatorinvite", "banuser", "invitemoderator", "removemoderator", "unbanuser"]

# List of actions that should always trigger a notification.
MOD_ACTIONS_ALWAYS_NOTIFY = ["acceptmoderatorinvite", "invitemoderator", "removemoderator"]
