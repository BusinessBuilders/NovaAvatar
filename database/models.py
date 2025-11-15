"""SQLAlchemy database models for NovaAvatar."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, DateTime, Text, Float, Boolean, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from database.base import Base


class JobStatus(str, enum.Enum):
    """Job status enumeration."""
    PENDING = "pending"
    SCRAPING = "scraping"
    GENERATING_SCRIPT = "generating_script"
    GENERATING_IMAGE = "generating_image"
    GENERATING_AUDIO = "generating_audio"
    GENERATING_VIDEO = "generating_video"
    COMPLETED = "completed"
    FAILED = "failed"
    QUEUED_FOR_REVIEW = "queued_for_review"


class VideoJob(Base):
    """Video generation job model."""

    __tablename__ = "video_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(String(255), unique=True, index=True, nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False)

    # Content information
    content_item = Column(JSON, nullable=True)
    script = Column(JSON, nullable=True)

    # Generated files
    background_image = Column(String(512), nullable=True)
    audio_file = Column(String(512), nullable=True)
    video_file = Column(String(512), nullable=True)

    # Progress tracking
    progress = Column(Integer, default=0)
    error = Column(Text, nullable=True)

    # Metadata
    metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # User/API key association
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)
    api_key = relationship("APIKey", back_populates="jobs")

    def __repr__(self):
        return f"<VideoJob(job_id={self.job_id}, status={self.status})>"

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "job_id": self.job_id,
            "status": self.status.value,
            "content_item": self.content_item,
            "script": self.script,
            "background_image": self.background_image,
            "audio_file": self.audio_file,
            "video_file": self.video_file,
            "progress": self.progress,
            "error": self.error,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class ContentItemDB(Base):
    """Content item model for scraped content."""

    __tablename__ = "content_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Content fields
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    full_text = Column(Text, nullable=True)
    url = Column(String(1024), nullable=True)
    source_name = Column(String(255), nullable=True)

    # Metadata
    published_date = Column(DateTime, nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    relevance_score = Column(Float, nullable=True)
    tags = Column(JSON, default=list)

    # Search/filtering
    search_term = Column(String(255), nullable=True, index=True)

    # Processing status
    processed = Column(Boolean, default=False)
    job_id = Column(String(255), ForeignKey("video_jobs.job_id"), nullable=True)

    def __repr__(self):
        return f"<ContentItem(title={self.title[:50]}, source={self.source_name})>"

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "full_text": self.full_text,
            "url": self.url,
            "source_name": self.source_name,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "relevance_score": self.relevance_score,
            "tags": self.tags,
            "search_term": self.search_term,
            "processed": self.processed,
        }


class APIKey(Base):
    """API key model for authentication."""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Permissions
    is_active = Column(Boolean, default=True, nullable=False)
    permissions = Column(JSON, default=list)  # List of allowed endpoints

    # Rate limiting
    rate_limit = Column(Integer, default=100)  # Requests per hour
    requests_count = Column(Integer, default=0)
    last_request_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)

    # Relationships
    jobs = relationship("VideoJob", back_populates="api_key")

    def __repr__(self):
        return f"<APIKey(name={self.name}, active={self.is_active})>"

    def to_dict(self):
        """Convert model to dictionary (exclude sensitive key)."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "permissions": self.permissions,
            "rate_limit": self.rate_limit,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }

    def is_valid(self) -> bool:
        """Check if API key is valid and not expired."""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True


class SystemMetric(Base):
    """System metrics for monitoring."""

    __tablename__ = "system_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Metric details
    metric_name = Column(String(255), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_type = Column(String(50), nullable=False)  # counter, gauge, histogram

    # Labels/dimensions
    labels = Column(JSON, default=dict)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<SystemMetric(name={self.metric_name}, value={self.metric_value})>"


class AvatarProfile(Base):
    """Avatar profile for multi-avatar conversations."""

    __tablename__ = "avatar_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Profile details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    personality = Column(Text, nullable=False)  # Personality description for script generation
    voice_style = Column(String(100), nullable=True)  # Voice characteristics

    # Visual representation
    image_path = Column(String(512), nullable=True)  # Path to avatar image
    avatar_style = Column(String(100), default="professional")  # Visual style

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationships
    dialogues = relationship("DialogueLine", back_populates="avatar")

    def __repr__(self):
        return f"<AvatarProfile(name={self.name})>"

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "personality": self.personality,
            "voice_style": self.voice_style,
            "image_path": self.image_path,
            "avatar_style": self.avatar_style,
            "is_active": self.is_active,
        }


class Conversation(Base):
    """Multi-avatar conversation."""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(String(255), unique=True, index=True, nullable=False)

    # Conversation details
    title = Column(String(512), nullable=False)
    topic = Column(Text, nullable=False)
    context = Column(Text, nullable=True)  # Additional context for the conversation

    # Configuration
    num_avatars = Column(Integer, nullable=False)
    num_exchanges = Column(Integer, default=3)  # Number of back-and-forth exchanges
    conversation_style = Column(String(100), default="discussion")  # discussion, debate, interview, etc.

    # Generated content
    script = Column(JSON, nullable=True)  # Full conversation script

    # Final video
    final_video_path = Column(String(512), nullable=True)

    # Status
    status = Column(String(50), default="pending")  # pending, generating, completed, failed
    progress = Column(Integer, default=0)
    error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    dialogue_lines = relationship("DialogueLine", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(id={self.conversation_id}, title={self.title})>"

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "conversation_id": self.conversation_id,
            "title": self.title,
            "topic": self.topic,
            "num_avatars": self.num_avatars,
            "num_exchanges": self.num_exchanges,
            "conversation_style": self.conversation_style,
            "status": self.status,
            "progress": self.progress,
            "final_video_path": self.final_video_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class DialogueLine(Base):
    """Single line of dialogue in a conversation."""

    __tablename__ = "dialogue_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relationships
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    avatar_id = Column(UUID(as_uuid=True), ForeignKey("avatar_profiles.id"), nullable=False)

    # Dialogue details
    sequence = Column(Integer, nullable=False)  # Order in conversation
    text = Column(Text, nullable=False)
    duration_estimate = Column(Float, nullable=True)

    # Generated media
    audio_path = Column(String(512), nullable=True)
    video_path = Column(String(512), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="dialogue_lines")
    avatar = relationship("AvatarProfile", back_populates="dialogues")

    def __repr__(self):
        return f"<DialogueLine(sequence={self.sequence}, avatar={self.avatar_id})>"

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "sequence": self.sequence,
            "text": self.text,
            "duration_estimate": self.duration_estimate,
            "audio_path": self.audio_path,
            "video_path": self.video_path,
            "avatar": self.avatar.to_dict() if self.avatar else None,
        }
