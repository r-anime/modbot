"""
Unarchived Comments

Admins enabled commenting on old posts that used to be archived after 6 months, details here: https://redd.it/py2xy2
We trialed this, then began archiving threads again after 16 days and gathered information on comments and users that
posted on old threads in this time. Results of this script posted in the meta thread:
https://www.reddit.com/r/anime/comments/qocky5/-/hjm4hvs/
"""

from sqlalchemy.sql import text

from services import post_service, comment_service
from utils.logger import logger
from utils.reddit import base36encode, make_permalink

_comment_data = comment_service.CommentData()
_post_data = post_service.PostData()


def get_comments_on_old_posts() -> list[comment_service.CommentModel]:
    logger.info("Getting comments...")
    sql = text(
        """
    select comments.* from comments join posts p on comments.post_id = p.id join users u on comments.author = u.username
    where comments.created_time >= '2021-10-01' and comments.created_time >= p.created_time + '6 months'
    and u.moderator is FALSE;
    """
    )

    rows = _comment_data.execute(sql)

    comment_list = []
    for row in rows:
        comment = comment_service.CommentModel(row)
        comment.is_reply_to_recent_comment = (
            comment.parent_id is not None and comment.parent_id > 37911017436
        )  # roughly 2021-10-01
        comment_list.append(comment)

    return comment_list


def get_other_user_activity(users, user_comment_ids) -> dict:
    logger.info("Getting other user history...")
    sql = text(
        f"""
    select comments.* from comments join posts on comments.post_id = posts.id
    where comments.author in ('{"','".join(users)}')
    and comments.created_time >= '2021-06-01' and comments.created_time < '2021-11-01'
    and comments.id not in ({",".join(str(cid) for cid in user_comment_ids)});
    """
    )
    rows = _comment_data.execute(sql)
    comment_list = [comment_service.CommentModel(row) for row in rows]

    sql = text(
        f"""
    select posts.* from posts
    where posts.author in ('{"','".join(users)}')
    and posts.created_time >= '2021-06-01' and posts.created_time < '2021-11-01';
    """
    )
    rows = _post_data.execute(sql)
    post_list = [post_service.PostModel(row) for row in rows]

    return {"comments": comment_list, "posts": post_list}


def get_posts(post_list: list) -> dict:
    logger.info("Getting posts...")

    sql = text(
        f"""
    select posts.* from posts
    where posts.id36 in ('{"','".join(post_list)}');
    """
    )
    rows = _post_data.execute(sql)
    posts = [post_service.PostModel(row) for row in rows]
    posts_by_id = {post.id: post for post in posts}

    return posts_by_id


def main():
    # get comments on old posts (+ unique posts)
    comments = get_comments_on_old_posts()
    earliest_comment_time = min([c.created_time for c in comments])
    latest_comment_time = max([c.created_time for c in comments])
    logger.info(f"{len(comments)} comments: earliest {earliest_comment_time}, latest {latest_comment_time}")

    comment_ids = []
    post_list = set()
    replies_recent = []
    author_list = {}
    author_recent_list = {}
    for comment in comments:
        post_list.add(base36encode(comment.post_id))
        comment_ids.append(comment.id)

        # If they're only replying to someone else that made a recent comment, likely because they made the old
        # comment/post first and were replied to recently. Ignoring them in this case.
        if comment.is_reply_to_recent_comment:
            replies_recent.append(comment)
            if comment.author not in author_recent_list:
                author_recent_list[comment.author] = []
            author_recent_list[comment.author].append(comment.id)
            continue

        if comment.author not in author_list:
            author_list[comment.author] = []
        author_list[comment.author].append(comment.id)

    posts = get_posts(list(post_list))
    for post in posts.values():
        post_comments = [c for c in comments if c.post_id == post.id and not c.is_reply_to_recent_comment]
        for comment in post_comments:
            logger.debug(f"{make_permalink(comment)} - {post.title}")

    # For authors, get all other activity in sub from June onward
    logger.info(
        f"{len(comments)} total comments on {len(post_list)} posts, {len(author_list)}"
        f" unique authors replying to old comments/posts ({len(replies_recent)} replies to recent comments)"
    )
    # logger.info(f"\n{', '.join(author_list)}")
    logger.info(f"{len(author_recent_list)} authors replying to recent comments on old posts")
    # logger.info(', '.join(author_recent_list))

    user_history = {}
    other_user_activity = get_other_user_activity(list(author_list), comment_ids)
    for comment in other_user_activity["comments"]:
        if comment.author not in user_history:
            user_history[comment.author] = {"comments": [], "posts": []}
        user_history[comment.author]["comments"].append(comment)
    for post in other_user_activity["posts"]:
        if post.author not in user_history:
            user_history[post.author] = {"comments": [], "posts": []}
        user_history[post.author]["posts"].append(post)

    for user in user_history.values():
        user["total"] = len(user["comments"]) + len(user["posts"])

    users_no_history = [user for user in author_list if user not in user_history]
    # logger.info(f"Users with no activity since 2021-06-01: {len(users_no_history)}")
    # logger.info(", ".join(users_no_history))

    # logger.info(f"Other user activity since 2021-06-01: {len(user_history)}")

    # for user, user_info in user_history.items():
    #     logger.info(f"{user}: {len(user_info['comments'])} comments, {len(user_info['posts'])} posts")

    logger.info(f"Other user activity since 2021-06-01: {len(user_history)}")
    logger.info(f"Since {earliest_comment_time} (earliest comment time):")
    logger.info(f"{len(comments)} total comments on {len(post_list)} posts, {len(author_list)} unique authors")
    under_10 = len([user for user in user_history.values() if user["total"] < 10]) + len(users_no_history)
    under_5 = len([user for user in user_history.values() if user["total"] < 5]) + len(users_no_history)
    over_100 = len([user for user in user_history.values() if user["total"] >= 100])
    logger.info(f"Users with at least 100 posts/comments: {over_100}")
    logger.info(f"Users with under 10 comments/posts: {under_10}; under 5 comments/posts: {under_5}")
    logger.info(f"Users with no other activity between 2021-06-01 and 2021-11-01: {len(users_no_history)}")


if __name__ == "__main__":
    result = _comment_data.execute(sql=text("""SELECT count(*) from comments;"""))
    logger.info(f"Total comments in db: {result[0][0]}")
    result = _comment_data.execute(sql=text("""SELECT count(*) from posts;"""))
    logger.info(f"Total posts in db: {result[0][0]}")
    result = _comment_data.execute(sql=text("""SELECT count(*) from users;"""))
    logger.info(f"Total users in db: {result[0][0]}")
    main()
