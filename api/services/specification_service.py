"""
Specification service that wraps Phase 2 of the Specify system.

Provides a service layer interface for specification refinement with proper
error handling, logging, and session management.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Import Phase 2 components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from src.engine import (
    SpecificationEngine,
    RefinedSpecification as CoreRefinedSpecification,
    ProcessorMode
)
from src.analyzer.models import AnalysisResult as CoreAnalysisResult
from api.schemas.response_schemas import (
    RefinedSpecification,
    EdgeCase,
    Contradiction,
    CompressedRequirement
)
from api.services.session_manager import SessionManager

logger = logging.getLogger(__name__)


class SpecificationService:
    """Service wrapper for the specification engine (Phase 2)."""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.engine = SpecificationEngine()
        self._active_specifications: Dict[str, Dict[str, Any]] = {}

    async def refine_specification(
        self,
        analysis_result_id: str,
        analysis_result_data: Dict[str, Any],
        mode: str = "balanced",
        session_id: Optional[str] = None,
        custom_rules: Optional[List[str]] = None,
        focus_areas: Optional[List[str]] = None
    ) -> tuple[str, Optional[RefinedSpecification]]:
        """
        Refine a specification from analysis result.

        Args:
            analysis_result_id: ID of the analysis result
            analysis_result_data: Analysis result data
            mode: Processing mode (fast, balanced, intelligent)
            session_id: Optional session ID for tracking
            custom_rules: Custom rules to apply
            focus_areas: Specific areas to focus on

        Returns:
            Tuple of (specification_id, refined_specification)
        """
        specification_id = str(uuid.uuid4())

        logger.info(f"Starting specification refinement {specification_id} for session {session_id}")

        # Track specification in session if provided
        if session_id:
            await self.session_manager.add_operation(session_id, f"specification:{specification_id}")

        # Store specification metadata
        self._active_specifications[specification_id] = {
            "id": specification_id,
            "session_id": session_id,
            "analysis_result_id": analysis_result_id,
            "mode": mode,
            "custom_rules": custom_rules or [],
            "focus_areas": focus_areas or [],
            "status": "running",
            "started_at": datetime.now(),
            "result": None,
            "error": None
        }

        try:
            # Convert analysis result data to core format
            core_analysis_result = self._convert_to_core_analysis_result(analysis_result_data)

            # Configure engine for this processing mode
            await self._configure_engine(mode, custom_rules, focus_areas)

            # Run specification refinement
            result = await self._run_refinement(core_analysis_result)

            # Convert core result to API schema
            api_result = self._convert_specification_result(specification_id, result)

            # Update tracking
            self._active_specifications[specification_id].update({
                "status": "completed",
                "completed_at": datetime.now(),
                "result": api_result
            })

            logger.info(f"Completed specification refinement {specification_id}")

            # Remove from session operations
            if session_id:
                await self.session_manager.remove_operation(session_id, f"specification:{specification_id}")

            return specification_id, api_result

        except Exception as e:
            logger.exception(f"Error in specification refinement {specification_id}: {e}")

            # Update tracking with error
            self._active_specifications[specification_id].update({
                "status": "failed",
                "completed_at": datetime.now(),
                "error": str(e)
            })

            # Remove from session operations
            if session_id:
                await self.session_manager.remove_operation(session_id, f"specification:{specification_id}")

            raise

    async def get_specification_result(self, specification_id: str) -> Optional[RefinedSpecification]:
        """
        Get specification result by ID.

        Args:
            specification_id: Specification ID

        Returns:
            Refined specification or None if not found/not completed
        """
        spec_data = self._active_specifications.get(specification_id)
        if not spec_data:
            return None

        if spec_data["status"] == "completed":
            return spec_data["result"]

        return None

    async def get_specification_status(self, specification_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specification status and metadata.

        Args:
            specification_id: Specification ID

        Returns:
            Specification status info or None if not found
        """
        spec_data = self._active_specifications.get(specification_id)
        if not spec_data:
            return None

        return {
            "id": spec_data["id"],
            "session_id": spec_data["session_id"],
            "analysis_result_id": spec_data["analysis_result_id"],
            "mode": spec_data["mode"],
            "status": spec_data["status"],
            "started_at": spec_data["started_at"],
            "completed_at": spec_data.get("completed_at"),
            "error": spec_data.get("error")
        }

    async def get_edge_cases(self, specification_id: str) -> List[EdgeCase]:
        """
        Get edge cases for a specification.

        Args:
            specification_id: Specification ID

        Returns:
            List of edge cases
        """
        result = await self.get_specification_result(specification_id)
        if result:
            return result.edge_cases
        return []

    async def get_contradictions(self, specification_id: str) -> List[Contradiction]:
        """
        Get contradictions for a specification.

        Args:
            specification_id: Specification ID

        Returns:
            List of contradictions
        """
        result = await self.get_specification_result(specification_id)
        if result:
            return result.contradictions
        return []

    async def cancel_specification(self, specification_id: str) -> bool:
        """
        Cancel a running specification refinement.

        Args:
            specification_id: Specification ID

        Returns:
            True if cancelled, False if not found or already completed
        """
        spec_data = self._active_specifications.get(specification_id)
        if not spec_data or spec_data["status"] != "running":
            return False

        # Update status
        spec_data.update({
            "status": "cancelled",
            "completed_at": datetime.now()
        })

        # Remove from session operations
        session_id = spec_data.get("session_id")
        if session_id:
            await self.session_manager.remove_operation(session_id, f"specification:{specification_id}")

        logger.info(f"Cancelled specification {specification_id}")
        return True

    async def list_session_specifications(self, session_id: str) -> List[Dict[str, Any]]:
        """
        List all specifications for a session.

        Args:
            session_id: Session ID

        Returns:
            List of specification status info
        """
        specifications = []
        for spec_data in self._active_specifications.values():
            if spec_data.get("session_id") == session_id:
                specifications.append({
                    "id": spec_data["id"],
                    "analysis_result_id": spec_data["analysis_result_id"],
                    "mode": spec_data["mode"],
                    "status": spec_data["status"],
                    "started_at": spec_data["started_at"],
                    "completed_at": spec_data.get("completed_at"),
                    "error": spec_data.get("error")
                })

        return sorted(specifications, key=lambda x: x["started_at"], reverse=True)

    async def _configure_engine(
        self,
        mode: str,
        custom_rules: Optional[List[str]] = None,
        focus_areas: Optional[List[str]] = None
    ):
        """
        Configure the specification engine for processing.

        Args:
            mode: Processing mode
            custom_rules: Custom rules to apply
            focus_areas: Specific areas to focus on
        """
        # Map mode to ProcessorMode enum
        mode_mapping = {
            "fast": ProcessorMode.FAST,
            "balanced": ProcessorMode.BALANCED,
            "intelligent": ProcessorMode.INTELLIGENT
        }

        processor_mode = mode_mapping.get(mode, ProcessorMode.BALANCED)

        # Configure engine (this would typically involve setting processor configurations)
        # For now, we'll use the engine as-is since the current implementation
        # handles configuration internally

    async def _run_refinement(
        self,
        analysis_result: CoreAnalysisResult
    ) -> CoreRefinedSpecification:
        """
        Run the actual specification refinement.

        Args:
            analysis_result: Core analysis result

        Returns:
            Core refined specification
        """
        # Run refinement in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.engine.refine_specification,
            analysis_result
        )

        return result

    def _convert_to_core_analysis_result(self, analysis_data: Dict[str, Any]) -> CoreAnalysisResult:
        """
        Convert API analysis result data to core format.

        Args:
            analysis_data: Analysis result data from API

        Returns:
            Core analysis result
        """
        # Create a core analysis result from the API data
        # This is a simplified conversion - in practice, you might need
        # to handle more complex data structures
        return CoreAnalysisResult(
            intent=analysis_data.get("intent", ""),
            requirements=analysis_data.get("requirements", []),
            assumptions=analysis_data.get("assumptions", []),
            ambiguities=analysis_data.get("ambiguities", []),
            metadata=analysis_data.get("metadata", {})
        )

    def _convert_specification_result(
        self,
        specification_id: str,
        core_result: CoreRefinedSpecification
    ) -> RefinedSpecification:
        """
        Convert core specification result to API schema.

        Args:
            specification_id: Specification ID
            core_result: Core refined specification

        Returns:
            API refined specification
        """
        # Convert edge cases
        edge_cases = []
        for edge_case in getattr(core_result, "edge_cases", []):
            edge_cases.append(EdgeCase(
                id=str(uuid.uuid4()),
                category=getattr(edge_case, "category", "general"),
                description=getattr(edge_case, "description", str(edge_case)),
                severity=getattr(edge_case, "severity", "medium"),
                suggested_handling=getattr(edge_case, "suggested_handling", None)
            ))

        # Convert contradictions
        contradictions = []
        for contradiction in getattr(core_result, "contradictions", []):
            contradictions.append(Contradiction(
                id=str(uuid.uuid4()),
                conflicting_requirements=getattr(contradiction, "conflicting_requirements", []),
                description=getattr(contradiction, "description", str(contradiction)),
                severity=getattr(contradiction, "severity", "medium"),
                resolution_suggestions=getattr(contradiction, "resolution_suggestions", [])
            ))

        # Convert compressed requirements
        compressed_requirements = []
        for req in getattr(core_result, "compressed_requirements", []):
            compressed_requirements.append(CompressedRequirement(
                id=str(uuid.uuid4()),
                original_requirements=getattr(req, "original_requirements", []),
                compressed_text=getattr(req, "compressed_text", str(req)),
                priority=getattr(req, "priority", "medium")
            ))

        # Get specification metadata from tracking
        spec_data = self._active_specifications.get(specification_id, {})

        return RefinedSpecification(
            id=specification_id,
            original_analysis_id=spec_data.get("analysis_result_id", ""),
            compressed_requirements=compressed_requirements,
            edge_cases=edge_cases,
            contradictions=contradictions,
            completeness_score=getattr(core_result, "completeness_score", 0.8),
            processing_metrics={
                "processing_time": (datetime.now() - spec_data.get("started_at", datetime.now())).total_seconds(),
                "mode_used": spec_data.get("mode", "balanced"),
                "custom_rules_applied": len(spec_data.get("custom_rules", [])),
                "focus_areas_count": len(spec_data.get("focus_areas", []))
            },
            created_at=spec_data.get("started_at", datetime.now())
        )