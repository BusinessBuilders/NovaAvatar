"""Pytest configuration and shared fixtures."""

import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, AsyncMock

import pytest
from faker import Faker

# Prevent loading of actual .env file during tests
os.environ["TESTING"] = "true"


@pytest.fixture
def fake() -> Faker:
    """Faker instance for generating test data."""
    return Faker()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    mock = MagicMock()
    mock.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content='{"script": "Test script", "scene_description": "Test scene", "duration_estimate": 45}'
                    )
                )
            ]
        )
    )
    return mock


@pytest.fixture
def mock_replicate_client():
    """Mock Replicate client."""
    mock = MagicMock()
    mock.run = MagicMock(return_value=["https://example.com/image.jpg"])
    return mock


@pytest.fixture
def sample_content_item(fake):
    """Sample ContentItem for testing."""
    from services.content_scraper import ContentItem

    return ContentItem(
        title=fake.sentence(nb_words=6),
        description=fake.text(max_nb_chars=200),
        url=fake.url(),
        source_name="TestSource",
        published_date=fake.date_time_this_month(),
    )


@pytest.fixture
def sample_video_script():
    """Sample VideoScript for testing."""
    from services.script_generator import VideoScript

    return VideoScript(
        script="This is a test script for our avatar video.",
        scene_description="Modern office with professional lighting",
        avatar_prompt="Professional presenter speaking confidently",
        duration_estimate=45,
        style="professional",
        keywords=["test", "demo"],
    )


@pytest.fixture
def mock_storage_dir(temp_dir: Path) -> Path:
    """Create mock storage directory structure."""
    storage = temp_dir / "storage"
    storage.mkdir()
    (storage / "generated").mkdir()
    (storage / "videos").mkdir()
    (storage / "queue").mkdir()
    return storage


@pytest.fixture(autouse=True)
def reset_env_vars():
    """Reset environment variables after each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_avatar_service():
    """Mock AvatarService for testing."""
    from services.avatar_service import AvatarVideo

    mock = MagicMock()
    mock.generate_video = AsyncMock(
        return_value=AvatarVideo(
            video_path="test_video.mp4",
            duration=45.0,
            prompt="Test prompt",
        )
    )
    return mock
