"""
Runs various reports against the database.
All output is via console.
"""

import argparse
from datetime import datetime, date
import time

import config_loader
from constants import mod_constants
from services import mod_action_service
from utils import discord

# Make a copy of both lists combined for easier use later.
_bots_and_admins = mod_constants.BOTS[:] + mod_constants.ADMINS


def _report_monthly(report_args: argparse.Namespace):
    """
    Prints monthly meta report.
    :param report_args: argparse arguments, date contains datetime with the month to run the report for (ignores day)
    """

    # Wait 10 seconds just in case there are any last second mod actions.
    time.sleep(10)

    # Reports start on the first day of the month and end on the first day of the next month.
    start_date = date(year=report_args.date.year, month=report_args.date.month, day=1)
    end_month = start_date.month + 1 if start_date.month < 12 else 1
    end_year = start_date.year if start_date.month < 12 else start_date.year + 1
    end_date = date(year=end_year, month=end_month, day=1)

    removed_posts_humans = mod_action_service.count_mod_actions(
        "removelink", start_date, end_date, distinct=True, exclude_mod_accounts_list=_bots_and_admins
    )
    removed_posts_humans += mod_action_service.count_mod_actions(
        "spamlink", start_date, end_date, distinct=True, exclude_mod_accounts_list=_bots_and_admins
    )

    removed_posts_bots = mod_action_service.count_mod_actions(
        "removelink", start_date, end_date, distinct=True, mod_accounts_list=mod_constants.BOTS
    )
    removed_posts_bots += mod_action_service.count_mod_actions(
        "spamlink", start_date, end_date, distinct=True, mod_accounts_list=mod_constants.BOTS
    )

    removed_posts_total = mod_action_service.count_mod_actions(
        "removelink", start_date, end_date, distinct=True, exclude_mod_accounts_list=mod_constants.ADMINS
    )
    removed_posts_total += mod_action_service.count_mod_actions(
        "spamlink", start_date, end_date, distinct=True, exclude_mod_accounts_list=mod_constants.ADMINS
    )

    removed_comments_humans = mod_action_service.count_mod_actions(
        "removecomment", start_date, end_date, distinct=True, exclude_mod_accounts_list=_bots_and_admins
    )
    removed_comments_humans += mod_action_service.count_mod_actions(
        "spamcomment", start_date, end_date, distinct=True, exclude_mod_accounts_list=_bots_and_admins
    )

    removed_comments_bots = mod_action_service.count_mod_actions(
        "removecomment", start_date, end_date, distinct=True, mod_accounts_list=mod_constants.BOTS
    )
    removed_comments_bots += mod_action_service.count_mod_actions(
        "spamcomment", start_date, end_date, distinct=True, mod_accounts_list=mod_constants.BOTS
    )

    removed_comments_total = mod_action_service.count_mod_actions(
        "removecomment", start_date, end_date, distinct=True, exclude_mod_accounts_list=mod_constants.ADMINS
    )
    removed_comments_total += mod_action_service.count_mod_actions(
        "spamcomment", start_date, end_date, distinct=True, exclude_mod_accounts_list=mod_constants.ADMINS
    )

    approved_posts = mod_action_service.count_mod_actions(
        "approvelink", start_date, end_date, distinct=True, exclude_mod_accounts_list=_bots_and_admins
    )
    approved_comments = mod_action_service.count_mod_actions(
        "approvecomment", start_date, end_date, distinct=True, exclude_mod_accounts_list=_bots_and_admins
    )
    distinguished_comments = mod_action_service.count_mod_actions(
        "distinguish", start_date, end_date, distinct=True, exclude_mod_accounts_list=_bots_and_admins
    )

    banned_users = mod_action_service.count_mod_actions(
        "banuser", start_date, end_date, distinct=True, exclude_mod_accounts_list=_bots_and_admins
    )
    permabanned_users = mod_action_service.count_mod_actions(
        "banuser", start_date, end_date, distinct=True, details="permanent", exclude_mod_accounts_list=_bots_and_admins
    )
    unbanned_users = mod_action_service.count_mod_actions(
        "unbanuser", start_date, end_date, distinct=True, exclude_mod_accounts_list=_bots_and_admins
    )

    admin_removed_posts = mod_action_service.count_mod_actions(
        "removelink", start_date, end_date, distinct=True, mod_accounts_list=mod_constants.ADMINS
    )
    admin_removed_comments = mod_action_service.count_mod_actions(
        "removecomment", start_date, end_date, distinct=True, mod_accounts_list=mod_constants.ADMINS
    )

    # Adjust numbers based on crowd control filter.
    crowd_control_removed_comments = mod_action_service.count_mod_actions(
        "removecomment", start_date, end_date, distinct=True, details="Crowd Control", mod_accounts_list=["reddit"]
    )
    admin_removed_comments -= crowd_control_removed_comments
    removed_comments_bots += crowd_control_removed_comments

    crowd_control_removed_posts = mod_action_service.count_mod_actions(
        "removelink", start_date, end_date, distinct=True, details="Crowd Control", mod_accounts_list=["reddit"]
    )
    admin_removed_posts -= crowd_control_removed_posts
    removed_posts_bots += crowd_control_removed_posts

    meta_message = f"""Monthly Report – {start_date.strftime("%B %Y")}:
```* Removed posts: {removed_posts_humans} by moderators, {removed_posts_bots} by bots, {removed_posts_total} distinct
* Removed comments: {removed_comments_humans} by moderators, {removed_comments_bots} by bots, {removed_comments_total} distinct
* Approved posts: {approved_posts}
* Approved comments: {approved_comments}
* Distinguished comments: {distinguished_comments}
* Users banned: {banned_users} ({permabanned_users} permanent)
* Users unbanned: {unbanned_users}
* Admin/Anti-Evil Operations: removed posts: {admin_removed_posts}, removed comments: {admin_removed_comments}.```"""  # noqa: E501

    discord.send_webhook_message(config_loader.DISCORD["webhook_url"], {"content": meta_message})


def _get_parser() -> argparse.ArgumentParser:
    new_parser = argparse.ArgumentParser(description="Runs reports against the database")
    new_parser.add_argument("name", help="Name of the report to run.", choices=["monthly"])
    new_parser.add_argument(
        "-d",
        "--date",
        type=lambda d: datetime.fromisoformat(d),
        help="Date to run report for (month for monthly)",
    )
    return new_parser


_reports = {"monthly": _report_monthly}


if __name__ == "__main__":
    parser = _get_parser()
    args = parser.parse_args()
    report_func = _reports[args.name]
    report_func(args)
