"""
Audit logging middleware for tracking sensitive operations.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log security-sensitive operations.

    Logs:
    - Authentication attempts (login, logout, token refresh)
    - Authorization failures
    - Data modifications (CREATE, UPDATE, DELETE)
    - Administrative actions
    - Payment operations
    """

    # Paths that trigger audit logs
    AUDIT_PATHS = {
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/refresh",
        "/api/v1/auth/register",
        "/api/v1/payments",
        "/api/v1/invoices",
    }

    # Methods that trigger audit logs
    AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log security-sensitive operations."""
        should_audit = (
            request.method in self.AUDIT_METHODS
            or any(request.url.path.startswith(path) for path in self.AUDIT_PATHS)
        )

        if should_audit:
            # Extract user info from token (if available)
            user_id = None
            user_email = None

            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                # Try to decode token for user info (non-blocking)
                try:
                    from app.core.security import decode_token
                    token = auth_header[7:]
                    payload = decode_token(token)
                    if payload:
                        user_id = payload.get("sub")
                except Exception:
                    pass

            # Log the request
            audit_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "method": request.method,
                "path": request.url.path,
                "user_id": user_id,
                "ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }

        # Process request
        response = await call_next(request)

        # Log response for audited requests
        if should_audit:
            audit_data["status_code"] = response.status_code
            audit_data["success"] = 200 <= response.status_code < 300

            # Log as JSON for structured logging
            logger.info(
                f"AUDIT: {json.dumps(audit_data)}",
                extra=audit_data,
            )

        return response
