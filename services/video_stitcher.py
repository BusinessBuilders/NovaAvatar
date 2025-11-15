"""
Video Stitching Service for Multi-Avatar Conversations.

Combines individual avatar videos into a single conversation video.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Optional
from loguru import logger
from pydantic import BaseModel


class VideoSegment(BaseModel):
    """Single video segment for stitching."""
    video_path: str
    start_time: float = 0.0
    duration: Optional[float] = None
    avatar_name: str


class StitchedVideo(BaseModel):
    """Result of video stitching."""
    video_path: str
    total_duration: float
    num_segments: int


class VideoStitcher:
    """Stitch multiple avatar videos into a conversation."""

    def __init__(self, output_dir: str = "storage/conversations"):
        """
        Initialize video stitcher.

        Args:
            output_dir: Directory for output videos
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Video stitcher initialized with output dir: {output_dir}")

    def stitch_conversation(
        self,
        segments: List[VideoSegment],
        output_name: str,
        add_transitions: bool = True,
        transition_duration: float = 0.3
    ) -> StitchedVideo:
        """
        Stitch video segments into a single conversation video.

        Args:
            segments: List of video segments in order
            output_name: Name for output file (without extension)
            add_transitions: Add fade transitions between segments
            transition_duration: Duration of transitions in seconds

        Returns:
            StitchedVideo with path and metadata

        Example:
            >>> segments = [
            ...     VideoSegment(video_path="alice_1.mp4", avatar_name="Alice"),
            ...     VideoSegment(video_path="bob_1.mp4", avatar_name="Bob"),
            ...     VideoSegment(video_path="alice_2.mp4", avatar_name="Alice"),
            ... ]
            >>> result = stitcher.stitch_conversation(segments, "conversation_1")
        """
        logger.info(f"Stitching {len(segments)} video segments into {output_name}")

        # Verify all videos exist
        for seg in segments:
            if not Path(seg.video_path).exists():
                raise FileNotFoundError(f"Video not found: {seg.video_path}")

        output_path = self.output_dir / f"{output_name}.mp4"

        if add_transitions:
            result = self._stitch_with_transitions(segments, output_path, transition_duration)
        else:
            result = self._stitch_simple(segments, output_path)

        logger.info(f"Stitched video saved to: {output_path}")
        return result

    def _stitch_simple(self, segments: List[VideoSegment], output_path: Path) -> StitchedVideo:
        """Simple concatenation without transitions."""

        # Create concat file list
        concat_file = self.output_dir / "concat_list.txt"

        with open(concat_file, "w") as f:
            for seg in segments:
                # FFmpeg concat requires absolute paths
                abs_path = Path(seg.video_path).absolute()
                f.write(f"file '{abs_path}'\n")

        # Use FFmpeg to concatenate
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",  # Copy without re-encoding (faster)
            "-y",  # Overwrite output
            str(output_path)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr.decode()}")
            raise

        # Get total duration
        duration = self._get_video_duration(str(output_path))

        # Cleanup
        concat_file.unlink()

        return StitchedVideo(
            video_path=str(output_path),
            total_duration=duration,
            num_segments=len(segments)
        )

    def _stitch_with_transitions(
        self,
        segments: List[VideoSegment],
        output_path: Path,
        transition_duration: float
    ) -> StitchedVideo:
        """Stitch with crossfade transitions."""

        # Build complex FFmpeg filter for crossfades
        filter_parts = []
        input_parts = []

        for i, seg in enumerate(segments):
            input_parts.extend(["-i", seg.video_path])

        # Build xfade filter chain
        # [0:v][1:v]xfade=transition=fade:duration=0.3:offset=5[v01];
        # [v01][2:v]xfade=transition=fade:duration=0.3:offset=10[v02];

        filter_complex = ""
        last_label = "0:v"

        for i in range(1, len(segments)):
            current_label = f"v{i-1}{i}"
            next_input = f"{i}:v"

            # Calculate offset (cumulative duration minus transition)
            offset = sum(self._get_video_duration(segments[j].video_path) for j in range(i))
            offset -= transition_duration * i

            filter_complex += f"[{last_label}][{next_input}]xfade=transition=fade:duration={transition_duration}:offset={offset}"

            if i < len(segments) - 1:
                filter_complex += f"[{current_label}];"
                last_label = current_label
            else:
                filter_complex += "[outv]"

        cmd = [
            "ffmpeg",
            *input_parts,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-y",
            str(output_path)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr.decode()}")
            # Fallback to simple concatenation
            logger.warning("Falling back to simple concatenation")
            return self._stitch_simple(segments, output_path)

        duration = self._get_video_duration(str(output_path))

        return StitchedVideo(
            video_path=str(output_path),
            total_duration=duration,
            num_segments=len(segments)
        )

    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True)
            duration = float(result.stdout.decode().strip())
            return duration
        except (subprocess.CalledProcessError, ValueError) as e:
            logger.warning(f"Could not get duration for {video_path}: {e}")
            return 0.0

    def create_split_screen(
        self,
        segments: List[VideoSegment],
        output_name: str,
        layout: str = "horizontal"
    ) -> StitchedVideo:
        """
        Create split-screen video with multiple avatars visible simultaneously.

        Args:
            segments: List of video segments (all should have same duration)
            output_name: Output filename
            layout: 'horizontal', 'vertical', or 'grid'

        Returns:
            StitchedVideo result
        """
        logger.info(f"Creating {layout} split-screen with {len(segments)} videos")

        output_path = self.output_dir / f"{output_name}.mp4"

        if layout == "horizontal" and len(segments) == 2:
            # Side-by-side layout
            filter_complex = "[0:v][1:v]hstack=inputs=2[outv]"
        elif layout == "vertical" and len(segments) == 2:
            # Top-bottom layout
            filter_complex = "[0:v][1:v]vstack=inputs=2[outv]"
        elif layout == "grid" and len(segments) == 4:
            # 2x2 grid
            filter_complex = (
                "[0:v][1:v]hstack=inputs=2[top];"
                "[2:v][3:v]hstack=inputs=2[bottom];"
                "[top][bottom]vstack=inputs=2[outv]"
            )
        else:
            raise ValueError(f"Unsupported layout '{layout}' for {len(segments)} segments")

        cmd = [
            "ffmpeg",
        ]

        # Add inputs
        for seg in segments:
            cmd.extend(["-i", seg.video_path])

        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-y",
            str(output_path)
        ])

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr.decode()}")
            raise

        duration = self._get_video_duration(str(output_path))

        return StitchedVideo(
            video_path=str(output_path),
            total_duration=duration,
            num_segments=len(segments)
        )


# Example usage
if __name__ == "__main__":
    stitcher = VideoStitcher()

    # Example: Stitch conversation
    segments = [
        VideoSegment(video_path="alice_intro.mp4", avatar_name="Alice"),
        VideoSegment(video_path="bob_response.mp4", avatar_name="Bob"),
        VideoSegment(video_path="alice_reply.mp4", avatar_name="Alice"),
    ]

    # result = stitcher.stitch_conversation(
    #     segments,
    #     output_name="conversation_2024",
    #     add_transitions=True
    # )
    #
    # print(f"Created: {result.video_path}")
    # print(f"Duration: {result.total_duration}s")
