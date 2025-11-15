"""Rate limiting middleware for API endpoints."""

import time
from typing import Callable
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import redis
from loguru import logger


class RateLimiter(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window algorithm.

    Supports both in-memory and Redis-based rate limiting.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        redis_url: str = None,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # 60 seconds

        # Try to use Redis if available
        self.redis_client = None
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("Rate limiter using Redis backend")
            except Exception as e:
                logger.warning(f"Redis unavailable, using in-memory rate limiting: {e}")

        # Fallback to in-memory storage
        if not self.redis_client:
            self.requests = defaultdict(list)
            logger.info("Rate limiter using in-memory backend")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and apply rate limiting."""

        # Skip rate limiting for health checks and metrics
        if request.url.path in ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_id(request)

        # Check rate limit
        if not await self._is_allowed(client_id):
            logger.warning(f"Rate limit exceeded for {client_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after": self.window_size,
                    "limit": self.requests_per_minute,
                },
            )

        # Record request
        await self._record_request(client_id)

        # Add rate limit headers to response
        response = await call_next(request)
        remaining = await self._get_remaining(client_id)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.window_size)

        return response

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        # Try to get API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0]}"

        if request.client:
            return f"ip:{request.client.host}"

        return "unknown"

    async def _is_allowed(self, client_id: str) -> bool:
        """Check if client is within rate limit."""
        if self.redis_client:
            return await self._is_allowed_redis(client_id)
        else:
            return self._is_allowed_memory(client_id)

    async def _is_allowed_redis(self, client_id: str) -> bool:
        """Check rate limit using Redis."""
        key = f"rate_limit:{client_id}"
        now = time.time()
        window_start = now - self.window_size

        try:
            # Use Redis sorted set for sliding window
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.expire(key, self.window_size)
            _, count, _ = pipe.execute()

            return count < self.requests_per_minute
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            return True  # Fail open

    def _is_allowed_memory(self, client_id: str) -> bool:
        """Check rate limit using in-memory storage."""
        now = time.time()
        window_start = now - self.window_size

        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > window_start
        ]

        return len(self.requests[client_id]) < self.requests_per_minute

    async def _record_request(self, client_id: str):
        """Record a request."""
        if self.redis_client:
            await self._record_request_redis(client_id)
        else:
            self._record_request_memory(client_id)

    async def _record_request_redis(self, client_id: str):
        """Record request using Redis."""
        key = f"rate_limit:{client_id}"
        now = time.time()

        try:
            self.redis_client.zadd(key, {str(now): now})
        except Exception as e:
            logger.error(f"Failed to record request in Redis: {e}")

    def _record_request_memory(self, client_id: str):
        """Record request using in-memory storage."""
        self.requests[client_id].append(time.time())

    async def _get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client."""
        if self.redis_client:
            key = f"rate_limit:{client_id}"
            try:
                count = self.redis_client.zcard(key)
                return max(0, self.requests_per_minute - count)
            except Exception:
                return self.requests_per_minute
        else:
            count = len(self.requests[client_id])
            return max(0, self.requests_per_minute - count)
