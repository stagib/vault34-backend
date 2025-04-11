from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Post


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


def calculate_post_score(post: Post):
    now = datetime.now()
    hours_since = (now - post.date_created).total_seconds() / 3600
    reactions = post.likes + post.dislikes
    score = (
        reactions
        + post.comment_count * 2
        + post.saves * 3
        + post.views * 0.1
        + post.score
    ) / (hours_since + 1) ** 1.5
    return score
