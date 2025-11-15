"""API endpoints for multi-avatar conversations."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from database.models import AvatarProfile, Conversation
from services.conversation_orchestrator import ConversationOrchestrator
from api.dependencies.auth import get_api_key


router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


# Request/Response Models

class CreateAvatarRequest(BaseModel):
    """Request to create avatar profile."""
    name: str
    personality: str
    description: Optional[str] = None
    image_path: Optional[str] = None
    voice_style: Optional[str] = None
    avatar_style: str = "professional"


class AvatarResponse(BaseModel):
    """Avatar profile response."""
    id: str
    name: str
    personality: str
    description: Optional[str]
    image_path: Optional[str]
    voice_style: Optional[str]
    avatar_style: str
    is_active: bool


class CreateConversationRequest(BaseModel):
    """Request to create conversation."""
    title: str
    topic: str
    avatar_ids: List[str]  # List of avatar UUIDs
    num_exchanges: int = 3
    style: str = "discussion"  # discussion, debate, interview, panel
    context: Optional[str] = None
    stitch_videos: bool = True
    add_transitions: bool = True


class ConversationResponse(BaseModel):
    """Conversation response."""
    id: str
    conversation_id: str
    title: str
    topic: str
    num_avatars: int
    num_exchanges: int
    conversation_style: str
    status: str
    progress: int
    final_video_path: Optional[str]
    created_at: str
    completed_at: Optional[str]


class DialogueLineResponse(BaseModel):
    """Dialogue line response."""
    sequence: int
    avatar_name: str
    text: str
    audio_path: Optional[str]
    video_path: Optional[str]


# Avatar Profile Endpoints

@router.post("/avatars", response_model=AvatarResponse)
async def create_avatar(
    request: CreateAvatarRequest,
    db: Session = Depends(get_db),
    api_key = Depends(get_api_key)
):
    """
    Create a new avatar profile.

    Avatar profiles define the personality and appearance of avatars
    that can participate in conversations.

    Example:
        ```json
        {
            "name": "Dr. Sarah Chen",
            "personality": "AI researcher, enthusiastic about technology",
            "description": "Expert in machine learning",
            "image_path": "avatars/sarah.png",
            "voice_style": "professional, calm"
        }
        ```
    """
    orchestrator = ConversationOrchestrator(db)

    avatar = await orchestrator.create_avatar_profile(
        name=request.name,
        personality=request.personality,
        description=request.description,
        image_path=request.image_path,
        voice_style=request.voice_style,
        avatar_style=request.avatar_style
    )

    return AvatarResponse(
        id=str(avatar.id),
        name=avatar.name,
        personality=avatar.personality,
        description=avatar.description,
        image_path=avatar.image_path,
        voice_style=avatar.voice_style,
        avatar_style=avatar.avatar_style,
        is_active=avatar.is_active
    )


@router.get("/avatars", response_model=List[AvatarResponse])
async def list_avatars(
    active_only: bool = True,
    db: Session = Depends(get_db),
    api_key = Depends(get_api_key)
):
    """List all avatar profiles."""
    orchestrator = ConversationOrchestrator(db)
    avatars = orchestrator.list_avatar_profiles(active_only=active_only)

    return [
        AvatarResponse(
            id=str(a.id),
            name=a.name,
            personality=a.personality,
            description=a.description,
            image_path=a.image_path,
            voice_style=a.voice_style,
            avatar_style=a.avatar_style,
            is_active=a.is_active
        )
        for a in avatars
    ]


@router.get("/avatars/{avatar_id}", response_model=AvatarResponse)
async def get_avatar(
    avatar_id: str,
    db: Session = Depends(get_db),
    api_key = Depends(get_api_key)
):
    """Get avatar profile by ID."""
    orchestrator = ConversationOrchestrator(db)
    avatar = orchestrator.get_avatar_profile(avatar_id)

    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")

    return AvatarResponse(
        id=str(avatar.id),
        name=avatar.name,
        personality=avatar.personality,
        description=avatar.description,
        image_path=avatar.image_path,
        voice_style=avatar.voice_style,
        avatar_style=avatar.avatar_style,
        is_active=avatar.is_active
    )


# Conversation Endpoints

@router.post("", response_model=ConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    api_key = Depends(get_api_key)
):
    """
    Create a multi-avatar conversation.

    This generates a full conversation video with multiple avatars discussing a topic.

    **Process:**
    1. Generate dialogue using GPT-4
    2. Generate audio for each line (TTS)
    3. Generate video for each line (OmniAvatar)
    4. Stitch videos together

    **Example:**
        ```json
        {
            "title": "AI Ethics Discussion",
            "topic": "The impact of AI on employment",
            "avatar_ids": ["uuid1", "uuid2", "uuid3"],
            "num_exchanges": 5,
            "style": "panel",
            "stitch_videos": true,
            "add_transitions": true
        }
        ```

    **Conversation Styles:**
    - `discussion`: Balanced discussion, all participants contribute equally
    - `debate`: Opposing viewpoints, participants challenge each other
    - `interview`: Q&A format, first avatar asks questions
    - `panel`: Panel discussion with unique perspectives
    - `educational`: Explaining concepts with clarifying questions
    """
    orchestrator = ConversationOrchestrator(db)

    # Start generation in background
    conversation = await orchestrator.create_conversation(
        title=request.title,
        topic=request.topic,
        avatar_ids=request.avatar_ids,
        num_exchanges=request.num_exchanges,
        style=request.style,
        context=request.context,
        stitch_videos=request.stitch_videos,
        add_transitions=request.add_transitions
    )

    return ConversationResponse(
        id=str(conversation.id),
        conversation_id=conversation.conversation_id,
        title=conversation.title,
        topic=conversation.topic,
        num_avatars=conversation.num_avatars,
        num_exchanges=conversation.num_exchanges,
        conversation_style=conversation.conversation_style,
        status=conversation.status,
        progress=conversation.progress,
        final_video_path=conversation.final_video_path,
        created_at=conversation.created_at.isoformat(),
        completed_at=conversation.completed_at.isoformat() if conversation.completed_at else None
    )


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    limit: int = 50,
    db: Session = Depends(get_db),
    api_key = Depends(get_api_key)
):
    """List recent conversations."""
    orchestrator = ConversationOrchestrator(db)
    conversations = orchestrator.list_conversations(limit=limit)

    return [
        ConversationResponse(
            id=str(c.id),
            conversation_id=c.conversation_id,
            title=c.title,
            topic=c.topic,
            num_avatars=c.num_avatars,
            num_exchanges=c.num_exchanges,
            conversation_style=c.conversation_style,
            status=c.status,
            progress=c.progress,
            final_video_path=c.final_video_path,
            created_at=c.created_at.isoformat(),
            completed_at=c.completed_at.isoformat() if c.completed_at else None
        )
        for c in conversations
    ]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    api_key = Depends(get_api_key)
):
    """Get conversation by ID."""
    orchestrator = ConversationOrchestrator(db)
    conversation = orchestrator.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationResponse(
        id=str(conversation.id),
        conversation_id=conversation.conversation_id,
        title=conversation.title,
        topic=conversation.topic,
        num_avatars=conversation.num_avatars,
        num_exchanges=conversation.num_exchanges,
        conversation_style=conversation.conversation_style,
        status=conversation.status,
        progress=conversation.progress,
        final_video_path=conversation.final_video_path,
        created_at=conversation.created_at.isoformat(),
        completed_at=conversation.completed_at.isoformat() if conversation.completed_at else None
    )


@router.get("/{conversation_id}/dialogue", response_model=List[DialogueLineResponse])
async def get_conversation_dialogue(
    conversation_id: str,
    db: Session = Depends(get_db),
    api_key = Depends(get_api_key)
):
    """Get dialogue lines for a conversation."""
    conversation = db.query(Conversation).filter(
        Conversation.conversation_id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    dialogue_lines = sorted(conversation.dialogue_lines, key=lambda x: x.sequence)

    return [
        DialogueLineResponse(
            sequence=line.sequence,
            avatar_name=line.avatar.name,
            text=line.text,
            audio_path=line.audio_path,
            video_path=line.video_path
        )
        for line in dialogue_lines
    ]
