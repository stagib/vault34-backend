import re

from app.types import ReactionType


def normalize_text(query: str):
    q = query
    q = q.lower()
    q = q.strip()
    q = re.sub(r"\s+", " ", q)
    return q


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
