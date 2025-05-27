from datetime import datetime, timezone, timedelta

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models import Search, SearchMetric
from app.utils import calculate_trend_score


""" metric functions """


def create_search_log(search: Search):
    search_metric = SearchMetric(query=search.query, score=search.score)
    return search_metric


def search_popularity_score(db: Session, query: str, days: int = 7):
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=days)

    result = (
        db.query(func.sum(SearchMetric.score).label("total_score"))
        .filter(
            SearchMetric.query == query,
            SearchMetric.date_created >= start_time,
        )
        .first()
    )
    return result.total_score or 0


def average_search_score(db: Session, query: str, days: int = 7):
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=days)

    result = (
        db.query(func.avg(SearchMetric.score).label("avg_score"))
        .filter(
            SearchMetric.query == query,
            SearchMetric.date_created >= start_time,
        )
        .first()
    )
    return result.avg_score or 0


def log_search_metric(db: Session, search: Search, now: datetime):
    prev_log = (
        db.query(SearchMetric)
        .filter(SearchMetric.query == search.query)
        .order_by(desc(SearchMetric.date_created))
        .first()
    )

    if not prev_log:
        log = create_search_log(search)
        db.add(log)
        return

    if prev_log.date_created + timedelta(days=1) < now:
        log = create_search_log(search)
        avg_score_14 = average_search_score(db, search.query, 14)
        avg_score_3 = average_search_score(db, search.query, 3)
        trend_score = calculate_trend_score(avg_score_3, avg_score_14)
        week_score = search_popularity_score(db, search.query, 7)
        month_score = search_popularity_score(db, search.query, 30)
        year_score = search_popularity_score(db, search.query, 365)

        search.trend_score = trend_score
        search.week_score = week_score
        search.month_score = month_score
        search.year_score = year_score
        search.score = search.score + 1
        db.add(log)
