"""
Pydantic response schemas for the Specify API.

All response models that correspond to the existing Phase 1-4 data structures.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


# Base response schemas
class BaseResponse(BaseModel):
    """Base response model with common fields."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(None, description="Response message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    session_id: Optional[str] = Field(None, description="Session ID")


class ErrorResponse(BaseResponse):
    """Error response model."""
    success: bool = Field(False, description="Always false for errors")
    error_type: str = Field(..., description="Type of error")
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


# Analyzer response schemas (Phase 1)
class AnalysisResult(BaseModel):
    """Analysis result from Phase 1."""
    id: str = Field(..., description="Unique analysis ID")
    intent: str = Field(..., description="Analyzed intent")
    requirements: List[str] = Field(..., description="Extracted requirements")
    assumptions: List[str] = Field(..., description="Identified assumptions")
    ambiguities: List[str] = Field(..., description="Found ambiguities")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Analysis metadata")
    processing_time: float = Field(..., description="Analysis processing time in seconds")


class AnalyzeResponse(BaseResponse):
    """Response for prompt analysis."""
    analysis_id: str = Field(..., description="Analysis ID for retrieval")
    result: Optional[AnalysisResult] = Field(None, description="Analysis result if completed")
    status: str = Field(..., description="Analysis status")


# Specification response schemas (Phase 2)
class EdgeCase(BaseModel):
    """Edge case detected by specification engine."""
    id: str = Field(..., description="Edge case ID")
    category: str = Field(..., description="Edge case category")
    description: str = Field(..., description="Edge case description")
    severity: str = Field(..., description="Severity level")
    suggested_handling: Optional[str] = Field(None, description="Suggested handling approach")


class Contradiction(BaseModel):
    """Contradiction detected in requirements."""
    id: str = Field(..., description="Contradiction ID")
    conflicting_requirements: List[str] = Field(..., description="Conflicting requirements")
    description: str = Field(..., description="Contradiction description")
    severity: str = Field(..., description="Severity level")
    resolution_suggestions: List[str] = Field(default_factory=list, description="Resolution suggestions")


class CompressedRequirement(BaseModel):
    """Compressed requirement from specification engine."""
    id: str = Field(..., description="Requirement ID")
    original_requirements: List[str] = Field(..., description="Original requirements")
    compressed_text: str = Field(..., description="Compressed requirement text")
    priority: str = Field(..., description="Requirement priority")


class RefinedSpecification(BaseModel):
    """Refined specification from Phase 2."""
    id: str = Field(..., description="Specification ID")
    original_analysis_id: str = Field(..., description="Original analysis ID")
    compressed_requirements: List[CompressedRequirement] = Field(..., description="Compressed requirements")
    edge_cases: List[EdgeCase] = Field(..., description="Detected edge cases")
    contradictions: List[Contradiction] = Field(..., description="Found contradictions")
    completeness_score: float = Field(..., ge=0.0, le=1.0, description="Completeness score")
    processing_metrics: Dict[str, Any] = Field(default_factory=dict, description="Processing metrics")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")


class SpecificationResponse(BaseResponse):
    """Response for specification refinement."""
    specification_id: str = Field(..., description="Specification ID")
    result: Optional[RefinedSpecification] = Field(None, description="Refined specification")
    status: str = Field(..., description="Processing status")


# Refinement response schemas (Phase 3)
class RefinementSuggestion(BaseModel):
    """Refinement suggestion from Phase 3."""
    id: str = Field(..., description="Suggestion ID")
    type: str = Field(..., description="Suggestion type")
    title: str = Field(..., description="Suggestion title")
    description: str = Field(..., description="Detailed description")
    impact: str = Field(..., description="Impact level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    suggested_changes: List[str] = Field(..., description="Suggested changes")
    reasoning: str = Field(..., description="Reasoning for suggestion")


class UserDecision(BaseModel):
    """User decision on a refinement suggestion."""
    suggestion_id: str = Field(..., description="Suggestion ID")
    action: str = Field(..., description="User action taken")
    feedback: Optional[str] = Field(None, description="User feedback")
    timestamp: datetime = Field(default_factory=datetime.now, description="Decision timestamp")


class RefinementIteration(BaseModel):
    """Single iteration in refinement process."""
    iteration_number: int = Field(..., description="Iteration number")
    suggestions: List[RefinementSuggestion] = Field(..., description="Suggestions presented")
    user_decisions: List[UserDecision] = Field(default_factory=list, description="User decisions")
    completed_at: Optional[datetime] = Field(None, description="Iteration completion time")


class RefinementSession(BaseModel):
    """Complete refinement session from Phase 3."""
    id: str = Field(..., description="Session ID")
    specification_id: str = Field(..., description="Source specification ID")
    iterations: List[RefinementIteration] = Field(..., description="Refinement iterations")
    current_iteration: int = Field(..., description="Current iteration number")
    status: str = Field(..., description="Session status")
    finalized_specification: Optional[Dict[str, Any]] = Field(None, description="Finalized specification")
    started_at: datetime = Field(default_factory=datetime.now, description="Session start time")
    completed_at: Optional[datetime] = Field(None, description="Session completion time")


class RefinementResponse(BaseResponse):
    """Response for refinement operations."""
    session_id: str = Field(..., description="Refinement session ID")
    current_suggestions: List[RefinementSuggestion] = Field(default_factory=list, description="Current suggestions")
    session_status: str = Field(..., description="Session status")
    next_action: Optional[str] = Field(None, description="Next recommended action")


# Dispatch response schemas (Phase 4)
class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionStatus(str, Enum):
    """Overall execution status."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    """Individual task in execution."""
    id: str = Field(..., description="Task ID")
    type: str = Field(..., description="Task type")
    description: str = Field(..., description="Task description")
    status: TaskStatus = Field(..., description="Task status")
    agent_type: Optional[str] = Field(None, description="Assigned agent type")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")
    started_at: Optional[datetime] = Field(None, description="Task start time")
    completed_at: Optional[datetime] = Field(None, description="Task completion time")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result")
    error: Optional[str] = Field(None, description="Error message if failed")


class AgentResult(BaseModel):
    """Result from an individual agent."""
    agent_id: str = Field(..., description="Agent ID")
    agent_type: str = Field(..., description="Agent type")
    tasks_completed: List[str] = Field(..., description="Completed task IDs")
    outputs: Dict[str, Any] = Field(..., description="Agent outputs")
    execution_time: float = Field(..., description="Agent execution time")
    success: bool = Field(..., description="Whether agent succeeded")
    error: Optional[str] = Field(None, description="Error message if failed")


class ExecutionGraph(BaseModel):
    """Execution DAG representation."""
    nodes: List[Task] = Field(..., description="Task nodes")
    edges: List[Dict[str, str]] = Field(..., description="Dependency edges")
    critical_path: List[str] = Field(..., description="Critical path task IDs")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")


class ExecutionResult(BaseModel):
    """Complete execution result from Phase 4."""
    id: str = Field(..., description="Execution ID")
    specification_id: str = Field(..., description="Source specification ID")
    status: ExecutionStatus = Field(..., description="Execution status")
    tasks: List[Task] = Field(..., description="All tasks")
    agent_results: List[AgentResult] = Field(default_factory=list, description="Agent results")
    execution_graph: Optional[ExecutionGraph] = Field(None, description="Execution DAG")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Final outputs")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Execution metrics")
    started_at: datetime = Field(default_factory=datetime.now, description="Execution start time")
    completed_at: Optional[datetime] = Field(None, description="Execution completion time")
    error: Optional[str] = Field(None, description="Error message if failed")


class DispatchResponse(BaseResponse):
    """Response for dispatch operations."""
    execution_id: str = Field(..., description="Execution ID")
    status: ExecutionStatus = Field(..., description="Execution status")
    current_tasks: List[Task] = Field(default_factory=list, description="Currently running tasks")
    progress_percentage: float = Field(..., ge=0.0, le=100.0, description="Progress percentage")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")


# WebSocket event schemas
class WebSocketEvent(BaseModel):
    """WebSocket event structure."""
    type: str = Field(..., description="Event type")
    session_id: str = Field(..., description="Session ID")
    data: Dict[str, Any] = Field(..., description="Event data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")


# Session management schemas
class SessionInfo(BaseModel):
    """Session information."""
    id: str = Field(..., description="Session ID")
    user_id: Optional[str] = Field(None, description="User ID")
    created_at: datetime = Field(..., description="Session creation time")
    last_activity: datetime = Field(..., description="Last activity time")
    expires_at: datetime = Field(..., description="Session expiration time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")
    active_operations: List[str] = Field(default_factory=list, description="Active operations")


class SessionResponse(BaseResponse):
    """Response for session operations."""
    session: Optional[SessionInfo] = Field(None, description="Session information")


# Health and status schemas
class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.now, description="Check timestamp")
    components: Optional[Dict[str, str]] = Field(None, description="Component health")


class VersionResponse(BaseModel):
    """Version information response."""
    api_version: str = Field(..., description="API version")
    components: Dict[str, str] = Field(..., description="Component versions")
    description: str = Field(..., description="Service description")


# Export all schemas
__all__ = [
    # Base
    "BaseResponse",
    "ErrorResponse",

    # Analyzer
    "AnalysisResult",
    "AnalyzeResponse",

    # Specification
    "EdgeCase",
    "Contradiction",
    "CompressedRequirement",
    "RefinedSpecification",
    "SpecificationResponse",

    # Refinement
    "RefinementSuggestion",
    "UserDecision",
    "RefinementIteration",
    "RefinementSession",
    "RefinementResponse",

    # Dispatch
    "TaskStatus",
    "ExecutionStatus",
    "Task",
    "AgentResult",
    "ExecutionGraph",
    "ExecutionResult",
    "DispatchResponse",

    # WebSocket
    "WebSocketEvent",

    # Session
    "SessionInfo",
    "SessionResponse",

    # Health
    "HealthResponse",
    "VersionResponse",
]