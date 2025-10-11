"""
Monitors a subreddit and saves all mod actions to the database.
Will send a notification to Discord if the action was taken by someone not previously registered as a mod.
"""

import argparse
from datetime import datetime, timedelta, timezone
import time
from typing import Optional

from praw.models.mod_action import ModAction

import config_loader
from constants import mod_constants
from data.mod_action_data import ModActionModel
from services import base_data_service, comment_service, mod_action_service, post_service, user_service
from services.rabbit_service import RabbitService
from utils import discord, reddit as reddit_utils
from utils.logger import logger


# Cache a list of moderator usernames so we can tell if an action is taken by admins.
active_mods = []


def parse_mod_action(mod_action: ModAction, reddit, subreddit, rabbit: RabbitService):
    """
    Process a single PRAW ModAction. Assumes that reddit and subreddit are already instantiated by
    one of the two entry points (monitor_stream or load_archive).
    """

    def _format_action_embed_field(mod_action_model: ModActionModel = None) -> Optional[dict]:
        """By default use the parent mod_action, use provided mod_action_model if provided."""

        if mod_action_model:
            created_timestamp = int(mod_action_model.created_time.timestamp())
            mod_name = mod_action_model.mod
            details = mod_action_model.details
            action = mod_action_model.action
        else:
            created_timestamp = int(mod_action.created_utc)
            mod_name = mod_action.mod.name
            details = mod_action.details
            action = mod_action.action

        field = {"inline": True, "value": f"<t:{created_timestamp}:t>"}

        if mod_name in ("AutoModerator", "reddit"):
            field["value"] = details

        if action == mod_constants.ModActionEnum.approve_post.value:
            field["name"] = f"Approved By {mod_name}"
        elif action == mod_constants.ModActionEnum.remove_post.value:
            field["name"] = f"Removed By {mod_name}"
        elif action == mod_constants.ModActionEnum.spam_post.value:
            field["name"] = f"Spammed By {mod_name}"
        else:
            return None

        return field

    # Check if we've already processed this mod action, do nothing if so.
    mod_action_id = mod_action.id.replace("ModAction_", "")
    if mod_action_service.get_mod_action_by_id(mod_action_id):
        logger.debug(f"Already processed, skipping mod action {mod_action_id}")
        return

    logger.info(
        f"Processing mod action {mod_action_id}: {mod_action.mod.name} - "
        f"{mod_action.action} - {mod_action.target_fullname}"
    )

    # If there's an action by an unknown moderator or admin, make a note of it and check to see
    # if they should be added to the mod list.
    send_notification = False
    if mod_action.action in mod_constants.MOD_ACTIONS_ALWAYS_NOTIFY:
        send_notification = True

    if mod_action.action == "editsettings" and mod_action.details not in (
        "description",
        "del_image",
        "upload_image",
        "header_title",
    ):
        send_notification = True

    if mod_action.mod.name not in active_mods:
        # Add them to the database if necessary.
        mod_user = user_service.get_user(mod_action.mod.name)
        if not mod_user:
            mod_user = user_service.add_user(mod_action.mod)

        # We'd normally send a notification for all actions from non-mods, but temporary mutes expiring
        # always come from reddit and we don't really care about those.
        # Similarly, crowd control removals as those are filtered to the mod queue.
        if not (
            (mod_action.mod.name == "reddit" and mod_action.action == "unmuteuser")
            or (
                mod_action.mod.name == "reddit"
                and mod_action.action in ("removecomment", "removelink")
                and mod_action.details == "Crowd Control"
            )
        ):
            send_notification = True

        # For non-admin cases, check to see if they're a [new] mod of the subreddit and refresh the list if so.
        if mod_action.mod not in ("Anti-Evil Operations", "reddit"):
            logger.info(f"Unknown mod found: {mod_action.mod.name}")
            if mod_user.username in subreddit.moderator():
                logger.debug(f"Updating mod status for {mod_user}")
                mod_user.moderator = True
                base_data_service.update(mod_user)
                get_moderators()

    # See if the user targeted by this action exists in the system, add them if not.
    # Bans and similar user-focused actions independent of posts/comments will also have
    # a target_fullname value (t2_...) but won't be necessary to check after this.
    if mod_action.target_author:
        user = user_service.get_user(mod_action.target_author)
        if not user:
            logger.debug(f"Saving user {mod_action.target_author}")
            user = user_service.add_user(reddit.redditor(name=mod_action.target_author))

        # For bans and unbans, update the user in the database.
        if mod_action.action == "banuser":
            # Weirdly this returns a ListingGenerator so we have to iterate over it; there should only be one though.
            # If the user isn't banned, the loop won't execute.
            for ban_user in subreddit.banned(redditor=user.username):
                # Permanent if days_left is None
                if ban_user.days_left is None:
                    user.banned_until = "infinity"
                # days_left will show 0 if they were banned for 1 day a few seconds ago; it seems like it rounds down
                # based on the time of the ban occurring, so we can safely assume that even if the ban happened
                # a few seconds before getting to this point, we should add an extra day onto the reported number.
                else:
                    ban_start = datetime.fromtimestamp(mod_action.created_utc, tz=timezone.utc)
                    user.banned_until = ban_start + timedelta(days=ban_user.days_left + 1)
                break
            base_data_service.update(user)
        elif mod_action.action == "unbanuser":
            user.banned_until = None
            base_data_service.update(user)
        elif mod_action.action == "removemoderator":
            logger.debug(f"Updating mod status for {user}")
            user.moderator = False
            base_data_service.update(user)
            get_moderators()

    # See if the post targeted by this action exists in the system, add it if not.
    if mod_action.target_fullname and mod_action.target_fullname.startswith("t3_"):
        post_id = mod_action.target_fullname.split("_")[1]
        post = post_service.get_post_by_id(post_id)
        reddit_post = reddit.submission(id=post_id)

        # Add or update post as necessary.
        if not post:
            logger.debug(f"Saving post {post_id}")
            post = post_service.add_post(reddit_post)
        else:
            post = post_service.update_post(post, reddit_post)

        # Send post to the feed if it hasn't been yet or if it needs an update.
        if (
            mod_action.action in mod_constants.MOD_ACTIONS_POST_FEED_UPDATE and post.discord_message_id
        ) or not post.sent_to_feed:
            discord_embed = post_service.format_post_embed(post)

            # For cases where this action isn't removing/approving we want to grab the last action that *was*
            # to appropriately show in the feed.
            action_list = [
                mod_constants.ModActionEnum.approve_post.value,
                mod_constants.ModActionEnum.remove_post.value,
                mod_constants.ModActionEnum.spam_post.value,
            ]
            if mod_action.action in action_list:
                previous_action = None
            else:
                previous_action = mod_action_service.get_most_recent_approve_remove_by_post(post)

            action_field = _format_action_embed_field(previous_action)
            if action_field:
                discord_embed["fields"].append(action_field)

            if not post.sent_to_feed:
                discord_message_id = discord.send_webhook_message(
                    config_loader.DISCORD["post_webhook_url"], {"embeds": [discord_embed]}, return_message_id=True
                )
                if discord_message_id:
                    post.sent_to_feed = True
                    post.discord_message_id = discord_message_id
            else:
                discord.update_webhook_message(
                    config_loader.DISCORD["post_webhook_url"], post.discord_message_id, {"embeds": [discord_embed]}
                )

        # If the user deleted their text post, the mod action still has the post body that we can save in place.
        if post.deleted and post.body == "[deleted]" and post.body != mod_action.target_body:
            post.body = mod_action.target_body

        base_data_service.update(post)

    # See if the comment targeted by this action *and its post* exist in the system, add either if not.
    if mod_action.target_fullname and mod_action.target_fullname.startswith("t1_"):
        comment_id = mod_action.target_fullname.split("_")[1]
        comment = comment_service.get_comment_by_id(comment_id)
        reddit_comment = reddit.comment(id=comment_id)

        if not comment:
            # Post needs to exist before we can add a comment for it, start with that.
            post = post_service.get_post_by_id(reddit_comment.submission.id)

            if not post:
                post_service.add_post(reddit_comment.submission)

            # Since all comments will reference a parent if it exists, add all parent comments first.
            logger.debug(f"Saving parent comments of {comment_id}")
            comment_service.add_comment_parent_tree(reddit, reddit_comment)
            logger.debug(f"Saving comment {comment_id}")
            comment = comment_service.add_comment(reddit_comment)
        else:
            # Update our record of the comment if necessary.
            comment = comment_service.update_comment(comment, reddit_comment)

        # If the user deleted their comment, the mod action still has the body that we can save in place.
        if comment.deleted and comment.body != mod_action.target_body:
            comment.body = mod_action.target_body
            base_data_service.update(comment)

    logger.debug(f"Saving mod action {mod_action_id}")
    mod_action_db = mod_action_service.add_mod_action(mod_action)
    rabbit.publish_mod_action(mod_action, mod_action_db)

    if send_notification:
        send_discord_message(mod_action_db)


def send_discord_message(mod_action: ModActionModel):
    logger.info(f"Sending a message to Discord for {mod_action}")

    embed_json = {
        "author": {
            "name": f"Mod Log - /u/{mod_action.mod}",
        },
        "title": f"{mod_action.mod}: {mod_action.action}",
        "timestamp": mod_action.created_time.isoformat(),
        "fields": [],
        "color": 0xCC0000,
    }

    # Add a URL if there's a specific thing we can focus on, also update title if possible.
    target = None
    if mod_action.target_comment_id:
        target = comment_service.get_comment_by_id(mod_action.target_comment_id)
        embed_json["title"] = f"{mod_action.mod}: {mod_action.action} by {mod_action.target_user}"
    elif mod_action.target_post_id:
        target = post_service.get_post_by_id(mod_action.target_post_id)
        title = discord.escape_formatting(
            f"{mod_action.mod}: {mod_action.action} - {target.title} by {mod_action.target_user}"
        )
        embed_json["title"] = title[:253] + "..." if len(title) > 256 else title
    elif mod_action.target_user:
        target = user_service.get_user(mod_action.target_user)
        embed_json["title"] = f"{mod_action.mod}: {mod_action.action} - {mod_action.target_user}"
    if target:
        embed_json["url"] = reddit_utils.make_permalink(target)

    if mod_action.details:
        embed_json["description"] = mod_action.details

    if mod_action.description:
        desc_info = {"name": "Description", "value": mod_action.description}
        embed_json["fields"].append(desc_info)

    discord.send_webhook_message(config_loader.DISCORD["mod_log_webhook_url"], {"embeds": [embed_json]})


def monitor_stream():
    """
    Monitor the subreddit for new actions and parse them when they come in. Will restart upon encountering an error.
    """

    while True:
        try:
            logger.info("Connecting to Reddit...")
            reddit = reddit_utils.get_reddit_instance(config_loader.REDDIT["auth"])
            subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])
            rabbit = RabbitService(config_loader.RABBITMQ)
            get_moderators()
            logger.info("Loading flairs...")
            post_service.load_post_flairs(subreddit)
            logger.info("Starting mod log stream...")
            for mod_action in subreddit.mod.stream.log():
                parse_mod_action(mod_action, reddit, subreddit, rabbit)
        except Exception:
            delay_time = 30
            logger.exception(f"Encountered an unexpected error, restarting in {delay_time} seconds...")
            time.sleep(delay_time)


def load_archive(archive_args: argparse.Namespace):
    """
    Start loading earlier mod actions (prior to action specified by --id if provided) until reaching --date or
    the end of available logs. Will restart from last known action if encountering an error.
    It's rather inefficient as it processes a single action at a time and could probably batch together
    some Reddit API calls.
    """

    after_date = archive_args.date
    before_action_id = archive_args.id

    if after_date is None:
        after_date = datetime.now(timezone.utc) - timedelta(days=95)
    elif not after_date.tzname():
        after_date = after_date.replace(tzinfo=timezone.utc)
    after_timestamp = after_date.timestamp()

    if before_action_id and not before_action_id.startswith("ModAction_"):
        before_action_id = "ModAction_" + before_action_id

    reddit = reddit_utils.get_reddit_instance(config_loader.REDDIT["auth"])
    subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])

    current_id = before_action_id if before_action_id else [log.id for log in subreddit.mod.log(limit=1)][0]
    logger.info(f"[Archive] Loading mod log going back until {after_date.isoformat()}, starting from {current_id}")
    current_timestamp = datetime.now(timezone.utc).timestamp()
    # All this is put inside a loop in case it encounters an error; will automatically restart until it reaches
    # the target date or runs out of actions to process (if date is too far in the past).
    while True:
        try:
            logger.info("Connecting to Reddit...")
            # Since the parse_mod_action function relies on reddit and subreddit existing in the global scope.
            reddit = reddit_utils.get_reddit_instance(config_loader.REDDIT["auth"])
            subreddit = reddit.subreddit(config_loader.REDDIT["subreddit"])
            # Not exactly sure of behavior when running past what's available, but this attempts to track when there
            # aren't any processed so we can reasonably drop out.
            actions_processed = 0
            while after_timestamp < current_timestamp:
                actions_processed = 0
                logger.info("[Archive] Getting next batch of actions...")
                for mod_action in subreddit.mod.log(params={"after": current_id}, limit=500):
                    # Once we reach the target date, stop parsing.
                    if after_timestamp > mod_action.created_utc:
                        current_timestamp = mod_action.created_utc
                        break

                    parse_mod_action(mod_action, reddit, subreddit)
                    actions_processed += 1

                    # The earliest action in the batch and will be the start of the next loop.
                    if mod_action.created_utc < current_timestamp:
                        current_id = mod_action.id
                        current_timestamp = mod_action.created_utc

                if actions_processed == 0:
                    logger.info(
                        f"[Archive] No actions remaining, most recent:"
                        f" {current_id} - {datetime.fromtimestamp(current_timestamp).isoformat()}"
                    )
                    break

                logger.info(
                    f"[Archive] Processed {actions_processed} actions, most recent:"
                    f" {current_id} - {datetime.fromtimestamp(current_timestamp).isoformat()}"
                )

            return
        except Exception:
            delay_time = 30
            logger.exception(f"Encountered an unexpected error, restarting in {delay_time} seconds...")
            time.sleep(delay_time)


def get_moderators():
    """Initializes the list of currently active moderators."""

    # Clear out the previous list in case something changed.
    global active_mods
    active_mods = []

    mod_list = user_service.get_moderators()
    for mod in mod_list:
        active_mods.append(mod.username)


def _get_parser() -> argparse.ArgumentParser:
    new_parser = argparse.ArgumentParser(description="Monitor for new mod actions.")
    new_parser.add_argument(
        "--archive", action="store_true", help="Archive earlier mod actions rather than monitoring current activity."
    )
    new_parser.add_argument(
        "-d",
        "--date",
        type=lambda d: datetime.fromisoformat(d),
        help="Date to stop at (ISO 8601 format) with --archive.",
    )
    new_parser.add_argument(
        "-id", "--id", type=str, help="Starting mod action ID to work backward from with --archive."
    )
    return new_parser


if __name__ == "__main__":
    parser = _get_parser()
    args = parser.parse_args()
    # Load mod list regardless of what's next.
    get_moderators()
    if args.archive:
        # Load earlier mod actions.
        load_archive(args)
    else:
        # Default path - continually monitor for new mod actions.
        monitor_stream()
