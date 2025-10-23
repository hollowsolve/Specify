"""
Data models for the multi-agent orchestration system.

This module defines the core data structures used throughout the dispatcher
system for representing tasks, execution graphs, agent results, and system state.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union, Type
from datetime import datetime
import uuid


class TaskType(Enum):
    """Types of tasks that can be executed by agents."""
    CODE_WRITING = "code_writing"
    RESEARCH = "research"
    TESTING = "testing"
    REVIEW = "review"
    DOCUMENTATION = "documentation"
    DEBUGGING = "debugging"
    DEPLOYMENT = "deployment"
    ANALYSIS = "analysis"


class TaskStatus(Enum):
    """Status of a task in the execution pipeline."""
    PENDING = "pending"
    READY = "ready"           # Dependencies satisfied, ready to execute
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"       # Dependencies failed


class ExecutionStatus(Enum):
    """Overall execution status of the dispatcher."""
    INITIALIZING = "initializing"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DependencyType(Enum):
    """Types of dependencies between tasks."""
    DATA = "data"             # Output of one task is input to another
    LOGICAL = "logical"       # One task must complete before another can start
    RESOURCE = "resource"     # Tasks compete for the same resource


class AgentType(Enum):
    """Types of specialized agents."""
    CODE_WRITER = "code_writer"
    RESEARCHER = "researcher"
    TESTER = "tester"
    REVIEWER = "reviewer"
    DOCUMENTER = "documenter"
    DEBUGGER = "debugger"
    ANALYZER = "analyzer"


@dataclass
class TaskDependency:
    """Represents a dependency between two tasks."""
    source_task_id: str
    target_task_id: str
    dependency_type: DependencyType
    description: str
    required_artifacts: List[str] = field(default_factory=list)


@dataclass
class TaskArtifact:
    """Represents an artifact produced or consumed by a task."""
    name: str
    type: str  # file, data, report, etc.
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Task:
    """Represents an atomic unit of work in the execution graph."""
    task_id: str
    description: str
    task_type: TaskType
    required_agent_type: AgentType

    # Requirements and outputs
    input_requirements: List[str] = field(default_factory=list)
    output_artifacts: List[str] = field(default_factory=list)

    # Execution metadata
    estimated_complexity: float = 1.0  # 1.0 = simple, 5.0 = very complex
    priority: int = 0  # Higher number = higher priority
    max_retries: int = 3
    timeout_seconds: Optional[int] = None

    # Status tracking
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0

    # Context and configuration
    context: Dict[str, Any] = field(default_factory=dict)
    agent_config: Dict[str, Any] = field(default_factory=dict)

    # Dependencies
    dependencies: List[str] = field(default_factory=list)  # Task IDs this task depends on
    dependents: List[str] = field(default_factory=list)    # Task IDs that depend on this task

    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())

    def is_ready(self, completed_tasks: Set[str]) -> bool:
        """Check if this task is ready to execute (all dependencies completed)."""
        return all(dep_id in completed_tasks for dep_id in self.dependencies)

    def can_start(self) -> bool:
        """Check if this task can be started."""
        return self.status in [TaskStatus.PENDING, TaskStatus.READY]

    def start(self, agent_id: str):
        """Mark task as started."""
        self.status = TaskStatus.IN_PROGRESS
        self.assigned_agent_id = agent_id
        self.started_at = datetime.now()

    def complete(self):
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()

    def fail(self, reason: str = ""):
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        if 'failure_reason' not in self.context:
            self.context['failure_reason'] = reason


@dataclass
class AgentResult:
    """Result returned by an agent after executing a task."""
    task_id: str
    agent_id: str
    agent_type: AgentType
    success: bool

    # Outputs
    artifacts: List[TaskArtifact] = field(default_factory=list)
    output_data: Dict[str, Any] = field(default_factory=dict)

    # Execution details
    execution_time: float = 0.0  # seconds
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)

    # Follow-up recommendations
    suggested_next_tasks: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    completed_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionMetrics:
    """Metrics about the execution process."""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0

    total_execution_time: float = 0.0
    average_task_time: float = 0.0
    parallel_efficiency: float = 0.0  # Actual vs theoretical parallel time

    agent_utilization: Dict[AgentType, float] = field(default_factory=dict)
    critical_path_length: float = 0.0

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100.0


@dataclass
class ExecutionResult:
    """Complete result of executing a specification through the dispatcher."""
    execution_id: str
    specification_id: str
    status: ExecutionStatus

    # Results
    task_results: Dict[str, AgentResult] = field(default_factory=dict)
    final_artifacts: List[TaskArtifact] = field(default_factory=list)

    # Metrics and analysis
    metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)
    execution_graph_stats: Dict[str, Any] = field(default_factory=dict)

    # Logs and diagnostics
    execution_log: List[str] = field(default_factory=list)
    error_summary: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.execution_id:
            self.execution_id = str(uuid.uuid4())

    def add_task_result(self, result: AgentResult):
        """Add a task result to the execution."""
        self.task_results[result.task_id] = result
        if result.success:
            self.metrics.completed_tasks += 1
        else:
            self.metrics.failed_tasks += 1

        # Update final artifacts
        self.final_artifacts.extend(result.artifacts)

    def is_complete(self) -> bool:
        """Check if execution is complete."""
        return self.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]

    def success_rate(self) -> float:
        """Calculate success rate of completed tasks."""
        total_completed = self.metrics.completed_tasks + self.metrics.failed_tasks
        if total_completed == 0:
            return 0.0
        return (self.metrics.completed_tasks / total_completed) * 100.0


@dataclass
class AgentCapability:
    """Describes the capabilities of an agent."""
    agent_type: AgentType
    supported_task_types: List[TaskType]
    max_concurrent_tasks: int = 1
    average_task_time: Dict[TaskType, float] = field(default_factory=dict)
    complexity_limit: float = 5.0
    resource_requirements: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """A plan for executing tasks with scheduling and resource allocation."""
    plan_id: str
    tasks: List[Task]
    dependencies: List[TaskDependency]
    execution_phases: List[List[str]]  # Lists of task IDs that can run in parallel
    estimated_duration: float
    resource_requirements: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.plan_id:
            self.plan_id = str(uuid.uuid4())


class AgentMessage:
    """Base class for messages between agents."""

    def __init__(self, sender_id: str, message_type: str, data: Dict[str, Any]):
        self.message_id = str(uuid.uuid4())
        self.sender_id = sender_id
        self.message_type = message_type
        self.data = data
        self.timestamp = datetime.now()


@dataclass
class SystemState:
    """Current state of the execution system."""
    execution_id: str
    status: ExecutionStatus

    # Task tracking
    all_tasks: Dict[str, Task] = field(default_factory=dict)
    pending_tasks: Set[str] = field(default_factory=set)
    ready_tasks: Set[str] = field(default_factory=set)
    in_progress_tasks: Set[str] = field(default_factory=set)
    completed_tasks: Set[str] = field(default_factory=set)
    failed_tasks: Set[str] = field(default_factory=set)

    # Agent tracking
    active_agents: Dict[str, AgentType] = field(default_factory=dict)
    agent_task_assignments: Dict[str, str] = field(default_factory=dict)  # agent_id -> task_id

    # Artifacts
    artifacts: Dict[str, TaskArtifact] = field(default_factory=dict)

    # Checkpointing
    last_checkpoint: Optional[datetime] = None
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)

    def update_task_status(self, task_id: str, new_status: TaskStatus):
        """Update task status and maintain consistency."""
        if task_id not in self.all_tasks:
            return

        task = self.all_tasks[task_id]
        old_status = task.status

        # Remove from old status set
        if old_status == TaskStatus.PENDING:
            self.pending_tasks.discard(task_id)
        elif old_status == TaskStatus.READY:
            self.ready_tasks.discard(task_id)
        elif old_status == TaskStatus.IN_PROGRESS:
            self.in_progress_tasks.discard(task_id)
        elif old_status == TaskStatus.COMPLETED:
            self.completed_tasks.discard(task_id)
        elif old_status == TaskStatus.FAILED:
            self.failed_tasks.discard(task_id)

        # Update task status
        task.status = new_status

        # Add to new status set
        if new_status == TaskStatus.PENDING:
            self.pending_tasks.add(task_id)
        elif new_status == TaskStatus.READY:
            self.ready_tasks.add(task_id)
        elif new_status == TaskStatus.IN_PROGRESS:
            self.in_progress_tasks.add(task_id)
        elif new_status == TaskStatus.COMPLETED:
            self.completed_tasks.add(task_id)
        elif new_status == TaskStatus.FAILED:
            self.failed_tasks.add(task_id)

    def get_executable_tasks(self) -> List[str]:
        """Get tasks that are ready to be executed."""
        executable = []
        for task_id in self.ready_tasks:
            task = self.all_tasks[task_id]
            if task.is_ready(self.completed_tasks):
                executable.append(task_id)
        return executable

    def is_complete(self) -> bool:
        """Check if all tasks are completed or failed."""
        return len(self.pending_tasks) == 0 and len(self.ready_tasks) == 0 and len(self.in_progress_tasks) == 0