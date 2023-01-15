"""
Runs various reports against the database.
All output is via console.
"""

import argparse
from datetime import datetime, date
import time

import config_loader
from constants import mod_constants
from services import comment_service, mod_action_service, post_service, traffic_service
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

    total_posts = post_service.count_posts(start_date, end_date)
    total_post_authors = post_service.count_post_authors(start_date, end_date)

    total_comments = comment_service.count_comments(start_date, end_date, mod_constants.BOTS)
    total_comment_authors = comment_service.count_comment_authors(start_date, end_date, mod_constants.BOTS)

    monthly_traffic = traffic_service.get_monthly_traffic(start_date)
    total_views = monthly_traffic.total_pageviews
    unique_views = monthly_traffic.unique_pageviews

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
        "banuser", start_date, end_date, distinct=True, exclude_mod_accounts_list=mod_constants.ADMINS
    )
    permabanned_users = mod_action_service.count_mod_actions(
        "banuser", start_date, end_date, distinct=True, details="permanent", exclude_mod_accounts_list=mod_constants.ADMINS
    )
    banned_users_bots = mod_action_service.count_mod_actions(
        "banuser", start_date, end_date, distinct=True, mod_accounts_list=mod_constants.BOTS
    )
    unbanned_users = mod_action_service.count_mod_actions(
        "unbanuser", start_date, end_date, distinct=True, exclude_mod_accounts_list=_bots_and_admins
    )
    unbanned_users_temp = mod_action_service.count_mod_actions(
        "unbanuser",
        start_date,
        end_date,
        distinct=True,
        description="was temporary",
        exclude_mod_accounts_list=_bots_and_admins,
    )
    actual_unbanned = unbanned_users - unbanned_users_temp

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
```
- Total traffic: {total_views} pageviews, {unique_views} unique pageviews
- Total posts: {total_posts}, {total_post_authors} unique authors
- Total comments: {total_comments}, {total_comment_authors} unique authors (excluding mod bots)
- Removed posts: {removed_posts_humans} by moderators, {removed_posts_bots} by bots, {removed_posts_total} distinct
- Removed comments: {removed_comments_humans} by moderators, {removed_comments_bots} by bots, {removed_comments_total} distinct
- Approved posts: {approved_posts}
- Approved comments: {approved_comments}
- Distinguished comments: {distinguished_comments}
- Users banned: {banned_users} ({permabanned_users} permanent, {banned_users_bots} by BotDefense)
- Users unbanned: {actual_unbanned}
- Admin/Anti-Evil Operations: removed posts: {admin_removed_posts}, removed comments: {admin_removed_comments}.```"""  # noqa: E501

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
