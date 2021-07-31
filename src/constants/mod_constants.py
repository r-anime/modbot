"""
Static values about mods and mod actions that generally shouldn't need to change.
"""

BOTS = ["AnimeMod", "AutoModerator"]

ADMINS = ["reddit", "Reddit Legal", "Anti-Evil Operations"]

# There are more types of actions that can be set here, currently used in selecting distinct posts/comments/users.
MOD_ACTIONS_POSTS = [
    "approvelink",
    "editflair",
    "removelink",
    "spamlink",
    "spoiler",
    "unspoiler",
]

MOD_ACTIONS_COMMENTS = [
    "approvecomment",
    "distinguish",  # Posts can be distinguished too but we aren't counting those right now.
    "removecomment",
    "spamcomment",
]

MOD_ACTIONS_USERS = [
    "acceptmoderatorinvite",
    "banuser",
    "invitemoderator",
    "removemoderator",
    "unbanuser"
]
