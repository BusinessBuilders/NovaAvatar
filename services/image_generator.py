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
        output_dir: str = "storage/generated",
        use_local: bool = True  # Use local SD by default
    ):
        """
        Initialize image generator.

        Args:
            api_key: Replicate API key (optional if use_local=True)
            model: Flux model to use (flux-schnell is fastest, flux-dev is higher quality)
            output_dir: Directory to save generated images
            use_local: Use local Stable Diffusion instead of Replicate
        """
        self.use_local = use_local or os.getenv("USE_LOCAL_IMAGE_GEN", "true").lower() == "true"
        self.api_key = api_key or os.getenv("REPLICATE_API_TOKEN")
        self.model = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pipeline = None

        if not self.use_local:
            if not self.api_key:
                logger.warning("No Replicate API key, falling back to local generation")
                self.use_local = True
            else:
                # Set API token
                os.environ["REPLICATE_API_TOKEN"] = self.api_key
                logger.info(f"Image generator initialized with Replicate model: {model}")

        if self.use_local:
            logger.info(f"Image generator initialized with local Stable Diffusion")

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

        if self.use_local:
            return await self._generate_local(prompt, aspect_ratio, save_name)
        else:
            return await self._generate_replicate(prompt, aspect_ratio, save_name)

    async def _generate_local(
        self,
        prompt: str,
        aspect_ratio: str,
        save_name: Optional[str]
    ) -> GeneratedImage:
        """Generate image using local Flux Dev FP8."""

        try:
            logger.info(f"Generating image locally with Flux: {prompt[:50]}...")

            # Import here to avoid loading if not needed
            from diffusers import FluxPipeline
            import torch

            # Load pipeline if not already loaded
            if self.pipeline is None:
                logger.info("Loading Flux Dev pipeline...")

                # Use the downloaded Flux model directory
                flux_path = os.getenv("FLUX_MODEL_PATH", "./pretrained_models/FLUX.1-dev")

                self.pipeline = FluxPipeline.from_pretrained(
                    flux_path,
                    torch_dtype=torch.bfloat16
                )
                self.pipeline.to("cuda")
                logger.info("Flux Dev pipeline loaded")

            # Calculate dimensions from aspect ratio (Flux works best with these)
            if aspect_ratio == "16:9":
                width, height = 1024, 576
            elif aspect_ratio == "4:3":
                width, height = 896, 672
            else:
                width, height = 1024, 1024

            # Generate image
            image = self.pipeline(
                prompt=prompt,
                num_inference_steps=20,  # Flux is fast, 20 steps is good
                width=width,
                height=height,
                guidance_scale=3.5
            ).images[0]

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

            # Cleanup VRAM
            self.cleanup()

            return GeneratedImage(
                image_path=str(image_path),
                prompt=prompt,
                model="flux-dev-fp8-local",
                metadata={
                    "width": width,
                    "height": height,
                    "aspect_ratio": aspect_ratio
                }
            )

        except Exception as e:
            logger.error(f"Error generating image locally: {e}")
            raise

    async def _generate_replicate(
        self,
        prompt: str,
        aspect_ratio: str,
        save_name: Optional[str]
    ) -> GeneratedImage:
        """Generate image using Replicate Flux API."""

        try:
            logger.info(f"Generating image with Flux: {prompt[:50]}...")

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

    def cleanup(self):
        """Cleanup VRAM by unloading the image generation pipeline."""
        if self.pipeline is not None:
            logger.info("Cleaning up image generation pipeline...")
            try:
                import torch
                del self.pipeline
                self.pipeline = None
                torch.cuda.empty_cache()
                logger.info("Image pipeline unloaded, VRAM freed")
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")

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
