from datetime import datetime, timezone, timedelta
import numpy
import random

from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.neo4j import get_top_tags_
from app.models import Post, PostMetric, VaultPost, Vault
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
    s = score or 0
    return s - avg


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
            post.score = calculate_post_score(
                post.likes, post.dislikes, post.saves, post.comment_count
            )
            db.add(log)
    else:
        log = create_post_log(post)
        db.add(log)


def get_similar_post(db: Session, embed: list[float], size: int = 32):
    vector = numpy.array(embed).tolist()
    posts = (
        db.query(Post.id)
        .order_by(Post.embedding.cosine_distance(vector), desc(Post.score))
        .limit(100)
    )
    postIds = [post.id for post in posts]
    results = random.sample(postIds, size)
    return results


def get_post_vaults(db: Session, ids: list[int], size: int = 4):
    vaults = (
        db.query(Vault.id)
        .join(VaultPost, VaultPost.vault_id == Vault.id)
        .filter(VaultPost.post_id.in_(ids))
        .order_by(desc(Vault.likes))
        .limit(size)
        .all()
    )
    return list(set([vault.id for vault in vaults]))


def update_top_vaults(db: Session, post: Post):
    similarIds = get_similar_post(db, post.embedding)
    vaultIds = get_post_vaults(db, similarIds)
    post.top_vaults = vaultIds
    flag_modified(post, "top_vaults")


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


def update_top_tags(post):
    current_tags = post.top_tags or []
    new_tags = get_top_tags_(post.id)
    combined = list(set(new_tags + current_tags))
    post.top_tags = combined[:5]
