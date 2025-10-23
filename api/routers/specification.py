"""
Specification router for Phase 2 endpoints.

Handles specification refinement through the SpecificationEngine service.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List
import logging

from api.schemas.request_schemas import SpecificationRequest
from api.schemas.response_schemas import (
    SpecificationResponse,
    RefinedSpecification,
    EdgeCase,
    Contradiction,
    BaseResponse
)
from api.services import SpecificationService, AnalyzerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/specify", tags=["specification"])


def get_specification_service() -> SpecificationService:
    """Dependency to get specification service."""
    from api.main import app
    session_manager = app.state.session_manager
    return SpecificationService(session_manager)


def get_analyzer_service() -> AnalyzerService:
    """Dependency to get analyzer service."""
    from api.main import app
    session_manager = app.state.session_manager
    return AnalyzerService(session_manager)


@router.post("/", response_model=SpecificationResponse)
async def create_specification(
    request: SpecificationRequest,
    specification_service: SpecificationService = Depends(get_specification_service),
    analyzer_service: AnalyzerService = Depends(get_analyzer_service)
):
    """
    Create a refined specification from analysis results.

    This endpoint uses Phase 2 of the Specify system to refine and enhance
    the analysis results with edge case detection, requirement compression,
    contradiction finding, and completeness validation.
    """
    try:
        logger.info(f"Creating specification for session {request.session_id}")

        # Get the analysis result
        analysis_result = await analyzer_service.get_analysis_result(request.analysis_result_id)
        if not analysis_result:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis result not found: {request.analysis_result_id}"
            )

        # Convert analysis result to dict for processing
        analysis_data = analysis_result.dict()

        # Create specification
        specification_id, result = await specification_service.refine_specification(
            analysis_result_id=request.analysis_result_id,
            analysis_result_data=analysis_data,
            mode=request.mode.value,
            session_id=request.session_id,
            custom_rules=request.custom_rules,
            focus_areas=request.focus_areas
        )

        return SpecificationResponse(
            success=True,
            message="Specification created successfully",
            session_id=request.session_id,
            specification_id=specification_id,
            result=result,
            status="completed" if result else "processing"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating specification: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Specification creation failed: {str(e)}"
        )


@router.get("/{specification_id}", response_model=RefinedSpecification)
async def get_specification(
    specification_id: str,
    specification_service: SpecificationService = Depends(get_specification_service)
):
    """
    Get a refined specification by ID.

    Returns the complete refined specification including compressed requirements,
    edge cases, contradictions, and completeness analysis.
    """
    try:
        result = await specification_service.get_specification_result(specification_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Specification not found: {specification_id}"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving specification: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve specification: {str(e)}"
        )


@router.get("/{specification_id}/status")
async def get_specification_status(
    specification_id: str,
    specification_service: SpecificationService = Depends(get_specification_service)
):
    """
    Get the status of a specification refinement operation.

    Returns status information including current state, timing, and any errors.
    """
    try:
        status = await specification_service.get_specification_status(specification_id)

        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Specification not found: {specification_id}"
            )

        return BaseResponse(
            success=True,
            message=f"Specification status: {status['status']}",
            session_id=status.get("session_id"),
            **status
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving specification status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve specification status: {str(e)}"
        )


@router.get("/{specification_id}/edge-cases", response_model=List[EdgeCase])
async def get_specification_edge_cases(
    specification_id: str,
    specification_service: SpecificationService = Depends(get_specification_service)
):
    """
    Get edge cases detected for a specification.

    Returns all edge cases found during specification analysis with
    categories, severity levels, and suggested handling approaches.
    """
    try:
        edge_cases = await specification_service.get_edge_cases(specification_id)
        return edge_cases

    except Exception as e:
        logger.exception(f"Error retrieving edge cases: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve edge cases: {str(e)}"
        )


@router.get("/{specification_id}/contradictions", response_model=List[Contradiction])
async def get_specification_contradictions(
    specification_id: str,
    specification_service: SpecificationService = Depends(get_specification_service)
):
    """
    Get contradictions found in a specification.

    Returns all contradictions detected between requirements with
    descriptions, severity levels, and resolution suggestions.
    """
    try:
        contradictions = await specification_service.get_contradictions(specification_id)
        return contradictions

    except Exception as e:
        logger.exception(f"Error retrieving contradictions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve contradictions: {str(e)}"
        )


@router.post("/{specification_id}/cancel")
async def cancel_specification(
    specification_id: str,
    specification_service: SpecificationService = Depends(get_specification_service)
):
    """
    Cancel a running specification refinement operation.

    This will attempt to cancel the specification refinement if it's still running.
    """
    try:
        success = await specification_service.cancel_specification(specification_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel specification {specification_id} - not found or already completed"
            )

        return BaseResponse(
            success=True,
            message=f"Specification {specification_id} cancelled successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error cancelling specification: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel specification: {str(e)}"
        )


@router.get("/session/{session_id}/specifications")
async def list_session_specifications(
    session_id: str,
    specification_service: SpecificationService = Depends(get_specification_service)
):
    """
    List all specifications for a specific session.

    Returns a list of specification operations with their status and metadata.
    """
    try:
        specifications = await specification_service.list_session_specifications(session_id)

        return BaseResponse(
            success=True,
            message=f"Found {len(specifications)} specifications for session {session_id}",
            session_id=session_id,
            specifications=specifications
        )

    except Exception as e:
        logger.exception(f"Error listing session specifications: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list session specifications: {str(e)}"
        )