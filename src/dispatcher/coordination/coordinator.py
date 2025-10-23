"""
Coordinator - Manages parallel agent execution and task scheduling.

This module orchestrates the execution of tasks across multiple agents,
handling scheduling, resource allocation, failure recovery, and
real-time progress monitoring.
"""

import threading
import time
import asyncio
from typing import Dict, List, Set, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from queue import Queue, PriorityQueue, Empty
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from .message_bus import MessageBus, MessagePriority
from .state_manager import StateManager
from ..agents.agent_factory import AgentFactory
from ..agents.base_agent import BaseAgent
from ..models import Task, TaskStatus, AgentResult, ExecutionStatus, AgentType


class CoordinatorState(Enum):
    """States of the coordinator."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class TaskExecution:
    """Represents a task being executed."""
    task_id: str
    agent_id: str
    agent: BaseAgent
    future: Future
    started_at: datetime
    estimated_completion: Optional[datetime] = None


@dataclass
class WorkerMetrics:
    """Metrics for a worker thread."""
    worker_id: str
    tasks_processed: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_execution_time: float = 0.0
    last_activity: Optional[datetime] = None
    current_task: Optional[str] = None


class Coordinator:
    """
    Orchestrates parallel execution of tasks across multiple agents.

    Features:
    - Task queue management with priorities
    - Agent pool management
    - Work stealing and load balancing
    - Failure handling and recovery
    - Real-time progress monitoring
    - Resource limits and throttling
    - Cancellation and graceful shutdown
    """

    def __init__(self, agent_factory: AgentFactory, state_manager: StateManager,
                 message_bus: MessageBus, config: Dict[str, Any] = None):
        self.agent_factory = agent_factory
        self.state_manager = state_manager
        self.message_bus = message_bus
        self.config = config or {}

        # Coordinator state
        self.state = CoordinatorState.IDLE
        self.execution_id: Optional[str] = None

        # Task management
        self.task_queue = PriorityQueue()
        self.ready_tasks: Set[str] = set()
        self.executing_tasks: Dict[str, TaskExecution] = {}
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()

        # Worker management
        self.max_workers = self.config.get('max_workers', 4)
        self.worker_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        self.worker_metrics: Dict[str, WorkerMetrics] = {}

        # Agent management
        self.active_agents: Dict[str, BaseAgent] = {}
        self.max_concurrent_tasks = self.config.get('max_concurrent_tasks', 10)
        self.agent_timeout = self.config.get('agent_timeout', 300)  # 5 minutes

        # Control flow
        self.running = False
        self.shutdown_event = threading.Event()
        self.pause_event = threading.Event()

        # Monitoring and metrics
        self.coordinator_thread: Optional[threading.Thread] = None
        self.monitor_interval = self.config.get('monitor_interval', 5.0)

        # Callbacks
        self.task_start_callbacks: List[Callable[[str, Task], None]] = []
        self.task_complete_callbacks: List[Callable[[str, AgentResult], None]] = []
        self.progress_callbacks: List[Callable[[Dict[str, Any]], None]] = []

        # Setup message bus subscriptions
        self._setup_message_subscriptions()

    def start(self, execution_id: str, tasks: List[Task]):
        """
        Start coordinated execution of tasks.

        Args:
            execution_id: Unique identifier for this execution
            tasks: List of tasks to execute
        """
        if self.state != CoordinatorState.IDLE:
            raise RuntimeError(f"Coordinator is not idle (current state: {self.state})")

        self.execution_id = execution_id
        self.state = CoordinatorState.RUNNING
        self.running = True
        self.shutdown_event.clear()
        self.pause_event.set()  # Not paused initially

        # Initialize state manager
        self.state_manager.start_execution(execution_id, tasks)

        # Queue initial ready tasks
        self._queue_ready_tasks()

        # Start coordinator monitoring thread
        self.coordinator_thread = threading.Thread(
            target=self._coordination_loop,
            daemon=True
        )
        self.coordinator_thread.start()

        # Publish start event
        self.message_bus.publish(
            "coordinator.execution.started",
            "execution_started",
            {
                "execution_id": execution_id,
                "total_tasks": len(tasks),
                "max_workers": self.max_workers
            },
            priority=MessagePriority.HIGH
        )

        print(f"Coordinator started execution {execution_id} with {len(tasks)} tasks")

    def pause(self):
        """Pause execution (complete current tasks but don't start new ones)."""
        if self.state == CoordinatorState.RUNNING:
            self.state = CoordinatorState.PAUSING
            self.pause_event.clear()

            # Wait for current tasks to complete
            self._wait_for_current_tasks()
            self.state = CoordinatorState.PAUSED

            self.message_bus.publish(
                "coordinator.execution.paused",
                "execution_paused",
                {"execution_id": self.execution_id}
            )

    def resume(self):
        """Resume paused execution."""
        if self.state == CoordinatorState.PAUSED:
            self.state = CoordinatorState.RUNNING
            self.pause_event.set()

            self.message_bus.publish(
                "coordinator.execution.resumed",
                "execution_resumed",
                {"execution_id": self.execution_id}
            )

    def stop(self, timeout: float = 30.0):
        """
        Stop execution gracefully.

        Args:
            timeout: Maximum time to wait for graceful shutdown
        """
        if self.state in [CoordinatorState.STOPPED, CoordinatorState.STOPPING]:
            return

        self.state = CoordinatorState.STOPPING
        self.running = False
        self.shutdown_event.set()

        # Cancel all executing tasks
        self._cancel_executing_tasks()

        # Shutdown worker pool
        self.worker_pool.shutdown(wait=True, timeout=timeout)

        # Stop coordinator thread
        if self.coordinator_thread and self.coordinator_thread.is_alive():
            self.coordinator_thread.join(timeout=5.0)

        # Return agents to factory
        self._cleanup_agents()

        self.state = CoordinatorState.STOPPED

        self.message_bus.publish(
            "coordinator.execution.stopped",
            "execution_stopped",
            {
                "execution_id": self.execution_id,
                "completed_tasks": len(self.completed_tasks),
                "failed_tasks": len(self.failed_tasks)
            },
            priority=MessagePriority.HIGH
        )

    def get_status(self) -> Dict[str, Any]:
        """Get current coordinator status."""
        return {
            'state': self.state.value,
            'execution_id': self.execution_id,
            'running': self.running,
            'tasks_queued': self.task_queue.qsize(),
            'tasks_executing': len(self.executing_tasks),
            'tasks_completed': len(self.completed_tasks),
            'tasks_failed': len(self.failed_tasks),
            'active_agents': len(self.active_agents),
            'worker_metrics': {wid: {
                'tasks_processed': metrics.tasks_processed,
                'successful_tasks': metrics.successful_tasks,
                'failed_tasks': metrics.failed_tasks,
                'current_task': metrics.current_task
            } for wid, metrics in self.worker_metrics.items()}
        }

    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed execution metrics."""
        total_tasks = len(self.completed_tasks) + len(self.failed_tasks) + len(self.executing_tasks) + self.task_queue.qsize()

        metrics = {
            'execution_overview': {
                'execution_id': self.execution_id,
                'state': self.state.value,
                'total_tasks': total_tasks,
                'completed_tasks': len(self.completed_tasks),
                'failed_tasks': len(self.failed_tasks),
                'executing_tasks': len(self.executing_tasks),
                'queued_tasks': self.task_queue.qsize(),
                'completion_percentage': (len(self.completed_tasks) / total_tasks * 100) if total_tasks > 0 else 0
            },
            'resource_utilization': {
                'max_workers': self.max_workers,
                'active_agents': len(self.active_agents),
                'max_concurrent_tasks': self.max_concurrent_tasks,
                'current_utilization': (len(self.executing_tasks) / self.max_concurrent_tasks * 100) if self.max_concurrent_tasks > 0 else 0
            },
            'worker_performance': {
                worker_id: {
                    'tasks_processed': metrics.tasks_processed,
                    'success_rate': (metrics.successful_tasks / metrics.tasks_processed * 100) if metrics.tasks_processed > 0 else 0,
                    'average_task_time': (metrics.total_execution_time / metrics.tasks_processed) if metrics.tasks_processed > 0 else 0,
                    'last_activity': metrics.last_activity.isoformat() if metrics.last_activity else None
                }
                for worker_id, metrics in self.worker_metrics.items()
            },
            'agent_distribution': self._get_agent_distribution_stats(),
            'execution_timeline': self._get_execution_timeline()
        }

        return metrics

    def _coordination_loop(self):
        """Main coordination loop."""
        while self.running:
            try:
                # Wait if paused
                self.pause_event.wait()

                if not self.running:
                    break

                # Process ready tasks
                self._process_ready_tasks()

                # Monitor executing tasks
                self._monitor_executing_tasks()

                # Update metrics
                self._update_metrics()

                # Check for completion
                if self._is_execution_complete():
                    self._handle_execution_completion()
                    break

                # Sleep before next iteration
                time.sleep(self.monitor_interval)

            except Exception as e:
                print(f"Error in coordination loop: {e}")
                self.state = CoordinatorState.ERROR

        print("Coordination loop ended")

    def _queue_ready_tasks(self):
        """Queue tasks that are ready for execution."""
        ready_task_ids = self.state_manager.get_ready_tasks()

        for task_id in ready_task_ids:
            if task_id not in self.ready_tasks and task_id not in self.executing_tasks:
                task = self.state_manager.get_task(task_id)
                if task:
                    # Priority queue: lower number = higher priority
                    priority = -task.priority  # Negate to make higher priority values come first
                    self.task_queue.put((priority, task_id))
                    self.ready_tasks.add(task_id)

    def _process_ready_tasks(self):
        """Process tasks from the ready queue."""
        while (not self.task_queue.empty() and
               len(self.executing_tasks) < self.max_concurrent_tasks and
               self.running and self.pause_event.is_set()):

            try:
                # Get next task
                priority, task_id = self.task_queue.get_nowait()
                self.ready_tasks.discard(task_id)

                # Get task details
                task = self.state_manager.get_task(task_id)
                if not task or task.status != TaskStatus.READY:
                    continue

                # Get agent for task
                agent = self._get_agent_for_task(task)
                if not agent:
                    # Put task back in queue
                    self.task_queue.put((priority, task_id))
                    self.ready_tasks.add(task_id)
                    break

                # Submit task for execution
                self._submit_task_for_execution(task, agent)

            except Empty:
                break
            except Exception as e:
                print(f"Error processing ready task: {e}")

    def _submit_task_for_execution(self, task: Task, agent: BaseAgent):
        """Submit a task for execution by an agent."""
        # Update task status
        self.state_manager.update_task_status(task.task_id, TaskStatus.IN_PROGRESS)
        self.state_manager.assign_task_to_agent(task.task_id, agent.agent_id)

        # Submit to worker pool
        future = self.worker_pool.submit(self._execute_task_wrapper, task, agent)

        # Track execution
        execution = TaskExecution(
            task_id=task.task_id,
            agent_id=agent.agent_id,
            agent=agent,
            future=future,
            started_at=datetime.now()
        )

        self.executing_tasks[task.task_id] = execution
        self.active_agents[agent.agent_id] = agent

        # Notify callbacks
        for callback in self.task_start_callbacks:
            try:
                callback(task.task_id, task)
            except Exception as e:
                print(f"Error in task start callback: {e}")

        # Publish start event
        self.message_bus.publish(
            "coordinator.task.started",
            "task_started",
            {
                "execution_id": self.execution_id,
                "task_id": task.task_id,
                "agent_id": agent.agent_id,
                "agent_type": agent.get_agent_type().value
            }
        )

    def _execute_task_wrapper(self, task: Task, agent: BaseAgent) -> AgentResult:
        """Wrapper for task execution with metrics tracking."""
        worker_id = threading.current_thread().name

        # Initialize worker metrics if needed
        if worker_id not in self.worker_metrics:
            self.worker_metrics[worker_id] = WorkerMetrics(worker_id=worker_id)

        metrics = self.worker_metrics[worker_id]
        metrics.current_task = task.task_id
        metrics.last_activity = datetime.now()

        start_time = time.time()

        try:
            # Execute task
            result = agent.execute(task)

            # Update metrics
            execution_time = time.time() - start_time
            metrics.tasks_processed += 1
            metrics.total_execution_time += execution_time

            if result.success:
                metrics.successful_tasks += 1
            else:
                metrics.failed_tasks += 1

            return result

        except Exception as e:
            # Create error result
            execution_time = time.time() - start_time
            metrics.tasks_processed += 1
            metrics.failed_tasks += 1
            metrics.total_execution_time += execution_time

            return AgentResult(
                task_id=task.task_id,
                agent_id=agent.agent_id,
                agent_type=agent.get_agent_type(),
                success=False,
                error_message=f"Execution wrapper error: {e}",
                execution_time=execution_time
            )

        finally:
            metrics.current_task = None
            metrics.last_activity = datetime.now()

    def _monitor_executing_tasks(self):
        """Monitor executing tasks for completion and timeouts."""
        completed_executions = []

        for task_id, execution in list(self.executing_tasks.items()):
            # Check for completion
            if execution.future.done():
                completed_executions.append(task_id)
                continue

            # Check for timeout
            if self.agent_timeout:
                elapsed = (datetime.now() - execution.started_at).total_seconds()
                if elapsed > self.agent_timeout:
                    print(f"Task {task_id} timed out after {elapsed:.1f} seconds")
                    execution.future.cancel()
                    completed_executions.append(task_id)

        # Process completed executions
        for task_id in completed_executions:
            self._handle_task_completion(task_id)

    def _handle_task_completion(self, task_id: str):
        """Handle completion of a task."""
        if task_id not in self.executing_tasks:
            return

        execution = self.executing_tasks[task_id]

        try:
            # Get result
            if execution.future.cancelled():
                result = AgentResult(
                    task_id=task_id,
                    agent_id=execution.agent_id,
                    agent_type=execution.agent.get_agent_type(),
                    success=False,
                    error_message="Task was cancelled"
                )
            else:
                result = execution.future.result(timeout=1.0)

            # Update state
            if result.success:
                self.state_manager.update_task_status(task_id, TaskStatus.COMPLETED, result)
                self.completed_tasks.add(task_id)
            else:
                self.state_manager.update_task_status(task_id, TaskStatus.FAILED, result)
                self.failed_tasks.add(task_id)

            # Return agent to factory
            self.agent_factory.return_agent(execution.agent)

            # Notify callbacks
            for callback in self.task_complete_callbacks:
                try:
                    callback(task_id, result)
                except Exception as e:
                    print(f"Error in task completion callback: {e}")

            # Publish completion event
            self.message_bus.publish(
                "coordinator.task.completed",
                "task_completed",
                {
                    "execution_id": self.execution_id,
                    "task_id": task_id,
                    "agent_id": execution.agent_id,
                    "success": result.success,
                    "execution_time": result.execution_time,
                    "error_message": result.error_message
                }
            )

        except Exception as e:
            print(f"Error handling task completion for {task_id}: {e}")
            self.state_manager.update_task_status(task_id, TaskStatus.FAILED)
            self.failed_tasks.add(task_id)

        finally:
            # Clean up
            self.state_manager.unassign_task_from_agent(execution.agent_id)
            if execution.agent_id in self.active_agents:
                del self.active_agents[execution.agent_id]
            del self.executing_tasks[task_id]

        # Queue new ready tasks
        self._queue_ready_tasks()

    def _get_agent_for_task(self, task: Task) -> Optional[BaseAgent]:
        """Get an available agent for a task."""
        try:
            return self.agent_factory.get_agent_for_task(task)
        except Exception as e:
            print(f"Error getting agent for task {task.task_id}: {e}")
            return None

    def _is_execution_complete(self) -> bool:
        """Check if execution is complete."""
        return (self.task_queue.empty() and
                len(self.executing_tasks) == 0 and
                len(self.ready_tasks) == 0)

    def _handle_execution_completion(self):
        """Handle completion of the entire execution."""
        self.running = False

        # Determine final status
        if len(self.failed_tasks) == 0:
            final_status = ExecutionStatus.COMPLETED
        else:
            final_status = ExecutionStatus.FAILED

        # Update state manager
        self.state_manager.state.status = final_status

        # Publish completion event
        self.message_bus.publish(
            "coordinator.execution.completed",
            "execution_completed",
            {
                "execution_id": self.execution_id,
                "final_status": final_status.value,
                "completed_tasks": len(self.completed_tasks),
                "failed_tasks": len(self.failed_tasks),
                "total_execution_time": self._get_total_execution_time()
            },
            priority=MessagePriority.HIGH
        )

        print(f"Execution {self.execution_id} completed with status {final_status.value}")

    def _cancel_executing_tasks(self):
        """Cancel all executing tasks."""
        for execution in self.executing_tasks.values():
            execution.future.cancel()

    def _cleanup_agents(self):
        """Return all agents to the factory."""
        for agent in self.active_agents.values():
            self.agent_factory.return_agent(agent)
        self.active_agents.clear()

    def _wait_for_current_tasks(self, timeout: float = 60.0):
        """Wait for current tasks to complete."""
        start_time = time.time()
        while self.executing_tasks and (time.time() - start_time) < timeout:
            time.sleep(1.0)

    def _update_metrics(self):
        """Update and publish progress metrics."""
        progress_data = {
            'execution_id': self.execution_id,
            'timestamp': datetime.now().isoformat(),
            'state': self.state.value,
            'tasks': {
                'total': len(self.completed_tasks) + len(self.failed_tasks) + len(self.executing_tasks) + self.task_queue.qsize(),
                'completed': len(self.completed_tasks),
                'failed': len(self.failed_tasks),
                'executing': len(self.executing_tasks),
                'queued': self.task_queue.qsize()
            },
            'resources': {
                'active_agents': len(self.active_agents),
                'max_workers': self.max_workers,
                'utilization': (len(self.executing_tasks) / self.max_concurrent_tasks * 100) if self.max_concurrent_tasks > 0 else 0
            }
        }

        # Notify progress callbacks
        for callback in self.progress_callbacks:
            try:
                callback(progress_data)
            except Exception as e:
                print(f"Error in progress callback: {e}")

    def _get_total_execution_time(self) -> float:
        """Get total execution time so far."""
        if hasattr(self.state_manager, 'start_time') and self.state_manager.start_time:
            return (datetime.now() - self.state_manager.start_time).total_seconds()
        return 0.0

    def _get_agent_distribution_stats(self) -> Dict[str, Any]:
        """Get statistics about agent type distribution."""
        agent_types = {}
        for agent in self.active_agents.values():
            agent_type = agent.get_agent_type().value
            if agent_type not in agent_types:
                agent_types[agent_type] = 0
            agent_types[agent_type] += 1

        return agent_types

    def _get_execution_timeline(self) -> List[Dict[str, Any]]:
        """Get execution timeline events."""
        # This would track major events during execution
        # For now, return basic info
        return [
            {
                'event': 'execution_started',
                'timestamp': self.state_manager.start_time.isoformat() if hasattr(self.state_manager, 'start_time') and self.state_manager.start_time else None,
                'details': {'execution_id': self.execution_id}
            }
        ]

    def _setup_message_subscriptions(self):
        """Setup message bus subscriptions."""
        # Subscribe to state manager events
        self.message_bus.subscribe(
            "coordinator",
            "state.*",
            self._handle_state_message
        )

        # Subscribe to agent events
        self.message_bus.subscribe(
            "coordinator",
            "agent.*",
            self._handle_agent_message
        )

    def _handle_state_message(self, message):
        """Handle state-related messages."""
        # Process state change messages
        pass

    def _handle_agent_message(self, message):
        """Handle agent-related messages."""
        # Process agent status messages
        pass

    # Callback management
    def add_task_start_callback(self, callback: Callable[[str, Task], None]):
        """Add callback for task start events."""
        self.task_start_callbacks.append(callback)

    def add_task_complete_callback(self, callback: Callable[[str, AgentResult], None]):
        """Add callback for task completion events."""
        self.task_complete_callbacks.append(callback)

    def add_progress_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for progress updates."""
        self.progress_callbacks.append(callback)