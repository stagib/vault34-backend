from datetime import datetime, timezone, timedelta

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models import Post, PostMetric
from app.types import ReactionType


def add_item_to_string(string: str, item: str, limit: int = 100):
    string_list = string.split()
    if item in string_list:
        string_list.remove(item)
    string_list.append(item)
    if len(string_list) > limit:
        string_list.pop(0)
    return " ".join(string_list)


def get_emeddings(post_ids: str, db: Session):
    id_list = post_ids.split()
    posts = db.query(Post).filter(Post.id.in_(id_list)).all()
    return [post.embedding for post in posts]


def calculate_post_score(
    likes: int = 0, dislikes: int = 0, saves: int = 0, comment_count: int = 0
):
    score = likes + dislikes + (comment_count * 2) + (saves * 3)
    return score


def create_post_log(post: Post):
    post_metric = PostMetric(
        post_id=post.id,
        likes=post.likes,
        dislikes=post.dislikes,
        saves=post.saves,
        comment_count=post.comment_count,
        score=post.score,
        week_score=post.week_score,
        month_score=post.month_score,
        year_score=post.year_score,
        trend_score=post.trend_score,
    )
    return post_metric


def get_trend_score(score: float, avg_score: float):
    avg = avg_score or 0
    return score - avg


def popularity_score(db: Session, post_id: int, days: int = 7):
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=days)

    result = (
        db.query(func.sum(PostMetric.score).label("total_score"))
        .filter(
            PostMetric.post_id == post_id,
            PostMetric.date_created >= start_time,
        )
        .first()
    )
    if result:
        return result.total_score
    else:
        return None


def average_post_score(db: Session, post_id: int, days: int = 7):
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=days)

    result = (
        db.query(func.avg(PostMetric.score).label("avg_score"))
        .filter(
            PostMetric.post_id == post_id,
            PostMetric.date_created >= start_time,
        )
        .first()
    )
    if result:
        return result.avg_score
    else:
        return None


def log_post_metric(db: Session, post: Post, now: datetime):
    prev_log = (
        db.query(PostMetric)
        .filter(PostMetric.post_id == post.id)
        .order_by(desc(PostMetric.date_created))
        .first()
    )
    if prev_log:
        if prev_log.date_created + timedelta(days=1) < now:
            log = create_post_log(post)
            avg_score = average_post_score(db, post.id, 14)
            avg_score_3 = average_post_score(db, post.id, 3)
            trend_score = get_trend_score(avg_score_3, avg_score)
            week_score = popularity_score(db, post.id, 7)
            month_score = popularity_score(db, post.id, 30)
            year_score = popularity_score(db, post.id, 365)

            post.trend_score = trend_score
            post.week_score = week_score
            post.month_score = month_score
            post.year_score = year_score
            db.add(log)
    else:
        log = create_post_log(post)
        db.add(log)


def update_reaction_count(
    model,
    db_reaction: ReactionType,
    reaction: ReactionType,
):
    if db_reaction:
        if db_reaction == reaction:
            return

        if db_reaction == ReactionType.LIKE:
            model.likes -= 1
        elif db_reaction == ReactionType.DISLIKE:
            model.dislikes -= 1

        if reaction == ReactionType.LIKE:
            model.likes += 1
        elif reaction == ReactionType.DISLIKE:
            model.dislikes += 1
    else:
        if reaction == ReactionType.LIKE:
            model.likes += 1
        elif reaction == ReactionType.DISLIKE:
            model.dislikes += 1
