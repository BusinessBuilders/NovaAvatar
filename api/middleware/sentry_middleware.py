"""Sentry integration for error monitoring."""

import os
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from loguru import logger


def init_sentry(
    dsn: Optional[str] = None,
    environment: str = "development",
    traces_sample_rate: float = 0.1,
) -> None:
    """
    Initialize Sentry error tracking.

    Args:
        dsn: Sentry DSN (Data Source Name)
        environment: Environment name (development, staging, production)
        traces_sample_rate: Percentage of transactions to sample (0.0 to 1.0)
    """
    # Get DSN from parameter or environment
    dsn = dsn or os.getenv("SENTRY_DSN")

    if not dsn:
        logger.info("Sentry DSN not configured, error tracking disabled")
        return

    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            traces_sample_rate=traces_sample_rate,
            integrations=[
                SqlalchemyIntegration(),
                RedisIntegration(),
                LoggingIntegration(
                    level=None,  # Capture all logs
                    event_level=None,  # Send no logs as events
                ),
            ],
            # Don't send sensitive data
            send_default_pii=False,
            # Performance monitoring
            enable_tracing=True,
            # Release tracking
            release=os.getenv("SENTRY_RELEASE", "novaavatar@unknown"),
            # Filter out health check endpoints
            before_send=_before_send,
        )

        logger.info(f"Sentry initialized for environment: {environment}")

    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def _before_send(event, hint):
    """
    Filter events before sending to Sentry.

    Args:
        event: Sentry event
        hint: Additional context

    Returns:
        Event to send or None to drop
    """
    # Don't send events for health check endpoints
    if event.get("request", {}).get("url", "").endswith("/health"):
        return None

    # Don't send 404 errors
    if event.get("level") == "info":
        return None

    return event


def capture_exception(error: Exception, context: dict = None):
    """
    Manually capture an exception to Sentry.

    Args:
        error: Exception to capture
        context: Additional context to include
    """
    if context:
        sentry_sdk.set_context("custom", context)

    sentry_sdk.capture_exception(error)
