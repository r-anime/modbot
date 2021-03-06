"""
Mod Apps Parser/Poster

One caveat is that the username field must be sanitized (i.e. ensured valid) in the CSV prior to running this script.
"""


import csv
from datetime import datetime, timedelta

import psaw
import praw

import config


response_dump_thread_id = ''
app_announcement_datetime = datetime(2020, 6, 16, 20, 38, 5)
activity_window_datetime = app_announcement_datetime - timedelta(days=90)
csv_file_path = 'apps.csv'
username_key = 'What is your Reddit username?'


psaw_api = psaw.PushshiftAPI()
reddit = praw.Reddit(**config.REDDIT["auth"])


def process_row(row):
    """
    Turns a response row into a list of one or more strings to be posted as comments.

    :param row: row of DictReader
    :return: list of strings
    """

    username = row[username_key]
    print(f"Processing {username}...")

    response_body = f"### {username_key}\n\n> https://www.reddit.com/user/{username}\n\n"

    # Get the activity of the user both in the 90-day window prior to the posting of applications (as specified)
    # and overall history on /r/anime.
    user_activity_window = psaw_api.redditor_subreddit_activity(
        username,
        before=app_announcement_datetime,
        after=activity_window_datetime)
    user_comments_window = user_activity_window['comment']['anime']
    user_submissions_window = user_activity_window['submission']['anime']

    user_activity_total = psaw_api.redditor_subreddit_activity(username)
    user_comments_total = user_activity_total['comment']['anime']
    user_submissions_total = user_activity_total['submission']['anime']

    passes_activity_threshold = '✅' if user_comments_window + user_submissions_window > 50 else '❌'

    response_body += f"### Activity in past 90 days {passes_activity_threshold}\n\n"
    response_body += f"> Comments: {user_comments_window} ({user_comments_total} total)"
    response_body += f" Submissions: {user_submissions_window} ({user_submissions_total} total)\n\n"

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
        if question in ('Timestamp', username_key):
            continue

        answer_str = '\n\n> '.join(answer.splitlines())  # for multi-line responses
        line = f"### {question}\n\n> {answer_str}\n\n"

        # If the comment would be too long with the new line, start a new comment.
        if len(response_body + line) > 10000:
            response_parts.append(response_body)
            response_body = ''
        response_body += line

    response_parts.append(response_body)

    print(f"Done with {username}")
    return response_parts


def main():
    thread = reddit.submission(id=response_dump_thread_id)

    # read CSV
    with open(csv_file_path, newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            comment_list = process_row(row)
            top_level = thread.reply(comment_list[0])
            for comment_str in comment_list[1:]:
                top_level.reply(comment_str)


if __name__ == "__main__":
    main()
