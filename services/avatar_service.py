"""
Avatar Generation Service
Wrapper for OmniAvatar WanInferencePipeline with production features.
"""

import os
import sys
from typing import Optional, Dict, Callable
from pathlib import Path
from datetime import datetime
from loguru import logger
from pydantic import BaseModel

# Add OmniAvatar to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class AvatarVideo(BaseModel):
    """Represents a generated avatar video."""

    video_path: str
    prompt: str
    image_path: str
    audio_path: str
    duration: float
    metadata: Dict = {}


class AvatarService:
    """
    Production wrapper for OmniAvatar generation.
    Handles initialization, generation, and error recovery.
    """

    def __init__(
        self,
        config_path: str = "configs/inference_1.3B.yaml",
        output_dir: str = "storage/videos",
        use_14b_model: bool = False,
        enable_vram_management: bool = True,
        num_steps: int = 25,
        guidance_scale: float = 4.5,
        audio_scale: Optional[float] = None,
        tea_cache_thresh: float = 0.14
    ):
        """
        Initialize avatar service.

        Args:
            config_path: Path to inference config YAML
            output_dir: Directory to save videos
            use_14b_model: Use 14B model (higher quality, more VRAM)
            enable_vram_management: Enable VRAM optimization
            num_steps: Inference steps (20-50)
            guidance_scale: CFG scale for text (4-6 recommended)
            audio_scale: CFG scale for audio (defaults to guidance_scale)
            tea_cache_thresh: TeaCache threshold (0.05-0.15, 0 to disable)
        """

        self.config_path = config_path if not use_14b_model else "configs/inference.yaml"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.pipeline = None
        self.config = None

        # Generation parameters
        self.params = {
            "num_steps": num_steps,
            "guidance_scale": guidance_scale,
            "audio_scale": audio_scale or guidance_scale,
            "tea_cache_l1_thresh": tea_cache_thresh,
            "enable_vram_management": enable_vram_management,
        }

        logger.info(f"Avatar service initialized with config: {self.config_path}")
        logger.info(f"Parameters: {self.params}")

    def load_pipeline(self):
        """Load the OmniAvatar pipeline (lazy loading)."""

        if self.pipeline is not None:
            logger.info("Pipeline already loaded")
            return

        try:
            logger.info("Loading OmniAvatar pipeline...")

            # Import here to avoid loading models at import time
            from scripts.inference import WanInferencePipeline
            from OmniAvatar.utils.args_config import load_config_from_yaml

            # Load config
            self.config = load_config_from_yaml(self.config_path)

            # Override with our parameters
            for key, value in self.params.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)

            # Initialize pipeline
            self.pipeline = WanInferencePipeline(self.config)

            logger.info("Pipeline loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load pipeline: {e}")
            raise

    async def generate_video(
        self,
        prompt: str,
        image_path: str,
        audio_path: str,
        output_name: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> AvatarVideo:
        """
        Generate avatar video.

        Args:
            prompt: Text prompt for video generation
            image_path: Path to reference image
            audio_path: Path to audio file (16kHz recommended)
            output_name: Optional output filename
            progress_callback: Optional callback(progress: int, status: str)

        Returns:
            AvatarVideo with path and metadata
        """

        # Ensure pipeline is loaded
        if self.pipeline is None:
            self.load_pipeline()

        # Validate inputs
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio not found: {audio_path}")

        # Generate output name if not provided
        if not output_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"avatar_{timestamp}"

        output_base = self.output_dir / output_name

        try:
            logger.info(f"Generating avatar video: {output_name}")
            logger.info(f"Prompt: {prompt}")
            logger.info(f"Image: {image_path}")
            logger.info(f"Audio: {audio_path}")

            if progress_callback:
                progress_callback(0, "Initializing...")

            # Create input string in OmniAvatar format
            input_line = f"{prompt}@@{image_path}@@{audio_path}"

            # Run generation
            if progress_callback:
                progress_callback(10, "Loading models...")

            # Note: The actual WanInferencePipeline.forward() method
            # We'll need to adapt it to work with our wrapper
            import torch

            with torch.no_grad():
                if progress_callback:
                    progress_callback(20, "Processing audio...")

                # Call the pipeline
                # The actual implementation depends on WanInferencePipeline interface
                # This is a simplified version - actual integration may differ
                result = self.pipeline.forward(
                    input_line=input_line,
                    output_base=str(output_base),
                    rank=0,  # Single GPU for now
                    callback=lambda p: progress_callback(20 + int(p * 0.7), "Generating video...") if progress_callback else None
                )

                if progress_callback:
                    progress_callback(95, "Saving video...")

            # Find the generated video file
            video_path = self._find_output_video(output_base)

            if not video_path:
                raise RuntimeError("Video generation completed but output file not found")

            if progress_callback:
                progress_callback(100, "Complete!")

            # Get video duration
            duration = self._get_video_duration(video_path)

            logger.info(f"Video generated successfully: {video_path}")

            return AvatarVideo(
                video_path=str(video_path),
                prompt=prompt,
                image_path=image_path,
                audio_path=audio_path,
                duration=duration,
                metadata={
                    "output_name": output_name,
                    "params": self.params,
                    "generated_at": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error generating video: {e}")
            if progress_callback:
                progress_callback(-1, f"Error: {str(e)}")
            raise

    def _find_output_video(self, output_base: Path) -> Optional[str]:
        """Find the generated video file."""

        # OmniAvatar saves as {output_base}.mp4
        video_path = Path(str(output_base) + ".mp4")

        if video_path.exists():
            return str(video_path)

        # Check for other possible extensions
        for ext in ['.mp4', '_output.mp4', '_final.mp4']:
            possible_path = Path(str(output_base) + ext)
            if possible_path.exists():
                return str(possible_path)

        # Search in output directory
        video_files = list(self.output_dir.glob(f"{output_base.name}*.mp4"))
        if video_files:
            return str(video_files[0])

        return None

    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds."""

        try:
            import subprocess
            import json

            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                video_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            duration = float(data['format']['duration'])

            return duration

        except Exception as e:
            logger.warning(f"Could not get video duration: {e}")
            return 0.0

    def cleanup(self):
        """Cleanup resources."""

        if self.pipeline is not None:
            logger.info("Cleaning up pipeline resources...")

            try:
                # Clear CUDA cache
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

                # Delete pipeline
                del self.pipeline
                self.pipeline = None

                logger.info("Cleanup complete")

            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Initialize service
        service = AvatarService(
            use_14b_model=False,  # Use 1.3B model
            num_steps=25,
            tea_cache_thresh=0.14
        )

        # Progress callback
        def progress(percent, status):
            print(f"[{percent}%] {status}")

        # Generate video
        video = await service.generate_video(
            prompt="A professional woman speaking confidently to camera, modern office background",
            image_path="examples/images/0000.jpeg",
            audio_path="examples/audios/0000.MP3",
            progress_callback=progress
        )

        print(f"\nGenerated video: {video.video_path}")
        print(f"Duration: {video.duration:.2f}s")

    asyncio.run(main())
