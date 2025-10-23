"""
Analyzer router for Phase 1 endpoints.

Handles prompt analysis through the PromptAnalyzer service.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Optional
import logging

from api.schemas.request_schemas import AnalyzePromptRequest
from api.schemas.response_schemas import (
    AnalyzeResponse,
    AnalysisResult,
    BaseResponse,
    ErrorResponse
)
from api.services import AnalyzerService, SessionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["analyzer"])


def get_analyzer_service() -> AnalyzerService:
    """Dependency to get analyzer service."""
    from api.main import app
    session_manager = app.state.session_manager
    return AnalyzerService(session_manager)


@router.post("/", response_model=AnalyzeResponse)
async def analyze_prompt(
    request: AnalyzePromptRequest,
    analyzer_service: AnalyzerService = Depends(get_analyzer_service)
):
    """
    Analyze a prompt to extract intent, requirements, assumptions, and ambiguities.

    This endpoint uses Phase 1 of the Specify system to perform multi-pass
    analysis of the provided prompt.
    """
    try:
        logger.info(f"Analyzing prompt for session {request.session_id}")

        # Analyze the prompt
        analysis_id, result = await analyzer_service.analyze_prompt(
            prompt=request.prompt,
            session_id=request.session_id,
            analysis_options=request.analysis_options,
            user_context=request.user_context
        )

        return AnalyzeResponse(
            success=True,
            message="Prompt analysis completed successfully",
            session_id=request.session_id,
            analysis_id=analysis_id,
            result=result,
            status="completed" if result else "processing"
        )

    except Exception as e:
        logger.exception(f"Error analyzing prompt: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get("/{analysis_id}", response_model=AnalysisResult)
async def get_analysis_result(
    analysis_id: str,
    analyzer_service: AnalyzerService = Depends(get_analyzer_service)
):
    """
    Get the result of a prompt analysis by analysis ID.

    Returns the complete analysis result including intent, requirements,
    assumptions, and ambiguities.
    """
    try:
        result = await analyzer_service.get_analysis_result(analysis_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis result not found for ID: {analysis_id}"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving analysis result: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analysis result: {str(e)}"
        )


@router.get("/{analysis_id}/status")
async def get_analysis_status(
    analysis_id: str,
    analyzer_service: AnalyzerService = Depends(get_analyzer_service)
):
    """
    Get the status of an analysis operation.

    Returns status information including current state, timing, and any errors.
    """
    try:
        status = await analyzer_service.get_analysis_status(analysis_id)

        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis not found for ID: {analysis_id}"
            )

        return BaseResponse(
            success=True,
            message=f"Analysis status: {status['status']}",
            session_id=status.get("session_id"),
            **status
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving analysis status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analysis status: {str(e)}"
        )


@router.post("/{analysis_id}/cancel")
async def cancel_analysis(
    analysis_id: str,
    analyzer_service: AnalyzerService = Depends(get_analyzer_service)
):
    """
    Cancel a running analysis operation.

    This will attempt to cancel the analysis if it's still running.
    """
    try:
        success = await analyzer_service.cancel_analysis(analysis_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel analysis {analysis_id} - not found or already completed"
            )

        return BaseResponse(
            success=True,
            message=f"Analysis {analysis_id} cancelled successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error cancelling analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel analysis: {str(e)}"
        )


@router.get("/session/{session_id}/analyses")
async def list_session_analyses(
    session_id: str,
    analyzer_service: AnalyzerService = Depends(get_analyzer_service)
):
    """
    List all analyses for a specific session.

    Returns a list of analysis operations with their status and metadata.
    """
    try:
        analyses = await analyzer_service.list_session_analyses(session_id)

        return BaseResponse(
            success=True,
            message=f"Found {len(analyses)} analyses for session {session_id}",
            session_id=session_id,
            analyses=analyses
        )

    except Exception as e:
        logger.exception(f"Error listing session analyses: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list session analyses: {str(e)}"
        )


# Background task for cleanup
async def cleanup_analyses_task(analyzer_service: AnalyzerService):
    """Background task to clean up old analyses."""
    try:
        cleaned = await analyzer_service.cleanup_completed_analyses()
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old analyses")
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")


@router.post("/cleanup", include_in_schema=False)
async def trigger_cleanup(
    background_tasks: BackgroundTasks,
    analyzer_service: AnalyzerService = Depends(get_analyzer_service)
):
    """
    Trigger cleanup of old completed analyses.

    This is an internal endpoint for maintenance purposes.
    """
    background_tasks.add_task(cleanup_analyses_task, analyzer_service)

    return BaseResponse(
        success=True,
        message="Cleanup task started"
    )