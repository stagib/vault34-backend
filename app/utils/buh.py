from datetime import datetime, timezone, timedelta

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


def create_post_log(post: Post, previous_log):
    prev_likes = 0
    prev_dislikes = 0
    prev_saves = 0
    prev_comment_count = 0
    if previous_log:
        prev_likes = previous_log.likes
        prev_dislikes = previous_log.dislikes
        prev_saves = previous_log.saves
        prev_comment_count = previous_log.comment_count

    likes = post.likes - prev_likes
    dislikes = post.dislikes - prev_dislikes
    saves = post.saves - prev_saves
    comment_count = post.comment_count - prev_comment_count
    score = calculate_post_score(likes, dislikes, saves, comment_count)
    post_metric = PostMetric(
        post_id=post.id,
        likes=likes,
        dislikes=dislikes,
        saves=saves,
        comment_count=comment_count,
        score=score,
    )
    return post_metric


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
