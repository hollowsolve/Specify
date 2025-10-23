"""
Logging middleware for the Specify API.

Provides request/response logging with timing, user tracking, and
structured logging for monitoring and debugging.
"""

import time
import uuid
import logging
from typing import Callable
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""

    def __init__(self, app, logger_name: str = "api.requests"):
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Start timing
        start_time = time.time()

        # Extract request information
        client_ip = self.get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        session_id = self.extract_session_id(request)

        # Log request start
        self.logger.info(
            f"REQUEST START",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception
            processing_time = time.time() - start_time
            self.logger.error(
                f"REQUEST ERROR",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "client_ip": client_ip,
                    "session_id": session_id,
                    "processing_time": processing_time,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise

        # Calculate processing time
        processing_time = time.time() - start_time

        # Get response size (estimate for streaming responses)
        response_size = self.get_response_size(response)

        # Log response
        self.logger.info(
            f"REQUEST COMPLETE",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "client_ip": client_ip,
                "session_id": session_id,
                "status_code": response.status_code,
                "processing_time": processing_time,
                "response_size": response_size,
                "timestamp": datetime.now().isoformat()
            }
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response

    def get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers (when behind proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to client host
        if request.client:
            return request.client.host

        return "unknown"

    def extract_session_id(self, request: Request) -> str:
        """Extract session ID from request."""
        # Try query parameter first
        session_id = request.query_params.get("session_id")
        if session_id:
            return session_id

        # Try path parameter
        if hasattr(request, "path_params") and "session_id" in request.path_params:
            return request.path_params["session_id"]

        # Try JSON body (for POST requests)
        # Note: This is not ideal as it requires reading the body
        # In practice, you might want to extract this differently

        return "unknown"

    def get_response_size(self, response: Response) -> int:
        """Estimate response size."""
        if hasattr(response, "body"):
            if isinstance(response.body, bytes):
                return len(response.body)
            elif isinstance(response.body, str):
                return len(response.body.encode('utf-8'))

        # For streaming responses, we can't easily determine size
        if isinstance(response, StreamingResponse):
            return -1

        # Try to get from content-length header
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                return int(content_length)
            except ValueError:
                pass

        return -1


class StructuredLogger:
    """Utility class for structured logging."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def log_user_action(
        self,
        action: str,
        user_id: str = None,
        session_id: str = None,
        details: dict = None
    ):
        """Log user actions for analytics."""
        self.logger.info(
            f"USER ACTION: {action}",
            extra={
                "event_type": "user_action",
                "action": action,
                "user_id": user_id,
                "session_id": session_id,
                "details": details or {},
                "timestamp": datetime.now().isoformat()
            }
        )

    def log_system_event(
        self,
        event: str,
        component: str,
        level: str = "info",
        details: dict = None
    ):
        """Log system events."""
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(
            log_level,
            f"SYSTEM EVENT: {event}",
            extra={
                "event_type": "system_event",
                "event": event,
                "component": component,
                "details": details or {},
                "timestamp": datetime.now().isoformat()
            }
        )

    def log_performance_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "seconds",
        component: str = None,
        details: dict = None
    ):
        """Log performance metrics."""
        self.logger.info(
            f"PERFORMANCE: {metric_name} = {value} {unit}",
            extra={
                "event_type": "performance_metric",
                "metric_name": metric_name,
                "value": value,
                "unit": unit,
                "component": component,
                "details": details or {},
                "timestamp": datetime.now().isoformat()
            }
        )

    def log_error(
        self,
        error: Exception,
        context: str = None,
        user_id: str = None,
        session_id: str = None,
        additional_data: dict = None
    ):
        """Log errors with context."""
        self.logger.error(
            f"ERROR: {str(error)}",
            extra={
                "event_type": "error",
                "error_message": str(error),
                "error_type": type(error).__name__,
                "context": context,
                "user_id": user_id,
                "session_id": session_id,
                "additional_data": additional_data or {},
                "timestamp": datetime.now().isoformat()
            },
            exc_info=True
        )


# Global structured logger instance
structured_logger = StructuredLogger("api.structured")


# Helper functions for use throughout the application
def log_user_action(action: str, **kwargs):
    """Convenience function for logging user actions."""
    structured_logger.log_user_action(action, **kwargs)


def log_system_event(event: str, component: str, **kwargs):
    """Convenience function for logging system events."""
    structured_logger.log_system_event(event, component, **kwargs)


def log_performance_metric(metric_name: str, value: float, **kwargs):
    """Convenience function for logging performance metrics."""
    structured_logger.log_performance_metric(metric_name, value, **kwargs)


def log_error(error: Exception, **kwargs):
    """Convenience function for logging errors."""
    structured_logger.log_error(error, **kwargs)