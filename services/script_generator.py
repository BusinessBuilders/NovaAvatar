"""
Script Generator Service
Uses OpenAI GPT-4 to generate video scripts from content.
"""

import os
from typing import Optional, Dict, List
from enum import Enum
import openai
from loguru import logger
from pydantic import BaseModel, Field


class ScriptStyle(str, Enum):
    """Available script styles."""
    NEWS_ANCHOR = "news_anchor"
    CASUAL = "casual"
    EDUCATIONAL = "educational"
    ENTERTAINING = "entertaining"
    PROFESSIONAL = "professional"


class VideoScript(BaseModel):
    """Represents a generated video script."""

    script: str
    title: str
    duration_estimate: int  # in seconds
    style: ScriptStyle
    scene_description: str  # For image generation
    keywords: List[str] = Field(default_factory=list)
    metadata: Dict = Field(default_factory=dict)


class ScriptGenerator:
    """Generates video scripts using OpenAI GPT-4."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4-turbo-preview",
        default_style: ScriptStyle = ScriptStyle.PROFESSIONAL
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.default_style = default_style

        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        # Initialize OpenAI client
        openai.api_key = self.api_key
        self.client = openai.OpenAI(api_key=self.api_key)
        logger.info(f"Script generator initialized with model: {model}")

    async def generate_script(
        self,
        content_title: str,
        content_description: str,
        style: Optional[ScriptStyle] = None,
        duration: int = 45,
        additional_context: Optional[str] = None,
        call_to_action: Optional[str] = None
    ) -> VideoScript:
        """
        Generate a video script from content.

        Args:
            content_title: The title of the content
            content_description: Description/summary of the content
            style: Speaking style (defaults to professional)
            duration: Target duration in seconds (default: 45s)
            additional_context: Additional context to include
            call_to_action: Optional CTA to add at the end

        Returns:
            VideoScript object with generated script and metadata
        """
        style = style or self.default_style

        # Build the system prompt
        system_prompt = self._build_system_prompt(style, duration)

        # Build the user prompt
        user_prompt = self._build_user_prompt(
            content_title,
            content_description,
            additional_context,
            call_to_action
        )

        try:
            logger.info(f"Generating script for: {content_title}")

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            # Extract the script
            script_text = response.choices[0].message.content.strip()

            # Extract scene description using another GPT call
            scene_description = await self._generate_scene_description(
                content_title,
                content_description,
                style
            )

            # Extract keywords
            keywords = await self._extract_keywords(content_title, content_description)

            # Estimate actual duration (rough estimate: 150 words per minute)
            word_count = len(script_text.split())
            duration_estimate = int((word_count / 150) * 60)

            video_script = VideoScript(
                script=script_text,
                title=content_title,
                duration_estimate=duration_estimate,
                style=style,
                scene_description=scene_description,
                keywords=keywords,
                metadata={
                    "model": self.model,
                    "word_count": word_count,
                    "original_description": content_description
                }
            )

            logger.info(f"Script generated successfully ({word_count} words, ~{duration_estimate}s)")
            return video_script

        except Exception as e:
            logger.error(f"Error generating script: {e}")
            raise

    def _build_system_prompt(self, style: ScriptStyle, duration: int) -> str:
        """Build the system prompt based on style."""

        base_prompt = f"""You are a professional script writer for video content.
Your task is to write a {duration}-second video script for an avatar presenter.

The script should be:
- Natural and conversational for the avatar to speak
- Engaging and clear
- Appropriate for a {duration}-second video (~{int(duration * 2.5)} words)
- Written in a {style.value.replace('_', ' ')} style

IMPORTANT:
- Write ONLY the words the avatar should speak
- Do NOT include stage directions, camera notes, or descriptions
- Make it sound natural when spoken aloud
- Include appropriate pauses with punctuation"""

        style_guidelines = {
            ScriptStyle.NEWS_ANCHOR: """
Style: Professional news anchor
- Authoritative and credible tone
- Clear and factual presentation
- Strong opening hook
- Summarize key points concisely
- End with a professional sign-off""",

            ScriptStyle.CASUAL: """
Style: Casual and friendly
- Conversational and relatable tone
- Use contractions and informal language
- Address viewer directly ("you", "we")
- Be enthusiastic but authentic
- End with a friendly goodbye""",

            ScriptStyle.EDUCATIONAL: """
Style: Educational and informative
- Clear explanations
- Break down complex topics
- Use examples and analogies
- Maintain engagement while teaching
- End with a key takeaway""",

            ScriptStyle.ENTERTAINING: """
Style: Entertaining and engaging
- Hook viewers immediately
- Use storytelling techniques
- Inject personality and energy
- Keep it fun and dynamic
- End with a memorable punchline or thought""",

            ScriptStyle.PROFESSIONAL: """
Style: Professional and polished
- Balanced tone - authoritative but approachable
- Clear and articulate
- Well-structured points
- Professional yet engaging
- End with a strong conclusion"""
        }

        return base_prompt + "\n" + style_guidelines.get(style, style_guidelines[ScriptStyle.PROFESSIONAL])

    def _build_user_prompt(
        self,
        title: str,
        description: str,
        additional_context: Optional[str],
        call_to_action: Optional[str]
    ) -> str:
        """Build the user prompt with content details."""

        prompt = f"""Topic: {title}

Content Summary:
{description}"""

        if additional_context:
            prompt += f"\n\nAdditional Context:\n{additional_context}"

        if call_to_action:
            prompt += f"\n\nCall to Action (end with this):\n{call_to_action}"

        prompt += "\n\nGenerate the video script now:"

        return prompt

    async def _generate_scene_description(
        self,
        title: str,
        description: str,
        style: ScriptStyle
    ) -> str:
        """Generate a scene description for image generation."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{
                    "role": "user",
                    "content": f"""Based on this content, describe a professional background scene for an avatar video.

Topic: {title}
Description: {description}
Style: {style.value}

Write a 1-2 sentence description of an appropriate background setting.
Focus on: location, atmosphere, lighting, and relevant visual elements.
The avatar will be in the foreground, so describe the background only.

Example: "A modern office with large windows showing a city skyline, soft natural lighting, professional and clean aesthetic"

Your scene description:"""
                }],
                temperature=0.7,
                max_tokens=150
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.warning(f"Error generating scene description: {e}")
            return "A professional studio setting with neutral background"

    async def _extract_keywords(self, title: str, description: str) -> List[str]:
        """Extract relevant keywords from content."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{
                    "role": "user",
                    "content": f"""Extract 3-5 relevant keywords from this content.

Title: {title}
Description: {description}

Return only the keywords, comma-separated, no explanations."""
                }],
                temperature=0.5,
                max_tokens=50
            )

            keywords_text = response.choices[0].message.content.strip()
            keywords = [k.strip() for k in keywords_text.split(',')]
            return keywords[:5]  # Limit to 5 keywords

        except Exception as e:
            logger.warning(f"Error extracting keywords: {e}")
            return []

    async def batch_generate(
        self,
        content_items: List[Dict],
        style: Optional[ScriptStyle] = None,
        duration: int = 45
    ) -> List[VideoScript]:
        """Generate scripts for multiple content items."""

        scripts = []

        for item in content_items:
            try:
                script = await self.generate_script(
                    content_title=item.get('title'),
                    content_description=item.get('description'),
                    style=style,
                    duration=duration,
                    additional_context=item.get('context'),
                    call_to_action=item.get('cta')
                )
                scripts.append(script)

            except Exception as e:
                logger.error(f"Failed to generate script for '{item.get('title')}': {e}")

        logger.info(f"Generated {len(scripts)}/{len(content_items)} scripts")
        return scripts


# Example usage
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv

    load_dotenv()

    async def main():
        generator = ScriptGenerator()

        # Example content
        script = await generator.generate_script(
            content_title="AI Revolution in Healthcare",
            content_description="New AI system can detect diseases with 95% accuracy, "
                               "potentially saving millions of lives through early detection.",
            style=ScriptStyle.PROFESSIONAL,
            duration=45
        )

        print("=" * 80)
        print(f"Title: {script.title}")
        print(f"Style: {script.style}")
        print(f"Duration: ~{script.duration_estimate}s")
        print(f"Scene: {script.scene_description}")
        print("=" * 80)
        print(f"\nScript:\n{script.script}")
        print("=" * 80)
        print(f"Keywords: {', '.join(script.keywords)}")

    asyncio.run(main())
