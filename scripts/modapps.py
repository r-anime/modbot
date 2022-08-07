"""
Mod Apps Parser/Poster

One caveat is that the username field must be sanitized (i.e. ensured valid) in the CSV prior to running this script.
"""


import argparse
import csv
from datetime import datetime, timedelta
import re

import config_loader
from services import comment_service, post_service, mod_action_service
from utils import reddit as reddit_utils


username_key = "What is your Reddit username?"


reddit = reddit_utils.get_reddit_instance(config_loader.REDDIT["auth"])


def process_row(row, activity_start_date, activity_end_date):
    """
    Turns a response row into a list of one or more strings to be posted as comments.

    :param row: row of DictReader
    :return: list of strings
    """

    username = re.sub("/?u?/", "", row[username_key]).strip()
    print(f"Processing {username}...")

    response_body = f"### {username_key}\n\n> https://www.reddit.com/user/{username}\n\n"

    # Get the activity of the user both in the 90-day window prior to the posting of applications (as specified)
    # and overall history on /r/anime.
    activity_start_time_str = activity_start_date.isoformat()
    activity_end_time_str = activity_end_date.isoformat()
    user_comments_window = len(
        comment_service.get_comments_by_username(username, activity_start_time_str, activity_end_time_str)
    )
    user_posts_window = len(
        post_service.get_posts_by_username(username, activity_start_time_str, activity_end_time_str)
    )
    user_targeted_mod_actions = mod_action_service.get_mod_actions_targeting_username(username, start_date="2021-01-01")
    mod_actions = {}
    for mod_action in user_targeted_mod_actions:
        if mod_action.action not in mod_actions:
            mod_actions[mod_action.action] = []
        mod_actions[mod_action.action].append(mod_action)
    mod_actions_str = ", ".join(f"{action} ({len(action_list)})" for action, action_list in mod_actions.items())

    user_comments_total = len(comment_service.get_comments_by_username(username, "2021-06-01"))
    user_posts_total = len(post_service.get_posts_by_username(username, "2021-06-01"))

    passes_activity_threshold = "✅" if user_comments_window + user_posts_window > 50 else "❌"

    response_body += f"### Activity in past 90 days {passes_activity_threshold}\n\n"
    response_body += f"> Comments: {user_comments_window} ({user_comments_total} since 2021-06-01)"
    response_body += f" Submissions: {user_posts_window} ({user_posts_total} since 2021-06-01)\n\n"
    response_body += f"> Mod actions since 2021-01-01: {mod_actions_str}\n\n"

    redditor = reddit.redditor(username)
    other_subs = redditor.moderated()
    response_body += "### Other Subreddits Moderated (Subscribers)\n\n> "
    if other_subs:
        for sub in other_subs:
            response_body += f"/r/{sub.display_name} ({sub.subscribers}) // "
        response_body += "\n\n"
    else:
        response_body += "(none)\n\n"

    response_parts = []
    for question, answer in row.items():
        # Skip ones we already know/don't care about.
        if question in ("Timestamp", username_key):
            continue

        answer_str = "\n\n> ".join(answer.splitlines())  # for multi-line responses
        line = f"### {question}\n\n> {answer_str}\n\n"

        # Single answer longer than comment limit, for the verbose folks.
        if len(line) > 10000:
            print(f"Single answer longer than 10k for {username} on {question}.")
            response_parts.append(response_body)
            response_body = f"### {question}"
            answer_lines = answer.splitlines()

            # Use shorter paragraphs dammit. TODO: try to fix this?
            if any(len(f"### {question} (cont.)\n\n> {line}") > 10000 for line in answer_lines):
                print(f"Line too long for {username}, skipping them.")
                return []

            for line in answer_lines:
                if len(response_body + f"\n\n> {line}\n\n") > 10000:
                    response_parts.append(response_body)
                    response_body = f"### {question} (cont.)"
                response_body += f"\n\n> {line}"
            response_body += "\n\n"

        # If the comment would be too long with the new line, start a new comment.
        elif len(response_body + line) > 10000:
            response_parts.append(response_body)
            response_body = ""
            response_body += line
        else:
            response_body += line

    response_parts.append(response_body)

    print(f"Done with {username}.")
    return response_parts


def _get_parser() -> argparse.ArgumentParser:
    new_parser = argparse.ArgumentParser(description="Post mod applications to a thread.")
    new_parser.add_argument("--post_id", required=True, type=str, help="Thread ID to post comments to.")
    new_parser.add_argument(
        "-d",
        "--date",
        required=True,
        type=lambda d: datetime.fromisoformat(d),
        help="Date that mod apps opened on (ISO 8601 format).",
    )
    new_parser.add_argument("-f", "--file", required=True, type=str, help="CSV file to load applications from.")
    return new_parser


def main():
    parser = _get_parser()
    args = parser.parse_args()

    response_dump_thread_id = args.post_id
    app_announcement_datetime = args.date
    activity_window_datetime = app_announcement_datetime - timedelta(days=90)

    thread = reddit.submission(id=response_dump_thread_id)

    # read CSV
    with open(args.file, newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            comment_list = process_row(row, activity_window_datetime, app_announcement_datetime)
            top_level = thread.reply(comment_list[0])
            top_level.disable_inbox_replies()
            for comment_str in comment_list[1:]:
                comment = top_level.reply(comment_str)
                comment.disable_inbox_replies()


if __name__ == "__main__":
    main()
