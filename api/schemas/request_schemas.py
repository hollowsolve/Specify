"""
Pydantic request schemas for the Specify API.

All request models with validation for the REST endpoints.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


# Base schemas
class BaseRequest(BaseModel):
    """Base request model with common fields."""
    session_id: Optional[str] = Field(None, description="Session ID for tracking")


# Analyzer schemas (Phase 1)
class AnalyzePromptRequest(BaseRequest):
    """Request for prompt analysis."""
    prompt: str = Field(..., min_length=1, max_length=10000, description="The prompt to analyze")
    analysis_options: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional analysis options"
    )
    user_context: Optional[str] = Field(None, description="Additional user context")


# Specification schemas (Phase 2)
class SpecificationMode(str, Enum):
    """Processing modes for specification engine."""
    FAST = "fast"
    BALANCED = "balanced"
    INTELLIGENT = "intelligent"


class SpecificationRequest(BaseRequest):
    """Request for specification refinement."""
    analysis_result_id: str = Field(..., description="ID of the analysis result to refine")
    mode: SpecificationMode = Field(
        SpecificationMode.BALANCED,
        description="Processing mode for specification engine"
    )
    custom_rules: Optional[List[str]] = Field(None, description="Custom rules to apply")
    focus_areas: Optional[List[str]] = Field(None, description="Specific areas to focus on")


# Refinement schemas (Phase 3)
class UserDecisionAction(str, Enum):
    """User decision actions for refinement."""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    SKIP = "skip"


class RefinementStartRequest(BaseRequest):
    """Request to start a refinement session."""
    specification_id: str = Field(..., description="ID of the specification to refine")
    interaction_mode: str = Field("interactive", description="Mode for refinement interaction")
    auto_approve_threshold: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Threshold for auto-approval of suggestions"
    )


class RefinementDecisionRequest(BaseRequest):
    """Request for user decision on refinement suggestion."""
    suggestion_id: str = Field(..., description="ID of the suggestion to respond to")
    action: UserDecisionAction = Field(..., description="User decision action")
    feedback: Optional[str] = Field(None, description="Optional feedback or modification")
    reason: Optional[str] = Field(None, description="Reason for the decision")


class RefinementModifyRequest(BaseRequest):
    """Request to modify a refinement suggestion."""
    suggestion_id: str = Field(..., description="ID of the suggestion to modify")
    modified_content: str = Field(..., description="Modified content for the suggestion")
    reason: Optional[str] = Field(None, description="Reason for the modification")


class RefinementFinalizeRequest(BaseRequest):
    """Request to finalize a refinement session."""
    include_rejected: bool = Field(False, description="Include rejected suggestions in final spec")
    final_notes: Optional[str] = Field(None, description="Final notes for the specification")


# Dispatch schemas (Phase 4)
class ExecutionMode(str, Enum):
    """Execution modes for agent dispatch."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ADAPTIVE = "adaptive"


class DispatchExecutionRequest(BaseRequest):
    """Request to start agent execution."""
    specification_id: str = Field(..., description="ID of the finalized specification")
    execution_mode: ExecutionMode = Field(
        ExecutionMode.ADAPTIVE,
        description="Execution mode for agents"
    )
    agent_constraints: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Constraints for agent execution"
    )
    target_platform: Optional[str] = Field(None, description="Target platform for code generation")
    output_format: Optional[str] = Field("files", description="Output format preference")


class DispatchCancelRequest(BaseRequest):
    """Request to cancel an execution."""
    execution_id: str = Field(..., description="ID of the execution to cancel")
    reason: Optional[str] = Field(None, description="Reason for cancellation")


# WebSocket schemas
class WebSocketMessageType(str, Enum):
    """WebSocket message types."""
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"
    USER_INPUT = "user_input"
    REFINEMENT_FEEDBACK = "refinement_feedback"


class WebSocketMessage(BaseModel):
    """WebSocket message structure."""
    type: WebSocketMessageType = Field(..., description="Message type")
    session_id: str = Field(..., description="Session ID")
    data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Message data")
    timestamp: Optional[str] = Field(None, description="Message timestamp")


class WebSocketSubscribeRequest(BaseModel):
    """WebSocket subscription request."""
    session_id: str = Field(..., description="Session ID to subscribe to")
    event_types: List[str] = Field(..., description="Event types to subscribe to")


# File upload schemas
class FileUploadRequest(BaseModel):
    """Request for file upload."""
    session_id: Optional[str] = Field(None, description="Session ID")
    file_purpose: str = Field(..., description="Purpose of the file upload")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="File metadata")


# Session management schemas
class SessionCreateRequest(BaseModel):
    """Request to create a new session."""
    user_id: Optional[str] = Field(None, description="User ID for session")
    session_name: Optional[str] = Field(None, description="Name for the session")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session metadata")


class SessionUpdateRequest(BaseModel):
    """Request to update session."""
    session_id: str = Field(..., description="Session ID to update")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")
    extend_timeout: Optional[bool] = Field(False, description="Extend session timeout")


# Validation helpers
class RequestValidator:
    """Utility class for request validation."""

    @staticmethod
    def validate_session_id(session_id: str) -> bool:
        """Validate session ID format."""
        return len(session_id) >= 8 and session_id.isalnum()

    @staticmethod
    def validate_prompt_length(prompt: str) -> bool:
        """Validate prompt length."""
        return 1 <= len(prompt) <= 10000


# Export all schemas
__all__ = [
    # Base
    "BaseRequest",

    # Analyzer
    "AnalyzePromptRequest",

    # Specification
    "SpecificationMode",
    "SpecificationRequest",

    # Refinement
    "UserDecisionAction",
    "RefinementStartRequest",
    "RefinementDecisionRequest",
    "RefinementModifyRequest",
    "RefinementFinalizeRequest",

    # Dispatch
    "ExecutionMode",
    "DispatchExecutionRequest",
    "DispatchCancelRequest",

    # WebSocket
    "WebSocketMessageType",
    "WebSocketMessage",
    "WebSocketSubscribeRequest",

    # File upload
    "FileUploadRequest",

    # Session management
    "SessionCreateRequest",
    "SessionUpdateRequest",

    # Utilities
    "RequestValidator",
]