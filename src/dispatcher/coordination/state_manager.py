"""
State Manager - Manages execution state across the distributed system.

This module provides centralized state management with checkpointing,
recovery, metrics tracking, and state synchronization capabilities.
"""

import json
import pickle
import threading
import time
from typing import Dict, Any, Optional, List, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3

from ..models import (
    SystemState, Task, TaskStatus, AgentResult, TaskArtifact,
    ExecutionStatus, ExecutionMetrics, AgentType
)


@dataclass
class CheckpointInfo:
    """Information about a system checkpoint."""
    checkpoint_id: str
    created_at: datetime
    execution_id: str
    task_count: int
    completed_tasks: int
    file_path: str
    metadata: Dict[str, Any]


class StateManager:
    """
    Centralized state management for the execution system.

    Features:
    - Real-time state tracking
    - Checkpoint creation and recovery
    - Metrics aggregation
    - State persistence
    - Event-driven updates
    - State synchronization
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.state: SystemState = SystemState(
            execution_id="",
            status=ExecutionStatus.INITIALIZING
        )

        # Persistence
        self.checkpoint_dir = Path(self.config.get('checkpoint_dir', './checkpoints'))
        self.checkpoint_dir.mkdir(exist_ok=True)
        self.enable_persistence = self.config.get('enable_persistence', True)
        self.auto_checkpoint_interval = self.config.get('auto_checkpoint_interval', 300)  # 5 minutes

        # Database for state tracking
        self.db_path = self.checkpoint_dir / 'state.db'
        self._init_database()

        # Threading
        self.lock = threading.RLock()
        self.running = False
        self.checkpoint_thread: Optional[threading.Thread] = None

        # Metrics tracking
        self.metrics = ExecutionMetrics()
        self.start_time: Optional[datetime] = None

        # Event callbacks
        self.state_change_callbacks: List[Callable[[SystemState], None]] = []
        self.task_completion_callbacks: List[Callable[[str, AgentResult], None]] = []
        self.checkpoint_callbacks: List[Callable[[CheckpointInfo], None]] = []

    def start_execution(self, execution_id: str, tasks: List[Task]):
        """
        Start a new execution session.

        Args:
            execution_id: Unique identifier for this execution
            tasks: List of tasks to execute
        """
        with self.lock:
            # Initialize state
            self.state = SystemState(
                execution_id=execution_id,
                status=ExecutionStatus.EXECUTING
            )

            # Add all tasks
            for task in tasks:
                self.state.all_tasks[task.task_id] = task
                self.state.pending_tasks.add(task.task_id)

            # Update ready tasks
            self._update_ready_tasks()

            # Initialize metrics
            self.metrics = ExecutionMetrics()
            self.metrics.total_tasks = len(tasks)
            self.metrics.started_at = datetime.now()
            self.start_time = datetime.now()

            # Start background thread
            if not self.running:
                self.running = True
                self.checkpoint_thread = threading.Thread(
                    target=self._checkpoint_loop,
                    daemon=True
                )
                self.checkpoint_thread.start()

            # Persist initial state
            if self.enable_persistence:
                self._save_state_to_db()

            # Notify callbacks
            self._notify_state_change()

    def update_task_status(self, task_id: str, new_status: TaskStatus,
                          result: Optional[AgentResult] = None):
        """
        Update the status of a task.

        Args:
            task_id: Task ID to update
            new_status: New status for the task
            result: Optional agent result if task completed
        """
        with self.lock:
            if task_id not in self.state.all_tasks:
                return

            old_status = self.state.all_tasks[task_id].status
            self.state.update_task_status(task_id, new_status)

            # Update metrics
            self._update_metrics_for_status_change(old_status, new_status)

            # Handle task completion
            if new_status == TaskStatus.COMPLETED and result:
                self._handle_task_completion(task_id, result)

            # Update ready tasks when dependencies change
            if new_status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                self._update_ready_tasks()

            # Check if execution is complete
            if self._is_execution_complete():
                self._complete_execution()

            # Persist state changes
            if self.enable_persistence:
                self._save_state_to_db()

            # Notify callbacks
            self._notify_state_change()

            if new_status == TaskStatus.COMPLETED and result:
                self._notify_task_completion(task_id, result)

    def assign_task_to_agent(self, task_id: str, agent_id: str):
        """Assign a task to an agent."""
        with self.lock:
            if task_id in self.state.all_tasks:
                self.state.agent_task_assignments[agent_id] = task_id
                self.state.all_tasks[task_id].assigned_agent_id = agent_id

    def unassign_task_from_agent(self, agent_id: str):
        """Remove task assignment from an agent."""
        with self.lock:
            if agent_id in self.state.agent_task_assignments:
                task_id = self.state.agent_task_assignments[agent_id]
                del self.state.agent_task_assignments[agent_id]

                if task_id in self.state.all_tasks:
                    self.state.all_tasks[task_id].assigned_agent_id = None

    def add_artifact(self, artifact: TaskArtifact):
        """Add an artifact to the state."""
        with self.lock:
            self.state.artifacts[artifact.name] = artifact

    def get_artifact(self, name: str) -> Optional[TaskArtifact]:
        """Get an artifact by name."""
        with self.lock:
            return self.state.artifacts.get(name)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        with self.lock:
            return self.state.all_tasks.get(task_id)

    def get_ready_tasks(self) -> List[str]:
        """Get list of tasks ready for execution."""
        with self.lock:
            return list(self.state.ready_tasks)

    def get_execution_progress(self) -> Dict[str, Any]:
        """Get current execution progress."""
        with self.lock:
            total_tasks = len(self.state.all_tasks)
            completed_tasks = len(self.state.completed_tasks)
            failed_tasks = len(self.state.failed_tasks)
            in_progress_tasks = len(self.state.in_progress_tasks)

            progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

            return {
                'execution_id': self.state.execution_id,
                'status': self.state.status.value,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'failed_tasks': failed_tasks,
                'in_progress_tasks': in_progress_tasks,
                'pending_tasks': len(self.state.pending_tasks),
                'ready_tasks': len(self.state.ready_tasks),
                'progress_percentage': progress_percentage,
                'elapsed_time': self._get_elapsed_time(),
                'estimated_remaining_time': self._estimate_remaining_time()
            }

    def create_checkpoint(self, checkpoint_id: str = None) -> CheckpointInfo:
        """
        Create a checkpoint of the current state.

        Args:
            checkpoint_id: Optional custom checkpoint ID

        Returns:
            CheckpointInfo object
        """
        if not checkpoint_id:
            checkpoint_id = f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        with self.lock:
            checkpoint_data = {
                'state': self._serialize_state(),
                'metrics': asdict(self.metrics),
                'timestamp': datetime.now().isoformat(),
                'execution_id': self.state.execution_id
            }

            # Save to file
            checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2, default=str)

            # Create checkpoint info
            checkpoint_info = CheckpointInfo(
                checkpoint_id=checkpoint_id,
                created_at=datetime.now(),
                execution_id=self.state.execution_id,
                task_count=len(self.state.all_tasks),
                completed_tasks=len(self.state.completed_tasks),
                file_path=str(checkpoint_file),
                metadata={}
            )

            # Save checkpoint info to database
            self._save_checkpoint_info(checkpoint_info)

            # Update state
            self.state.last_checkpoint = datetime.now()
            self.state.checkpoint_data = {'last_checkpoint_id': checkpoint_id}

            # Notify callbacks
            self._notify_checkpoint_created(checkpoint_info)

            return checkpoint_info

    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Restore state from a checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to restore

        Returns:
            True if restoration was successful
        """
        try:
            checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
            if not checkpoint_file.exists():
                return False

            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)

            with self.lock:
                # Restore state
                self._deserialize_state(checkpoint_data['state'])

                # Restore metrics
                metrics_data = checkpoint_data['metrics']
                self.metrics = ExecutionMetrics(**metrics_data)

                # Update checkpoint info
                self.state.last_checkpoint = datetime.now()
                self.state.checkpoint_data = {'restored_from': checkpoint_id}

                # Restart background thread if needed
                if not self.running:
                    self.running = True
                    self.checkpoint_thread = threading.Thread(
                        target=self._checkpoint_loop,
                        daemon=True
                    )
                    self.checkpoint_thread.start()

                # Notify callbacks
                self._notify_state_change()

            return True

        except Exception as e:
            print(f"Failed to restore checkpoint {checkpoint_id}: {e}")
            return False

    def get_checkpoints(self) -> List[CheckpointInfo]:
        """Get list of available checkpoints."""
        checkpoints = []

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT checkpoint_id, created_at, execution_id, task_count,
                           completed_tasks, file_path, metadata
                    FROM checkpoints
                    ORDER BY created_at DESC
                """)

                for row in cursor.fetchall():
                    checkpoint = CheckpointInfo(
                        checkpoint_id=row[0],
                        created_at=datetime.fromisoformat(row[1]),
                        execution_id=row[2],
                        task_count=row[3],
                        completed_tasks=row[4],
                        file_path=row[5],
                        metadata=json.loads(row[6]) if row[6] else {}
                    )
                    checkpoints.append(checkpoint)

        except sqlite3.Error as e:
            print(f"Error retrieving checkpoints: {e}")

        return checkpoints

    def get_metrics(self) -> ExecutionMetrics:
        """Get current execution metrics."""
        with self.lock:
            # Update real-time metrics
            self.metrics.completed_tasks = len(self.state.completed_tasks)
            self.metrics.failed_tasks = len(self.state.failed_tasks)
            self.metrics.cancelled_tasks = len([
                t for t in self.state.all_tasks.values()
                if t.status == TaskStatus.CANCELLED
            ])

            if self.start_time:
                self.metrics.total_execution_time = (
                    datetime.now() - self.start_time
                ).total_seconds()

                if self.metrics.completed_tasks > 0:
                    self.metrics.average_task_time = (
                        self.metrics.total_execution_time / self.metrics.completed_tasks
                    )

            return self.metrics

    def stop(self):
        """Stop the state manager."""
        self.running = False
        if self.checkpoint_thread:
            self.checkpoint_thread.join(timeout=5.0)

    def add_state_change_callback(self, callback: Callable[[SystemState], None]):
        """Add a callback for state changes."""
        self.state_change_callbacks.append(callback)

    def add_task_completion_callback(self, callback: Callable[[str, AgentResult], None]):
        """Add a callback for task completions."""
        self.task_completion_callbacks.append(callback)

    def add_checkpoint_callback(self, callback: Callable[[CheckpointInfo], None]):
        """Add a callback for checkpoint creation."""
        self.checkpoint_callbacks.append(callback)

    def _update_ready_tasks(self):
        """Update the list of ready tasks."""
        for task_id in list(self.state.pending_tasks):
            task = self.state.all_tasks[task_id]
            if task.is_ready(self.state.completed_tasks):
                self.state.pending_tasks.remove(task_id)
                self.state.ready_tasks.add(task_id)

    def _update_metrics_for_status_change(self, old_status: TaskStatus, new_status: TaskStatus):
        """Update metrics when task status changes."""
        # Track agent utilization
        if new_status == TaskStatus.IN_PROGRESS:
            # Task started
            pass
        elif old_status == TaskStatus.IN_PROGRESS and new_status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            # Task finished
            pass

    def _handle_task_completion(self, task_id: str, result: AgentResult):
        """Handle task completion."""
        # Add artifacts from result
        for artifact in result.artifacts:
            self.add_artifact(artifact)

        # Update task with result data
        task = self.state.all_tasks[task_id]
        task.complete()

    def _is_execution_complete(self) -> bool:
        """Check if execution is complete."""
        return (len(self.state.pending_tasks) == 0 and
                len(self.state.ready_tasks) == 0 and
                len(self.state.in_progress_tasks) == 0)

    def _complete_execution(self):
        """Complete the execution."""
        self.state.status = ExecutionStatus.COMPLETED
        self.metrics.completed_at = datetime.now()

        # Create final checkpoint
        self.create_checkpoint("final_checkpoint")

    def _get_elapsed_time(self) -> float:
        """Get elapsed execution time in seconds."""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0

    def _estimate_remaining_time(self) -> Optional[float]:
        """Estimate remaining execution time."""
        if not self.start_time or self.metrics.completed_tasks == 0:
            return None

        elapsed = self._get_elapsed_time()
        completion_rate = self.metrics.completed_tasks / elapsed  # tasks per second
        remaining_tasks = len(self.state.pending_tasks) + len(self.state.ready_tasks) + len(self.state.in_progress_tasks)

        if completion_rate > 0:
            return remaining_tasks / completion_rate

        return None

    def _checkpoint_loop(self):
        """Background thread for automatic checkpointing."""
        while self.running:
            try:
                time.sleep(self.auto_checkpoint_interval)
                if self.running and self.state.status == ExecutionStatus.EXECUTING:
                    self.create_checkpoint()
            except Exception as e:
                print(f"Error in checkpoint loop: {e}")

    def _serialize_state(self) -> Dict[str, Any]:
        """Serialize the current state."""
        return {
            'execution_id': self.state.execution_id,
            'status': self.state.status.value,
            'all_tasks': {
                task_id: {
                    'task_id': task.task_id,
                    'description': task.description,
                    'task_type': task.task_type.value,
                    'required_agent_type': task.required_agent_type.value,
                    'status': task.status.value,
                    'estimated_complexity': task.estimated_complexity,
                    'priority': task.priority,
                    'dependencies': task.dependencies,
                    'context': task.context,
                    'assigned_agent_id': task.assigned_agent_id,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None
                }
                for task_id, task in self.state.all_tasks.items()
            },
            'pending_tasks': list(self.state.pending_tasks),
            'ready_tasks': list(self.state.ready_tasks),
            'in_progress_tasks': list(self.state.in_progress_tasks),
            'completed_tasks': list(self.state.completed_tasks),
            'failed_tasks': list(self.state.failed_tasks),
            'agent_task_assignments': dict(self.state.agent_task_assignments),
            'artifacts': {
                name: {
                    'name': artifact.name,
                    'type': artifact.type,
                    'content': artifact.content,
                    'metadata': artifact.metadata,
                    'created_at': artifact.created_at.isoformat()
                }
                for name, artifact in self.state.artifacts.items()
            }
        }

    def _deserialize_state(self, state_data: Dict[str, Any]):
        """Deserialize state from data."""
        from ..models import Task, TaskType, AgentType, TaskStatus, TaskArtifact

        # Restore basic state
        self.state.execution_id = state_data['execution_id']
        self.state.status = ExecutionStatus(state_data['status'])

        # Restore tasks
        self.state.all_tasks = {}
        for task_id, task_data in state_data['all_tasks'].items():
            task = Task(
                task_id=task_data['task_id'],
                description=task_data['description'],
                task_type=TaskType(task_data['task_type']),
                required_agent_type=AgentType(task_data['required_agent_type']),
                estimated_complexity=task_data['estimated_complexity'],
                priority=task_data['priority'],
                dependencies=task_data['dependencies'],
                context=task_data['context']
            )
            task.status = TaskStatus(task_data['status'])
            task.assigned_agent_id = task_data['assigned_agent_id']

            if task_data['started_at']:
                task.started_at = datetime.fromisoformat(task_data['started_at'])
            if task_data['completed_at']:
                task.completed_at = datetime.fromisoformat(task_data['completed_at'])

            self.state.all_tasks[task_id] = task

        # Restore sets
        self.state.pending_tasks = set(state_data['pending_tasks'])
        self.state.ready_tasks = set(state_data['ready_tasks'])
        self.state.in_progress_tasks = set(state_data['in_progress_tasks'])
        self.state.completed_tasks = set(state_data['completed_tasks'])
        self.state.failed_tasks = set(state_data['failed_tasks'])

        # Restore assignments
        self.state.agent_task_assignments = state_data['agent_task_assignments']

        # Restore artifacts
        self.state.artifacts = {}
        for name, artifact_data in state_data['artifacts'].items():
            artifact = TaskArtifact(
                name=artifact_data['name'],
                type=artifact_data['type'],
                content=artifact_data['content'],
                metadata=artifact_data['metadata'],
                created_at=datetime.fromisoformat(artifact_data['created_at'])
            )
            self.state.artifacts[name] = artifact

    def _init_database(self):
        """Initialize SQLite database for state persistence."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS checkpoints (
                        checkpoint_id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL,
                        execution_id TEXT NOT NULL,
                        task_count INTEGER NOT NULL,
                        completed_tasks INTEGER NOT NULL,
                        file_path TEXT NOT NULL,
                        metadata TEXT
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS execution_history (
                        execution_id TEXT PRIMARY KEY,
                        started_at TEXT NOT NULL,
                        completed_at TEXT,
                        status TEXT NOT NULL,
                        total_tasks INTEGER,
                        completed_tasks INTEGER,
                        failed_tasks INTEGER,
                        metadata TEXT
                    )
                """)
        except sqlite3.Error as e:
            print(f"Failed to initialize database: {e}")

    def _save_state_to_db(self):
        """Save current state to database."""
        if not self.enable_persistence:
            return

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO execution_history
                    (execution_id, started_at, completed_at, status, total_tasks, completed_tasks, failed_tasks, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.state.execution_id,
                    self.start_time.isoformat() if self.start_time else None,
                    self.metrics.completed_at.isoformat() if self.metrics.completed_at else None,
                    self.state.status.value,
                    len(self.state.all_tasks),
                    len(self.state.completed_tasks),
                    len(self.state.failed_tasks),
                    json.dumps({})
                ))
        except sqlite3.Error as e:
            print(f"Failed to save state to database: {e}")

    def _save_checkpoint_info(self, checkpoint_info: CheckpointInfo):
        """Save checkpoint info to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO checkpoints
                    (checkpoint_id, created_at, execution_id, task_count, completed_tasks, file_path, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    checkpoint_info.checkpoint_id,
                    checkpoint_info.created_at.isoformat(),
                    checkpoint_info.execution_id,
                    checkpoint_info.task_count,
                    checkpoint_info.completed_tasks,
                    checkpoint_info.file_path,
                    json.dumps(checkpoint_info.metadata)
                ))
        except sqlite3.Error as e:
            print(f"Failed to save checkpoint info: {e}")

    def _notify_state_change(self):
        """Notify all state change callbacks."""
        for callback in self.state_change_callbacks:
            try:
                callback(self.state)
            except Exception as e:
                print(f"Error in state change callback: {e}")

    def _notify_task_completion(self, task_id: str, result: AgentResult):
        """Notify all task completion callbacks."""
        for callback in self.task_completion_callbacks:
            try:
                callback(task_id, result)
            except Exception as e:
                print(f"Error in task completion callback: {e}")

    def _notify_checkpoint_created(self, checkpoint_info: CheckpointInfo):
        """Notify all checkpoint callbacks."""
        for callback in self.checkpoint_callbacks:
            try:
                callback(checkpoint_info)
            except Exception as e:
                print(f"Error in checkpoint callback: {e}")