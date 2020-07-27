"""
String templates for messaging users about mod-related activity, from reminders to removal messages.

Uses {name} style for placeholder variables that should be filled by calling .format.

In the long run these should live in the database and be configurable though a UI.
"""

# All messages should have the footer appended to them as part of their definition here.
message_footer = """

*I am a bot, and this action was performed automatically. Please [contact the moderators of this subreddit](/message/compose/?to=/r/anime) if you have any questions or concerns.*"""


flair_reminder_subject = "Your post needs a flair!"
flair_reminder_body = """Hi {username}! You recently submitted [this post]({link}) without a flair. This subreddit requires that all posts be flaired, so please add a flair to your post. If a flair is not added within {removal_age_minutes} minutes from posting, it will be removed and you will have to resubmit it before it will show up in the community.

On old desktop Reddit, flairs can be added by clicking the "flair" button underneath the post. On mobile and other platforms, flairs can often be set through a dropdown menu when viewing the post.

If you're not sure which flair to use, please see [this guide](/r/anime/wiki/rules#wiki_flair_your_posts).""" + message_footer

# All removal messages should have username and link placeholders.
removal_message_subject = "Your post has been removed"

# Also has removal_age_minutes
removal_unflaired = """Hi {username}! Because [this post]({link}) was not flaired within {removal_age_minutes} minutes, it has been removed. Please resubmit your post and flair it within that time.""" + message_footer

removal_not_text = """Hi {username}! [This post]({link}) was removed because the type of content you posted is only allowed as a self (text) post.

Please provide some information on the context of your post or question to help other users come up with relevant replies and encourage discussion.""" + message_footer

removal_single_image_news = """Hi {username}! [This post]({link}) was removed because news and official media posts must be sourced from the original or trusted sources. Please post a link to the source or a text post instead of a single image.""" + message_footer

removal_single_image = """Hi {username}! [This post]({link}) was removed because the format you used (single image or clip) is not allowed for this kind of post. Please check our [restricted content rules](/r/anime/wiki/rules#wiki_restricted_content) for more information.""" + message_footer

removal_not_text_fanart = """Hi {username}! [This post]({link}) was removed because fanart is only allowed as a self (text) post.

You can embed images in a text post in some Reddit apps or upload your fanart to another site (such as Imgur) and link to it in your post.

To read the full fanart rules on /r/anime, check [our rules page](https://www.reddit.com/r/anime/wiki/rules#wiki_fanart).""" + message_footer

removal_not_text_help = """Hi {username}! [This post]({link}) was removed as single image posts are generally not allowed. Since it looks like you need help with an image, the following may provide the answer you seek:

- For **source of fanart**, try [SauceNAO](https://saucenao.com/)
- For **source of anime screenshots**, try [trace.moe](https://trace.moe/)
- For **watch orders**, try [our Watch Order wiki](https://www.reddit.com/r/anime/wiki/watch_order)
- For other questions, check if they are answered in the [FAAQ](https://www.reddit.com/r/anime/wiki/faaq)

Do none of these answer your question? If that's the case, you can resubmit your question as a **text post** instead of an image to ask help from the /r/anime community.""" + message_footer

removal_meme = """Hi {username}! [This post]({link}) was removed as memes are not allowed on /r/anime. We have implemented this flair to catch people who post memes in order to make removals quicker for us. Sorry for this inconvenience.""" + message_footer
