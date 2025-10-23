"""
Pydantic schemas for the Specify API.

This module contains all request and response schemas used by the FastAPI
endpoints. The schemas provide type safety, validation, and automatic
API documentation generation.
"""

from .request_schemas import *
from .response_schemas import *

__all__ = [
    # Request schemas
    "BaseRequest",
    "AnalyzePromptRequest",
    "SpecificationMode",
    "SpecificationRequest",
    "UserDecisionAction",
    "RefinementStartRequest",
    "RefinementDecisionRequest",
    "RefinementModifyRequest",
    "RefinementFinalizeRequest",
    "ExecutionMode",
    "DispatchExecutionRequest",
    "DispatchCancelRequest",
    "WebSocketMessageType",
    "WebSocketMessage",
    "WebSocketSubscribeRequest",
    "FileUploadRequest",
    "SessionCreateRequest",
    "SessionUpdateRequest",
    "RequestValidator",

    # Response schemas
    "BaseResponse",
    "ErrorResponse",
    "AnalysisResult",
    "AnalyzeResponse",
    "EdgeCase",
    "Contradiction",
    "CompressedRequirement",
    "RefinedSpecification",
    "SpecificationResponse",
    "RefinementSuggestion",
    "UserDecision",
    "RefinementIteration",
    "RefinementSession",
    "RefinementResponse",
    "TaskStatus",
    "ExecutionStatus",
    "Task",
    "AgentResult",
    "ExecutionGraph",
    "ExecutionResult",
    "DispatchResponse",
    "WebSocketEvent",
    "SessionInfo",
    "SessionResponse",
    "HealthResponse",
    "VersionResponse",
]