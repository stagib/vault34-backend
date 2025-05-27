import numpy
import random

from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.neo4j import get_top_tags_
from app.models import (
    Post,
    VaultPost,
    Vault,
)
from app.types import ReactionType


def add_item_to_string(string: str, item: str, limit: int = 100):
    string_list = string.split()
    if item in string_list:
        string_list.remove(item)
    string_list.append(item)
    if len(string_list) > limit:
        string_list.pop(0)
    return " ".join(string_list)


def calculate_score(
    likes: int = 0, dislikes: int = 0, saves: int = 0, comment_count: int = 0
):
    score = likes + dislikes + (comment_count * 2) + (saves * 3)
    return score


def calculate_trend_score(score: float, avg_score: float):
    avg = avg_score or 0
    s = score or 0
    return s - avg


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
