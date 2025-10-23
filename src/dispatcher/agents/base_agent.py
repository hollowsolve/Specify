"""
Base Agent - Abstract base class for all specialized agents.

This module defines the common interface and shared functionality
for all agents in the multi-agent system.
"""

import time
import uuid
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum

from ..models import (
    Task, AgentResult, TaskArtifact, AgentType, TaskType, TaskStatus
)


class AgentState(Enum):
    """States an agent can be in."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class ExecutionMode(Enum):
    """Execution modes for agents."""
    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.

    Provides common functionality for:
    - Task execution lifecycle
    - Error handling and retry logic
    - Progress reporting
    - Resource management
    - Logging and telemetry
    """

    def __init__(self, agent_id: str = None, config: Dict[str, Any] = None):
        self.agent_id = agent_id or f"{self.__class__.__name__}_{uuid.uuid4().hex[:8]}"
        self.config = config or {}
        self.state = AgentState.IDLE
        self.current_task: Optional[Task] = None
        self.execution_history: List[AgentResult] = []

        # Performance tracking
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.total_execution_time = 0.0
        self.average_task_time = 0.0

        # Configuration
        self.max_retries = self.config.get('max_retries', 3)
        self.timeout_seconds = self.config.get('timeout_seconds', 300)  # 5 minutes default
        self.retry_delay = self.config.get('retry_delay', 1.0)  # seconds

        # Setup logging
        self.logger = self._setup_logger()

        # Event callbacks
        self.on_task_start: Optional[Callable[[str, Task], None]] = None
        self.on_task_complete: Optional[Callable[[str, AgentResult], None]] = None
        self.on_task_failed: Optional[Callable[[str, Task, str], None]] = None
        self.on_progress: Optional[Callable[[str, float, str], None]] = None

    @abstractmethod
    def get_agent_type(self) -> AgentType:
        """Return the type of this agent."""
        pass

    @abstractmethod
    def get_supported_task_types(self) -> List[TaskType]:
        """Return list of task types this agent can handle."""
        pass

    @abstractmethod
    def _execute_task_impl(self, task: Task) -> AgentResult:
        """
        Core task execution implementation.

        Subclasses must implement this method to define their specific
        task execution logic.

        Args:
            task: Task to execute

        Returns:
            AgentResult with execution results
        """
        pass

    def can_handle(self, task: Task) -> bool:
        """
        Check if this agent can handle the given task.

        Args:
            task: Task to check

        Returns:
            True if agent can handle the task
        """
        return (task.task_type in self.get_supported_task_types() and
                task.required_agent_type == self.get_agent_type())

    def estimate_effort(self, task: Task) -> float:
        """
        Estimate effort required for a task in relative units.

        Args:
            task: Task to estimate

        Returns:
            Effort estimate (higher = more effort)
        """
        # Base estimation using task complexity
        base_effort = task.estimated_complexity

        # Adjust based on agent's historical performance
        if self.average_task_time > 0:
            # Consider agent's efficiency
            efficiency_factor = min(2.0, max(0.5, self.average_task_time / 60.0))  # Normalize around 1 minute
            base_effort *= efficiency_factor

        # Adjust based on task context
        context_complexity = self._analyze_context_complexity(task)
        base_effort *= (1.0 + context_complexity * 0.2)

        return base_effort

    def execute(self, task: Task) -> AgentResult:
        """
        Execute a task with full lifecycle management.

        Args:
            task: Task to execute

        Returns:
            AgentResult with execution outcome
        """
        if not self.can_handle(task):
            return self._create_error_result(
                task,
                f"Agent {self.agent_id} cannot handle task type {task.task_type}"
            )

        if self.state != AgentState.IDLE:
            return self._create_error_result(
                task,
                f"Agent {self.agent_id} is not available (state: {self.state})"
            )

        # Start task execution
        self.state = AgentState.BUSY
        self.current_task = task
        start_time = time.time()

        try:
            # Notify start
            if self.on_task_start:
                self.on_task_start(self.agent_id, task)

            self.logger.info(f"Starting task {task.task_id}: {task.description}")

            # Execute with retry logic
            result = self._execute_with_retries(task)

            # Calculate execution time
            execution_time = time.time() - start_time
            result.execution_time = execution_time

            # Update statistics
            self._update_statistics(result, execution_time)

            # Log result
            if result.success:
                self.logger.info(f"Task {task.task_id} completed successfully in {execution_time:.2f}s")
                if self.on_task_complete:
                    self.on_task_complete(self.agent_id, result)
            else:
                self.logger.error(f"Task {task.task_id} failed: {result.error_message}")
                if self.on_task_failed:
                    self.on_task_failed(self.agent_id, task, result.error_message or "Unknown error")

            # Add to history
            self.execution_history.append(result)

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Unexpected error executing task {task.task_id}: {str(e)}"
            self.logger.exception(error_msg)

            result = self._create_error_result(task, error_msg)
            result.execution_time = execution_time
            self._update_statistics(result, execution_time)

            if self.on_task_failed:
                self.on_task_failed(self.agent_id, task, error_msg)

            return result

        finally:
            self.state = AgentState.IDLE
            self.current_task = None

    def _execute_with_retries(self, task: Task) -> AgentResult:
        """Execute task with retry logic."""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.info(f"Retrying task {task.task_id} (attempt {attempt + 1}/{self.max_retries + 1})")
                    time.sleep(self.retry_delay * attempt)  # Exponential backoff

                # Set timeout if specified
                if self.timeout_seconds:
                    result = self._execute_with_timeout(task, self.timeout_seconds)
                else:
                    result = self._execute_task_impl(task)

                if result.success:
                    return result
                else:
                    last_error = result.error_message
                    if not self._should_retry(result):
                        return result

            except TimeoutError as e:
                last_error = f"Task timed out after {self.timeout_seconds} seconds"
                self.logger.warning(f"Task {task.task_id} timed out on attempt {attempt + 1}")

            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"Task {task.task_id} failed on attempt {attempt + 1}: {e}")

        # All retries exhausted
        return self._create_error_result(
            task,
            f"Task failed after {self.max_retries + 1} attempts. Last error: {last_error}"
        )

    def _execute_with_timeout(self, task: Task, timeout: float) -> AgentResult:
        """Execute task with timeout."""
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError(f"Task execution timed out after {timeout} seconds")

        # Set up timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))

        try:
            result = self._execute_task_impl(task)
            signal.alarm(0)  # Cancel timeout
            return result
        except TimeoutError:
            signal.alarm(0)  # Cancel timeout
            raise
        except Exception:
            signal.alarm(0)  # Cancel timeout
            raise

    def _should_retry(self, result: AgentResult) -> bool:
        """Determine if a failed task should be retried."""
        # Don't retry if it's a configuration or validation error
        if result.error_message:
            non_retryable_errors = [
                "invalid configuration",
                "validation failed",
                "unsupported task type",
                "permission denied"
            ]

            error_lower = result.error_message.lower()
            if any(error in error_lower for error in non_retryable_errors):
                return False

        return True

    def _update_statistics(self, result: AgentResult, execution_time: float):
        """Update agent performance statistics."""
        if result.success:
            self.tasks_completed += 1
        else:
            self.tasks_failed += 1

        self.total_execution_time += execution_time
        total_tasks = self.tasks_completed + self.tasks_failed
        if total_tasks > 0:
            self.average_task_time = self.total_execution_time / total_tasks

    def _analyze_context_complexity(self, task: Task) -> float:
        """Analyze task context to estimate additional complexity."""
        complexity_factors = 0.0

        # Check input requirements
        if len(task.input_requirements) > 3:
            complexity_factors += 0.1

        # Check output artifacts
        if len(task.output_artifacts) > 3:
            complexity_factors += 0.1

        # Check context size
        context_size = sum(len(str(v)) for v in task.context.values())
        if context_size > 1000:
            complexity_factors += 0.2

        return min(complexity_factors, 0.5)  # Cap at 50% increase

    def _create_error_result(self, task: Task, error_message: str) -> AgentResult:
        """Create an error result for a failed task."""
        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            agent_type=self.get_agent_type(),
            success=False,
            error_message=error_message,
            completed_at=datetime.now()
        )

    def _setup_logger(self) -> logging.Logger:
        """Set up logging for the agent."""
        logger = logging.getLogger(f"agent.{self.agent_id}")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics."""
        total_tasks = self.tasks_completed + self.tasks_failed
        success_rate = (self.tasks_completed / total_tasks * 100) if total_tasks > 0 else 0

        return {
            'agent_id': self.agent_id,
            'agent_type': self.get_agent_type().value,
            'state': self.state.value,
            'tasks_completed': self.tasks_completed,
            'tasks_failed': self.tasks_failed,
            'total_tasks': total_tasks,
            'success_rate': success_rate,
            'average_task_time': self.average_task_time,
            'total_execution_time': self.total_execution_time,
            'current_task': self.current_task.task_id if self.current_task else None,
            'supported_task_types': [t.value for t in self.get_supported_task_types()]
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            'agent_id': self.agent_id,
            'agent_type': self.get_agent_type().value,
            'state': self.state.value,
            'current_task': self.current_task.task_id if self.current_task else None,
            'last_activity': datetime.now().isoformat(),
            'configuration': self.config
        }

    def shutdown(self):
        """Gracefully shutdown the agent."""
        self.logger.info(f"Shutting down agent {self.agent_id}")
        self.state = AgentState.SHUTDOWN

        # Cancel current task if any
        if self.current_task:
            self.logger.warning(f"Cancelling current task {self.current_task.task_id}")
            self.current_task = None

    def reset(self):
        """Reset agent to initial state."""
        if self.state == AgentState.BUSY:
            self.logger.warning("Cannot reset agent while busy")
            return False

        self.state = AgentState.IDLE
        self.current_task = None
        # Optionally clear history and statistics

        return True

    def update_config(self, new_config: Dict[str, Any]):
        """Update agent configuration."""
        self.config.update(new_config)

        # Update derived settings
        self.max_retries = self.config.get('max_retries', self.max_retries)
        self.timeout_seconds = self.config.get('timeout_seconds', self.timeout_seconds)
        self.retry_delay = self.config.get('retry_delay', self.retry_delay)

        self.logger.info(f"Agent {self.agent_id} configuration updated")

    def validate_task(self, task: Task) -> Tuple[bool, Optional[str]]:
        """
        Validate if a task can be executed by this agent.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.can_handle(task):
            return False, f"Agent cannot handle task type {task.task_type}"

        # Check required inputs
        for requirement in task.input_requirements:
            if not self._validate_input_requirement(requirement, task):
                return False, f"Missing or invalid input requirement: {requirement}"

        # Check agent-specific validations
        return self._validate_task_specific(task)

    def _validate_input_requirement(self, requirement: str, task: Task) -> bool:
        """Validate a specific input requirement."""
        # Default implementation - can be overridden by subclasses
        return True

    def _validate_task_specific(self, task: Task) -> Tuple[bool, Optional[str]]:
        """Agent-specific task validation."""
        # Default implementation - can be overridden by subclasses
        return True, None

    def report_progress(self, progress: float, message: str):
        """Report task progress."""
        if self.on_progress:
            self.on_progress(self.agent_id, progress, message)

        self.logger.debug(f"Progress: {progress:.1%} - {message}")

    def create_artifact(self, name: str, artifact_type: str, content: Any,
                       metadata: Dict[str, Any] = None) -> TaskArtifact:
        """Helper to create task artifacts."""
        return TaskArtifact(
            name=name,
            type=artifact_type,
            content=content,
            metadata=metadata or {},
            created_at=datetime.now()
        )