from sqlalchemy import Column, Integer, String, DateTime, func
from pgvector.sqlalchemy import Vector

from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(DateTime, default=func.now(), nullable=True)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)


class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(DateTime, default=func.now(), nullable=True)

    post_id = Column(Integer)
    preview_url = Column(String)
    sample_url = Column(String)
    file_url = Column(String)
    owner = Column(String)
    rating = Column(String)
    tags = Column(String)
    source = Column(String)
    score = Column(Integer)

    embedding = Column(Vector(512))
    """ views = Column(Integer)
    view_time = Column(Integer)
    saves = Column(Integer)
    reactions = Column(Integer) """
