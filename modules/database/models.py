"""
Database models for CoderAgent
Defines all database tables and relationships
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    """User model - stores Discord user information"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    discord_user_id = Column(String(50), unique=True, nullable=False, index=True)
    discord_username = Column(String(255), nullable=False)
    discord_discriminator = Column(String(10))
    
    # User settings
    is_active = Column(Boolean, default=True)
    is_banned = Column(Boolean, default=False)
    model_preset = Column(String(50), default="balance")  # "high", "balance", "low"
    language = Column(String(10), default="en-US")  # "en-US", "ja"
    
    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="user", cascade="all, delete-orphan")
    requirements = relationship("Requirement", back_populates="user", cascade="all, delete-orphan", primaryjoin="User.id == Requirement.user_id")
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    def __repr__(self):
        return f"<User {self.discord_user_id}: {self.discord_username}>"


class APIKey(Base):
    """APIKey model - stores encrypted OpenRouter API keys"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Encrypted API key (stored encrypted, never in plaintext)
    encrypted_key = Column(Text, nullable=False)
    key_name = Column(String(255), default="Default")
    
    # Key metadata
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="api_keys")
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    def __repr__(self):
        return f"<APIKey {self.id} for User {self.user_id}>"


class Session(Base):
    """Session model - stores coding session information"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True)
    session_uuid = Column(String(36), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Session details
    guild_id = Column(String(50), nullable=False)
    channel_id = Column(String(50), nullable=True)
    
    # Session state
    is_active = Column(Boolean, default=True)
    project_name = Column(String(255), nullable=True)
    
    # AI model used
    ai_model = Column(String(255), default="openrouter/auto")
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="session", cascade="all, delete-orphan")
    requirements = relationship("Requirement", back_populates="session", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="session", cascade="all, delete-orphan", primaryjoin="foreign(Session.id) == Task.session_id")
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    def __repr__(self):
        return f"<Session {self.session_uuid} for User {self.user_id}>"


class Message(Base):
    """Message model - stores conversation history"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    
    # Message content
    role = Column(String(50), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    
    # Token usage
    token_input = Column(Integer, default=0)
    token_output = Column(Integer, default=0)
    
    # Relationship
    session = relationship("Session", back_populates="messages")
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    
    def __repr__(self):
        return f"<Message {self.id} in Session {self.session_id}>"


class Project(Base):
    """Project model - stores generated project information"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    
    # Project details
    project_name = Column(String(255), nullable=False)
    project_description = Column(Text, nullable=True)
    file_count = Column(Integer, default=0)
    
    # Metadata
    project_metadata = Column(JSON, nullable=True)
    
    # Relationship
    session = relationship("Session", back_populates="projects")
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    def __repr__(self):
        return f"<Project {self.project_name} in Session {self.session_id}>"


class UsageLog(Base):
    """UsageLog model - tracks API usage and costs"""
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Usage details
    model = Column(String(255), nullable=False)
    token_input = Column(Integer, default=0)
    token_output = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    
    # Relationship
    user = relationship("User", back_populates="usage_logs")
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    
    def __repr__(self):
        return f"<UsageLog {self.id} for User {self.user_id}>"


class SystemLog(Base):
    """SystemLog model - stores system events and errors"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True)
    
    # Log details
    event_type = Column(String(100), nullable=False)  # "bot_start", "error", "permission_denied", etc.
    message = Column(Text, nullable=False)
    severity = Column(String(50), default="INFO")  # "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    
    # Context
    user_id = Column(String(50), nullable=True)
    guild_id = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    
    def __repr__(self):
        return f"<SystemLog {self.event_type} at {self.created_at}>"


class Requirement(Base):
    """Requirement model - stores structured requirement JSONs"""
    __tablename__ = "requirements"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Requirement data
    json_data = Column(JSON, nullable=False)
    status = Column(String(50), default="pending")  # "pending", "approved", "completed"
    
    # Relationship
    session = relationship("Session", back_populates="requirements")
    user = relationship("User", back_populates="requirements")
    tasks = relationship("Task", back_populates="requirement", cascade="all, delete-orphan")
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    def __repr__(self):
        return f"<Requirement {self.id} for Session {self.session_id} (Status: {self.status})>"


class Task(Base):
    """Task model - stores planned tasks for agents"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    requirement_id = Column(Integer, ForeignKey("requirements.id"), nullable=False, index=True)

    task_id = Column(Integer, nullable=False) # Unique ID within a requirement
    type = Column(String(50), nullable=False) # e.g., "create_project_structure", "create_flask_app", "execute_test"
    role = Column(String(50), nullable=False) # e.g., "coder", "executor", "debugger"
    status = Column(String(50), default="pending") # "pending", "in_progress", "completed", "failed"
    description = Column(Text, nullable=True)
    assigned_to = Column(String(50), nullable=True) # Which agent is assigned
    result = Column(JSON, nullable=True)

    # Relationships
    session = relationship("Session", back_populates="tasks")
    user = relationship("User", back_populates="tasks")
    requirement = relationship("Requirement", back_populates="tasks")

    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    def __repr__(self):
        return f"<Task {self.task_id} ({self.type}) for Requirement {self.requirement_id} (Status: {self.status})>"
