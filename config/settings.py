"""
Application Settings
Centralized configuration management using Pydantic.
"""

import os
from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # =============================================================================
    # AI Services
    # =============================================================================
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    replicate_api_token: str = Field(default="", env="REPLICATE_API_TOKEN")

    # =============================================================================
    # Content Sources
    # =============================================================================
    reddit_client_id: Optional[str] = Field(default=None, env="REDDIT_CLIENT_ID")
    reddit_client_secret: Optional[str] = Field(default=None, env="REDDIT_CLIENT_SECRET")
    newsapi_key: Optional[str] = Field(default=None, env="NEWSAPI_KEY")

    # =============================================================================
    # TTS Configuration
    # =============================================================================
    dia_model_path: Optional[str] = Field(default=None, env="DIA_MODEL_PATH")

    # =============================================================================
    # Redis Configuration
    # =============================================================================
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")

    # =============================================================================
    # Model Configuration
    # =============================================================================
    use_14b_model: bool = Field(default=False, env="USE_14B_MODEL")

    # =============================================================================
    # Generation Parameters
    # =============================================================================
    num_steps: int = Field(default=25, env="NUM_STEPS")
    guidance_scale: float = Field(default=4.5, env="GUIDANCE_SCALE")
    audio_scale: Optional[float] = Field(default=None, env="AUDIO_SCALE")
    tea_cache_thresh: float = Field(default=0.14, env="TEA_CACHE_THRESH")
    enable_vram_management: bool = Field(default=True, env="ENABLE_VRAM_MANAGEMENT")

    # =============================================================================
    # Server Configuration
    # =============================================================================
    gradio_server_port: int = Field(default=7860, env="GRADIO_SERVER_PORT")
    gradio_server_name: str = Field(default="0.0.0.0", env="GRADIO_SERVER_NAME")
    api_server_port: int = Field(default=8000, env="API_SERVER_PORT")
    api_server_host: str = Field(default="0.0.0.0", env="API_SERVER_HOST")
    gradio_share: bool = Field(default=False, env="GRADIO_SHARE")

    # =============================================================================
    # Storage Configuration
    # =============================================================================
    storage_dir: str = Field(default="storage", env="STORAGE_DIR")
    auto_approve: bool = Field(default=False, env="AUTO_APPROVE")

    # =============================================================================
    # Logging & Monitoring
    # =============================================================================
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")

    # =============================================================================
    # Production Settings
    # =============================================================================
    enable_cors: bool = Field(default=True, env="ENABLE_CORS")
    rate_limit_per_minute: int = Field(default=10, env="RATE_LIMIT_PER_MINUTE")
    max_concurrent_jobs: int = Field(default=2, env="MAX_CONCURRENT_JOBS")
    job_timeout: int = Field(default=3600, env="JOB_TIMEOUT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def setup_logging():
    """Setup logging configuration."""
    from loguru import logger
    import sys

    # Remove default handler
    logger.remove()

    # Add console handler
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )

    # Add file handler
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger.add(
        "logs/novaavatar_{time}.log",
        rotation="1 day",
        retention="7 days",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
    )

    logger.info("Logging configured")

    # Setup Sentry if configured
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                traces_sample_rate=0.1,
                environment="production"
            )
            logger.info("Sentry monitoring enabled")
        except Exception as e:
            logger.warning(f"Failed to initialize Sentry: {e}")


def validate_settings():
    """Validate required settings are configured."""
    from loguru import logger

    errors = []

    # Check required API keys
    if not settings.openai_api_key:
        errors.append("OPENAI_API_KEY not set")

    if not settings.replicate_api_token:
        errors.append("REPLICATE_API_TOKEN not set")

    # Check model paths exist
    model_base = Path("pretrained_models")
    if settings.use_14b_model:
        model_path = model_base / "Wan2.1-T2V-14B"
    else:
        model_path = model_base / "Wan2.1-T2V-1.3B"

    if not model_path.exists():
        errors.append(f"Model path not found: {model_path}")

    if errors:
        logger.error("Configuration errors found:")
        for error in errors:
            logger.error(f"  - {error}")

        logger.info("\nPlease:")
        logger.info("1. Copy .env.example to .env")
        logger.info("2. Fill in your API keys")
        logger.info("3. Download required models")

        return False

    logger.info("Configuration validated successfully")
    return True


if __name__ == "__main__":
    setup_logging()

    from loguru import logger
    logger.info("Current settings:")
    logger.info(f"  Model: {'14B' if settings.use_14b_model else '1.3B'}")
    logger.info(f"  Gradio port: {settings.gradio_server_port}")
    logger.info(f"  API port: {settings.api_server_port}")
    logger.info(f"  Storage: {settings.storage_dir}")
    logger.info(f"  Auto-approve: {settings.auto_approve}")

    validate_settings()
