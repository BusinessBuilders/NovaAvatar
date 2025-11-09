"""
Pipeline Orchestrator
Coordinates the full content-to-video pipeline.
"""

import os
import json
from typing import Optional, Dict, List, Callable
from pathlib import Path
from datetime import datetime
from enum import Enum
from loguru import logger
from pydantic import BaseModel, Field
import redis
from rq import Queue
from rq.job import Job

from services.content_scraper import ContentScraper, ContentItem
from services.script_generator import ScriptGenerator, ScriptStyle, VideoScript
from services.image_generator import ImageGenerator, GeneratedImage
from services.image_compositor import ImageCompositor, CompositeImage
from services.tts_service import TTSService, GeneratedAudio
from services.avatar_service import AvatarService, AvatarVideo


class JobStatus(str, Enum):
    """Job status enum."""
    PENDING = "pending"
    SCRAPING = "scraping"
    GENERATING_SCRIPT = "generating_script"
    GENERATING_IMAGE = "generating_image"
    GENERATING_AUDIO = "generating_audio"
    GENERATING_VIDEO = "generating_video"
    COMPLETED = "completed"
    FAILED = "failed"
    QUEUED_FOR_REVIEW = "queued_for_review"


class VideoJob(BaseModel):
    """Represents a video generation job."""

    job_id: str
    status: JobStatus = JobStatus.PENDING
    content_item: Optional[Dict] = None
    script: Optional[Dict] = None
    background_image: Optional[str] = None
    audio_file: Optional[str] = None
    video_file: Optional[str] = None
    error: Optional[str] = None
    progress: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PipelineOrchestrator:
    """
    Orchestrates the full content-to-video pipeline.

    Pipeline stages:
    1. Content Scraping
    2. Script Generation
    3. Image Generation
    4. Audio Generation (TTS)
    5. Video Generation (Avatar)
    6. Review Queue
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        storage_dir: str = "storage",
        enable_queue: bool = True,
        auto_approve: bool = False
    ):
        """
        Initialize orchestrator.

        Args:
            redis_url: Redis connection URL
            storage_dir: Base storage directory
            enable_queue: Use Redis queue for async processing
            auto_approve: Auto-approve videos (skip review queue)
        """

        self.storage_dir = Path(storage_dir)
        self.queue_dir = self.storage_dir / "queue"
        self.queue_dir.mkdir(parents=True, exist_ok=True)

        self.enable_queue = enable_queue
        self.auto_approve = auto_approve

        # Initialize services
        self.content_scraper = ContentScraper()
        self.script_generator = ScriptGenerator()
        self.image_generator = ImageGenerator()
        self.image_compositor = ImageCompositor()
        self.tts_service = TTSService()
        self.avatar_service = AvatarService()

        # Initialize Redis queue if enabled
        if self.enable_queue:
            try:
                self.redis_conn = redis.from_url(redis_url)
                self.queue = Queue(connection=self.redis_conn)
                logger.info("Redis queue initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis queue: {e}")
                self.enable_queue = False
                self.redis_conn = None
                self.queue = None
        else:
            self.redis_conn = None
            self.queue = None

        # Job storage (simple file-based for now)
        self.jobs_file = self.storage_dir / "jobs.json"
        self.jobs: Dict[str, VideoJob] = self._load_jobs()

        logger.info("Pipeline orchestrator initialized")

    def _load_jobs(self) -> Dict[str, VideoJob]:
        """Load jobs from storage."""

        if self.jobs_file.exists():
            try:
                with open(self.jobs_file, 'r') as f:
                    data = json.load(f)
                    return {k: VideoJob(**v) for k, v in data.items()}
            except Exception as e:
                logger.warning(f"Error loading jobs: {e}")

        return {}

    def _save_jobs(self):
        """Save jobs to storage."""

        try:
            with open(self.jobs_file, 'w') as f:
                data = {k: v.dict() for k, v in self.jobs.items()}
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving jobs: {e}")

    async def scrape_content(
        self,
        max_items: int = 10,
        sources: Optional[List[str]] = None,
        search_term: Optional[str] = None
    ) -> List[ContentItem]:
        """Scrape content from configured sources."""

        if search_term:
            logger.info(f"Scraping content for '{search_term}' (max {max_items} items)...")
        else:
            logger.info(f"Scraping content (max {max_items} items)...")

        items = await self.content_scraper.scrape_all(
            max_items_per_source=max_items,
            search_term=search_term
        )

        logger.info(f"Scraped {len(items)} content items")
        return items

    async def create_video_from_content(
        self,
        content_item: ContentItem,
        style: ScriptStyle = ScriptStyle.PROFESSIONAL,
        duration: int = 45,
        avatar_image: Optional[str] = None,
        background_prompt: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> VideoJob:
        """
        Create video from a content item (full pipeline).

        Args:
            content_item: Content to generate video from
            style: Script style
            duration: Target duration in seconds
            progress_callback: Progress callback(percent, status)

        Returns:
            VideoJob with all generated assets
        """

        # Create job
        import uuid
        job_id = str(uuid.uuid4())

        job = VideoJob(
            job_id=job_id,
            content_item=content_item.dict(),
            status=JobStatus.GENERATING_SCRIPT
        )

        self.jobs[job_id] = job
        self._save_jobs()

        try:
            # Stage 0: Fetch full article if needed
            if content_item.url and not content_item.full_text:
                logger.info(f"[{job_id}] Fetching full article...")
                if progress_callback:
                    progress_callback(5, "Fetching full article...")

                full_text = await self.content_scraper.fetch_full_article(content_item.url)
                if full_text:
                    content_item.full_text = full_text
                    logger.info(f"[{job_id}] Full article fetched ({len(full_text)} chars)")

            # Stage 1: Generate script
            logger.info(f"[{job_id}] Generating script...")
            if progress_callback:
                progress_callback(10, "Generating script...")

            # Use full article text if available, otherwise use description
            content_for_script = content_item.full_text if content_item.full_text else content_item.description

            script = await self.script_generator.generate_script(
                content_title=content_item.title,
                content_description=content_for_script,
                style=style,
                duration=duration
            )

            job.script = script.dict()
            job.status = JobStatus.GENERATING_IMAGE
            job.progress = 30
            self._save_jobs()

            # Stage 2: Generate background image
            logger.info(f"[{job_id}] Generating background image...")
            if progress_callback:
                progress_callback(30, "Generating background...")

            # Use custom background prompt if provided, otherwise use GPT-4 scene description
            bg_description = background_prompt if background_prompt else script.scene_description
            logger.info(f"[{job_id}] Background: {bg_description[:100]}...")

            background = await self.image_generator.generate_background(
                scene_description=bg_description,
                style="photorealistic"
            )

            job.background_image = background.image_path
            job.status = JobStatus.GENERATING_AUDIO
            job.progress = 50
            self._save_jobs()

            # Stage 3: Generate audio (TTS)
            logger.info(f"[{job_id}] Generating audio...")
            if progress_callback:
                progress_callback(50, "Generating audio...")

            audio = await self.tts_service.generate_speech(
                text=script.script,
                speed=1.0
            )

            job.audio_file = audio.audio_path
            job.status = JobStatus.GENERATING_VIDEO
            job.progress = 60
            self._save_jobs()

            # Stage 3.5: Composite avatar onto background
            import os
            avatar_path = avatar_image if avatar_image else os.getenv("BASE_AVATAR_PATH", "examples/images/bill.png")
            use_compositing = os.getenv("USE_AVATAR_COMPOSITING", "true").lower() == "true"

            if use_compositing:
                logger.info(f"[{job_id}] Compositing avatar onto background...")
                if progress_callback:
                    progress_callback(60, "Compositing avatar onto background...")

                composite = await self.image_compositor.composite_avatar(
                    avatar_path=avatar_path,
                    background_path=background.image_path,
                    output_name=f"composite_{job_id}.png"
                )
                final_image_path = composite.composite_path
                logger.info(f"[{job_id}] Composite created: {final_image_path}")
            else:
                # Use avatar directly without compositing
                final_image_path = avatar_path
                logger.info(f"[{job_id}] Using avatar directly: {final_image_path}")

            job.progress = 70
            self._save_jobs()

            # Stage 4: Generate avatar video
            logger.info(f"[{job_id}] Generating avatar video...")
            if progress_callback:
                progress_callback(70, "Generating avatar video...")

            # Build prompt from script title and scene
            video_prompt = f"{script.title}. {script.scene_description}"

            video = await self.avatar_service.generate_video(
                prompt=video_prompt,
                image_path=final_image_path,
                audio_path=audio.audio_path,
                output_name=f"video_{job_id}",
                progress_callback=lambda p, s: progress_callback(
                    70 + int(p * 0.25), s
                ) if progress_callback else None
            )

            job.video_file = video.video_path
            job.progress = 100

            # Move to review queue or complete
            if self.auto_approve:
                job.status = JobStatus.COMPLETED
            else:
                job.status = JobStatus.QUEUED_FOR_REVIEW
                self._add_to_review_queue(job)

            job.updated_at = datetime.now()
            self._save_jobs()

            logger.info(f"[{job_id}] Pipeline complete!")
            if progress_callback:
                progress_callback(100, "Complete!")

            return job

        except Exception as e:
            logger.error(f"[{job_id}] Pipeline failed: {e}")
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.updated_at = datetime.now()
            self._save_jobs()

            if progress_callback:
                progress_callback(-1, f"Failed: {str(e)}")

            raise

    def _add_to_review_queue(self, job: VideoJob):
        """Add job to review queue."""

        queue_file = self.queue_dir / f"{job.job_id}.json"

        try:
            with open(queue_file, 'w') as f:
                json.dump(job.dict(), f, indent=2, default=str)

            logger.info(f"Added to review queue: {job.job_id}")

        except Exception as e:
            logger.error(f"Error adding to review queue: {e}")

    def get_review_queue(self) -> List[VideoJob]:
        """Get all videos in review queue."""

        queue_items = []

        for queue_file in self.queue_dir.glob("*.json"):
            try:
                with open(queue_file, 'r') as f:
                    data = json.load(f)
                    job = VideoJob(**data)
                    queue_items.append(job)
            except Exception as e:
                logger.error(f"Error loading queue item {queue_file}: {e}")

        # Sort by creation time
        queue_items.sort(key=lambda x: x.created_at, reverse=True)

        return queue_items

    def approve_video(self, job_id: str) -> VideoJob:
        """Approve a video from review queue."""

        job = self.jobs.get(job_id)

        if not job:
            raise ValueError(f"Job not found: {job_id}")

        if job.status != JobStatus.QUEUED_FOR_REVIEW:
            raise ValueError(f"Job not in review queue: {job_id}")

        # Update status
        job.status = JobStatus.COMPLETED
        job.updated_at = datetime.now()
        self._save_jobs()

        # Remove from queue
        queue_file = self.queue_dir / f"{job_id}.json"
        if queue_file.exists():
            queue_file.unlink()

        logger.info(f"Approved video: {job_id}")

        return job

    def delete_video(self, job_id: str):
        """Delete a video and cleanup files."""

        job = self.jobs.get(job_id)

        if not job:
            raise ValueError(f"Job not found: {job_id}")

        # Delete files
        files_to_delete = [
            job.background_image,
            job.audio_file,
            job.video_file
        ]

        for file_path in files_to_delete:
            if file_path and Path(file_path).exists():
                try:
                    Path(file_path).unlink()
                    logger.debug(f"Deleted: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")

        # Remove from jobs
        del self.jobs[job_id]
        self._save_jobs()

        # Remove from review queue if present
        queue_file = self.queue_dir / f"{job_id}.json"
        if queue_file.exists():
            queue_file.unlink()

        logger.info(f"Deleted video job: {job_id}")

    def get_job_status(self, job_id: str) -> Optional[VideoJob]:
        """Get job status."""
        return self.jobs.get(job_id)

    async def batch_create_videos(
        self,
        content_items: List[ContentItem],
        **kwargs
    ) -> List[VideoJob]:
        """Create multiple videos from content items."""

        jobs = []

        for i, item in enumerate(content_items):
            logger.info(f"Processing item {i+1}/{len(content_items)}: {item.title}")

            try:
                job = await self.create_video_from_content(item, **kwargs)
                jobs.append(job)

            except Exception as e:
                logger.error(f"Failed to create video for '{item.title}': {e}")

        logger.info(f"Batch complete: {len(jobs)}/{len(content_items)} videos created")

        return jobs


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        orchestrator = PipelineOrchestrator()

        # Scrape content
        items = await orchestrator.scrape_content(max_items=3)

        if items:
            # Create video from first item
            def progress(percent, status):
                print(f"[{percent}%] {status}")

            job = await orchestrator.create_video_from_content(
                items[0],
                progress_callback=progress
            )

            print(f"\nJob ID: {job.job_id}")
            print(f"Status: {job.status}")
            print(f"Video: {job.video_file}")

    asyncio.run(main())
