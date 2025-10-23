"""
Middleware components for the Specify API.

This module contains middleware for logging, error handling,
authentication, and other cross-cutting concerns.
"""

from .logging_middleware import (
    LoggingMiddleware,
    StructuredLogger,
    structured_logger,
    log_user_action,
    log_system_event,
    log_performance_metric,
    log_error
)

from .error_handler import (
    CustomExceptionHandler,
    SpecifyAPIException,
    AnalysisException,
    SpecificationException,
    RefinementException,
    DispatchException,
    SessionException,
    handle_specify_api_exception,
    raise_not_found,
    raise_validation_error,
    raise_permission_error,
    raise_rate_limit_error,
    raise_service_unavailable
)

__all__ = [
    # Logging middleware
    "LoggingMiddleware",
    "StructuredLogger",
    "structured_logger",
    "log_user_action",
    "log_system_event",
    "log_performance_metric",
    "log_error",

    # Error handling
    "CustomExceptionHandler",
    "SpecifyAPIException",
    "AnalysisException",
    "SpecificationException",
    "RefinementException",
    "DispatchException",
    "SessionException",
    "handle_specify_api_exception",
    "raise_not_found",
    "raise_validation_error",
    "raise_permission_error",
    "raise_rate_limit_error",
    "raise_service_unavailable",
]