"""
Refinement service that wraps Phase 3 of the Specify system.

Provides a service layer interface for interactive refinement with proper
error handling, logging, and session management.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

# Import Phase 3 components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from src.refinement import (
    RefinementLoop,
    RefinementSession as CoreRefinementSession,
    UserDecision as CoreUserDecision,
    UserDecisionAction,
    FinalizedSpecification
)
from src.engine.models import RefinedSpecification as CoreRefinedSpecification
from api.schemas.response_schemas import (
    RefinementSession,
    RefinementSuggestion,
    UserDecision,
    RefinementIteration
)
from api.services.session_manager import SessionManager

logger = logging.getLogger(__name__)


class RefinementService:
    """Service wrapper for the refinement loop (Phase 3)."""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self._active_refinements: Dict[str, Dict[str, Any]] = {}
        self._refinement_loops: Dict[str, RefinementLoop] = {}

    async def start_refinement_session(
        self,
        specification_id: str,
        specification_data: Dict[str, Any],
        session_id: Optional[str] = None,
        interaction_mode: str = "interactive",
        auto_approve_threshold: Optional[float] = None
    ) -> tuple[str, RefinementSession]:
        """
        Start a new refinement session.

        Args:
            specification_id: ID of the specification to refine
            specification_data: Specification data
            session_id: Optional session ID for tracking
            interaction_mode: Mode for refinement interaction
            auto_approve_threshold: Threshold for auto-approval

        Returns:
            Tuple of (refinement_session_id, refinement_session)
        """
        refinement_session_id = str(uuid.uuid4())

        logger.info(f"Starting refinement session {refinement_session_id} for session {session_id}")

        # Track refinement in session if provided
        if session_id:
            await self.session_manager.add_operation(session_id, f"refinement:{refinement_session_id}")

        try:
            # Convert specification data to core format
            core_specification = self._convert_to_core_specification(specification_data)

            # Create refinement loop
            refinement_loop = RefinementLoop()
            self._refinement_loops[refinement_session_id] = refinement_loop

            # Start refinement session
            core_session = await self._start_core_refinement(
                refinement_loop,
                core_specification,
                interaction_mode,
                auto_approve_threshold
            )

            # Convert to API format
            api_session = self._convert_refinement_session(refinement_session_id, core_session)

            # Store refinement metadata
            self._active_refinements[refinement_session_id] = {
                "id": refinement_session_id,
                "session_id": session_id,
                "specification_id": specification_id,
                "interaction_mode": interaction_mode,
                "auto_approve_threshold": auto_approve_threshold,
                "status": "active",
                "started_at": datetime.now(),
                "core_session": core_session,
                "api_session": api_session
            }

            logger.info(f"Started refinement session {refinement_session_id}")

            return refinement_session_id, api_session

        except Exception as e:
            logger.exception(f"Error starting refinement session {refinement_session_id}: {e}")

            # Remove from session operations
            if session_id:
                await self.session_manager.remove_operation(session_id, f"refinement:{refinement_session_id}")

            raise

    async def get_refinement_session(self, refinement_session_id: str) -> Optional[RefinementSession]:
        """
        Get refinement session by ID.

        Args:
            refinement_session_id: Refinement session ID

        Returns:
            Refinement session or None if not found
        """
        refinement_data = self._active_refinements.get(refinement_session_id)
        if not refinement_data:
            return None

        return refinement_data["api_session"]

    async def approve_suggestion(
        self,
        refinement_session_id: str,
        suggestion_id: str,
        feedback: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Optional[RefinementSession]:
        """
        Approve a refinement suggestion.

        Args:
            refinement_session_id: Refinement session ID
            suggestion_id: Suggestion ID to approve
            feedback: Optional feedback
            reason: Optional reason for approval

        Returns:
            Updated refinement session or None if not found
        """
        refinement_data = self._active_refinements.get(refinement_session_id)
        if not refinement_data:
            return None

        try:
            # Create user decision
            user_decision = CoreUserDecision(
                suggestion_id=suggestion_id,
                action=UserDecisionAction.APPROVE,
                feedback=feedback,
                reason=reason
            )

            # Process decision through core refinement loop
            refinement_loop = self._refinement_loops.get(refinement_session_id)
            if refinement_loop:
                core_session = await self._process_user_decision(
                    refinement_loop,
                    refinement_data["core_session"],
                    user_decision
                )

                # Update API session
                api_session = self._convert_refinement_session(refinement_session_id, core_session)
                refinement_data["core_session"] = core_session
                refinement_data["api_session"] = api_session

                logger.info(f"Approved suggestion {suggestion_id} in session {refinement_session_id}")

                return api_session

        except Exception as e:
            logger.exception(f"Error approving suggestion {suggestion_id}: {e}")
            raise

        return None

    async def reject_suggestion(
        self,
        refinement_session_id: str,
        suggestion_id: str,
        feedback: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Optional[RefinementSession]:
        """
        Reject a refinement suggestion.

        Args:
            refinement_session_id: Refinement session ID
            suggestion_id: Suggestion ID to reject
            feedback: Optional feedback
            reason: Optional reason for rejection

        Returns:
            Updated refinement session or None if not found
        """
        refinement_data = self._active_refinements.get(refinement_session_id)
        if not refinement_data:
            return None

        try:
            # Create user decision
            user_decision = CoreUserDecision(
                suggestion_id=suggestion_id,
                action=UserDecisionAction.REJECT,
                feedback=feedback,
                reason=reason
            )

            # Process decision through core refinement loop
            refinement_loop = self._refinement_loops.get(refinement_session_id)
            if refinement_loop:
                core_session = await self._process_user_decision(
                    refinement_loop,
                    refinement_data["core_session"],
                    user_decision
                )

                # Update API session
                api_session = self._convert_refinement_session(refinement_session_id, core_session)
                refinement_data["core_session"] = core_session
                refinement_data["api_session"] = api_session

                logger.info(f"Rejected suggestion {suggestion_id} in session {refinement_session_id}")

                return api_session

        except Exception as e:
            logger.exception(f"Error rejecting suggestion {suggestion_id}: {e}")
            raise

        return None

    async def modify_suggestion(
        self,
        refinement_session_id: str,
        suggestion_id: str,
        modified_content: str,
        reason: Optional[str] = None
    ) -> Optional[RefinementSession]:
        """
        Modify a refinement suggestion.

        Args:
            refinement_session_id: Refinement session ID
            suggestion_id: Suggestion ID to modify
            modified_content: Modified content
            reason: Optional reason for modification

        Returns:
            Updated refinement session or None if not found
        """
        refinement_data = self._active_refinements.get(refinement_session_id)
        if not refinement_data:
            return None

        try:
            # Create user decision with modification
            user_decision = CoreUserDecision(
                suggestion_id=suggestion_id,
                action=UserDecisionAction.MODIFY,
                feedback=modified_content,
                reason=reason
            )

            # Process decision through core refinement loop
            refinement_loop = self._refinement_loops.get(refinement_session_id)
            if refinement_loop:
                core_session = await self._process_user_decision(
                    refinement_loop,
                    refinement_data["core_session"],
                    user_decision
                )

                # Update API session
                api_session = self._convert_refinement_session(refinement_session_id, core_session)
                refinement_data["core_session"] = core_session
                refinement_data["api_session"] = api_session

                logger.info(f"Modified suggestion {suggestion_id} in session {refinement_session_id}")

                return api_session

        except Exception as e:
            logger.exception(f"Error modifying suggestion {suggestion_id}: {e}")
            raise

        return None

    async def finalize_refinement(
        self,
        refinement_session_id: str,
        include_rejected: bool = False,
        final_notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Finalize a refinement session.

        Args:
            refinement_session_id: Refinement session ID
            include_rejected: Include rejected suggestions
            final_notes: Final notes for the specification

        Returns:
            Finalized specification data or None if not found
        """
        refinement_data = self._active_refinements.get(refinement_session_id)
        if not refinement_data:
            return None

        try:
            # Finalize through core refinement loop
            refinement_loop = self._refinement_loops.get(refinement_session_id)
            if refinement_loop:
                finalized_spec = await self._finalize_core_refinement(
                    refinement_loop,
                    refinement_data["core_session"],
                    include_rejected,
                    final_notes
                )

                # Update status
                refinement_data.update({
                    "status": "finalized",
                    "completed_at": datetime.now(),
                    "finalized_specification": finalized_spec
                })

                # Remove from session operations
                session_id = refinement_data.get("session_id")
                if session_id:
                    await self.session_manager.remove_operation(session_id, f"refinement:{refinement_session_id}")

                logger.info(f"Finalized refinement session {refinement_session_id}")

                return self._convert_finalized_specification(finalized_spec)

        except Exception as e:
            logger.exception(f"Error finalizing refinement session {refinement_session_id}: {e}")
            raise

        return None

    async def cancel_refinement(self, refinement_session_id: str) -> bool:
        """
        Cancel a refinement session.

        Args:
            refinement_session_id: Refinement session ID

        Returns:
            True if cancelled, False if not found or already completed
        """
        refinement_data = self._active_refinements.get(refinement_session_id)
        if not refinement_data or refinement_data["status"] != "active":
            return False

        # Update status
        refinement_data.update({
            "status": "cancelled",
            "completed_at": datetime.now()
        })

        # Clean up refinement loop
        if refinement_session_id in self._refinement_loops:
            del self._refinement_loops[refinement_session_id]

        # Remove from session operations
        session_id = refinement_data.get("session_id")
        if session_id:
            await self.session_manager.remove_operation(session_id, f"refinement:{refinement_session_id}")

        logger.info(f"Cancelled refinement session {refinement_session_id}")
        return True

    async def _start_core_refinement(
        self,
        refinement_loop: RefinementLoop,
        specification: CoreRefinedSpecification,
        interaction_mode: str,
        auto_approve_threshold: Optional[float]
    ) -> CoreRefinementSession:
        """
        Start core refinement session.

        Args:
            refinement_loop: Refinement loop instance
            specification: Core specification
            interaction_mode: Interaction mode
            auto_approve_threshold: Auto-approval threshold

        Returns:
            Core refinement session
        """
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        session = await loop.run_in_executor(
            None,
            refinement_loop.start_refinement,
            specification
        )

        return session

    async def _process_user_decision(
        self,
        refinement_loop: RefinementLoop,
        session: CoreRefinementSession,
        decision: CoreUserDecision
    ) -> CoreRefinementSession:
        """
        Process user decision through core refinement loop.

        Args:
            refinement_loop: Refinement loop instance
            session: Core refinement session
            decision: User decision

        Returns:
            Updated core refinement session
        """
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        updated_session = await loop.run_in_executor(
            None,
            refinement_loop.process_decision,
            session,
            decision
        )

        return updated_session

    async def _finalize_core_refinement(
        self,
        refinement_loop: RefinementLoop,
        session: CoreRefinementSession,
        include_rejected: bool,
        final_notes: Optional[str]
    ) -> FinalizedSpecification:
        """
        Finalize core refinement session.

        Args:
            refinement_loop: Refinement loop instance
            session: Core refinement session
            include_rejected: Include rejected suggestions
            final_notes: Final notes

        Returns:
            Finalized specification
        """
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        finalized = await loop.run_in_executor(
            None,
            refinement_loop.finalize,
            session,
            include_rejected
        )

        return finalized

    def _convert_to_core_specification(self, specification_data: Dict[str, Any]) -> CoreRefinedSpecification:
        """
        Convert API specification data to core format.

        Args:
            specification_data: Specification data from API

        Returns:
            Core refined specification
        """
        # This is a simplified conversion - in practice, you would need
        # to properly reconstruct the core data structures
        return CoreRefinedSpecification(
            # Map the API data to core fields
            # This would need to be implemented based on the actual core structure
        )

    def _convert_refinement_session(
        self,
        session_id: str,
        core_session: CoreRefinementSession
    ) -> RefinementSession:
        """
        Convert core refinement session to API format.

        Args:
            session_id: Session ID
            core_session: Core refinement session

        Returns:
            API refinement session
        """
        # Convert iterations
        iterations = []
        for iteration in getattr(core_session, "iterations", []):
            # Convert suggestions
            suggestions = []
            for suggestion in getattr(iteration, "suggestions", []):
                suggestions.append(RefinementSuggestion(
                    id=getattr(suggestion, "id", str(uuid.uuid4())),
                    type=getattr(suggestion, "type", "improvement"),
                    title=getattr(suggestion, "title", "Suggestion"),
                    description=getattr(suggestion, "description", ""),
                    impact=getattr(suggestion, "impact", "medium"),
                    confidence=getattr(suggestion, "confidence", 0.8),
                    suggested_changes=getattr(suggestion, "suggested_changes", []),
                    reasoning=getattr(suggestion, "reasoning", "")
                ))

            # Convert user decisions
            decisions = []
            for decision in getattr(iteration, "user_decisions", []):
                decisions.append(UserDecision(
                    suggestion_id=getattr(decision, "suggestion_id", ""),
                    action=getattr(decision, "action", "approve"),
                    feedback=getattr(decision, "feedback", None),
                    timestamp=getattr(decision, "timestamp", datetime.now())
                ))

            iterations.append(RefinementIteration(
                iteration_number=getattr(iteration, "iteration_number", 1),
                suggestions=suggestions,
                user_decisions=decisions,
                completed_at=getattr(iteration, "completed_at", None)
            ))

        return RefinementSession(
            id=session_id,
            specification_id=getattr(core_session, "specification_id", ""),
            iterations=iterations,
            current_iteration=getattr(core_session, "current_iteration", 1),
            status=getattr(core_session, "status", "active"),
            finalized_specification=getattr(core_session, "finalized_specification", None),
            started_at=getattr(core_session, "started_at", datetime.now()),
            completed_at=getattr(core_session, "completed_at", None)
        )

    def _convert_finalized_specification(self, finalized_spec: FinalizedSpecification) -> Dict[str, Any]:
        """
        Convert finalized specification to API format.

        Args:
            finalized_spec: Core finalized specification

        Returns:
            API finalized specification data
        """
        return {
            "id": str(uuid.uuid4()),
            "title": getattr(finalized_spec, "title", "Finalized Specification"),
            "content": getattr(finalized_spec, "content", ""),
            "approved_suggestions": getattr(finalized_spec, "approved_suggestions", []),
            "rejected_suggestions": getattr(finalized_spec, "rejected_suggestions", []),
            "final_notes": getattr(finalized_spec, "final_notes", ""),
            "created_at": datetime.now().isoformat(),
            "metadata": getattr(finalized_spec, "metadata", {})
        }