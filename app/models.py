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
from sqlalchemy.orm import relationship

from app.database import Base
from app.types import PrivacyType, ReactionType


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )

    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    history = Column(String, nullable=False, default="")
    reactions = relationship("Reaction", back_populates="user", lazy="dynamic")
    comments = relationship("Comment", back_populates="user", lazy="dynamic")
    vaults = relationship("Vault", back_populates="user", lazy="dynamic")


class VaultPost(Base):
    __tablename__ = "vault_post"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    index = Column(Integer, default=0, nullable=False)
    vault_id = Column(Integer, ForeignKey("vaults.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)

    vault = relationship("Vault", back_populates="vault_posts")
    post = relationship("Post", backref="vault_post")

    __table_args__ = (
        Index("ix_post_id", "post_id"),
        Index("ix_vault_id", "vault_id"),
    )


class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )

    post_id = Column(Integer, unique=True, index=True)
    preview_url = Column(String)
    sample_url = Column(String)
    file_url = Column(String)
    owner = Column(String)
    rating = Column(String)
    tags = Column(String)
    source = Column(String)

    reactions = relationship("Reaction", back_populates="post", lazy="dynamic")
    comments = relationship("Comment", back_populates="post", lazy="dynamic")

    embedding = Column(Vector(512))
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    views = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    score = Column(Float, default=0)

    __table_args__ = (
        Index("ix_post_score_desc", score.desc()),
        Index("ix_post_date_created", "date_created"),
    )


class Vault(Base):
    __tablename__ = "vaults"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
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
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    content = Column(String, nullable=False)
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)

    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")
    reactions = relationship(
        "Reaction", back_populates="comment", lazy="dynamic"
    )


class Reaction(Base):
    __tablename__ = "reactions"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="reactions")
    type = Column(Enum(ReactionType), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)
    comment_id = Column(Integer, ForeignKey("comments.id"), nullable=True)

    post = relationship("Post", back_populates="reactions")
    comment = relationship("Comment", back_populates="reactions")


class SearchQuery(Base):
    __tablename__ = "search_queries"
    query = Column(String, primary_key=True)
    count = Column(Integer, default=1)
