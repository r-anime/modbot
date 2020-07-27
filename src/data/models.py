from sqlalchemy import ForeignKey, Column, Integer, Date, DateTime, String, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base


BaseModel = declarative_base()


class UserModel(BaseModel):
    __tablename__ = "users"
    __table_args__ = {"schema": "reddit"}

    psk = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    name_formatted = Column(String, unique=True)
    is_mod = Column(Boolean, nullable=False, default=False)
    is_deleted = Column(Boolean, nullable=False, default=False)

    posts = relationship("PostModel", back_populates="author")


class PostModel(BaseModel):
    __tablename__ = "posts"
    __table_args__ = {"schema": "reddit"}

    psk = Column(Integer, primary_key=True)
    id = Column(String, unique=True)  # reddit base36 id
    title = Column(String, nullable=False)
    flair_id = Column(String)
    flair_text = Column(String)
    created_time = Column(DateTime, nullable=False)
    author_psk = Column(Integer, ForeignKey("reddit.users.psk"))
    is_deleted = Column(Boolean, nullable=False, default=False)
    is_removed = Column(Boolean, nullable=False, default=False)

    author = relationship("UserModel")


class SnapshotModel(BaseModel):
    __tablename__ = "snapshots"
    __table_args__ = {"schema": "reddit"}

    psk = Column(Integer, primary_key=True)
    created_time = Column(DateTime)
    date = Column(Date)
    hour = Column(Integer)
    subscribers = Column(Integer)

    frontpage = relationship("SnapshotFrontpageModel", back_populates="snapshot")


class SnapshotFrontpageModel(BaseModel):
    __tablename__ = "snapshot_frontpage"
    __table_args__ = {"schema": "reddit"}

    post_psk = Column(Integer, ForeignKey("reddit.posts.psk"))
    snapshot_psk = Column(Integer, ForeignKey("reddit.snapshots.psk"), primary_key=True)
    rank = Column(Integer, primary_key=True)
    score = Column(Integer)

    post = relationship("PostModel")
    snapshot = relationship("SnapshotModel")
