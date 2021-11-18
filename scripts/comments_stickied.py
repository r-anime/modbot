"""
Comments While Stickied

Gets numbers of comments on posts while the posts were stickied (pinned) compared to when they weren't.
Useful for analyzing how much activity a weekly thread will get when not stickied.
"""

from datetime import datetime, timezone, timedelta

from sqlalchemy.sql import text

from services import post_service, comment_service, mod_action_service
from utils.logger import logger

_comment_data = comment_service.CommentData()
_post_data = post_service.PostData()
_mod_action_data = mod_action_service.ModActionData()


def get_comments_in_period(post: post_service.PostModel, start_time: datetime, end_time: datetime) -> list[comment_service.CommentModel]:
    sql = text("""
    select comments.* from comments join posts p on comments.post_id = p.id
    where comments.post_id = :post_id and
    comments.created_time >= :start and comments.created_time < :end;
    """)

    rows = _comment_data.execute(sql, post_id=post.id, start=start_time, end=end_time)
    comment_list = [comment_service.CommentModel(row) for row in rows]

    return comment_list


def get_post_sticky_times(post: post_service.PostModel) -> list[tuple]:
    """Get each time a post was stickied/unstickied. Returns a list of tuples with sticky/unsticky times."""

    logger.debug(f"Getting sticky times for {post.id36}")
    sql = text("""
    select * from mod_actions
    where target_post_id = :post_id and target_comment_id is null
    and action in ('sticky', 'unsticky')
    order by created_time;
    """)
    rows = _mod_action_data.execute(sql, post_id=post.id)
    action_list = [mod_action_service.ModActionModel(row) for row in rows]

    times_list = []
    start_time = None
    while action_list:
        action = action_list.pop(0)
        if action.action == 'sticky':
            if start_time:  # shouldn't get here, was already just stickied?
                logger.warning(f"Post {post.id36} was stickied twice in a row?")
                continue
            start_time = action.created_time
            continue

        # else action == unsticky
        if not start_time:
            logger.warning(f"Post {post.id36} was unstickied twice in a row?")
            continue

        times_list.append((start_time, action.created_time))
        start_time = None
    # Currently still stickied?
    if start_time:
        times_list.append((start_time, datetime.now(tz=timezone.utc)))

    return times_list


def get_weekly_posts(start_date: datetime = None, end_date: datetime = None) -> list[post_service.PostModel]:
    """Get all weekly threads between certain times."""

    if not start_date:
        start_date = datetime.fromtimestamp(1199145600, tz=timezone.utc)  # January 1 2008
    if not end_date:
        end_date = datetime.now(tz=timezone.utc)

    sql = text(f"""
    select * from posts
    where flair_text = 'Weekly' and author in ('AutoModerator', 'AnimeMod')
    and created_time >= :start and created_time < :end
    and removed is false
    order by created_time;
    """)

    rows = _post_data.execute(sql, start=start_date, end=end_date)
    post_list = [post_service.PostModel(row) for row in rows]

    return post_list


def process_posts(posts: list[post_service.PostModel]):
    """Main logic section for a list of posts."""

    post_calculated_stats = []

    for post in posts:
        logger.debug(f"Getting comments for post {post.id36} - {post.title}")
        all_comments = comment_service.get_comments_by_post_id(post.id)

        # Ignore any comments made more than a week after the post was created; should be going in next week's thread.
        comments_in_week = []
        for comment in all_comments:
            if comment.created_time < post.created_time + timedelta(days=7):
                comments_in_week.append(comment)

        # Get all comments while the post was stickied.
        sticky_time_comments = []
        sticky_times = get_post_sticky_times(post)
        sticky_time_total = timedelta()
        for period in sticky_times:
            sticky_time_total += (period[1] - period[0])
            comments = get_comments_in_period(post, period[0], period[1])
            sticky_time_comments.extend(comments)

        sticky_comment_ids = []
        sticky_comments_after_week = []
        for comment in sticky_time_comments:
            if comment.created_time > post.created_time + timedelta(days=7):
                sticky_comments_after_week.append(comment)
                continue
            sticky_comment_ids.append(comment.id)
        non_sticky_comments = [comment for comment in comments_in_week if comment.id not in sticky_comment_ids]
        top_level_sticky = [comment for comment in sticky_time_comments if not comment.parent_id]
        top_level_unsticky = [comment for comment in non_sticky_comments if not comment.parent_id]

        sticky_time_hours = round(sticky_time_total.total_seconds() / 3600, 1)
        sticky_rate = 0.0 if sticky_time_hours < 0.1 else round(len(sticky_time_comments) / sticky_time_hours, 1)
        unsticky_time_hours = (24 * 7) - sticky_time_hours
        unsticky_rate = round(len(non_sticky_comments) / unsticky_time_hours, 1)

        msg = f"{post.id36} - {post.title} - stickied {sticky_time_hours} hours"
        msg += f" - comments: {len(sticky_time_comments)} sticky ({sticky_rate}/hr, {len(top_level_sticky)} top level)"
        msg += f" - {len(non_sticky_comments)} non-sticky ({unsticky_rate}/hr, {len(top_level_unsticky)} top level)"
        msg += f" - {len(all_comments) - len(comments_in_week)} after a week"
        logger.info(msg)

        stats = (
            post.id36,
            f'"{post.title}"',
            sticky_time_hours,
            len(all_comments),
            len(comments_in_week),
            len(sticky_time_comments),
            len(top_level_sticky),
            len(non_sticky_comments),
            len(top_level_unsticky)
        )
        post_calculated_stats.append(stats)

    return post_calculated_stats


def main(start_date: datetime = None, end_date: datetime = None):
    # get all weekly posts
    if not start_date or start_date < datetime(2021, 6, 1, tzinfo=timezone.utc):
        start_date = datetime(2021, 6, 1, tzinfo=timezone.utc)
    posts = get_weekly_posts(start_date=start_date, end_date=end_date)

    # filter out CDF
    posts_by_title = {
        # "cdf": filter(lambda p: p.title.startswith("Casual Discussion"), posts),
        "miscq": filter(lambda p: p.title.startswith("Miscellaneous Anime Questions"), posts),
        "rec": filter(lambda p: p.title.startswith("Recommendation Tuesdays"), posts),
        "merch": filter(lambda p: p.title.startswith("Merch Mondays"), posts),
        "disc": filter(lambda p: "Thursday Anime Discussion Thread" in p.title, posts),
        "review": filter(lambda p: p.title.startswith("The /r/anime Week in Review"), posts)
    }

    csv_headers = ("post_id", "post_title", "sticky_hours", "comments_total", "comments_during_week",
                   "comments_sticky", "comments_sticky_top_level", "comments_unsticky", "comments_unsticky_top_level")
    csv_data = [csv_headers]
    for post_list in posts_by_title.values():
        posts_stats = process_posts(post_list)
        csv_data.extend(posts_stats)

    csv_str = "\n".join(",".join(map(str, row)) for row in csv_data)
    logger.info(csv_str)


if __name__ == "__main__":
    start = datetime(2021, 6, 1, tzinfo=timezone.utc)
    end = datetime(2021, 11, 1, tzinfo=timezone.utc)
    main(start, end)
