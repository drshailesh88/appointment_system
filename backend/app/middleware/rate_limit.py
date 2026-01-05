"""
Additional rate limiting middleware for sensitive endpoints.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Additional rate limiting for specific sensitive endpoints.

    Works alongside slowapi for enhanced protection.
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            app: FastAPI application
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

        # In-memory storage (use Redis in production)
        self._requests: dict[str, list[datetime]] = defaultdict(list)

    def _get_client_key(self, request: Request) -> str:
        """Get unique client identifier."""
        # Use IP + user ID if authenticated
        client_ip = request.client.host if request.client else "unknown"

        # Try to get user ID from token
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.core.security import decode_token
                token = auth_header[7:]
                payload = decode_token(token)
                if payload:
                    user_id = payload.get("sub")
                    return f"{client_ip}:{user_id}"
            except Exception:
                pass

        return client_ip

    def _cleanup_old_requests(self, key: str):
        """Remove requests outside the time window."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.window_seconds)
        self._requests[key] = [
            ts for ts in self._requests[key] if ts > cutoff_time
        ]

    def _is_rate_limited(self, key: str) -> bool:
        """Check if client has exceeded rate limit."""
        self._cleanup_old_requests(key)
        return len(self._requests[key]) >= self.max_requests

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit before processing request."""
        client_key = self._get_client_key(request)

        if self._is_rate_limited(client_key):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": self.window_seconds,
                },
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(
                        int(
                            (
                                datetime.utcnow()
                                + timedelta(seconds=self.window_seconds)
                            ).timestamp()
                        )
                    ),
                },
            )

        # Record this request
        self._requests[client_key].append(datetime.utcnow())

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = self.max_requests - len(self._requests[client_key])
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))

        return response
