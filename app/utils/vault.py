from datetime import datetime, timezone, timedelta

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models import Vault, VaultMetric
from app.utils import calculate_score, calculate_trend_score


""" metric functions """


def create_vault_log(vault: Vault):
    vault_metric = VaultMetric(
        vault_id=vault.id,
        score=vault.score,
    )
    return vault_metric


def vault_popularity_score(db: Session, id: int, days: int = 7):
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=days)

    result = (
        db.query(func.sum(VaultMetric.score).label("total_score"))
        .filter(
            VaultMetric.vault_id == id,
            VaultMetric.date_created >= start_time,
        )
        .first()
    )
    return result.total_score or 0


def average_vault_score(db: Session, id: int, days: int = 7):
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=days)

    result = (
        db.query(func.avg(VaultMetric.score).label("avg_score"))
        .filter(
            VaultMetric.vault_id == id,
            VaultMetric.date_created >= start_time,
        )
        .first()
    )
    return result.avg_score or 0


def log_vault_metric(db: Session, vault: Vault, now: datetime):
    prev_log = (
        db.query(VaultMetric)
        .filter(VaultMetric.vault_id == vault.id)
        .order_by(desc(VaultMetric.date_created))
        .first()
    )

    if not prev_log:
        log = create_vault_log(vault)
        db.add(log)
        return

    if prev_log.date_created + timedelta(days=1) < now:
        log = create_vault_log(vault)
        avg_score_14 = average_vault_score(db, vault.id, 14)
        avg_score_3 = average_vault_score(db, vault.id, 3)
        trend_score = calculate_trend_score(avg_score_3, avg_score_14)
        week_score = vault_popularity_score(db, vault.id, 7)
        month_score = vault_popularity_score(db, vault.id, 30)
        year_score = vault_popularity_score(db, vault.id, 365)

        vault.trend_score = trend_score
        vault.week_score = week_score
        vault.month_score = month_score
        vault.year_score = year_score
        vault.score = calculate_score(vault.likes, vault.dislikes)
        db.add(log)
