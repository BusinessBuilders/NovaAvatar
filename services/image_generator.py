"""
Image Generator Service
Generates background images using Flux API for avatar videos.
"""

import os
from typing import Optional, Dict
from pathlib import Path
import replicate
from PIL import Image
import requests
from io import BytesIO
from loguru import logger
from pydantic import BaseModel


class GeneratedImage(BaseModel):
    """Represents a generated image."""

    image_path: str
    prompt: str
    model: str
    metadata: Dict = {}


class ImageGenerator:
    """Generates images using Flux API via Replicate."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "black-forest-labs/flux-schnell",
        output_dir: str = "storage/generated"
    ):
        """
        Initialize image generator.

        Args:
            api_key: Replicate API key
            model: Flux model to use (flux-schnell is fastest, flux-dev is higher quality)
            output_dir: Directory to save generated images
        """
        self.api_key = api_key or os.getenv("REPLICATE_API_TOKEN")
        self.model = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if not self.api_key:
            raise ValueError("Replicate API token is required")

        # Set API token
        os.environ["REPLICATE_API_TOKEN"] = self.api_key
        logger.info(f"Image generator initialized with model: {model}")

    async def generate_background(
        self,
        scene_description: str,
        avatar_context: str = "professional avatar video",
        style: str = "photorealistic",
        aspect_ratio: str = "16:9",
        save_name: Optional[str] = None
    ) -> GeneratedImage:
        """
        Generate a background image for avatar video.

        Args:
            scene_description: Description of the scene
            avatar_context: Context about how it will be used
            style: Visual style (photorealistic, cinematic, etc.)
            aspect_ratio: Image aspect ratio
            save_name: Optional filename (auto-generated if not provided)

        Returns:
            GeneratedImage with path and metadata
        """

        # Build the full prompt
        prompt = self._build_prompt(scene_description, avatar_context, style)

        try:
            logger.info(f"Generating image with Flux: {scene_description[:50]}...")

            # Run Flux model
            output = replicate.run(
                self.model,
                input={
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                    "output_format": "jpg",
                    "output_quality": 90,
                    "num_outputs": 1,
                }
            )

            # Download the image
            if isinstance(output, list):
                image_url = output[0]
            else:
                image_url = output

            logger.info(f"Image generated, downloading from: {image_url}")

            # Download and save image
            response = requests.get(image_url)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))

            # Generate filename if not provided
            if not save_name:
                import hashlib
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                hash_suffix = hashlib.md5(prompt.encode()).hexdigest()[:8]
                save_name = f"bg_{timestamp}_{hash_suffix}.jpg"

            # Save image
            image_path = self.output_dir / save_name
            image.save(image_path, quality=95)

            logger.info(f"Image saved to: {image_path}")

            return GeneratedImage(
                image_path=str(image_path),
                prompt=prompt,
                model=self.model,
                metadata={
                    "scene_description": scene_description,
                    "style": style,
                    "aspect_ratio": aspect_ratio,
                    "url": image_url
                }
            )

        except Exception as e:
            logger.error(f"Error generating image: {e}")
            raise

    def _build_prompt(
        self,
        scene_description: str,
        avatar_context: str,
        style: str
    ) -> str:
        """Build optimized prompt for Flux."""

        # Base prompt components
        quality_modifiers = "high quality, professional photography, well-lit"

        # Style-specific modifiers
        style_modifiers = {
            "photorealistic": "photorealistic, natural lighting, sharp focus, 8k resolution",
            "cinematic": "cinematic lighting, dramatic, film grain, depth of field",
            "studio": "studio lighting, clean background, professional setup",
            "natural": "natural lighting, outdoor, authentic, realistic",
            "modern": "modern, minimalist, clean lines, contemporary"
        }

        style_suffix = style_modifiers.get(style.lower(), style_modifiers["photorealistic"])

        # Build full prompt
        prompt = f"{scene_description}. {style_suffix}, {quality_modifiers}. "
        prompt += f"Background for {avatar_context}, no people visible, empty scene."

        # Negative prompt elements (what to avoid)
        prompt += " Professional quality, high resolution."

        return prompt

    async def generate_batch(
        self,
        scene_descriptions: list[str],
        **kwargs
    ) -> list[GeneratedImage]:
        """Generate multiple images in batch."""

        images = []

        for i, description in enumerate(scene_descriptions):
            try:
                save_name = f"batch_{i:03d}.jpg"
                image = await self.generate_background(
                    scene_description=description,
                    save_name=save_name,
                    **kwargs
                )
                images.append(image)

            except Exception as e:
                logger.error(f"Failed to generate image {i+1}: {e}")

        logger.info(f"Generated {len(images)}/{len(scene_descriptions)} images")
        return images

    def use_default_background(self, background_type: str = "professional") -> str:
        """
        Return path to a default background image.

        Args:
            background_type: Type of background (professional, casual, studio, etc.)

        Returns:
            Path to default background image
        """

        # This would return paths to pre-generated or stock backgrounds
        # For now, we'll note that users should provide default backgrounds
        default_backgrounds_dir = self.output_dir / "defaults"
        default_backgrounds_dir.mkdir(exist_ok=True)

        default_bg = default_backgrounds_dir / f"{background_type}.jpg"

        if not default_bg.exists():
            logger.warning(f"Default background not found: {default_bg}")
            logger.info("Consider generating default backgrounds for fallback")

        return str(default_bg)


# Example usage
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv

    load_dotenv()

    async def main():
        generator = ImageGenerator()

        # Generate a background
        image = await generator.generate_background(
            scene_description="A modern office with large windows showing a city skyline at sunset",
            style="photorealistic"
        )

        print(f"Generated image saved to: {image.image_path}")
        print(f"Prompt used: {image.prompt}")

    asyncio.run(main())
