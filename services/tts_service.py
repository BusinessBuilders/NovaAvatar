"""
Text-to-Speech Service
Generates audio from text using Dia TTS or fallback services.
"""

import os
import subprocess
from typing import Optional, Dict
from pathlib import Path
from loguru import logger
from pydantic import BaseModel
import soundfile as sf
import numpy as np


class GeneratedAudio(BaseModel):
    """Represents generated audio."""

    audio_path: str
    text: str
    duration: float  # in seconds
    sample_rate: int
    model: str
    metadata: Dict = {}


class TTSService:
    """
    Text-to-speech service supporting multiple backends.

    Supports:
    - Dia TTS (preferred, open-source, local)
    - OpenAI TTS (fallback, API-based)
    """

    def __init__(
        self,
        backend: str = "dia",
        dia_model_path: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        output_dir: str = "storage/generated",
        target_sample_rate: int = 16000  # Required for OmniAvatar
    ):
        """
        Initialize TTS service.

        Args:
            backend: TTS backend to use ('dia' or 'openai')
            dia_model_path: Path to Dia TTS model
            openai_api_key: OpenAI API key (for fallback)
            output_dir: Directory to save audio files
            target_sample_rate: Sample rate for output audio (16000 for OmniAvatar)
        """
        self.backend = backend
        self.dia_model_path = dia_model_path or os.getenv("DIA_MODEL_PATH")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.target_sample_rate = target_sample_rate

        # Validate backend setup
        if self.backend == "dia":
            self._validate_dia_setup()
        elif self.backend == "openai":
            if not self.openai_api_key:
                raise ValueError("OpenAI API key required for OpenAI TTS backend")
        else:
            raise ValueError(f"Unknown TTS backend: {backend}")

        logger.info(f"TTS service initialized with backend: {backend}")

    def _validate_dia_setup(self):
        """Validate Dia TTS installation."""
        try:
            # Check if Dia is installed
            result = subprocess.run(
                ["which", "dia-tts"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.warning(
                    "Dia TTS not found in PATH. "
                    "Install from: https://github.com/nari-labs/dia/"
                )
                logger.info("Falling back to OpenAI TTS if available")
                self.backend = "openai"
            else:
                logger.info(f"Dia TTS found at: {result.stdout.strip()}")

        except Exception as e:
            logger.warning(f"Error checking Dia installation: {e}")
            self.backend = "openai"

    async def generate_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        save_name: Optional[str] = None
    ) -> GeneratedAudio:
        """
        Generate speech from text.

        Args:
            text: Text to convert to speech
            voice: Voice ID or name (backend-specific)
            speed: Speech speed multiplier (1.0 = normal)
            save_name: Optional filename

        Returns:
            GeneratedAudio with path and metadata
        """

        if self.backend == "dia":
            return await self._generate_with_dia(text, voice, speed, save_name)
        elif self.backend == "openai":
            return await self._generate_with_openai(text, voice, speed, save_name)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    async def _generate_with_dia(
        self,
        text: str,
        voice: Optional[str],
        speed: float,
        save_name: Optional[str]
    ) -> GeneratedAudio:
        """Generate speech using Dia TTS."""

        try:
            # Generate filename
            if not save_name:
                import hashlib
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                hash_suffix = hashlib.md5(text.encode()).hexdigest()[:8]
                save_name = f"tts_{timestamp}_{hash_suffix}.wav"

            output_path = self.output_dir / save_name

            logger.info(f"Generating speech with Dia TTS: {len(text)} characters")

            # Build Dia command
            # Note: Adjust this based on actual Dia CLI interface
            cmd = [
                "dia-tts",
                "--text", text,
                "--output", str(output_path),
                "--sample-rate", str(self.target_sample_rate)
            ]

            if voice:
                cmd.extend(["--voice", voice])

            if speed != 1.0:
                cmd.extend(["--speed", str(speed)])

            # Run Dia TTS
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"Dia TTS failed: {result.stderr}")

            # Load audio to get metadata
            audio_data, sample_rate = sf.read(str(output_path))
            duration = len(audio_data) / sample_rate

            logger.info(f"Audio generated: {duration:.2f}s, saved to {output_path}")

            return GeneratedAudio(
                audio_path=str(output_path),
                text=text,
                duration=duration,
                sample_rate=sample_rate,
                model="dia-tts",
                metadata={
                    "voice": voice,
                    "speed": speed,
                    "backend": "dia"
                }
            )

        except subprocess.TimeoutExpired:
            logger.error("Dia TTS timed out")
            raise
        except Exception as e:
            logger.error(f"Error with Dia TTS: {e}")
            # Fallback to OpenAI if available
            if self.openai_api_key:
                logger.info("Falling back to OpenAI TTS")
                return await self._generate_with_openai(text, voice, speed, save_name)
            raise

    async def _generate_with_openai(
        self,
        text: str,
        voice: Optional[str],
        speed: float,
        save_name: Optional[str]
    ) -> GeneratedAudio:
        """Generate speech using OpenAI TTS."""

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.openai_api_key)

            # Generate filename
            if not save_name:
                import hashlib
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                hash_suffix = hashlib.md5(text.encode()).hexdigest()[:8]
                save_name = f"tts_{timestamp}_{hash_suffix}.mp3"

            output_path = self.output_dir / save_name

            logger.info(f"Generating speech with OpenAI TTS: {len(text)} characters")

            # OpenAI TTS voices: alloy, echo, fable, onyx, nova, shimmer
            voice = voice or "alloy"

            # Generate speech
            response = client.audio.speech.create(
                model="tts-1-hd",  # or tts-1 for faster/cheaper
                voice=voice,
                input=text,
                speed=speed
            )

            # Save to file
            response.stream_to_file(str(output_path))

            # Convert to WAV at correct sample rate if needed
            wav_path = output_path.with_suffix('.wav')
            self._convert_to_wav(str(output_path), str(wav_path))

            # Load audio to get metadata
            audio_data, sample_rate = sf.read(str(wav_path))
            duration = len(audio_data) / sample_rate

            logger.info(f"Audio generated: {duration:.2f}s, saved to {wav_path}")

            return GeneratedAudio(
                audio_path=str(wav_path),
                text=text,
                duration=duration,
                sample_rate=sample_rate,
                model="openai-tts-1-hd",
                metadata={
                    "voice": voice,
                    "speed": speed,
                    "backend": "openai"
                }
            )

        except Exception as e:
            logger.error(f"Error with OpenAI TTS: {e}")
            raise

    def _convert_to_wav(self, input_path: str, output_path: str):
        """Convert audio to WAV format at target sample rate using ffmpeg."""

        try:
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-ar", str(self.target_sample_rate),
                "-ac", "1",  # Mono
                "-y",  # Overwrite
                output_path
            ]

            subprocess.run(cmd, capture_output=True, check=True)
            logger.debug(f"Converted to WAV: {output_path}")

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg conversion failed: {e.stderr.decode()}")
            raise

    async def batch_generate(
        self,
        texts: list[str],
        **kwargs
    ) -> list[GeneratedAudio]:
        """Generate audio for multiple texts."""

        audio_files = []

        for i, text in enumerate(texts):
            try:
                save_name = f"batch_{i:03d}.wav"
                audio = await self.generate_speech(
                    text=text,
                    save_name=save_name,
                    **kwargs
                )
                audio_files.append(audio)

            except Exception as e:
                logger.error(f"Failed to generate audio {i+1}: {e}")

        logger.info(f"Generated {len(audio_files)}/{len(texts)} audio files")
        return audio_files


# Example usage
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv

    load_dotenv()

    async def main():
        # Try Dia first, fallback to OpenAI
        tts = TTSService(backend="dia")

        text = """
        Welcome to NovaAvatar! Today we're discussing the latest breakthrough in AI technology.
        This new system represents a significant step forward in making AI more accessible to everyone.
        Stay tuned for more updates!
        """

        audio = await tts.generate_speech(text.strip())

        print(f"Generated audio: {audio.audio_path}")
        print(f"Duration: {audio.duration:.2f} seconds")
        print(f"Sample rate: {audio.sample_rate} Hz")

    asyncio.run(main())
