from datetime import datetime, timezone, timedelta
import numpy
import random

from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models import Post, PostMetric
from app.utils import calculate_trend_score, calculate_score
from app.utils.vault import get_post_vaults


def get_similar_post(db: Session, embed: list[float], size: int = 32):
    """Return post ids of post most similar to input vector."""
    vector = numpy.array(embed).tolist()
    posts = (
        db.query(Post.id)
        .order_by(Post.embedding.cosine_distance(vector), desc(Post.score))
        .limit(100)
    )
    postIds = [post.id for post in posts]
    results = random.sample(postIds, size)
    return results


def update_top_vaults(db: Session, post: Post):
    similarIds = get_similar_post(db, post.embedding)
    vaultIds = get_post_vaults(db, similarIds, 4)
    post.top_vaults = vaultIds
    flag_modified(post, "top_vaults")


def update_top_tags(post):
    """
    update later

    current_tags = post.top_tags or []
    new_tags = get_top_tags_(post.id)
    combined = list(set(new_tags + current_tags))
    post.top_tags = combined[:5]
    """


""" metric functions """


def create_post_log(post: Post):
    post_metric = PostMetric(
        post_id=post.id,
        score=post.score,
        week_score=post.week_score,
        month_score=post.month_score,
        year_score=post.year_score,
        trend_score=post.trend_score,
    )
    return post_metric


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
    return result.total_score or 0


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
    return result.avg_score or 0


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
            trend_score = calculate_trend_score(avg_score_3, avg_score)
            week_score = popularity_score(db, post.id, 7)
            month_score = popularity_score(db, post.id, 30)
            year_score = popularity_score(db, post.id, 365)

            post.trend_score = trend_score
            post.week_score = week_score
            post.month_score = month_score
            post.year_score = year_score
            post.score = calculate_score(
                post.likes, post.dislikes, post.saves, post.comment_count
            )
            db.add(log)
    else:
        log = create_post_log(post)
        db.add(log)
