"""
Dispatch service that wraps Phase 4 of the Specify system.

Provides a service layer interface for agent execution with proper
error handling, logging, and session management.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Import Phase 4 components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from src.dispatcher import (
    AgentDispatcher,
    ExecutionResult as CoreExecutionResult,
    ExecutionStatus as CoreExecutionStatus,
    Task as CoreTask,
    AgentResult as CoreAgentResult
)
from api.schemas.response_schemas import (
    ExecutionResult,
    ExecutionStatus,
    Task,
    TaskStatus,
    AgentResult,
    ExecutionGraph
)
from api.services.session_manager import SessionManager

logger = logging.getLogger(__name__)


class DispatchService:
    """Service wrapper for the agent dispatcher (Phase 4)."""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self._active_executions: Dict[str, Dict[str, Any]] = {}
        self._dispatchers: Dict[str, AgentDispatcher] = {}

    async def start_execution(
        self,
        specification_id: str,
        specification_data: Dict[str, Any],
        execution_mode: str = "adaptive",
        session_id: Optional[str] = None,
        agent_constraints: Optional[Dict[str, Any]] = None,
        target_platform: Optional[str] = None,
        output_format: str = "files"
    ) -> tuple[str, ExecutionResult]:
        """
        Start agent execution for a finalized specification.

        Args:
            specification_id: ID of the finalized specification
            specification_data: Specification data
            execution_mode: Execution mode (sequential, parallel, adaptive)
            session_id: Optional session ID for tracking
            agent_constraints: Constraints for agent execution
            target_platform: Target platform for code generation
            output_format: Output format preference

        Returns:
            Tuple of (execution_id, execution_result)
        """
        execution_id = str(uuid.uuid4())

        logger.info(f"Starting execution {execution_id} for session {session_id}")

        # Track execution in session if provided
        if session_id:
            await self.session_manager.add_operation(session_id, f"execution:{execution_id}")

        try:
            # Configure dispatcher
            dispatcher_config = self._create_dispatcher_config(
                execution_mode,
                agent_constraints,
                target_platform,
                output_format
            )

            # Create dispatcher
            dispatcher = AgentDispatcher(dispatcher_config)
            self._dispatchers[execution_id] = dispatcher

            # Convert specification data to format expected by dispatcher
            finalized_specification = self._convert_to_finalized_specification(specification_data)

            # Start execution
            core_result = await self._start_core_execution(dispatcher, finalized_specification)

            # Convert to API format
            api_result = self._convert_execution_result(execution_id, core_result)

            # Store execution metadata
            self._active_executions[execution_id] = {
                "id": execution_id,
                "session_id": session_id,
                "specification_id": specification_id,
                "execution_mode": execution_mode,
                "target_platform": target_platform,
                "output_format": output_format,
                "status": api_result.status,
                "started_at": datetime.now(),
                "core_result": core_result,
                "api_result": api_result
            }

            logger.info(f"Started execution {execution_id}")

            return execution_id, api_result

        except Exception as e:
            logger.exception(f"Error starting execution {execution_id}: {e}")

            # Remove from session operations
            if session_id:
                await self.session_manager.remove_operation(session_id, f"execution:{execution_id}")

            raise

    async def get_execution_status(self, execution_id: str) -> Optional[ExecutionResult]:
        """
        Get execution status and current progress.

        Args:
            execution_id: Execution ID

        Returns:
            Execution result or None if not found
        """
        execution_data = self._active_executions.get(execution_id)
        if not execution_data:
            return None

        # Check for updates from dispatcher
        dispatcher = self._dispatchers.get(execution_id)
        if dispatcher:
            # Get latest status from dispatcher
            try:
                core_result = await self._get_core_execution_status(dispatcher)
                api_result = self._convert_execution_result(execution_id, core_result)

                # Update stored result
                execution_data["core_result"] = core_result
                execution_data["api_result"] = api_result
                execution_data["status"] = api_result.status

                return api_result
            except Exception as e:
                logger.error(f"Error getting execution status for {execution_id}: {e}")

        return execution_data.get("api_result")

    async def get_execution_graph(self, execution_id: str) -> Optional[ExecutionGraph]:
        """
        Get execution DAG for visualization.

        Args:
            execution_id: Execution ID

        Returns:
            Execution graph or None if not found
        """
        execution_data = self._active_executions.get(execution_id)
        if not execution_data:
            return None

        api_result = execution_data.get("api_result")
        if api_result and api_result.execution_graph:
            return api_result.execution_graph

        return None

    async def get_execution_results(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get final execution results.

        Args:
            execution_id: Execution ID

        Returns:
            Execution outputs or None if not found/not completed
        """
        execution_data = self._active_executions.get(execution_id)
        if not execution_data:
            return None

        api_result = execution_data.get("api_result")
        if api_result and api_result.status == ExecutionStatus.COMPLETED:
            return api_result.outputs

        return None

    async def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel a running execution.

        Args:
            execution_id: Execution ID

        Returns:
            True if cancelled, False if not found or already completed
        """
        execution_data = self._active_executions.get(execution_id)
        if not execution_data:
            return False

        dispatcher = self._dispatchers.get(execution_id)
        if not dispatcher:
            return False

        try:
            # Cancel through dispatcher
            success = await self._cancel_core_execution(dispatcher)

            if success:
                # Update status
                execution_data.update({
                    "status": ExecutionStatus.CANCELLED,
                    "completed_at": datetime.now()
                })

                # Remove from session operations
                session_id = execution_data.get("session_id")
                if session_id:
                    await self.session_manager.remove_operation(session_id, f"execution:{execution_id}")

                # Clean up dispatcher
                del self._dispatchers[execution_id]

                logger.info(f"Cancelled execution {execution_id}")

            return success

        except Exception as e:
            logger.exception(f"Error cancelling execution {execution_id}: {e}")
            return False

    async def list_session_executions(self, session_id: str) -> List[Dict[str, Any]]:
        """
        List all executions for a session.

        Args:
            session_id: Session ID

        Returns:
            List of execution status info
        """
        executions = []
        for execution_data in self._active_executions.values():
            if execution_data.get("session_id") == session_id:
                executions.append({
                    "id": execution_data["id"],
                    "specification_id": execution_data["specification_id"],
                    "execution_mode": execution_data["execution_mode"],
                    "status": execution_data["status"],
                    "started_at": execution_data["started_at"],
                    "completed_at": execution_data.get("completed_at"),
                    "target_platform": execution_data.get("target_platform"),
                    "output_format": execution_data.get("output_format")
                })

        return sorted(executions, key=lambda x: x["started_at"], reverse=True)

    def _create_dispatcher_config(
        self,
        execution_mode: str,
        agent_constraints: Optional[Dict[str, Any]],
        target_platform: Optional[str],
        output_format: str
    ) -> Dict[str, Any]:
        """
        Create dispatcher configuration.

        Args:
            execution_mode: Execution mode
            agent_constraints: Agent constraints
            target_platform: Target platform
            output_format: Output format

        Returns:
            Dispatcher configuration
        """
        config = {
            "execution_mode": execution_mode,
            "max_parallel_agents": 4,
            "enable_parallel_execution": execution_mode in ["parallel", "adaptive"],
            "output_format": output_format
        }

        if agent_constraints:
            config.update(agent_constraints)

        if target_platform:
            config["target_platform"] = target_platform

        return config

    async def _start_core_execution(
        self,
        dispatcher: AgentDispatcher,
        specification: Dict[str, Any]
    ) -> CoreExecutionResult:
        """
        Start core execution through dispatcher.

        Args:
            dispatcher: Agent dispatcher
            specification: Finalized specification

        Returns:
            Core execution result
        """
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            dispatcher.dispatch,
            specification
        )

        return result

    async def _get_core_execution_status(self, dispatcher: AgentDispatcher) -> CoreExecutionResult:
        """
        Get current execution status from dispatcher.

        Args:
            dispatcher: Agent dispatcher

        Returns:
            Updated core execution result
        """
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            dispatcher.get_status
        )

        return result

    async def _cancel_core_execution(self, dispatcher: AgentDispatcher) -> bool:
        """
        Cancel execution through dispatcher.

        Args:
            dispatcher: Agent dispatcher

        Returns:
            True if cancelled successfully
        """
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            dispatcher.cancel
        )

        return result

    def _convert_to_finalized_specification(self, specification_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert API specification data to format expected by dispatcher.

        Args:
            specification_data: Specification data from API

        Returns:
            Finalized specification for dispatcher
        """
        # This conversion depends on the actual interface expected by the dispatcher
        return specification_data

    def _convert_execution_result(
        self,
        execution_id: str,
        core_result: CoreExecutionResult
    ) -> ExecutionResult:
        """
        Convert core execution result to API format.

        Args:
            execution_id: Execution ID
            core_result: Core execution result

        Returns:
            API execution result
        """
        # Convert status
        status_mapping = {
            CoreExecutionStatus.INITIALIZING: ExecutionStatus.INITIALIZING,
            CoreExecutionStatus.RUNNING: ExecutionStatus.RUNNING,
            CoreExecutionStatus.COMPLETED: ExecutionStatus.COMPLETED,
            CoreExecutionStatus.FAILED: ExecutionStatus.FAILED,
            CoreExecutionStatus.CANCELLED: ExecutionStatus.CANCELLED,
        }

        status = status_mapping.get(getattr(core_result, "status", CoreExecutionStatus.RUNNING), ExecutionStatus.RUNNING)

        # Convert tasks
        tasks = []
        for task in getattr(core_result, "tasks", []):
            # Convert task status
            task_status_mapping = {
                "pending": TaskStatus.PENDING,
                "running": TaskStatus.RUNNING,
                "completed": TaskStatus.COMPLETED,
                "failed": TaskStatus.FAILED,
                "cancelled": TaskStatus.CANCELLED,
            }

            task_status = task_status_mapping.get(
                getattr(task, "status", "pending"),
                TaskStatus.PENDING
            )

            tasks.append(Task(
                id=getattr(task, "id", str(uuid.uuid4())),
                type=getattr(task, "type", "general"),
                description=getattr(task, "description", ""),
                status=task_status,
                agent_type=getattr(task, "agent_type", None),
                dependencies=getattr(task, "dependencies", []),
                started_at=getattr(task, "started_at", None),
                completed_at=getattr(task, "completed_at", None),
                result=getattr(task, "result", None),
                error=getattr(task, "error", None)
            ))

        # Convert agent results
        agent_results = []
        for agent_result in getattr(core_result, "agent_results", []):
            agent_results.append(AgentResult(
                agent_id=getattr(agent_result, "agent_id", str(uuid.uuid4())),
                agent_type=getattr(agent_result, "agent_type", "general"),
                tasks_completed=getattr(agent_result, "tasks_completed", []),
                outputs=getattr(agent_result, "outputs", {}),
                execution_time=getattr(agent_result, "execution_time", 0.0),
                success=getattr(agent_result, "success", True),
                error=getattr(agent_result, "error", None)
            ))

        # Create execution graph
        execution_graph = None
        if hasattr(core_result, "execution_graph"):
            execution_graph = ExecutionGraph(
                nodes=tasks,
                edges=getattr(core_result.execution_graph, "edges", []),
                critical_path=getattr(core_result.execution_graph, "critical_path", []),
                estimated_completion=getattr(core_result.execution_graph, "estimated_completion", None)
            )

        # Get execution metadata from tracking
        execution_data = self._active_executions.get(execution_id, {})

        return ExecutionResult(
            id=execution_id,
            specification_id=execution_data.get("specification_id", ""),
            status=status,
            tasks=tasks,
            agent_results=agent_results,
            execution_graph=execution_graph,
            outputs=getattr(core_result, "outputs", {}),
            metrics=getattr(core_result, "metrics", {}),
            started_at=execution_data.get("started_at", datetime.now()),
            completed_at=getattr(core_result, "completed_at", None),
            error=getattr(core_result, "error", None)
        )