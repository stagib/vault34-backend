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
from app.types import (
    PrivacyType,
    ReactionType,
    TargetType,
    RatingType,
    FileType,
)


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False,
    )

    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    comments = relationship("Comment", back_populates="user", lazy="dynamic")
    vaults = relationship("Vault", back_populates="user", lazy="dynamic")


class VaultPost(Base):
    __tablename__ = "vault_post"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False,
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
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )

    title = Column(String, default="")
    preview_url = Column(String)
    sample_url = Column(String)
    file_url = Column(String)
    rating = Column(
        Enum(RatingType), nullable=False, default=RatingType.EXPLICIT
    )
    type = Column(Enum(FileType), nullable=False, default=FileType.IMAGE)
    tags = Column(String)
    top_tags = Column(JSONB, nullable=False, default=[])
    top_vaults = Column(JSONB, nullable=False, default=[])
    source_id = Column(Integer, index=True)
    source = Column(String)
    likes = Column(Integer, default=0, nullable=False)
    dislikes = Column(Integer, default=0, nullable=False)
    saves = Column(Integer, default=0, nullable=False)
    comment_count = Column(Integer, default=0, nullable=False)
    embedding = Column(Vector(512))
    last_updated = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False,
    )

    score = Column(Float, nullable=False, default=0, index=True)
    week_score = Column(Float, nullable=False, default=0, index=True)
    month_score = Column(Float, nullable=False, default=0, index=True)
    year_score = Column(Float, nullable=False, default=0, index=True)
    trend_score = Column(Float, nullable=False, default=0, index=True)

    comments = relationship("Comment", back_populates="post", lazy="dynamic")


class Vault(Base):
    __tablename__ = "vault"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False,
    )

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String)
    previews = Column(JSONB, nullable=False, default=[])
    post_count = Column(Integer, default=0, nullable=False)
    likes = Column(Integer, default=0, nullable=False)
    dislikes = Column(Integer, default=0, nullable=False)
    layout = Column(String, default="")
    privacy = Column(
        Enum(PrivacyType), nullable=False, default=PrivacyType.PRIVATE
    )
    last_updated = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False,
    )

    score = Column(Float, default=0, index=True, nullable=False)
    week_score = Column(Float, default=0, index=True, nullable=False)
    month_score = Column(Float, default=0, index=True, nullable=False)
    year_score = Column(Float, default=0, index=True, nullable=False)
    trend_score = Column(Float, default=0, index=True, nullable=False)

    user = relationship("User", back_populates="vaults")
    vault_posts = relationship(
        "VaultPost", back_populates="vault", cascade="all, delete-orphan"
    )


class Comment(Base):
    __tablename__ = "comment"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False,
    )

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("post.id"), nullable=False)
    content = Column(String, nullable=False)
    likes = Column(Integer, default=0, nullable=False)
    dislikes = Column(Integer, default=0, nullable=False)

    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")


class Reaction(Base):
    __tablename__ = "reaction"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False,
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
    query = Column(
        String, primary_key=True, index=True, unique=True, nullable=False
    )
    last_updated = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False,
    )
    score = Column(Integer, default=1, index=True, nullable=False)
    week_score = Column(Integer, default=1, index=True, nullable=False)
    month_score = Column(Integer, default=1, index=True, nullable=False)
    year_score = Column(Integer, default=1, index=True, nullable=False)
    trend_score = Column(Integer, default=0, index=True, nullable=False)


class SearchMetric(Base):
    __tablename__ = "search_metric"
    id = Column(Integer, primary_key=True, index=True)
    query = Column(String, index=True, nullable=False)
    date_created = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False,
    )
    score = Column(Integer, default=1, nullable=False)

    __table_args__ = (
        Index("ix_search_query_date_created", "query", "date_created"),
    )


class VaultMetric(Base):
    __tablename__ = "vault_metric"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False,
    )
    vault_id = Column(Integer, ForeignKey("vault.id"), nullable=False)
    score = Column(Float, default=0, nullable=False)

    __table_args__ = (
        Index("ix_vault_id_date_created", "vault_id", "date_created"),
    )


class PostMetric(Base):
    __tablename__ = "post_metric"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False,
    )
    post_id = Column(Integer, ForeignKey("post.id"), nullable=False)
    score = Column(Float, default=0, nullable=False)
    trend_score = Column(Float, default=0, nullable=False)

    __table_args__ = (
        Index("ix_post_id_date_created", "post_id", "date_created"),
    )


""" Index("ix_post_top_tags", Post.top_tags, postgresql_using="gin") """
