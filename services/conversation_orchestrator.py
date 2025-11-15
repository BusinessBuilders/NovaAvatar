"""
Conversation Orchestrator for Multi-Avatar Videos.

Coordinates the full pipeline for generating multi-avatar conversation videos.
"""

import uuid
from typing import List, Optional, Callable
from pathlib import Path
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session

from database.models import AvatarProfile, Conversation, DialogueLine
from services.dialogue_generator import DialogueGenerator, AvatarPersona
from services.tts_service import TTSService
from services.avatar_service import AvatarService
from services.video_stitcher import VideoStitcher, VideoSegment


class ConversationOrchestrator:
    """
    Orchestrates multi-avatar conversation generation.

    Pipeline:
    1. Load avatar profiles
    2. Generate dialogue using GPT-4
    3. Generate audio for each line (TTS)
    4. Generate video for each line (OmniAvatar)
    5. Stitch videos together
    """

    def __init__(
        self,
        db: Session,
        storage_dir: str = "storage",
        use_14b_model: bool = False
    ):
        """
        Initialize conversation orchestrator.

        Args:
            db: Database session
            storage_dir: Base storage directory
            use_14b_model: Use 14B model for better quality (requires more VRAM)
        """
        self.db = db
        self.storage_dir = Path(storage_dir)
        self.conversation_dir = self.storage_dir / "conversations"
        self.conversation_dir.mkdir(parents=True, exist_ok=True)

        # Initialize services
        self.dialogue_generator = DialogueGenerator()
        self.tts_service = TTSService()
        self.avatar_service = AvatarService(use_14b_model=use_14b_model)
        self.video_stitcher = VideoStitcher(output_dir=str(self.conversation_dir))

        logger.info("Conversation orchestrator initialized")

    async def create_conversation(
        self,
        title: str,
        topic: str,
        avatar_ids: List[str],
        num_exchanges: int = 3,
        style: str = "discussion",
        context: Optional[str] = None,
        stitch_videos: bool = True,
        add_transitions: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Conversation:
        """
        Create a complete multi-avatar conversation video.

        Args:
            title: Conversation title
            topic: Topic to discuss
            avatar_ids: List of avatar profile IDs (UUIDs)
            num_exchanges: Number of dialogue exchanges
            style: Conversation style (discussion, debate, interview, etc.)
            context: Additional context
            stitch_videos: Stitch individual videos into one
            add_transitions: Add transitions when stitching
            progress_callback: Progress callback(percent, status)

        Returns:
            Conversation object with all generated content

        Example:
            >>> conversation = await orchestrator.create_conversation(
            ...     title="AI Ethics Discussion",
            ...     topic="The ethical implications of AGI",
            ...     avatar_ids=[alice_id, bob_id, carol_id],
            ...     num_exchanges=5,
            ...     style="panel"
            ... )
        """
        logger.info(f"Creating conversation: '{title}' with {len(avatar_ids)} avatars")

        # Create conversation record
        conversation_id = str(uuid.uuid4())
        conversation = Conversation(
            conversation_id=conversation_id,
            title=title,
            topic=topic,
            context=context,
            num_avatars=len(avatar_ids),
            num_exchanges=num_exchanges,
            conversation_style=style,
            status="generating"
        )
        self.db.add(conversation)
        self.db.commit()

        try:
            # Step 1: Load avatar profiles
            logger.info(f"[{conversation_id}] Loading {len(avatar_ids)} avatar profiles")
            if progress_callback:
                progress_callback(5, "Loading avatar profiles...")

            avatars = []
            for avatar_id in avatar_ids:
                avatar = self.db.query(AvatarProfile).filter(
                    AvatarProfile.id == avatar_id
                ).first()

                if not avatar:
                    raise ValueError(f"Avatar not found: {avatar_id}")

                avatars.append(avatar)

            # Step 2: Generate dialogue
            logger.info(f"[{conversation_id}] Generating dialogue")
            if progress_callback:
                progress_callback(10, "Generating dialogue...")

            # Convert to personas for dialogue generation
            personas = [
                AvatarPersona(
                    name=a.name,
                    personality=a.personality,
                    voice_style=a.voice_style
                )
                for a in avatars
            ]

            dialogue = await self.dialogue_generator.generate_conversation(
                topic=topic,
                avatars=personas,
                num_exchanges=num_exchanges,
                style=style,
                context=context
            )

            # Save script to conversation
            conversation.script = {
                "title": dialogue.title,
                "exchanges": [e.dict() for e in dialogue.exchanges]
            }
            self.db.commit()

            # Step 3: Generate audio and video for each line
            logger.info(f"[{conversation_id}] Generating {len(dialogue.exchanges)} dialogue lines")

            video_segments = []
            total_exchanges = len(dialogue.exchanges)

            for i, exchange in enumerate(dialogue.exchanges):
                # Find matching avatar
                avatar = next((a for a in avatars if a.name == exchange.avatar_name), None)
                if not avatar:
                    logger.warning(f"Avatar '{exchange.avatar_name}' not found, using first avatar")
                    avatar = avatars[0]

                logger.info(f"[{conversation_id}] [{i+1}/{total_exchanges}] {avatar.name}: {exchange.text[:50]}...")

                # Calculate progress (10% for setup, 80% for generation, 10% for stitching)
                base_progress = 10
                gen_progress = int(base_progress + (i / total_exchanges) * 80)

                if progress_callback:
                    progress_callback(gen_progress, f"{avatar.name} speaking...")

                # Create dialogue line record
                dialogue_line = DialogueLine(
                    conversation_id=conversation.id,
                    avatar_id=avatar.id,
                    sequence=i,
                    text=exchange.text,
                    duration_estimate=len(exchange.text.split()) / 150 * 60  # Rough estimate
                )
                self.db.add(dialogue_line)
                self.db.commit()

                # Generate audio
                logger.info(f"[{conversation_id}]   Generating audio...")
                audio = await self.tts_service.generate_speech(
                    text=exchange.text,
                    speed=1.0
                )
                dialogue_line.audio_path = audio.audio_path

                # Generate video
                logger.info(f"[{conversation_id}]   Generating video...")

                # Use avatar's image or default
                image_path = avatar.image_path or "examples/images/bill.png"

                # Create prompt for this specific line
                video_prompt = f"{avatar.description or avatar.name} speaking: {exchange.text[:100]}"

                video = await self.avatar_service.generate_video(
                    prompt=video_prompt,
                    image_path=image_path,
                    audio_path=audio.audio_path,
                    output_name=f"conv_{conversation_id}_line_{i}"
                )

                dialogue_line.video_path = video.video_path
                self.db.commit()

                # Add to segments for stitching
                video_segments.append(VideoSegment(
                    video_path=video.video_path,
                    avatar_name=avatar.name,
                    duration=video.duration
                ))

                logger.info(f"[{conversation_id}]   ✓ Line {i+1} complete")

            # Step 4: Stitch videos together
            if stitch_videos and len(video_segments) > 1:
                logger.info(f"[{conversation_id}] Stitching {len(video_segments)} videos together")
                if progress_callback:
                    progress_callback(90, "Stitching videos...")

                stitched = self.video_stitcher.stitch_conversation(
                    segments=video_segments,
                    output_name=f"conversation_{conversation_id}",
                    add_transitions=add_transitions
                )

                conversation.final_video_path = stitched.video_path
                logger.info(f"[{conversation_id}] Final video: {stitched.video_path}")

            # Mark as completed
            conversation.status = "completed"
            conversation.progress = 100
            conversation.completed_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"[{conversation_id}] Conversation complete!")
            if progress_callback:
                progress_callback(100, "Complete!")

            return conversation

        except Exception as e:
            logger.error(f"[{conversation_id}] Conversation generation failed: {e}")
            conversation.status = "failed"
            conversation.error = str(e)
            self.db.commit()
            raise

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID."""
        return self.db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()

    def list_conversations(self, limit: int = 50) -> List[Conversation]:
        """List recent conversations."""
        return self.db.query(Conversation).order_by(
            Conversation.created_at.desc()
        ).limit(limit).all()

    async def create_avatar_profile(
        self,
        name: str,
        personality: str,
        description: Optional[str] = None,
        image_path: Optional[str] = None,
        voice_style: Optional[str] = None,
        avatar_style: str = "professional"
    ) -> AvatarProfile:
        """
        Create a new avatar profile.

        Args:
            name: Avatar name
            personality: Personality description for dialogue generation
            description: Optional description
            image_path: Path to avatar image
            voice_style: Voice characteristics
            avatar_style: Visual style

        Returns:
            Created AvatarProfile

        Example:
            >>> avatar = await orchestrator.create_avatar_profile(
            ...     name="Dr. Sarah Chen",
            ...     personality="Expert AI researcher, thoughtful and measured in speech",
            ...     description="AI safety researcher at top university",
            ...     image_path="avatars/sarah.png",
            ...     voice_style="calm, professional"
            ... )
        """
        logger.info(f"Creating avatar profile: {name}")

        avatar = AvatarProfile(
            name=name,
            personality=personality,
            description=description,
            image_path=image_path,
            voice_style=voice_style,
            avatar_style=avatar_style
        )

        self.db.add(avatar)
        self.db.commit()
        self.db.refresh(avatar)

        logger.info(f"Avatar profile created: {name} (ID: {avatar.id})")
        return avatar

    def get_avatar_profile(self, avatar_id: str) -> Optional[AvatarProfile]:
        """Get avatar profile by ID."""
        return self.db.query(AvatarProfile).filter(
            AvatarProfile.id == avatar_id
        ).first()

    def list_avatar_profiles(self, active_only: bool = True) -> List[AvatarProfile]:
        """List avatar profiles."""
        query = self.db.query(AvatarProfile)
        if active_only:
            query = query.filter(AvatarProfile.is_active == True)
        return query.order_by(AvatarProfile.created_at.desc()).all()


# Example usage
if __name__ == "__main__":
    import asyncio
    from database.base import SessionLocal

    async def main():
        db = SessionLocal()
        orchestrator = ConversationOrchestrator(db)

        # Create avatar profiles
        alice = await orchestrator.create_avatar_profile(
            name="Alice",
            personality="Enthusiastic AI researcher who loves explaining complex topics",
            image_path="examples/images/avatar_alice.png"
        )

        bob = await orchestrator.create_avatar_profile(
            name="Bob",
            personality="Skeptical journalist who asks tough questions",
            image_path="examples/images/avatar_bob.png"
        )

        # Create conversation
        def progress(percent, status):
            print(f"[{percent}%] {status}")

        conversation = await orchestrator.create_conversation(
            title="The Future of AI",
            topic="How will artificial intelligence change society in the next 10 years?",
            avatar_ids=[str(alice.id), str(bob.id)],
            num_exchanges=4,
            style="discussion",
            progress_callback=progress
        )

        print(f"\n✓ Conversation created!")
        print(f"ID: {conversation.conversation_id}")
        print(f"Video: {conversation.final_video_path}")

        db.close()

    asyncio.run(main())
