FOOTER = "\n\n*I am a bot, and this action was performed automatically. Please [contact the moderators of this subreddit](/message/compose/?to=/r/anime) if you have any questions or concerns.*"

REMOVAL_SUBJECT = "Your post has been removed"

FLAIR_REMINDER_SUBJECT = "Your post needs a flair!"
FLAIR_REMINDER_MESSAGE = (
    """Hi {username}! You recently submitted [this post]({link}) without a flair. This subreddit requires that all posts be flaired, so please add a flair to your post. If a flair is not added within {removal_age_minutes} minutes from posting, it will be removed and you will have to resubmit it before it will show up in the community.

On old desktop Reddit, flairs can be added by clicking the "flair" button underneath the post. On mobile and other platforms, flairs can often be set through a dropdown menu when viewing the post.

If you're not sure which flair to use, please see [this guide](/r/anime/wiki/rules#wiki_flairs)."""
    + FOOTER
)

FLAIR_UNFLAIRED_REMOVAL_MESSAGE = (
    """Hi {username}! Because [this post]({link}) was not flaired within {removal_age_minutes} minutes, it has been removed. Please resubmit your post and flair it within that time."""
    + FOOTER
)
FLAIR_FREQUENCY_REMOVAL_MESSAGE = (
    """Hi {username}! [This post]({link}) was removed because you may only submit {frequency_limit} [{flair_name}] post(s) per {frequency_days}.

Your other [{flair_name}] post(s):\n\n*{post_list}"""
    + FOOTER
)
