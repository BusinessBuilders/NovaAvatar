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

            # Import directly from OmniAvatar to avoid scripts/inference.py parse_args() issue
            from OmniAvatar.wan_video import WanVideoPipeline
            import yaml
            import argparse

            # Load config YAML manually
            with open(self.config_path, 'r') as f:
                yaml_config = yaml.safe_load(f)

            # Create a Namespace object from YAML config
            self.config = argparse.Namespace(**yaml_config)

            # Set required distributed training variables
            import os
            self.config.rank = 0
            self.config.world_size = 1
            self.config.local_rank = 0
            self.config.device = 'cuda:0'
            self.config.num_nodes = 1

            # Override with our parameters
            for key, value in self.params.items():
                setattr(self.config, key, value)

            # Initialize pipeline
            self.pipeline = WanVideoPipeline(self.config)

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

        # Validate inputs
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio not found: {audio_path}")

        # Generate output name if not provided
        if not output_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"avatar_{timestamp}"

        output_path = self.output_dir / f"{output_name}.mp4"

        try:
            logger.info(f"Generating avatar video: {output_name}")
            logger.info(f"Prompt: {prompt}")
            logger.info(f"Image: {image_path}")
            logger.info(f"Audio: {audio_path}")

            if progress_callback:
                progress_callback(0, "Initializing...")

            # Create input file for OmniAvatar
            input_line = f"{prompt}@@{image_path}@@{audio_path}"
            input_file = self.output_dir / f"{output_name}_input.txt"
            with open(input_file, 'w') as f:
                f.write(input_line)

            if progress_callback:
                progress_callback(10, "Generating video with OmniAvatar...")

            # Run OmniAvatar inference using torchrun
            import subprocess
            import os

            # Get config path (already set in init)
            cmd = [
                'torchrun',
                '--standalone',
                '--nproc_per_node=1',
                'scripts/inference.py',
                '--config', self.config_path,
                '--input_file', str(input_file),
                '--hp', f'num_steps={self.params["num_steps"]},guidance_scale={self.params["guidance_scale"]},audio_scale={self.params["audio_scale"]},tea_cache_l1_thresh={self.params["tea_cache_l1_thresh"]}'
            ]

            logger.info(f"Running: {' '.join(cmd)}")

            # Run the command
            result = subprocess.run(
                cmd,
                cwd=os.getcwd(),
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.error(f"OmniAvatar failed: {result.stderr}")
                raise RuntimeError(f"OmniAvatar generation failed: {result.stderr}")

            if progress_callback:
                progress_callback(95, "Finding generated video...")

            # Find the generated video file
            video_path = self._find_output_video_in_demo_out(output_name, input_line)

            if not video_path:
                raise RuntimeError("Video generation completed but output file not found")

            # Copy to our output directory
            import shutil
            final_path = self.output_dir / f"{output_name}.mp4"
            shutil.copy(video_path, final_path)
            video_path = str(final_path)

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

    def _find_output_video_in_demo_out(self, output_name: str, input_line: str) -> Optional[str]:
        """Find the generated video in demo_out directory."""

        # OmniAvatar saves to demo_out/{exp_name}/res_...
        demo_out = Path("demo_out")

        if not demo_out.exists():
            logger.warning("demo_out directory not found")
            return None

        # Search for the most recent result_*.mp4 file
        import glob
        video_files = sorted(
            glob.glob(str(demo_out / "**" / "result_*.mp4"), recursive=True),
            key=lambda x: Path(x).stat().st_mtime,
            reverse=True
        )

        if video_files:
            logger.info(f"Found generated video: {video_files[0]}")
            return video_files[0]

        logger.warning("No video files found in demo_out")
        return None

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
