"""
Image Compositor Service
Composites avatar onto generated backgrounds.
"""

import os
from typing import Optional
from pathlib import Path
from PIL import Image
from loguru import logger
from pydantic import BaseModel


class CompositedImage(BaseModel):
    """Represents a composited image."""

    image_path: str
    avatar_path: str
    background_path: str


class ImageCompositor:
    """Composites avatar images onto backgrounds."""

    def __init__(self, output_dir: str = "storage/generated"):
        """
        Initialize compositor.

        Args:
            output_dir: Directory to save composited images
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Image compositor initialized")

    def composite_avatar_on_background(
        self,
        avatar_path: str,
        background_path: str,
        output_name: Optional[str] = None,
        avatar_scale: float = 1.0,
        position: str = "center"  # "center", "left", "right"
    ) -> CompositedImage:
        """
        Composite transparent avatar onto background.

        Args:
            avatar_path: Path to transparent PNG avatar
            background_path: Path to background image
            output_name: Optional output filename
            avatar_scale: Scale factor for avatar (1.0 = original size)
            position: Where to place avatar ("center", "left", "right")

        Returns:
            CompositedImage with path and metadata
        """

        try:
            logger.info(f"Compositing avatar onto background...")

            # Load images
            avatar = Image.open(avatar_path).convert("RGBA")
            background = Image.open(background_path).convert("RGBA")

            # Resize avatar if needed
            if avatar_scale != 1.0:
                new_size = (
                    int(avatar.width * avatar_scale),
                    int(avatar.height * avatar_scale)
                )
                avatar = avatar.resize(new_size, Image.Resampling.LANCZOS)

            # Ensure avatar fits on background
            if avatar.width > background.width or avatar.height > background.height:
                # Scale down avatar to fit
                scale = min(
                    background.width / avatar.width,
                    background.height / avatar.height
                ) * 0.9  # 90% of background size

                new_size = (
                    int(avatar.width * scale),
                    int(avatar.height * scale)
                )
                avatar = avatar.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"Scaled avatar to fit background: {new_size}")

            # Calculate position
            if position == "center":
                x = (background.width - avatar.width) // 2
                y = (background.height - avatar.height) // 2
            elif position == "left":
                x = background.width // 4 - avatar.width // 2
                y = (background.height - avatar.height) // 2
            elif position == "right":
                x = 3 * background.width // 4 - avatar.width // 2
                y = (background.height - avatar.height) // 2
            else:
                x = (background.width - avatar.width) // 2
                y = (background.height - avatar.height) // 2

            # Create composited image
            result = background.copy()
            result.paste(avatar, (x, y), avatar)  # Use avatar as mask

            # Convert to RGB for JPEG
            result = result.convert("RGB")

            # Generate filename if not provided
            if not output_name:
                import hashlib
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                hash_suffix = hashlib.md5(str(avatar_path + background_path).encode()).hexdigest()[:8]
                output_name = f"composited_{timestamp}_{hash_suffix}.jpg"

            # Save
            output_path = self.output_dir / output_name
            result.save(output_path, quality=95)

            logger.info(f"Composited image saved: {output_path}")

            return CompositedImage(
                image_path=str(output_path),
                avatar_path=avatar_path,
                background_path=background_path
            )

        except Exception as e:
            logger.error(f"Error compositing images: {e}")
            raise

    def prepare_avatar(
        self,
        avatar_path: str,
        output_name: str = "avatar_transparent.png"
    ) -> str:
        """
        Prepare avatar image (ensure it's RGBA format).

        Args:
            avatar_path: Path to avatar image
            output_name: Output filename

        Returns:
            Path to prepared avatar
        """

        try:
            avatar = Image.open(avatar_path)

            # Convert to RGBA
            if avatar.mode != "RGBA":
                avatar = avatar.convert("RGBA")
                logger.info(f"Converted avatar to RGBA format")

            output_path = self.output_dir / output_name
            avatar.save(output_path)

            logger.info(f"Avatar prepared: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error preparing avatar: {e}")
            raise


# Example usage
if __name__ == "__main__":
    compositor = ImageCompositor()

    # Example: Composite avatar onto background
    result = compositor.composite_avatar_on_background(
        avatar_path="examples/images/bill_transparent.png",  # Your transparent avatar
        background_path="storage/generated/background.jpg",   # Generated background
        position="center"
    )

    print(f"Composited image: {result.image_path}")
