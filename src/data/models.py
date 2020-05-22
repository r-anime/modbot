from sqlalchemy import ForeignKey, Column, Integer, Date, DateTime, String, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base


BaseModel = declarative_base()


class UserModel(BaseModel):
    __tablename__ = "users"

    psk = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    is_mod = Column(Boolean, nullable=False, default=False)
    is_deleted = Column(Boolean, nullable=False, default=False)


class PostModel(BaseModel):
    __tablename__ = "posts"

    psk = Column(Integer, primary_key=True)
    id = Column(String, unique=True)  # reddit base36 id
    title = Column(String, nullable=False)
    flair = Column(String)
    created_time = Column(DateTime, nullable=False)
    # user = relationship("UserModel", back_populates="posts")
    is_deleted = Column(Boolean, nullable=False, default=False)
    is_removed = Column(Boolean, nullable=False, default=False)


class SnapshotModel(BaseModel):
    __tablename__ = "snapshots"

    psk = Column(Integer, primary_key=True)
    datetime = Column(DateTime)  # really creation time, haven't renamed yet
    date = Column(Date)
    hour = Column(Integer)
    subscribers = Column(Integer)
    frontpage = relationship("SnapshotFrontpageModel", back_populates="snapshot")


class SnapshotFrontpageModel(BaseModel):
    __tablename__ = 'snapshot_frontpage'

    post_psk = Column(Integer, ForeignKey('posts.psk'))
    snapshot_psk = Column(Integer, ForeignKey('snapshots.psk'), primary_key=True)
    rank = Column(Integer, primary_key=True)
    score = Column(Integer)

    post = relationship("PostModel")
    snapshot = relationship("SnapshotModel")
