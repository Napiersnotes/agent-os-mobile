"""
Database models - FIXED: renamed 'metadata' column
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    input_text = Column(Text, nullable=False)
    priority = Column(Integer, default=1)
    status = Column(String, default="pending")
    # FIXED: renamed from 'metadata' to 'task_metadata'
    task_metadata = Column(Text, default="{}")
    device_info = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow, nullable=True)
    
    user = relationship("User", back_populates="tasks")
    results = relationship("TaskResult", back_populates="task", cascade="all, delete-orphan")

class TaskResult(Base):
    __tablename__ = "task_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    result = Column(Text, nullable=False)
    processing_time = Column(Integer, default=0)
    agent_used = Column(String)
    completed_at = Column(DateTime, default=datetime.utcnow)
    
    task = relationship("Task", back_populates="results")
