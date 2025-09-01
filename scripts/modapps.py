"""
Mod Apps Parser/Poster

One caveat is that the username field must be sanitized (i.e. ensured valid) in the CSV prior to running this script.
"""

import argparse
import csv
import time
from datetime import datetime, timezone, timedelta
import re
import requests
from io import StringIO

import config_loader
from services import comment_service, post_service, mod_action_service
from utils import reddit as reddit_utils


username_key = "What is your Reddit username?"


reddit = reddit_utils.get_reddit_instance(config_loader.REDDIT["auth"])


def upsert_voting_thread(voting_subreddit, app_announcement_datetime, numb_total_apps=-1, numb_troll_apps=-1):
    title = voting_thread_title(app_announcement_datetime)
    body = voting_thread_post_body(numb_total_apps, numb_troll_apps)

    voting_thread = find_voting_thread(voting_subreddit, title)
    if voting_thread:
        if numb_total_apps != -1 and numb_troll_apps != -1 and voting_thread.selftext != body:
            voting_thread.edit(body)

    else:
        voting_thread = voting_subreddit.submit(title=title, selftext=body)

    return voting_thread


def voting_thread_title(app_announcement_datetime):
    return f"Mod Applications — {app_announcement_datetime.strftime("%B %Y")}"


def voting_thread_post_body(numb_total_apps, numb_troll_apps):
    return """**This is the only round of voting.**

Extensive debates and trash talking can go in the proper Discord channel, which will be expunged before bringing new mods on board.

Vote [yes](#yes) or [no](#no) on each application. As usual there's no well-established threshold or simple majority so it might take some talking to determine who makes the cut.

If there are any troll applications, you must mark them using a `Troll` column in the form responses (it just needs to non empty). Note that you will need to be on the AnimeMod account to edit it.

There are **{numb_total_apps}** legitimate applications so far and an additional **{numb_troll_apps}** troll applications not included.""".format(
        numb_total_apps=numb_total_apps, numb_troll_apps=numb_troll_apps
    )


def find_voting_thread(voting_subreddit, title):
    username = config_loader.REDDIT["auth"]["username"]
    user = reddit.redditor(username)
    for submission in user.submissions.new(limit=100):
        if submission.title == title and submission.subreddit == voting_subreddit:
            return submission
    return None


def process_csv(csv_file, voting_thread, app_comments, app_announcement_datetime, activity_window_datetime):
    legit_apps = []
    troll_apps = []
    # read CSV
    reader = csv.DictReader(StringIO(csv_file))
    for row in reader:
        username, comment_list, troll = process_row(row, activity_window_datetime, app_announcement_datetime)
        if troll:
            troll_apps.append(username)
        else:
            legit_apps.append(username)
        if username not in app_comments:
            app_comments[username] = []
        upsert_comment_chain(voting_thread, app_comments[username], comment_list)

    for comment_list in app_comments.values():
        for entry in comment_list:
            if not entry["processed"]:
                entry["reddit_comment"].delete()
    return legit_apps, troll_apps


def find_comment_list(comment, bot_username):
    username = re.search("> https://www.reddit.com/user/(.*?)\n\n", comment.body).group(1)
    comment_list = []

    while comment:
        comment_list.append({"processed": False, "reddit_comment": comment})
        comment = find_bot_reply(comment, bot_username)

    return username, comment_list


def find_bot_reply(comment, bot_username):
    for comment in comment.replies:
        if comment.author.name == bot_username:
            return comment
    return None


def process_row(row, activity_start_date, activity_end_date):
    """
    Turns a response row into a list of one or more strings to be posted as comments.

    :param row: row of DictReader
    :param activity_start_date: beginning of when to start measuring user activity on the sub
    :param activity_end_date: when to stop measuring user activity on the sub (probably posting date of apps)
    :return: list of strings
    """

    username = re.sub("/?u?/", "", row[username_key]).strip()
    print(f"Processing {username}...")

    if row.get("Troll"):
        print(f"Skipping {username} as they are marked as troll")
        return username, [], True

    response_body = f"### {username_key}\n\n> https://www.reddit.com/user/{username}\n\n"
    ps_url = (
        f"https://camas.unddit.com/#%7B%22author%22:%22{username}%22,"
        + "%22subreddit%22:%22anime%22,%22resultSize%22:100%7D"
    )
    response_body += f"> [View comments via Pushshift]({ps_url}) (including deleted)\n\n"

    # Get the activity of the user both in the 90-day window prior to the posting of applications (as specified)
    # and overall history on /r/anime.
    activity_start_time_str = activity_start_date.isoformat()
    activity_end_time_str = activity_end_date.isoformat()
    user_comments_window_with_cdf = len(
        comment_service.get_comments_by_username(username, activity_start_time_str, activity_end_time_str)
    )
    user_comments_window = len(
        comment_service.get_comments_by_username(username, activity_start_time_str, activity_end_time_str, True)
    )
    cdf_window = user_comments_window_with_cdf - user_comments_window
    user_posts_window = len(
        post_service.get_posts_by_username(username, activity_start_time_str, activity_end_time_str)
    )
    user_targeted_mod_actions = mod_action_service.get_mod_actions_targeting_username(username, start_date="2021-01-01")
    mod_actions = {}
    for mod_action in user_targeted_mod_actions:
        if mod_action.action not in mod_actions:
            mod_actions[mod_action.action] = []
        mod_actions[mod_action.action].append(mod_action)
    # sort by number of mod actions desc, then action name asc
    sorted_mod_actions = sorted(mod_actions.items(), key=lambda item: (-len(item[1]), item[0]))
    mod_actions_str = ", ".join(f"{action} ({len(action_list):,})" for action, action_list in sorted_mod_actions)

    user_comments_total_with_cdf = len(comment_service.get_comments_by_username(username, "2020-01-01"))
    user_comments_total = len(comment_service.get_comments_by_username(username, "2020-01-01", exclude_cdf=True))
    cdf_total = user_comments_total_with_cdf - user_comments_total
    user_posts_total = len(post_service.get_posts_by_username(username, "2020-01-01"))

    passes_activity_threshold = "✅" if user_comments_window + user_posts_window > 50 else "❌"

    response_body += f"### Activity in past 90 days {passes_activity_threshold}\n\n"
    response_body += f"> Comments excluding CDF: {user_comments_window:,} ({user_comments_total:,} since 2020-01-01)"
    if cdf_window or cdf_total:
        response_body += f" (including CDF: {cdf_window:,}, {cdf_total:,} since 2020-01-01)"
    else:
        response_body += " (no CDF activity)"
    response_body += f" Submissions: {user_posts_window:,} ({user_posts_total:,} since 2020-01-01)\n\n"
    response_body += f"> Mod actions since 2021-01-01: {mod_actions_str}\n\n"

    redditor = reddit.redditor(username)
    other_subs = redditor.moderated()
    response_body += "### Other Subreddits Moderated (Subscribers)\n\n> "
    if other_subs:
        for sub in other_subs:
            response_body += f"/r/{sub.display_name} ({sub.subscribers:,}) // "
        response_body += "\n\n"
    else:
        response_body += "(none)\n\n"

    response_parts = []
    for question, answer in row.items():
        # Skip ones we already know/don't care about.
        if question in ("Timestamp", username_key, "Troll"):
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
                return username, [], False

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
    return username, response_parts, False


def upsert_comment_chain(voting_thread, app_comments, comment_list):
    last_comment = voting_thread
    for i, comment_body in enumerate(comment_list):
        if len(app_comments) <= i:
            last_comment = last_comment.reply(comment_body)
            last_comment.disable_inbox_replies()
            app_comments.append({"processed": True, "reddit_comment": last_comment})
        else:
            app_comments[i]["processed"] = True
            last_comment = app_comments[i]["reddit_comment"]

            # filter out these sections since they change over time negligibly.
            strip_pattern = r"### Activity in past 90 days.*?### Other Subreddits Moderated \(Subscribers\).*?###"
            if re.sub(strip_pattern, "###", comment_body.strip(), flags=re.S) != re.sub(
                strip_pattern, "###", last_comment.body, flags=re.S
            ):
                last_comment.edit(comment_body)


def _get_parser() -> argparse.ArgumentParser:
    new_parser = argparse.ArgumentParser(description="Post mod applications to a thread.")
    new_parser.add_argument("--application_id", required=True, type=str, help="Thread ID for mod applications.")
    new_parser.add_argument("--voting_subreddit", required=True, type=str, help="Subreddit for voting thread.")
    new_parser.add_argument(
        "--refresh_rate_mins", required=True, type=int, help="How long to wait between refreshes in minutes"
    )
    new_parser.add_argument(
        "-d",
        "--end_datetime",
        required=True,
        type=lambda d: datetime.fromisoformat(d).astimezone(timezone.utc),
        help="Datetime to stop refreshing.",
    )
    new_parser.add_argument(
        "-u", "--url", required=True, type=str, help="Google Sheets link to load applications from."
    )
    return new_parser


def normalize_google_sheets_url(url):
    return re.search(r"(.*/d/.*?/)", url).group(1) + "export?format=csv"


def main():
    parser = _get_parser()
    args = parser.parse_args()

    voting_subreddit = reddit.subreddit(args.voting_subreddit)
    apps_thread = reddit.submission(id=args.application_id)
    app_announcement_datetime = datetime.fromtimestamp(apps_thread.created_utc)
    activity_window_datetime = app_announcement_datetime - timedelta(days=90)
    url = normalize_google_sheets_url(args.url)
    end_datetime = args.end_datetime
    bot_username = config_loader.REDDIT["auth"]["username"]

    while datetime.now(timezone.utc) <= end_datetime:
        print(f"Checking Responses")
        voting_thread = upsert_voting_thread(voting_subreddit, app_announcement_datetime)

        app_comments = {}
        for comment in voting_thread.comments:
            if not comment.author or comment.author.name != bot_username:
                continue
            username, comment_list = find_comment_list(comment, bot_username)
            app_comments[username] = comment_list

        response = requests.get(url)
        response.raise_for_status()

        legit_apps, troll_apps = process_csv(
            response.text, voting_thread, app_comments, app_announcement_datetime, activity_window_datetime
        )

        upsert_voting_thread(voting_subreddit, app_announcement_datetime, len(legit_apps), len(troll_apps))

        print(f"sleeping for {60 * args.refresh_rate_mins}")
        time.sleep(60 * args.refresh_rate_mins)

    print(f"Reached end time of {end_datetime}, so exiting")


if __name__ == "__main__":
    main()
