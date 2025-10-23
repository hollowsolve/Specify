"""
Dispatch router for Phase 4 endpoints.

Handles agent execution through the AgentDispatcher service.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging

from api.schemas.request_schemas import (
    DispatchExecutionRequest,
    DispatchCancelRequest
)
from api.schemas.response_schemas import (
    DispatchResponse,
    ExecutionResult,
    ExecutionGraph,
    BaseResponse
)
from api.services import DispatchService, RefinementService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dispatch", tags=["dispatch"])


def get_dispatch_service() -> DispatchService:
    """Dependency to get dispatch service."""
    from api.main import app
    session_manager = app.state.session_manager
    return DispatchService(session_manager)


def get_refinement_service() -> RefinementService:
    """Dependency to get refinement service."""
    from api.main import app
    session_manager = app.state.session_manager
    return RefinementService(session_manager)


@router.post("/execute", response_model=DispatchResponse)
async def start_execution(
    request: DispatchExecutionRequest,
    dispatch_service: DispatchService = Depends(get_dispatch_service),
    refinement_service: RefinementService = Depends(get_refinement_service)
):
    """
    Start agent execution for a finalized specification.

    This endpoint initializes Phase 4 of the Specify system to execute
    the finalized specification using coordinated multi-agent execution.
    """
    try:
        logger.info(f"Starting execution for session {request.session_id}")

        # For this example, we'll assume the specification_id refers to a finalized specification
        # In practice, you might need to get it from the refinement service or have a separate
        # finalized specifications storage

        # Mock specification data - in practice, retrieve from refinement service
        specification_data = {
            "id": request.specification_id,
            "title": "Finalized Specification",
            "requirements": [],
            "implementation_plan": {},
            "metadata": {}
        }

        # Start execution
        execution_id, execution_result = await dispatch_service.start_execution(
            specification_id=request.specification_id,
            specification_data=specification_data,
            execution_mode=request.execution_mode.value,
            session_id=request.session_id,
            agent_constraints=request.agent_constraints,
            target_platform=request.target_platform,
            output_format=request.output_format
        )

        # Calculate progress
        total_tasks = len(execution_result.tasks) if execution_result.tasks else 1
        completed_tasks = len([t for t in execution_result.tasks if t.status.value == "completed"]) if execution_result.tasks else 0
        progress_percentage = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0

        return DispatchResponse(
            success=True,
            message="Execution started successfully",
            session_id=request.session_id,
            execution_id=execution_id,
            status=execution_result.status,
            current_tasks=[t for t in execution_result.tasks if t.status.value == "running"],
            progress_percentage=progress_percentage,
            estimated_completion=execution_result.execution_graph.estimated_completion if execution_result.execution_graph else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error starting execution: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Execution startup failed: {str(e)}"
        )


@router.get("/{execution_id}/status", response_model=ExecutionResult)
async def get_execution_status(
    execution_id: str,
    dispatch_service: DispatchService = Depends(get_dispatch_service)
):
    """
    Get the current status of an execution.

    Returns the complete execution state including task progress,
    agent results, and current status.
    """
    try:
        result = await dispatch_service.get_execution_status(execution_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Execution not found: {execution_id}"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving execution status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve execution status: {str(e)}"
        )


@router.get("/{execution_id}/graph", response_model=ExecutionGraph)
async def get_execution_graph(
    execution_id: str,
    dispatch_service: DispatchService = Depends(get_dispatch_service)
):
    """
    Get the execution DAG for visualization.

    Returns the task dependency graph showing the relationships
    between tasks and their execution order.
    """
    try:
        graph = await dispatch_service.get_execution_graph(execution_id)

        if not graph:
            raise HTTPException(
                status_code=404,
                detail=f"Execution graph not found: {execution_id}"
            )

        return graph

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving execution graph: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve execution graph: {str(e)}"
        )


@router.get("/{execution_id}/results")
async def get_execution_results(
    execution_id: str,
    dispatch_service: DispatchService = Depends(get_dispatch_service)
):
    """
    Get the final results of a completed execution.

    Returns the outputs and artifacts produced by the agent execution,
    only available after the execution has completed successfully.
    """
    try:
        results = await dispatch_service.get_execution_results(execution_id)

        if results is None:
            # Check if execution exists
            status = await dispatch_service.get_execution_status(execution_id)
            if not status:
                raise HTTPException(
                    status_code=404,
                    detail=f"Execution not found: {execution_id}"
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Execution {execution_id} is not yet completed"
                )

        return BaseResponse(
            success=True,
            message="Execution results retrieved successfully",
            execution_id=execution_id,
            results=results
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving execution results: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve execution results: {str(e)}"
        )


@router.post("/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    request: DispatchCancelRequest,
    dispatch_service: DispatchService = Depends(get_dispatch_service)
):
    """
    Cancel a running execution.

    Attempts to gracefully stop all running agents and clean up resources.
    """
    try:
        success = await dispatch_service.cancel_execution(execution_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel execution {execution_id} - not found or already completed"
            )

        return BaseResponse(
            success=True,
            message=f"Execution {execution_id} cancelled successfully",
            session_id=request.session_id,
            cancellation_reason=request.reason
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error cancelling execution: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel execution: {str(e)}"
        )


@router.get("/session/{session_id}/executions")
async def list_session_executions(
    session_id: str,
    dispatch_service: DispatchService = Depends(get_dispatch_service)
):
    """
    List all executions for a specific session.

    Returns a list of execution operations with their status and metadata.
    """
    try:
        executions = await dispatch_service.list_session_executions(session_id)

        return BaseResponse(
            success=True,
            message=f"Found {len(executions)} executions for session {session_id}",
            session_id=session_id,
            executions=executions
        )

    except Exception as e:
        logger.exception(f"Error listing session executions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list session executions: {str(e)}"
        )


@router.get("/{execution_id}/progress")
async def get_execution_progress(
    execution_id: str,
    dispatch_service: DispatchService = Depends(get_dispatch_service)
):
    """
    Get detailed progress information for an execution.

    Returns progress metrics, timing estimates, and current activity.
    """
    try:
        status = await dispatch_service.get_execution_status(execution_id)

        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Execution not found: {execution_id}"
            )

        # Calculate detailed progress metrics
        total_tasks = len(status.tasks)
        completed_tasks = len([t for t in status.tasks if t.status.value == "completed"])
        running_tasks = len([t for t in status.tasks if t.status.value == "running"])
        failed_tasks = len([t for t in status.tasks if t.status.value == "failed"])

        progress_percentage = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0

        return BaseResponse(
            success=True,
            message="Execution progress retrieved successfully",
            execution_id=execution_id,
            progress={
                "percentage": progress_percentage,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "running_tasks": running_tasks,
                "failed_tasks": failed_tasks,
                "status": status.status.value,
                "started_at": status.started_at.isoformat(),
                "estimated_completion": status.execution_graph.estimated_completion.isoformat() if status.execution_graph and status.execution_graph.estimated_completion else None
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving execution progress: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve execution progress: {str(e)}"
        )