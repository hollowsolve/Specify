"""
Agent Dispatcher - Main orchestrator for the multi-agent execution system.

This is the primary entry point that coordinates the entire execution pipeline:
decomposition → dependency resolution → graph building → agent coordination → execution → reporting.
"""

import uuid
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import asdict

from .models import (
    ExecutionResult, ExecutionStatus, ExecutionMetrics, Task, AgentResult,
    TaskStatus, ExecutionPlan
)
from .graph.execution_graph import ExecutionGraph
from .graph.task_decomposer import TaskDecomposer
from .graph.dependency_resolver import DependencyResolver
from .agents.agent_factory import AgentFactory
from .coordination.coordinator import Coordinator
from .coordination.message_bus import MessageBus, MessagePriority
from .coordination.state_manager import StateManager


class AgentDispatcher:
    """
    Main orchestrator for the multi-agent execution system.

    Features:
    - Specification decomposition into atomic tasks
    - Dependency resolution and execution graph building
    - Agent factory management and coordination
    - Real-time execution monitoring and progress tracking
    - Comprehensive result reporting and analytics
    - Failure handling and recovery
    - Resource optimization and scaling
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # Core components
        self.task_decomposer = TaskDecomposer(
            llm_client=self.config.get('llm_client')
        )
        self.dependency_resolver = DependencyResolver(
            llm_client=self.config.get('llm_client')
        )
        self.message_bus = MessageBus(
            config=self.config.get('message_bus', {})
        )
        self.state_manager = StateManager(
            config=self.config.get('state_manager', {})
        )
        self.agent_factory = AgentFactory(
            config=self.config.get('agent_factory', {})
        )
        self.coordinator = Coordinator(
            agent_factory=self.agent_factory,
            state_manager=self.state_manager,
            message_bus=self.message_bus,
            config=self.config.get('coordinator', {})
        )

        # Execution tracking
        self.current_execution: Optional[ExecutionResult] = None
        self.execution_history: List[ExecutionResult] = []

        # Event callbacks
        self.progress_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.completion_callbacks: List[Callable[[ExecutionResult], None]] = []
        self.error_callbacks: List[Callable[[str, Exception], None]] = []

        # Configuration
        self.enable_parallel_execution = self.config.get('enable_parallel_execution', True)
        self.max_execution_time = self.config.get('max_execution_time', 3600)  # 1 hour
        self.checkpoint_interval = self.config.get('checkpoint_interval', 300)  # 5 minutes

        # Setup
        self._setup_components()

    def dispatch(self, specification) -> ExecutionResult:
        """
        Main dispatch method - orchestrates the complete execution pipeline.

        Args:
            specification: FinalizedSpecification to execute

        Returns:
            ExecutionResult with complete execution details
        """
        execution_id = str(uuid.uuid4())

        try:
            # Initialize execution tracking
            execution_result = self._initialize_execution(execution_id, specification)
            self.current_execution = execution_result

            # Phase 1: Decompose specification into tasks
            self._update_execution_status(ExecutionStatus.PLANNING, "Decomposing specification")
            tasks = self._decompose_specification(specification)

            if not tasks:
                raise ValueError("No tasks generated from specification")

            # Phase 2: Resolve dependencies between tasks
            self._update_execution_status(ExecutionStatus.PLANNING, "Resolving task dependencies")
            dependencies = self._resolve_dependencies(tasks)

            # Phase 3: Build execution graph
            self._update_execution_status(ExecutionStatus.PLANNING, "Building execution graph")
            execution_graph = self._build_execution_graph(tasks, dependencies)

            # Phase 4: Create execution plan
            execution_plan = self._create_execution_plan(execution_graph)

            # Phase 5: Validate resources and capabilities
            self._validate_execution_plan(execution_plan)

            # Phase 6: Execute the plan
            self._update_execution_status(ExecutionStatus.EXECUTING, "Starting task execution")
            self._execute_plan(execution_plan, execution_graph)

            # Phase 7: Finalize and report
            self._finalize_execution()

            return self.current_execution

        except Exception as e:
            self._handle_execution_error(e)
            return self.current_execution

        finally:
            self._cleanup_execution()

    def get_execution_status(self) -> Dict[str, Any]:
        """Get current execution status and progress."""
        if not self.current_execution:
            return {'status': 'idle', 'no_active_execution': True}

        progress = self.state_manager.get_execution_progress()
        coordinator_status = self.coordinator.get_status()

        return {
            'execution_id': self.current_execution.execution_id,
            'status': self.current_execution.status.value,
            'progress': progress,
            'coordinator': coordinator_status,
            'metrics': asdict(self.current_execution.metrics),
            'started_at': self.current_execution.started_at.isoformat(),
            'elapsed_time': (datetime.now() - self.current_execution.started_at).total_seconds()
        }

    def cancel_execution(self, reason: str = "User cancelled") -> bool:
        """Cancel the current execution."""
        if not self.current_execution or self.current_execution.is_complete():
            return False

        try:
            # Stop coordinator
            self.coordinator.stop()

            # Update execution status
            self.current_execution.status = ExecutionStatus.CANCELLED
            self.current_execution.completed_at = datetime.now()
            self.current_execution.error_summary.append(f"Execution cancelled: {reason}")

            # Publish cancellation event
            self.message_bus.publish(
                "dispatcher.execution.cancelled",
                "execution_cancelled",
                {
                    "execution_id": self.current_execution.execution_id,
                    "reason": reason
                },
                priority=MessagePriority.HIGH
            )

            return True

        except Exception as e:
            self._handle_execution_error(e)
            return False

    def pause_execution(self) -> bool:
        """Pause the current execution."""
        if not self.current_execution or self.current_execution.is_complete():
            return False

        try:
            self.coordinator.pause()
            return True
        except Exception as e:
            self._handle_execution_error(e)
            return False

    def resume_execution(self) -> bool:
        """Resume a paused execution."""
        if not self.current_execution or self.current_execution.is_complete():
            return False

        try:
            self.coordinator.resume()
            return True
        except Exception as e:
            self._handle_execution_error(e)
            return False

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get history of all executions."""
        return [
            {
                'execution_id': execution.execution_id,
                'specification_id': execution.specification_id,
                'status': execution.status.value,
                'started_at': execution.started_at.isoformat(),
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                'task_count': len(execution.task_results),
                'success_rate': execution.success_rate(),
                'duration': (execution.completed_at - execution.started_at).total_seconds() if execution.completed_at else None
            }
            for execution in self.execution_history
        ]

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics."""
        return {
            'dispatcher': {
                'total_executions': len(self.execution_history),
                'current_execution': self.current_execution.execution_id if self.current_execution else None,
                'system_uptime': time.time()  # Would track actual uptime
            },
            'agent_factory': self.agent_factory.get_factory_stats(),
            'coordinator': self.coordinator.get_detailed_metrics() if hasattr(self.coordinator, 'get_detailed_metrics') else {},
            'message_bus': self.message_bus.get_stats(),
            'state_manager': {
                'checkpoints': len(self.state_manager.get_checkpoints()),
                'current_state': self.state_manager.get_execution_progress() if self.current_execution else {}
            }
        }

    def _initialize_execution(self, execution_id: str, specification) -> ExecutionResult:
        """Initialize execution tracking."""
        execution_result = ExecutionResult(
            execution_id=execution_id,
            specification_id=getattr(specification, 'spec_id', 'unknown'),
            status=ExecutionStatus.INITIALIZING,
            started_at=datetime.now()
        )

        # Initialize metrics
        execution_result.metrics.started_at = datetime.now()

        # Publish initialization event
        self.message_bus.publish(
            "dispatcher.execution.initialized",
            "execution_initialized",
            {
                "execution_id": execution_id,
                "specification_id": execution_result.specification_id
            },
            priority=MessagePriority.HIGH
        )

        return execution_result

    def _decompose_specification(self, specification) -> List[Task]:
        """Decompose specification into atomic tasks."""
        self._log_execution_step("Starting task decomposition")

        try:
            tasks = self.task_decomposer.decompose_specification(specification)

            # Update metrics
            self.current_execution.metrics.total_tasks = len(tasks)

            # Log task summary
            task_types = {}
            for task in tasks:
                task_type = task.task_type.value
                task_types[task_type] = task_types.get(task_type, 0) + 1

            self._log_execution_step(f"Decomposed into {len(tasks)} tasks: {task_types}")

            # Publish decomposition event
            self.message_bus.publish(
                "dispatcher.decomposition.completed",
                "decomposition_completed",
                {
                    "execution_id": self.current_execution.execution_id,
                    "task_count": len(tasks),
                    "task_types": task_types
                }
            )

            return tasks

        except Exception as e:
            raise RuntimeError(f"Task decomposition failed: {e}")

    def _resolve_dependencies(self, tasks: List[Task]) -> List:
        """Resolve dependencies between tasks."""
        self._log_execution_step("Resolving task dependencies")

        try:
            dependencies = self.dependency_resolver.resolve_dependencies(tasks)

            self._log_execution_step(f"Resolved {len(dependencies)} dependencies")

            # Publish dependency resolution event
            self.message_bus.publish(
                "dispatcher.dependencies.resolved",
                "dependencies_resolved",
                {
                    "execution_id": self.current_execution.execution_id,
                    "dependency_count": len(dependencies),
                    "dependency_types": [dep.dependency_type.value for dep in dependencies]
                }
            )

            return dependencies

        except Exception as e:
            raise RuntimeError(f"Dependency resolution failed: {e}")

    def _build_execution_graph(self, tasks: List[Task], dependencies: List) -> ExecutionGraph:
        """Build execution graph from tasks and dependencies."""
        self._log_execution_step("Building execution graph")

        try:
            execution_graph = ExecutionGraph()

            # Add all tasks
            for task in tasks:
                execution_graph.add_task(task)

            # Add all dependencies
            for dependency in dependencies:
                success = execution_graph.add_dependency(dependency)
                if not success:
                    self.current_execution.warnings.append(
                        f"Failed to add dependency: {dependency.source_task_id} -> {dependency.target_task_id}"
                    )

            # Validate graph
            is_valid, issues = execution_graph.validate_graph()
            if not is_valid:
                self.current_execution.warnings.extend(issues)

            # Get execution statistics
            stats = execution_graph.get_parallel_execution_stats()
            self.current_execution.execution_graph_stats = stats

            self._log_execution_step(f"Built execution graph with {stats['execution_phases']} phases")

            # Publish graph building event
            self.message_bus.publish(
                "dispatcher.graph.built",
                "graph_built",
                {
                    "execution_id": self.current_execution.execution_id,
                    "graph_stats": stats,
                    "validation_issues": issues
                }
            )

            return execution_graph

        except Exception as e:
            raise RuntimeError(f"Execution graph building failed: {e}")

    def _create_execution_plan(self, execution_graph: ExecutionGraph) -> ExecutionPlan:
        """Create execution plan from the graph."""
        self._log_execution_step("Creating execution plan")

        try:
            # Get execution phases
            phases = execution_graph.get_execution_phases()

            # Estimate duration
            estimated_duration = execution_graph.estimate_execution_time(
                max_parallel_agents=self.config.get('max_parallel_agents', 4)
            )

            # Get resource requirements
            resource_requirements = execution_graph.get_resource_requirements()

            execution_plan = ExecutionPlan(
                plan_id=f"plan_{self.current_execution.execution_id}",
                tasks=list(execution_graph.tasks.values()),
                dependencies=list(execution_graph.dependencies.values()),
                execution_phases=phases,
                estimated_duration=estimated_duration,
                resource_requirements=resource_requirements
            )

            self._log_execution_step(
                f"Created execution plan: {len(phases)} phases, "
                f"{estimated_duration:.1f}s estimated duration"
            )

            return execution_plan

        except Exception as e:
            raise RuntimeError(f"Execution plan creation failed: {e}")

    def _validate_execution_plan(self, execution_plan: ExecutionPlan):
        """Validate that the execution plan can be executed."""
        self._log_execution_step("Validating execution plan")

        # Check agent factory capabilities
        if not self.agent_factory.can_handle_workload(execution_plan.tasks):
            raise RuntimeError("Agent factory cannot handle the required workload")

        # Check resource requirements
        resource_requirements = execution_plan.resource_requirements
        available_resources = self.agent_factory.get_factory_stats()

        for agent_type, required_count in resource_requirements.items():
            if required_count > available_resources.get('max_total_agents', 0):
                self.current_execution.warnings.append(
                    f"High resource requirement for {agent_type.value}: {required_count} agents"
                )

        # Check execution time constraints
        if execution_plan.estimated_duration > self.max_execution_time:
            self.current_execution.warnings.append(
                f"Estimated execution time ({execution_plan.estimated_duration:.1f}s) "
                f"exceeds maximum ({self.max_execution_time}s)"
            )

        self._log_execution_step("Execution plan validation completed")

    def _execute_plan(self, execution_plan: ExecutionPlan, execution_graph: ExecutionGraph):
        """Execute the execution plan."""
        self._log_execution_step("Starting plan execution")

        try:
            # Start coordinator with the plan
            self.coordinator.start(self.current_execution.execution_id, execution_plan.tasks)

            # Monitor execution progress
            self._monitor_execution_progress()

            self._log_execution_step("Plan execution completed")

        except Exception as e:
            raise RuntimeError(f"Plan execution failed: {e}")

    def _monitor_execution_progress(self):
        """Monitor execution progress until completion."""
        start_time = datetime.now()

        while True:
            try:
                # Check if execution is complete
                coordinator_status = self.coordinator.get_status()

                if coordinator_status['state'] in ['stopped', 'error']:
                    break

                # Check for timeout
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > self.max_execution_time:
                    self._log_execution_step("Execution timeout reached")
                    self.coordinator.stop(timeout=30.0)
                    break

                # Update progress
                self._update_progress()

                # Sleep before next check
                time.sleep(5.0)

            except Exception as e:
                self._log_execution_step(f"Error during progress monitoring: {e}")
                break

    def _update_progress(self):
        """Update execution progress and notify callbacks."""
        progress_data = self.state_manager.get_execution_progress()

        # Update metrics
        self.current_execution.metrics.completed_tasks = progress_data.get('completed_tasks', 0)
        self.current_execution.metrics.failed_tasks = progress_data.get('failed_tasks', 0)

        # Notify progress callbacks
        for callback in self.progress_callbacks:
            try:
                callback(progress_data)
            except Exception as e:
                self._log_execution_step(f"Error in progress callback: {e}")

    def _finalize_execution(self):
        """Finalize execution and generate results."""
        self._log_execution_step("Finalizing execution")

        # Get final results from coordinator
        coordinator_status = self.coordinator.get_status()

        # Update execution status
        if coordinator_status['tasks_failed'] > 0:
            self.current_execution.status = ExecutionStatus.FAILED
        else:
            self.current_execution.status = ExecutionStatus.COMPLETED

        self.current_execution.completed_at = datetime.now()

        # Update final metrics
        self.current_execution.metrics.completed_at = datetime.now()
        self.current_execution.metrics.total_execution_time = (
            self.current_execution.completed_at - self.current_execution.started_at
        ).total_seconds()

        # Collect task results
        # This would normally collect results from the state manager
        # For now, we'll use placeholder data
        self.current_execution.task_results = {}

        # Generate final checkpoint
        if hasattr(self.state_manager, 'create_checkpoint'):
            self.state_manager.create_checkpoint("final_execution_checkpoint")

        # Add to execution history
        self.execution_history.append(self.current_execution)

        # Notify completion callbacks
        for callback in self.completion_callbacks:
            try:
                callback(self.current_execution)
            except Exception as e:
                self._log_execution_step(f"Error in completion callback: {e}")

        # Publish completion event
        self.message_bus.publish(
            "dispatcher.execution.completed",
            "execution_completed",
            {
                "execution_id": self.current_execution.execution_id,
                "status": self.current_execution.status.value,
                "duration": self.current_execution.metrics.total_execution_time,
                "success_rate": self.current_execution.success_rate()
            },
            priority=MessagePriority.HIGH
        )

        self._log_execution_step(
            f"Execution completed with status: {self.current_execution.status.value}"
        )

    def _handle_execution_error(self, error: Exception):
        """Handle execution errors."""
        error_message = f"Execution error: {str(error)}"
        self._log_execution_step(error_message)

        if self.current_execution:
            self.current_execution.status = ExecutionStatus.FAILED
            self.current_execution.completed_at = datetime.now()
            self.current_execution.error_summary.append(error_message)

            # Stop coordinator if running
            try:
                self.coordinator.stop(timeout=10.0)
            except:
                pass

        # Notify error callbacks
        for callback in self.error_callbacks:
            try:
                callback(error_message, error)
            except Exception as e:
                print(f"Error in error callback: {e}")

        # Publish error event
        self.message_bus.publish(
            "dispatcher.execution.error",
            "execution_error",
            {
                "execution_id": self.current_execution.execution_id if self.current_execution else "unknown",
                "error_message": error_message,
                "error_type": type(error).__name__
            },
            priority=MessagePriority.CRITICAL
        )

    def _cleanup_execution(self):
        """Clean up after execution."""
        try:
            # Ensure coordinator is stopped
            if hasattr(self.coordinator, 'state') and self.coordinator.state != 'stopped':
                self.coordinator.stop(timeout=10.0)

            # Clear current execution
            self.current_execution = None

            # Optimize agent pools
            self.agent_factory.optimize_pools()

        except Exception as e:
            print(f"Error during cleanup: {e}")

    def _update_execution_status(self, status: ExecutionStatus, message: str):
        """Update execution status and log message."""
        if self.current_execution:
            self.current_execution.status = status

        self._log_execution_step(f"[{status.value.upper()}] {message}")

    def _log_execution_step(self, message: str):
        """Log execution step."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"

        if self.current_execution:
            self.current_execution.execution_log.append(log_message)

        print(log_message)  # Also print to console

    def _setup_components(self):
        """Setup and configure all components."""
        # Start message bus
        self.message_bus.start()

        # Setup coordinator callbacks
        self.coordinator.add_progress_callback(self._on_coordinator_progress)

        # Subscribe to relevant messages
        self.message_bus.subscribe(
            "dispatcher",
            "coordinator.*",
            self._on_coordinator_message
        )

    def _on_coordinator_progress(self, progress_data: Dict[str, Any]):
        """Handle coordinator progress updates."""
        # Update our progress tracking
        self._update_progress()

    def _on_coordinator_message(self, message):
        """Handle coordinator messages."""
        # Process coordinator status messages
        pass

    def shutdown(self):
        """Shutdown the dispatcher and all components."""
        print("Shutting down AgentDispatcher...")

        # Cancel current execution if any
        if self.current_execution and not self.current_execution.is_complete():
            self.cancel_execution("System shutdown")

        # Stop components
        self.coordinator.stop()
        self.agent_factory.shutdown_all_agents()
        self.state_manager.stop()
        self.message_bus.stop()

        print("AgentDispatcher shutdown complete")

    # Callback management
    def add_progress_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for progress updates."""
        self.progress_callbacks.append(callback)

    def add_completion_callback(self, callback: Callable[[ExecutionResult], None]):
        """Add callback for execution completion."""
        self.completion_callbacks.append(callback)

    def add_error_callback(self, callback: Callable[[str, Exception], None]):
        """Add callback for execution errors."""
        self.error_callbacks.append(callback)