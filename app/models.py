from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db import Base
from app.types import PrivacyType, ReactionType, TargetType, RatingType


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )

    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    history = Column(String, nullable=False, default="")
    comments = relationship("Comment", back_populates="user", lazy="dynamic")
    vaults = relationship("Vault", back_populates="user", lazy="dynamic")


class VaultPost(Base):
    __tablename__ = "vault_post"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    index = Column(Integer, default=0, nullable=False)
    vault_id = Column(
        Integer, ForeignKey("vault.id"), nullable=False, index=True
    )
    post_id = Column(Integer, ForeignKey("post.id"), nullable=False)

    vault = relationship("Vault", back_populates="vault_posts")
    post = relationship("Post", backref="vault_post")

    __table_args__ = (Index("ix_vault_post", "post_id", "vault_id"),)


class Post(Base):
    __tablename__ = "post"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True), default=datetime.now(timezone.utc), index=True
    )

    title = Column(String)
    preview_url = Column(String)
    sample_url = Column(String)
    file_url = Column(String)
    rating = Column(Enum(RatingType), default=RatingType.EXPLICIT)
    tags = Column(String)
    top_tags = Column(JSONB, nullable=False)
    source = Column(String)
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    embedding = Column(Vector(512))
    last_updated = Column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )

    score = Column(Float, default=0, index=True)
    week_score = Column(Float, default=0, index=True)
    month_score = Column(Float, default=0, index=True)
    year_score = Column(Float, default=0, index=True)
    trend_score = Column(Float, default=0, index=True)

    comments = relationship("Comment", back_populates="post", lazy="dynamic")


class PostMetric(Base):
    __tablename__ = "post_metric"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    post_id = Column(Integer, ForeignKey("post.id"), nullable=False)
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)

    score = Column(Float, default=0)
    week_score = Column(Float, default=0)
    month_score = Column(Float, default=0)
    year_score = Column(Float, default=0)
    trend_score = Column(Float, default=0)

    __table_args__ = (
        Index("ix_post_id_date_created", "post_id", "date_created"),
    )


class Vault(Base):
    __tablename__ = "vault"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String)
    previews = Column(String, default="")
    post_count = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    layout = Column(String, default="")
    privacy = Column(
        Enum(PrivacyType), nullable=False, default=PrivacyType.PRIVATE
    )

    user = relationship("User", back_populates="vaults")
    vault_posts = relationship(
        "VaultPost", back_populates="vault", cascade="all, delete-orphan"
    )


class Comment(Base):
    __tablename__ = "comment"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("post.id"), nullable=False)
    content = Column(String, nullable=False)
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)

    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")


class Reaction(Base):
    __tablename__ = "reaction"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )

    user_id = Column(Integer, nullable=False)
    target_type = Column(Enum(TargetType), nullable=False)
    target_id = Column(Integer, nullable=False)
    type = Column(Enum(ReactionType), nullable=False)

    __table_args__ = (
        Index("ix_user_type_id", "user_id", "target_type", "target_id"),
        Index(
            "ix_date_created_type_id",
            "date_created",
            "target_type",
            "target_id",
        ),
    )


class Search(Base):
    __tablename__ = "search"
    query = Column(String, primary_key=True, index=True)
    count = Column(Integer, default=1, index=True)


class SearchLog(Base):
    __tablename__ = "search_log"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    query = Column(String)

    __table_args__ = (Index("ix_date_created", "date_created"),)


Index("ix_post_top_tags", Post.top_tags, postgresql_using="gin")
