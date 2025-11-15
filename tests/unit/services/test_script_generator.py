"""Unit tests for ScriptGenerator service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from services.script_generator import ScriptGenerator, ScriptStyle, VideoScript


@pytest.mark.unit
class TestScriptGenerator:
    """Test ScriptGenerator functionality."""

    @pytest.fixture
    def generator(self):
        """Create ScriptGenerator instance."""
        return ScriptGenerator()

    @pytest.mark.asyncio
    async def test_generate_script_success(self, generator, mock_openai_client):
        """Test successful script generation."""
        mock_response = {
            "script": "This is a generated script about AI.",
            "scene_description": "Modern tech office with screens",
            "avatar_prompt": "Professional presenter speaking",
            "duration_estimate": 45,
            "keywords": ["AI", "technology"],
        }

        with patch.object(generator, "_call_gpt", new=AsyncMock(return_value=mock_response)):
            script = await generator.generate_script(
                content_title="AI Breakthrough",
                content_description="New AI achieves amazing results",
                style=ScriptStyle.PROFESSIONAL,
                duration=45,
            )

            assert isinstance(script, VideoScript)
            assert len(script.script) > 0
            assert script.duration_estimate == 45
            assert script.style == ScriptStyle.PROFESSIONAL.value

    @pytest.mark.asyncio
    async def test_script_style_variation(self, generator):
        """Test different script styles produce different results."""
        mock_responses = {
            ScriptStyle.PROFESSIONAL: {"script": "In a professional manner...", "scene_description": "Office", "avatar_prompt": "Formal", "duration_estimate": 45, "keywords": []},
            ScriptStyle.CASUAL: {"script": "Hey everyone, let me tell you...", "scene_description": "Casual setting", "avatar_prompt": "Relaxed", "duration_estimate": 45, "keywords": []},
        }

        for style in [ScriptStyle.PROFESSIONAL, ScriptStyle.CASUAL]:
            with patch.object(
                generator, "_call_gpt", new=AsyncMock(return_value=mock_responses[style])
            ):
                script = await generator.generate_script(
                    content_title="Test",
                    content_description="Test content",
                    style=style,
                    duration=45,
                )

                assert script.style == style.value

    @pytest.mark.asyncio
    async def test_duration_control(self, generator):
        """Test that duration parameter affects script length."""
        short_response = {
            "script": "Short script.",
            "scene_description": "Scene",
            "avatar_prompt": "Prompt",
            "duration_estimate": 15,
            "keywords": [],
        }

        long_response = {
            "script": "Much longer script with more content and details.",
            "scene_description": "Scene",
            "avatar_prompt": "Prompt",
            "duration_estimate": 90,
            "keywords": [],
        }

        # Test short duration
        with patch.object(generator, "_call_gpt", new=AsyncMock(return_value=short_response)):
            short_script = await generator.generate_script(
                content_title="Test",
                content_description="Test",
                duration=15,
            )
            assert short_script.duration_estimate <= 20

        # Test long duration
        with patch.object(generator, "_call_gpt", new=AsyncMock(return_value=long_response)):
            long_script = await generator.generate_script(
                content_title="Test",
                content_description="Test",
                duration=90,
            )
            assert long_script.duration_estimate >= 60

    @pytest.mark.asyncio
    async def test_api_error_handling(self, generator):
        """Test handling of API errors."""
        with patch.object(
            generator, "_call_gpt", new=AsyncMock(side_effect=Exception("API Error"))
        ):
            with pytest.raises(Exception) as exc_info:
                await generator.generate_script(
                    content_title="Test",
                    content_description="Test",
                )

            assert "API Error" in str(exc_info.value)
