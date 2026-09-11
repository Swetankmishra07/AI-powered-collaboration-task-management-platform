from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.database import Base


class User(Base):
    """
    User ORM Model representing the `users` table in MySQL.
    Stores account credentials, hashed passwords, and owns tasks.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ORM Relationship: One User has Many Tasks
    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class Task(Base):
    """
    Task ORM Model representing the `tasks` table in MySQL.
    Stores task details, controlled status, and foreign key link to owner User.
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # ORM Relationship: Many Tasks belong to One User
    owner = relationship("User", back_populates="tasks")

    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}', user_id={self.user_id})>"
