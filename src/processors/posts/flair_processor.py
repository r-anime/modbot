"""
Post Processor

Imports and registers individual post handlers
"""

import datetime

import config_loader
from constants.flair_constants import Flair
from data import post_data
from services import post_service
from utils import templates
from utils.celery_utils import celery_app
from utils.reddit import reddit, make_permalink
from utils.logger import logger


RULES = {
    "removal_age_minutes": 15,
    "clip_frequency_limit": 2,
    "clip_frequency_days": 31,
    "video_edit_frequency_limit": 2,
    "video_edit_frequency_days": 31,
    "fanart_frequency_limit": 1,
    "fanart_frequency_days": 7,
    "oc_fanart_frequency_limit": 1,
    "oc_fanart_frequency_days": 7,
}


@celery_app.task
def check_flair(post_dict: dict, refetch_post: bool = False):
    post = post_data.PostModel(post_dict)
    if refetch_post:
        submission = reddit.submission(id=post.id36)
        post = post_service.update_post(post, submission)
    logger.info(f"Checking flair for {post}")

    if not post.flair_id:
        post_time = datetime.datetime.fromisoformat(post.created_time)
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        removal_time = post_time + datetime.timedelta(minutes=RULES["removal_age_minutes"])
        if now < removal_time:
            _send_flair_reminder(post)
            check_flair.apply_async((post_dict, True), eta=removal_time)
        else:
            _remove_unflaired_post(post)
        return

    validation_function = _flair_check_mapper.get(post.flair_id)
    if validation_function:
        validation_function(post)


def _remove_or_report_post(post: post_data.PostModel, removal_message: str, mod_note: str = "Modbot flair check"):
    """
    Will remove a post if it hasn't been approved, report otherwise.
    """

    submission = reddit.submission(id=post.id36)
    # In cases where it's specifically been approved by a mod, just report it. Repeated reports don't show up.
    if submission.mod.approved:
        submission.report(mod_note)
        logger.info(f"Reported previously approved post {post.id36} with reason {mod_note}")
    else:
        if not config_loader.DEBUG_MODE:
            submission.mod.remove(mod_note=mod_note)
            submission.author.message(templates.REMOVAL_SUBJECT, removal_message)
        logger.info(f"Removed unflaired post {post.id36} with reason {mod_note}")


def _send_flair_reminder(post: post_data.PostModel):
    author = reddit.redditor(post.author)
    reminder_message = templates.FLAIR_REMINDER_MESSAGE.format(
        removal_age_minutes=RULES["removal_age_minutes"],
        username=post.author,
        link=make_permalink(post),
    )
    if not config_loader.DEBUG_MODE:
        author.message(templates.FLAIR_REMINDER_SUBJECT, reminder_message)
    logger.info(f"Sent flair reminder message to {post.author} for {post.id36}")


def _remove_unflaired_post(post: post_data.PostModel):
    submission = reddit.submission(id=post.id36)
    if not config_loader.DEBUG_MODE:
        submission.mod.remove(mod_note="Modbot: Missing flair")
        removal_message = templates.FLAIR_UNFLAIRED_REMOVAL_MESSAGE.format(
            removal_age_minutes=RULES["removal_age_minutes"],
            username=post.author,
            link=make_permalink(post),
        )
        submission.author.message(templates.REMOVAL_SUBJECT, removal_message)
    logger.info(f"Removed unflaired post {post.id36}")


def _check_clip(post: post_data.PostModel):
    """
    Clip rules:
    - two per user per month (31 days)
    """

    frequency_limit = RULES["clip_frequency_limit"]
    frequency_days = RULES["clip_frequency_days"]

    _check_post_frequency(post, Flair.Clip, frequency_limit, frequency_days)


def _check_video_edit(post: post_data.PostModel):
    """
    Video Edit rules:
    - two per user per month (31 days)
    """

    frequency_limit = RULES["video_edit_frequency_limit"]
    frequency_days = RULES["video_edit_frequency_days"]

    _check_post_frequency(post, Flair.VideoEdit, frequency_limit, frequency_days)


def _check_fanart(post: post_data.PostModel):
    """
    Fanart rules:
    - one per user per week (7 days)
    """

    frequency_limit = RULES["fanart_frequency_limit"]
    frequency_days = RULES["fanart_frequency_days"]

    _check_post_frequency(post, Flair.Fanart, frequency_limit, frequency_days)


def _check_oc_fanart(post: post_data.PostModel):
    """
    OC Fanart rules:
    - one per user per week (7 days)
    """

    frequency_limit = RULES["oc_fanart_frequency_limit"]
    frequency_days = RULES["oc_fanart_frequency_days"]

    _check_post_frequency(post, Flair.OCFanart, frequency_limit, frequency_days)


def _check_post_frequency(post: post_data.PostModel, flair: Flair, frequency_limit: int, frequency_days: int):
    """Checks for other posts with the same flair by the same user, removes if over the limit."""

    post_time = datetime.datetime.fromisoformat(post.created_time)
    date_check_start = post_time - datetime.timedelta(days=frequency_days)
    user_posts = post_service.get_posts_by_username(
        post.author, start_date=date_check_start.isoformat(), end_date=post.created_time
    )

    non_removed_posts = []
    for user_post in user_posts:
        if user_post.flair_id != flair.id:
            continue
        if user_post.removed:
            continue
        if user_post.id == post.id:
            continue
        non_removed_posts.append(user_post)

    # Check if previously found posts with this flair are *below* the limit as it's not counting this current one.
    if len(non_removed_posts) < frequency_limit:
        return

    removal_message = templates.FLAIR_FREQUENCY_REMOVAL_MESSAGE.format(
        username=post.author,
        link=make_permalink(post),
        flair=flair.text,
        frequency_limit=frequency_limit,
        frequency_days=frequency_days,
        post_list="\n*".join(make_permalink(other_post) for other_post in non_removed_posts),
    )
    _remove_or_report_post(post, removal_message, f"Modbot: {flair.text} frequency")


_flair_check_mapper = {
    Flair.Clip.id: _check_clip,
    Flair.VideoEdit.id: _check_video_edit,
    Flair.OCFanart.id: _check_oc_fanart,
    Flair.Fanart.id: _check_fanart,
}
