"""
Refinement router for Phase 3 endpoints.

Handles interactive refinement through the RefinementLoop service.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import logging

from api.schemas.request_schemas import (
    RefinementStartRequest,
    RefinementDecisionRequest,
    RefinementModifyRequest,
    RefinementFinalizeRequest
)
from api.schemas.response_schemas import (
    RefinementResponse,
    RefinementSession,
    BaseResponse
)
from api.services import RefinementService, SpecificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/refinement", tags=["refinement"])


def get_refinement_service() -> RefinementService:
    """Dependency to get refinement service."""
    from api.main import app
    session_manager = app.state.session_manager
    return RefinementService(session_manager)


def get_specification_service() -> SpecificationService:
    """Dependency to get specification service."""
    from api.main import app
    session_manager = app.state.session_manager
    return SpecificationService(session_manager)


@router.post("/start", response_model=RefinementResponse)
async def start_refinement(
    request: RefinementStartRequest,
    refinement_service: RefinementService = Depends(get_refinement_service),
    specification_service: SpecificationService = Depends(get_specification_service)
):
    """
    Start an interactive refinement session.

    This endpoint initializes Phase 3 of the Specify system to begin
    interactive refinement of a specification with human feedback.
    """
    try:
        logger.info(f"Starting refinement for session {request.session_id}")

        # Get the specification
        specification = await specification_service.get_specification_result(request.specification_id)
        if not specification:
            raise HTTPException(
                status_code=404,
                detail=f"Specification not found: {request.specification_id}"
            )

        # Convert specification to dict for processing
        specification_data = specification.dict()

        # Start refinement session
        refinement_session_id, refinement_session = await refinement_service.start_refinement_session(
            specification_id=request.specification_id,
            specification_data=specification_data,
            session_id=request.session_id,
            interaction_mode=request.interaction_mode,
            auto_approve_threshold=request.auto_approve_threshold
        )

        # Get current suggestions
        current_iteration = refinement_session.iterations[-1] if refinement_session.iterations else None
        current_suggestions = current_iteration.suggestions if current_iteration else []

        return RefinementResponse(
            success=True,
            message="Refinement session started successfully",
            session_id=refinement_session_id,
            current_suggestions=current_suggestions,
            session_status=refinement_session.status,
            next_action="review_suggestions" if current_suggestions else "wait_for_suggestions"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error starting refinement: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Refinement startup failed: {str(e)}"
        )


@router.get("/{refinement_session_id}", response_model=RefinementSession)
async def get_refinement_session(
    refinement_session_id: str,
    refinement_service: RefinementService = Depends(get_refinement_service)
):
    """
    Get the current state of a refinement session.

    Returns the complete refinement session including all iterations,
    suggestions, and user decisions.
    """
    try:
        session = await refinement_service.get_refinement_session(refinement_session_id)

        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Refinement session not found: {refinement_session_id}"
            )

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving refinement session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve refinement session: {str(e)}"
        )


@router.post("/{refinement_session_id}/approve", response_model=RefinementResponse)
async def approve_suggestion(
    refinement_session_id: str,
    request: RefinementDecisionRequest,
    refinement_service: RefinementService = Depends(get_refinement_service)
):
    """
    Approve a refinement suggestion.

    Records the user's approval and continues the refinement process
    with the accepted suggestion.
    """
    try:
        updated_session = await refinement_service.approve_suggestion(
            refinement_session_id=refinement_session_id,
            suggestion_id=request.suggestion_id,
            feedback=request.feedback,
            reason=request.reason
        )

        if not updated_session:
            raise HTTPException(
                status_code=404,
                detail=f"Refinement session not found: {refinement_session_id}"
            )

        # Get current suggestions
        current_iteration = updated_session.iterations[-1] if updated_session.iterations else None
        current_suggestions = current_iteration.suggestions if current_iteration else []

        return RefinementResponse(
            success=True,
            message=f"Suggestion {request.suggestion_id} approved successfully",
            session_id=refinement_session_id,
            current_suggestions=current_suggestions,
            session_status=updated_session.status,
            next_action="review_suggestions" if current_suggestions else "finalize"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error approving suggestion: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to approve suggestion: {str(e)}"
        )


@router.post("/{refinement_session_id}/reject", response_model=RefinementResponse)
async def reject_suggestion(
    refinement_session_id: str,
    request: RefinementDecisionRequest,
    refinement_service: RefinementService = Depends(get_refinement_service)
):
    """
    Reject a refinement suggestion.

    Records the user's rejection and continues the refinement process
    without the rejected suggestion.
    """
    try:
        updated_session = await refinement_service.reject_suggestion(
            refinement_session_id=refinement_session_id,
            suggestion_id=request.suggestion_id,
            feedback=request.feedback,
            reason=request.reason
        )

        if not updated_session:
            raise HTTPException(
                status_code=404,
                detail=f"Refinement session not found: {refinement_session_id}"
            )

        # Get current suggestions
        current_iteration = updated_session.iterations[-1] if updated_session.iterations else None
        current_suggestions = current_iteration.suggestions if current_iteration else []

        return RefinementResponse(
            success=True,
            message=f"Suggestion {request.suggestion_id} rejected successfully",
            session_id=refinement_session_id,
            current_suggestions=current_suggestions,
            session_status=updated_session.status,
            next_action="review_suggestions" if current_suggestions else "finalize"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error rejecting suggestion: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reject suggestion: {str(e)}"
        )


@router.post("/{refinement_session_id}/modify", response_model=RefinementResponse)
async def modify_suggestion(
    refinement_session_id: str,
    request: RefinementModifyRequest,
    refinement_service: RefinementService = Depends(get_refinement_service)
):
    """
    Modify a refinement suggestion.

    Allows the user to modify a suggestion with their own content
    and continues the refinement process with the modified version.
    """
    try:
        updated_session = await refinement_service.modify_suggestion(
            refinement_session_id=refinement_session_id,
            suggestion_id=request.suggestion_id,
            modified_content=request.modified_content,
            reason=request.reason
        )

        if not updated_session:
            raise HTTPException(
                status_code=404,
                detail=f"Refinement session not found: {refinement_session_id}"
            )

        # Get current suggestions
        current_iteration = updated_session.iterations[-1] if updated_session.iterations else None
        current_suggestions = current_iteration.suggestions if current_iteration else []

        return RefinementResponse(
            success=True,
            message=f"Suggestion {request.suggestion_id} modified successfully",
            session_id=refinement_session_id,
            current_suggestions=current_suggestions,
            session_status=updated_session.status,
            next_action="review_suggestions" if current_suggestions else "finalize"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error modifying suggestion: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to modify suggestion: {str(e)}"
        )


@router.post("/{refinement_session_id}/finalize")
async def finalize_refinement(
    refinement_session_id: str,
    request: RefinementFinalizeRequest,
    refinement_service: RefinementService = Depends(get_refinement_service)
):
    """
    Finalize a refinement session.

    Completes the refinement process and produces a finalized specification
    incorporating all approved suggestions and user modifications.
    """
    try:
        finalized_spec = await refinement_service.finalize_refinement(
            refinement_session_id=refinement_session_id,
            include_rejected=request.include_rejected,
            final_notes=request.final_notes
        )

        if not finalized_spec:
            raise HTTPException(
                status_code=404,
                detail=f"Refinement session not found: {refinement_session_id}"
            )

        return BaseResponse(
            success=True,
            message="Refinement session finalized successfully",
            session_id=request.session_id,
            finalized_specification=finalized_spec
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error finalizing refinement: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to finalize refinement: {str(e)}"
        )


@router.post("/{refinement_session_id}/cancel")
async def cancel_refinement(
    refinement_session_id: str,
    refinement_service: RefinementService = Depends(get_refinement_service)
):
    """
    Cancel a refinement session.

    Cancels the ongoing refinement process and cleans up resources.
    """
    try:
        success = await refinement_service.cancel_refinement(refinement_session_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel refinement {refinement_session_id} - not found or already completed"
            )

        return BaseResponse(
            success=True,
            message=f"Refinement session {refinement_session_id} cancelled successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error cancelling refinement: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel refinement: {str(e)}"
        )