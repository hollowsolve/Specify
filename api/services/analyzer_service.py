"""
Analyzer service that wraps Phase 1 of the Specify system.

Provides a service layer interface for prompt analysis with proper
error handling, logging, and session management.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Import Phase 1 components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from src.analyzer import PromptAnalyzer, AnalysisResult as CoreAnalysisResult
from api.schemas.response_schemas import AnalysisResult
from api.services.session_manager import SessionManager

logger = logging.getLogger(__name__)


class AnalyzerService:
    """Service wrapper for the prompt analyzer (Phase 1)."""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.analyzer = PromptAnalyzer()
        self._active_analyses: Dict[str, Dict[str, Any]] = {}

    async def analyze_prompt(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        analysis_options: Optional[Dict[str, Any]] = None,
        user_context: Optional[str] = None
    ) -> tuple[str, Optional[AnalysisResult]]:
        """
        Analyze a prompt and return analysis ID and optional result.

        Args:
            prompt: The prompt to analyze
            session_id: Optional session ID for tracking
            analysis_options: Additional analysis options
            user_context: Additional user context

        Returns:
            Tuple of (analysis_id, analysis_result)
            analysis_result is None if analysis is async/long-running
        """
        analysis_id = str(uuid.uuid4())

        logger.info(f"Starting prompt analysis {analysis_id} for session {session_id}")

        # Track analysis in session if provided
        if session_id:
            await self.session_manager.add_operation(session_id, f"analysis:{analysis_id}")

        # Store analysis metadata
        self._active_analyses[analysis_id] = {
            "id": analysis_id,
            "session_id": session_id,
            "prompt": prompt,
            "analysis_options": analysis_options or {},
            "user_context": user_context,
            "status": "running",
            "started_at": datetime.now(),
            "result": None,
            "error": None
        }

        try:
            # Run analysis (this is typically synchronous but we'll wrap it for consistency)
            result = await self._run_analysis(prompt, analysis_options, user_context)

            # Convert core result to API schema
            api_result = self._convert_analysis_result(analysis_id, result)

            # Update tracking
            self._active_analyses[analysis_id].update({
                "status": "completed",
                "completed_at": datetime.now(),
                "result": api_result
            })

            logger.info(f"Completed prompt analysis {analysis_id}")

            # Remove from session operations
            if session_id:
                await self.session_manager.remove_operation(session_id, f"analysis:{analysis_id}")

            return analysis_id, api_result

        except Exception as e:
            logger.exception(f"Error in prompt analysis {analysis_id}: {e}")

            # Update tracking with error
            self._active_analyses[analysis_id].update({
                "status": "failed",
                "completed_at": datetime.now(),
                "error": str(e)
            })

            # Remove from session operations
            if session_id:
                await self.session_manager.remove_operation(session_id, f"analysis:{analysis_id}")

            raise

    async def get_analysis_result(self, analysis_id: str) -> Optional[AnalysisResult]:
        """
        Get analysis result by ID.

        Args:
            analysis_id: Analysis ID

        Returns:
            Analysis result or None if not found/not completed
        """
        analysis_data = self._active_analyses.get(analysis_id)
        if not analysis_data:
            return None

        if analysis_data["status"] == "completed":
            return analysis_data["result"]

        return None

    async def get_analysis_status(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """
        Get analysis status and metadata.

        Args:
            analysis_id: Analysis ID

        Returns:
            Analysis status info or None if not found
        """
        analysis_data = self._active_analyses.get(analysis_id)
        if not analysis_data:
            return None

        return {
            "id": analysis_data["id"],
            "session_id": analysis_data["session_id"],
            "status": analysis_data["status"],
            "started_at": analysis_data["started_at"],
            "completed_at": analysis_data.get("completed_at"),
            "error": analysis_data.get("error")
        }

    async def cancel_analysis(self, analysis_id: str) -> bool:
        """
        Cancel a running analysis.

        Args:
            analysis_id: Analysis ID

        Returns:
            True if cancelled, False if not found or already completed
        """
        analysis_data = self._active_analyses.get(analysis_id)
        if not analysis_data or analysis_data["status"] != "running":
            return False

        # Update status
        analysis_data.update({
            "status": "cancelled",
            "completed_at": datetime.now()
        })

        # Remove from session operations
        session_id = analysis_data.get("session_id")
        if session_id:
            await self.session_manager.remove_operation(session_id, f"analysis:{analysis_id}")

        logger.info(f"Cancelled analysis {analysis_id}")
        return True

    async def list_session_analyses(self, session_id: str) -> list[Dict[str, Any]]:
        """
        List all analyses for a session.

        Args:
            session_id: Session ID

        Returns:
            List of analysis status info
        """
        analyses = []
        for analysis_data in self._active_analyses.values():
            if analysis_data.get("session_id") == session_id:
                analyses.append({
                    "id": analysis_data["id"],
                    "status": analysis_data["status"],
                    "started_at": analysis_data["started_at"],
                    "completed_at": analysis_data.get("completed_at"),
                    "error": analysis_data.get("error")
                })

        return sorted(analyses, key=lambda x: x["started_at"], reverse=True)

    async def cleanup_completed_analyses(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed analyses.

        Args:
            max_age_hours: Maximum age in hours for completed analyses

        Returns:
            Number of analyses cleaned up
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        to_remove = []
        for analysis_id, analysis_data in self._active_analyses.items():
            if (analysis_data["status"] in ["completed", "failed", "cancelled"] and
                analysis_data.get("completed_at", datetime.now()) < cutoff_time):
                to_remove.append(analysis_id)

        for analysis_id in to_remove:
            del self._active_analyses[analysis_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old analyses")

        return len(to_remove)

    async def _run_analysis(
        self,
        prompt: str,
        analysis_options: Optional[Dict[str, Any]] = None,
        user_context: Optional[str] = None
    ) -> CoreAnalysisResult:
        """
        Run the actual analysis using the core analyzer.

        Args:
            prompt: Prompt to analyze
            analysis_options: Additional options
            user_context: User context

        Returns:
            Core analysis result
        """
        # Prepare context if provided
        full_prompt = prompt
        if user_context:
            full_prompt = f"Context: {user_context}\n\nPrompt: {prompt}"

        # Run analysis in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.analyzer.analyze,
            full_prompt
        )

        return result

    def _convert_analysis_result(
        self,
        analysis_id: str,
        core_result: CoreAnalysisResult
    ) -> AnalysisResult:
        """
        Convert core analysis result to API schema.

        Args:
            analysis_id: Analysis ID
            core_result: Core analysis result

        Returns:
            API analysis result
        """
        # Calculate processing time from tracking data
        analysis_data = self._active_analyses.get(analysis_id, {})
        started_at = analysis_data.get("started_at", datetime.now())
        processing_time = (datetime.now() - started_at).total_seconds()

        return AnalysisResult(
            id=analysis_id,
            intent=core_result.intent,
            requirements=core_result.explicit_requirements,
            assumptions=core_result.implicit_assumptions,
            ambiguities=core_result.ambiguities,
            metadata={
                "confidence_score": getattr(core_result, "confidence_score", 0.8),
                "processing_metadata": getattr(core_result, "metadata", {}),
                "analysis_version": "1.0.0"
            },
            processing_time=processing_time
        )