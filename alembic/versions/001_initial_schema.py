"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2025-11-15 14:18:12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON
import uuid


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema."""

    # Create API keys table
    op.create_table(
        'api_keys',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('key', sa.String(64), unique=True, index=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('permissions', JSON, default=list),
        sa.Column('rate_limit', sa.Integer, default=100),
        sa.Column('requests_count', sa.Integer, default=0),
        sa.Column('last_request_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
    )

    # Create video jobs table
    op.create_table(
        'video_jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('job_id', sa.String(255), unique=True, index=True, nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('content_item', JSON, nullable=True),
        sa.Column('script', JSON, nullable=True),
        sa.Column('background_image', sa.String(512), nullable=True),
        sa.Column('audio_file', sa.String(512), nullable=True),
        sa.Column('video_file', sa.String(512), nullable=True),
        sa.Column('progress', sa.Integer, default=0),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('metadata', JSON, default=dict),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('api_key_id', UUID(as_uuid=True), sa.ForeignKey('api_keys.id'), nullable=True),
    )

    # Create content items table
    op.create_table(
        'content_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('full_text', sa.Text, nullable=True),
        sa.Column('url', sa.String(1024), nullable=True),
        sa.Column('source_name', sa.String(255), nullable=True),
        sa.Column('published_date', sa.DateTime, nullable=True),
        sa.Column('scraped_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('relevance_score', sa.Float, nullable=True),
        sa.Column('tags', JSON, default=list),
        sa.Column('search_term', sa.String(255), nullable=True, index=True),
        sa.Column('processed', sa.Boolean, default=False),
        sa.Column('job_id', sa.String(255), sa.ForeignKey('video_jobs.job_id'), nullable=True),
    )

    # Create system metrics table
    op.create_table(
        'system_metrics',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('metric_name', sa.String(255), nullable=False, index=True),
        sa.Column('metric_value', sa.Float, nullable=False),
        sa.Column('metric_type', sa.String(50), nullable=False),
        sa.Column('labels', JSON, default=dict),
        sa.Column('timestamp', sa.DateTime, nullable=False, server_default=sa.func.now(), index=True),
    )

    # Create avatar profiles table
    op.create_table(
        'avatar_profiles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('personality', sa.Text, nullable=False),
        sa.Column('voice_style', sa.String(100), nullable=True),
        sa.Column('image_path', sa.String(512), nullable=True),
        sa.Column('avatar_style', sa.String(100), default='professional'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('is_active', sa.Boolean, default=True),
    )

    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('conversation_id', sa.String(255), unique=True, index=True, nullable=False),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('topic', sa.Text, nullable=False),
        sa.Column('context', sa.Text, nullable=True),
        sa.Column('num_avatars', sa.Integer, nullable=False),
        sa.Column('num_exchanges', sa.Integer, default=3),
        sa.Column('conversation_style', sa.String(100), default='discussion'),
        sa.Column('script', JSON, nullable=True),
        sa.Column('final_video_path', sa.String(512), nullable=True),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('progress', sa.Integer, default=0),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('completed_at', sa.DateTime, nullable=True),
    )

    # Create dialogue lines table
    op.create_table(
        'dialogue_lines',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('conversation_id', UUID(as_uuid=True), sa.ForeignKey('conversations.id'), nullable=False),
        sa.Column('avatar_id', UUID(as_uuid=True), sa.ForeignKey('avatar_profiles.id'), nullable=False),
        sa.Column('sequence', sa.Integer, nullable=False),
        sa.Column('text', sa.Text, nullable=False),
        sa.Column('duration_estimate', sa.Float, nullable=True),
        sa.Column('audio_path', sa.String(512), nullable=True),
        sa.Column('video_path', sa.String(512), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # Create indexes
    op.create_index('idx_video_jobs_status', 'video_jobs', ['status'])
    op.create_index('idx_video_jobs_created', 'video_jobs', ['created_at'])
    op.create_index('idx_conversations_status', 'conversations', ['status'])
    op.create_index('idx_dialogue_lines_conversation', 'dialogue_lines', ['conversation_id', 'sequence'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('dialogue_lines')
    op.drop_table('conversations')
    op.drop_table('avatar_profiles')
    op.drop_table('system_metrics')
    op.drop_table('content_items')
    op.drop_table('video_jobs')
    op.drop_table('api_keys')
