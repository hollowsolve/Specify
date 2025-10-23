"""
Error handling middleware for the Specify API.

Provides global exception handling, error response formatting,
and error logging for the entire application.
"""

import logging
import traceback
from typing import Callable, Union
from datetime import datetime

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import ValidationError

from api.schemas.response_schemas import ErrorResponse

logger = logging.getLogger(__name__)


class CustomExceptionHandler(BaseHTTPMiddleware):
    """Middleware for handling exceptions and formatting error responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle any exceptions."""
        try:
            response = await call_next(request)
            return response

        except HTTPException as e:
            # FastAPI HTTP exceptions - already formatted
            return await self.handle_http_exception(request, e)

        except ValidationError as e:
            # Pydantic validation errors
            return await self.handle_validation_error(request, e)

        except Exception as e:
            # Unexpected exceptions
            return await self.handle_unexpected_error(request, e)

    async def handle_http_exception(self, request: Request, exc: HTTPException) -> JSONResponse:
        """Handle FastAPI HTTP exceptions."""
        request_id = getattr(request.state, "request_id", "unknown")

        # Log the HTTP exception
        logger.warning(
            f"HTTP Exception: {exc.status_code} - {exc.detail}",
            extra={
                "request_id": request_id,
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": request.url.path,
                "method": request.method
            }
        )

        # Format error response
        error_response = ErrorResponse(
            error_type="http_error",
            error_code=f"HTTP_{exc.status_code}",
            message=exc.detail,
            details={
                "status_code": exc.status_code,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method
            }
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.dict(),
            headers=getattr(exc, "headers", None)
        )

    async def handle_validation_error(self, request: Request, exc: ValidationError) -> JSONResponse:
        """Handle Pydantic validation errors."""
        request_id = getattr(request.state, "request_id", "unknown")

        # Log validation error
        logger.warning(
            f"Validation Error: {exc}",
            extra={
                "request_id": request_id,
                "errors": exc.errors(),
                "path": request.url.path,
                "method": request.method
            }
        )

        # Format validation errors
        validation_errors = []
        for error in exc.errors():
            validation_errors.append({
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input")
            })

        error_response = ErrorResponse(
            error_type="validation_error",
            error_code="VALIDATION_FAILED",
            message="Request validation failed",
            details={
                "validation_errors": validation_errors,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method
            }
        )

        return JSONResponse(
            status_code=422,
            content=error_response.dict()
        )

    async def handle_unexpected_error(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions."""
        request_id = getattr(request.state, "request_id", "unknown")

        # Log the unexpected error with full traceback
        logger.exception(
            f"Unexpected Error: {str(exc)}",
            extra={
                "request_id": request_id,
                "error_type": type(exc).__name__,
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc()
            }
        )

        # Determine if this is a known internal error type
        error_code = self.get_error_code(exc)
        status_code = self.get_status_code(exc)

        error_response = ErrorResponse(
            error_type="internal_error",
            error_code=error_code,
            message="An unexpected error occurred",
            details={
                "error_id": request_id,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "timestamp": datetime.now().isoformat()
            }
        )

        return JSONResponse(
            status_code=status_code,
            content=error_response.dict()
        )

    def get_error_code(self, exc: Exception) -> str:
        """Get appropriate error code for exception type."""
        error_type = type(exc).__name__

        # Map common exception types to error codes
        error_code_mapping = {
            "ConnectionError": "CONNECTION_ERROR",
            "TimeoutError": "TIMEOUT_ERROR",
            "PermissionError": "PERMISSION_ERROR",
            "FileNotFoundError": "FILE_NOT_FOUND",
            "ValueError": "VALUE_ERROR",
            "TypeError": "TYPE_ERROR",
            "KeyError": "KEY_ERROR",
            "AttributeError": "ATTRIBUTE_ERROR",
        }

        return error_code_mapping.get(error_type, "UNKNOWN_ERROR")

    def get_status_code(self, exc: Exception) -> int:
        """Get appropriate HTTP status code for exception type."""
        error_type = type(exc).__name__

        # Map exception types to HTTP status codes
        status_code_mapping = {
            "ConnectionError": 503,  # Service Unavailable
            "TimeoutError": 504,     # Gateway Timeout
            "PermissionError": 403,  # Forbidden
            "FileNotFoundError": 404, # Not Found
            "ValueError": 400,       # Bad Request
            "TypeError": 400,        # Bad Request
        }

        return status_code_mapping.get(error_type, 500)  # Internal Server Error


class SpecifyAPIException(Exception):
    """Custom exception for Specify API errors."""

    def __init__(
        self,
        message: str,
        error_code: str = None,
        error_type: str = "api_error",
        status_code: int = 500,
        details: dict = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "API_ERROR"
        self.error_type = error_type
        self.status_code = status_code
        self.details = details or {}


class AnalysisException(SpecifyAPIException):
    """Exception for analysis phase errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_type="analysis_error",
            error_code=kwargs.get("error_code", "ANALYSIS_FAILED"),
            **kwargs
        )


class SpecificationException(SpecifyAPIException):
    """Exception for specification phase errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_type="specification_error",
            error_code=kwargs.get("error_code", "SPECIFICATION_FAILED"),
            **kwargs
        )


class RefinementException(SpecifyAPIException):
    """Exception for refinement phase errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_type="refinement_error",
            error_code=kwargs.get("error_code", "REFINEMENT_FAILED"),
            **kwargs
        )


class DispatchException(SpecifyAPIException):
    """Exception for dispatch phase errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_type="dispatch_error",
            error_code=kwargs.get("error_code", "DISPATCH_FAILED"),
            **kwargs
        )


class SessionException(SpecifyAPIException):
    """Exception for session management errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_type="session_error",
            error_code=kwargs.get("error_code", "SESSION_ERROR"),
            status_code=kwargs.get("status_code", 400),
            **kwargs
        )


# Exception handler functions for custom exceptions
async def handle_specify_api_exception(request: Request, exc: SpecifyAPIException) -> JSONResponse:
    """Handle custom Specify API exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")

    # Log the custom exception
    logger.error(
        f"Specify API Exception: {exc.error_type} - {exc.message}",
        extra={
            "request_id": request_id,
            "error_type": exc.error_type,
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )

    error_response = ErrorResponse(
        error_type=exc.error_type,
        error_code=exc.error_code,
        message=exc.message,
        details={
            **exc.details,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )


# Utility functions for raising common errors
def raise_not_found(resource: str, identifier: str = None):
    """Raise a not found error."""
    message = f"{resource} not found"
    if identifier:
        message += f": {identifier}"

    raise HTTPException(status_code=404, detail=message)


def raise_validation_error(message: str, field: str = None):
    """Raise a validation error."""
    detail = message
    if field:
        detail = f"Validation error in field '{field}': {message}"

    raise HTTPException(status_code=422, detail=detail)


def raise_permission_error(message: str = "Permission denied"):
    """Raise a permission error."""
    raise HTTPException(status_code=403, detail=message)


def raise_rate_limit_error(message: str = "Rate limit exceeded"):
    """Raise a rate limit error."""
    raise HTTPException(status_code=429, detail=message)


def raise_service_unavailable(message: str = "Service temporarily unavailable"):
    """Raise a service unavailable error."""
    raise HTTPException(status_code=503, detail=message)