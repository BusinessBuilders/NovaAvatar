"""Middleware for tracking HTTP metrics."""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from api.routers.metrics import http_requests_total, http_request_duration_seconds


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track request metrics."""

    async def dispatch(self, request: Request, call_next):
        """Track request metrics."""
        # Start timer
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Record metrics
        method = request.method
        endpoint = request.url.path
        status = response.status_code

        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()

        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

        return response
