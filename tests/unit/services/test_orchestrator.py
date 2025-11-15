"""Unit tests for PipelineOrchestrator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from services.orchestrator import PipelineOrchestrator, JobStatus
from services.content_scraper import ContentItem
from services.script_generator import VideoScript, ScriptStyle


@pytest.mark.unit
class TestPipelineOrchestrator:
    """Test PipelineOrchestrator functionality."""

    @pytest.fixture
    def orchestrator(self, mock_storage_dir):
        """Create PipelineOrchestrator instance."""
        return PipelineOrchestrator(
            storage_dir=str(mock_storage_dir),
            enable_queue=False,  # Disable Redis for unit tests
        )

    @pytest.mark.asyncio
    async def test_scrape_content(self, orchestrator, sample_content_item):
        """Test content scraping."""
        orchestrator.content_scraper.scrape_all = AsyncMock(
            return_value=[sample_content_item]
        )

        items = await orchestrator.scrape_content(max_items=5)

        assert len(items) == 1
        assert items[0].title == sample_content_item.title

    @pytest.mark.asyncio
    async def test_create_video_full_pipeline(
        self, orchestrator, sample_content_item, sample_video_script
    ):
        """Test full video creation pipeline."""
        # Mock all service calls
        orchestrator.script_generator.generate_script = AsyncMock(
            return_value=sample_video_script
        )
        orchestrator.image_generator.generate_background = AsyncMock(
            return_value=MagicMock(image_path="test_bg.jpg")
        )
        orchestrator.image_compositor.composite_avatar_on_background = MagicMock(
            return_value=MagicMock(image_path="test_composite.jpg")
        )
        orchestrator.tts_service.generate_speech = AsyncMock(
            return_value=MagicMock(audio_path="test_audio.wav", duration=45.0)
        )
        orchestrator.avatar_service.generate_video = AsyncMock(
            return_value=MagicMock(video_path="test_video.mp4", duration=45.0)
        )

        # Track progress
        progress_calls = []

        def progress_callback(percent, status):
            progress_calls.append((percent, status))

        job = await orchestrator.create_video_from_content(
            content_item=sample_content_item,
            style=ScriptStyle.PROFESSIONAL,
            duration=45,
            progress_callback=progress_callback,
        )

        # Verify job completion
        assert job.status in [JobStatus.COMPLETED, JobStatus.QUEUED_FOR_REVIEW]
        assert job.video_file == "test_video.mp4"
        assert job.progress == 100

        # Verify progress was tracked
        assert len(progress_calls) > 0
        assert progress_calls[-1] == (100, "Complete!")

    @pytest.mark.asyncio
    async def test_job_persistence(self, orchestrator, mock_storage_dir):
        """Test that jobs are saved and loaded correctly."""
        # Create a mock job
        from services.orchestrator import VideoJob
        import uuid

        job_id = str(uuid.uuid4())
        job = VideoJob(job_id=job_id, status=JobStatus.COMPLETED)

        orchestrator.jobs[job_id] = job
        orchestrator._save_jobs()

        # Create new orchestrator instance to test loading
        new_orchestrator = PipelineOrchestrator(
            storage_dir=str(mock_storage_dir),
            enable_queue=False,
        )

        # Verify job was loaded
        assert job_id in new_orchestrator.jobs
        assert new_orchestrator.jobs[job_id].status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_review_queue(self, orchestrator, sample_content_item):
        """Test review queue functionality."""
        # Mock services
        orchestrator.script_generator.generate_script = AsyncMock(
            return_value=MagicMock(
                script="Test",
                scene_description="Test",
                avatar_prompt="Test",
                duration_estimate=45,
            )
        )
        orchestrator.image_generator.generate_background = AsyncMock(
            return_value=MagicMock(image_path="test.jpg")
        )
        orchestrator.image_compositor.composite_avatar_on_background = MagicMock(
            return_value=MagicMock(image_path="test.jpg")
        )
        orchestrator.tts_service.generate_speech = AsyncMock(
            return_value=MagicMock(audio_path="test.wav", duration=45.0)
        )
        orchestrator.avatar_service.generate_video = AsyncMock(
            return_value=MagicMock(video_path="test.mp4", duration=45.0)
        )

        # Create video (should go to queue)
        job = await orchestrator.create_video_from_content(sample_content_item)

        # Verify it's in the queue
        queue = orchestrator.get_review_queue()
        assert len(queue) > 0
        assert queue[0].job_id == job.job_id

        # Approve the video
        approved = orchestrator.approve_video(job.job_id)
        assert approved.status == JobStatus.COMPLETED

        # Verify it's removed from queue
        queue_after = orchestrator.get_review_queue()
        assert len(queue_after) == 0

    @pytest.mark.asyncio
    async def test_batch_create_videos(self, orchestrator):
        """Test batch video creation."""
        items = [
            ContentItem(
                title=f"Test {i}",
                description=f"Description {i}",
                url=f"https://example.com/{i}",
                source_name="Test",
            )
            for i in range(3)
        ]

        # Mock all services
        orchestrator.script_generator.generate_script = AsyncMock(
            return_value=MagicMock(
                script="Test",
                scene_description="Test",
                avatar_prompt="Test",
                duration_estimate=45,
            )
        )
        orchestrator.image_generator.generate_background = AsyncMock(
            return_value=MagicMock(image_path="test.jpg")
        )
        orchestrator.image_compositor.composite_avatar_on_background = MagicMock(
            return_value=MagicMock(image_path="test.jpg")
        )
        orchestrator.tts_service.generate_speech = AsyncMock(
            return_value=MagicMock(audio_path="test.wav", duration=45.0)
        )
        orchestrator.avatar_service.generate_video = AsyncMock(
            return_value=MagicMock(video_path="test.mp4", duration=45.0)
        )

        jobs = await orchestrator.batch_create_videos(items)

        assert len(jobs) == 3
        assert all(job.status in [JobStatus.COMPLETED, JobStatus.QUEUED_FOR_REVIEW] for job in jobs)
