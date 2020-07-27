from datetime import datetime, timezone, timedelta

from celery import Celery

import config
from constants import Flair
from data import message_templates
from data.db import Session, session_scope
from data.models import PostModel, UserModel
from utils import reddit as reddit_utils
from utils.logger import logger

app = Celery("post_processor", broker=config.AMQP["connection"])
reddit = reddit_utils.get_instance()
session = Session()

UNFLAIRED_REMOVAL_TIME_MINUTES = 15


@app.task
def new_post_job(submission_id):
    submission = reddit.submission(id=submission_id)

    # If post has been deleted or removed already, mark as such and don't do anything else.
    if submission.author is None or submission.banned_by is not None:
        _mark_deleted_or_removed_post(submission)
        return

    # Set up flair check for 3 minutes after submission to give time for the user to set/fix it.
    post_creation_time = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
    validate_flair_job.apply_async((submission.id,), eta=post_creation_time + timedelta(minutes=3))


@app.task
def validate_flair_job(submission_id):
    submission = reddit.submission(id=submission_id)

    # If post has been deleted or removed already, mark as such and don't do anything else.
    if submission.author is None or submission.banned_by is not None:
        _mark_deleted_or_removed_post(submission)
        return

    # Do nothing for mod-distinguished posts.
    if submission.distinguished:
        return

    if submission.link_flair_text is None:
        logger.info(f"submission {submission.id} has no flair, reminding user and checking again later")
        reddit_utils.message_user(
            submission.author.name,
            message_templates.flair_reminder_subject,
            message_templates.flair_reminder_body.format(
                username=submission.author.name,
                link=submission.shortlink,
                removal_age_minutes=UNFLAIRED_REMOVAL_TIME_MINUTES
            )
        )
        post_creation_time = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
        unflaired_removal_job.apply_async(
            args=(submission.id,),
            eta=post_creation_time + timedelta(minutes=UNFLAIRED_REMOVAL_TIME_MINUTES))
    else:
        # For cases where the post has been manually approved by a mod, just report instead of removing.
        if submission.approved_by is None:
            _validate_flair(submission)
        else:
            _validate_flair(submission, report_only_reason="Post type not allowed for selected flair")


@app.task
def unflaired_removal_job(submission_id):
    submission = reddit.submission(id=submission_id)

    # If post has been deleted or removed already, mark as such and don't do anything else.
    if submission.author is None or submission.banned_by is not None:
        _mark_deleted_or_removed_post(submission)
        return

    if submission.link_flair_text is None:
        logger.info(f"submission {submission.id} has no flair after {UNFLAIRED_REMOVAL_TIME_MINUTES} minutes")

        # For cases where a post has been manually approved by a mod, report instead of removing.
        if submission.approved_by is not None:
            submission.report("Approved post missing flair, please select one")
            return

        _remove_post_and_message_user(
            submission,
            message_templates.removal_unflaired.format(
                username=submission.author.name,
                link=submission.shortlink,
                removal_age_minutes=UNFLAIRED_REMOVAL_TIME_MINUTES
            )
        )


def _validate_flair(submission, report_only_reason=None):
    """
    Runs checks on a post based on its flair.

    If no flair is set, does nothing.

    If the submission breaks the rules for the select flair, removes the post and messages the user unless
    report_only_reason is set. Uses a single report reason instead of one matching each kind of message sent
    to the user.

    These checks are largely taken from flairbot.

    :param submission: praw SubmissionModel instance
    :param report_only_reason: string, if specified will report the post rather than remove it
    :return: None
    """

    if submission.link_flair_text is None:
        return

    flair = Flair.get_flair_by_id(submission.link_flair_template_id)
    username = submission.author.name
    link = submission.shortlink

    if flair == Flair.Meme:
        _remove_post_and_message_user(
            submission,
            message_templates.removal_meme.format(username=username, link=submission.shortlink),
            report_only_reason
        )
        return

    if not reddit_utils.is_text(submission):
        if flair in (Flair.Discussion, Flair.Rewatch, Flair.Recommendation, Flair.Cosplay):
            _remove_post_and_message_user(
                submission,
                message_templates.removal_not_text.format(username=username, link=link),
                report_only_reason
            )
        if flair in (Flair.OCFanart, Flair.Fanart):
            _remove_post_and_message_user(
                submission,
                message_templates.removal_not_text_fanart.format(username=username, link=link),
                report_only_reason
            )

    if reddit_utils.is_image(submission):
        if flair == Flair.News:
            _remove_post_and_message_user(
                submission,
                message_templates.removal_single_image_news.format(username=username, link=link),
                report_only_reason
            )
        if flair == Flair.Help:
            _remove_post_and_message_user(
                submission,
                message_templates.removal_not_text_help.format(username=username, link=link),
                report_only_reason
            )


def _remove_post_and_message_user(submission, message_body, report_only_reason=None):
    if report_only_reason is not None:
        logger.info(f"reporting submission {submission.id}, reason {report_only_reason}")
        submission.report(report_only_reason)
        return

    logger.info(f"removing submission {submission.id}")
    if not config.DEBUG_MODE:
        submission.mod.remove()
    reddit_utils.message_user(submission.author.name, message_templates.removal_message_subject, message_body)


def _mark_deleted_or_removed_post(submission, post_model=None):

    # If post has been deleted or removed already, mark as such and don't do anything else.
    if submission.author is None or submission.banned_by is not None:
        # If a model wasn't passed in, retrieve it.
        if not post_model:
            post_model = session.query(PostModel).filter_by(id=submission.id).one_or_none()
            # If we *still* don't have a model, don't do anything.
            if not post_model:
                return

        if submission.author is None:
            post_model.is_deleted = True

        if submission.banned_by is not None:
            post_model.is_removed = True

        session.commit()


def _insert_post(submission):
    """
    Adds a post to the database for cases where it doesn't yet exist.
    :param submission: praw SubmissionModel object
    :return: PostModel object
    """

    with session_scope() as insert_session:
        username_lower = submission.author.name.lower()
        user_model = insert_session.query(UserModel).filter_by(name=username_lower).one_or_none()
        if not user_model:
            user_model = UserModel(
                name=username_lower,
                name_formatted=submission.author.name
            )
            insert_session.add(user_model)

        post_model = PostModel(
            id=submission.id,
            title=submission.title,
            author_psk=user_model.psk,
            created_time=datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
            is_deleted=submission.author is None,
            is_removed=submission.banned_by is not None)
        insert_session.add(post_model)

    return post_model
