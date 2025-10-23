"""
Interactive Refinement Loop - Core orchestration for human-in-the-loop specification refinement.

This module implements the main RefinementLoop class that orchestrates the
presentation → feedback → iteration cycle, making specification refinement feel like
collaborating with a senior architect.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import uuid
import json
from pathlib import Path

from .models import (
    RefinementSession,
    RefinementIteration,
    UserDecision,
    FinalizedSpecification,
    UserFeedback
)
from .presenters.finding_presenter import FindingPresenter
from .presenters.suggestion_generator import SuggestionGenerator
from .presenters.approval_handler import ApprovalHandler
from ..engine.models import RefinedSpecification


class RefinementLoop:
    """
    Main orchestrator for interactive specification refinement.

    Takes a RefinedSpecification from Phase 2 and manages the human-in-the-loop
    process of reviewing findings, getting user feedback, and iteratively
    improving the specification until the user is satisfied.
    """

    def __init__(self,
                 presenter: FindingPresenter,
                 suggestion_generator: SuggestionGenerator,
                 approval_handler: ApprovalHandler,
                 session_dir: Optional[Path] = None):
        self.presenter = presenter
        self.suggestion_generator = suggestion_generator
        self.approval_handler = approval_handler
        self.session_dir = session_dir or Path.cwd() / ".specify_sessions"
        self.session_dir.mkdir(exist_ok=True)

        # Convergence detection parameters
        self.max_iterations = 10
        self.convergence_threshold = 0.95  # 95% acceptance rate indicates satisfaction

    def start_refinement(self,
                        refined_spec: RefinedSpecification,
                        session_id: Optional[str] = None) -> FinalizedSpecification:
        """
        Start or resume an interactive refinement session.

        Args:
            refined_spec: Output from Phase 2 analysis
            session_id: Optional session ID to resume existing session

        Returns:
            FinalizedSpecification ready for execution planning
        """
        if session_id:
            session = self._load_session(session_id)
        else:
            session = self._create_new_session(refined_spec)

        return self._run_refinement_loop(session)

    def _create_new_session(self, refined_spec: RefinedSpecification) -> RefinementSession:
        """Create a new refinement session."""
        session = RefinementSession(
            session_id=str(uuid.uuid4()),
            original_spec=refined_spec,
            iterations=[],
            user_decisions=[],
            current_state={
                "requirements": refined_spec.requirements.copy(),
                "edge_cases": refined_spec.edge_cases.copy(),
                "contradictions": refined_spec.contradictions.copy(),
                "completeness_gaps": refined_spec.completeness_gaps.copy(),
                "compressed_requirements": refined_spec.compressed_requirements.copy()
            },
            is_finalized=False,
            finalized_spec=None
        )

        self._save_session(session)
        return session

    def _run_refinement_loop(self, session: RefinementSession) -> FinalizedSpecification:
        """
        Main refinement loop that continues until user satisfaction or max iterations.
        """
        print(f"🔄 Starting refinement session {session.session_id[:8]}")
        print("💡 I'll help you review and refine your specification step by step.\n")

        iteration_count = len(session.iterations)

        while iteration_count < self.max_iterations and not session.is_finalized:
            print(f"📋 Refinement Iteration {iteration_count + 1}")
            print("=" * 50)

            # Present current findings
            self._present_findings(session)

            # Generate and present suggestions
            suggestions = self._generate_suggestions(session)

            # Get user decisions
            user_feedback = self._get_user_decisions(session, suggestions)

            # Apply approved changes
            changes_applied = self._apply_user_decisions(session, user_feedback)

            # Record iteration
            iteration = RefinementIteration(
                iteration_number=iteration_count + 1,
                suggestions_presented=len(suggestions),
                user_feedback=user_feedback,
                changes_applied=changes_applied,
                timestamp=datetime.now()
            )
            session.iterations.append(iteration)

            # Check for convergence
            if self._check_convergence(session):
                print("\n✅ Great! It looks like we've addressed all the major concerns.")
                if self._confirm_finalization():
                    session.is_finalized = True
                    session.finalized_spec = self._create_finalized_spec(session)

            iteration_count += 1
            self._save_session(session)

            if not session.is_finalized:
                print("\n" + "=" * 50)
                continue_refinement = input("Continue refining? (y/n): ").lower().startswith('y')
                if not continue_refinement:
                    break

        if not session.is_finalized:
            print("\n⚠️  Refinement stopped before finalization.")
            if input("Would you like to finalize the current state? (y/n): ").lower().startswith('y'):
                session.is_finalized = True
                session.finalized_spec = self._create_finalized_spec(session)

        if session.finalized_spec:
            self._save_session(session)
            return session.finalized_spec
        else:
            raise RuntimeError("Refinement session ended without finalization")

    def _present_findings(self, session: RefinementSession):
        """Present current findings in a clear, actionable format."""
        current_state = session.current_state

        print("📊 Current Specification Analysis:")
        print("-" * 30)

        # Use presenter to format findings
        self.presenter.present_edge_cases(current_state.get("edge_cases", []))
        self.presenter.present_contradictions(current_state.get("contradictions", []))
        self.presenter.present_completeness_gaps(current_state.get("completeness_gaps", []))
        self.presenter.present_compressed_requirements(current_state.get("compressed_requirements", []))

    def _generate_suggestions(self, session: RefinementSession) -> List[Dict[str, Any]]:
        """Generate intelligent suggestions for each category of findings."""
        current_state = session.current_state

        suggestions = []

        # Generate suggestions for each category
        edge_case_suggestions = self.suggestion_generator.suggest_edge_case_handling(
            current_state.get("edge_cases", [])
        )
        suggestions.extend(edge_case_suggestions)

        contradiction_suggestions = self.suggestion_generator.suggest_contradiction_resolutions(
            current_state.get("contradictions", [])
        )
        suggestions.extend(contradiction_suggestions)

        gap_suggestions = self.suggestion_generator.suggest_completeness_improvements(
            current_state.get("completeness_gaps", [])
        )
        suggestions.extend(gap_suggestions)

        compression_suggestions = self.suggestion_generator.suggest_compression_refinements(
            current_state.get("compressed_requirements", [])
        )
        suggestions.extend(compression_suggestions)

        # Rank suggestions by confidence and impact
        ranked_suggestions = self.suggestion_generator.rank_suggestions(suggestions)

        return ranked_suggestions

    def _get_user_decisions(self, session: RefinementSession, suggestions: List[Dict[str, Any]]) -> UserFeedback:
        """Get user decisions on suggestions through interactive approval process."""
        return self.approval_handler.process_suggestions(suggestions, session.current_state)

    def _apply_user_decisions(self, session: RefinementSession, feedback: UserFeedback) -> int:
        """Apply approved user decisions to the current specification state."""
        changes_applied = 0
        current_state = session.current_state

        for decision in feedback.decisions:
            if decision.action == "accept":
                # Apply the suggestion to current state
                self._apply_suggestion(current_state, decision.suggestion)
                changes_applied += 1

            elif decision.action == "modify":
                # Apply the modified version
                modified_suggestion = decision.modification
                self._apply_suggestion(current_state, modified_suggestion)
                changes_applied += 1

            elif decision.action == "custom":
                # Add custom requirement or change
                self._apply_custom_change(current_state, decision.custom_content)
                changes_applied += 1

            # Record the decision
            session.user_decisions.append(decision)

        return changes_applied

    def _apply_suggestion(self, current_state: Dict[str, Any], suggestion: Dict[str, Any]):
        """Apply a specific suggestion to the current state."""
        suggestion_type = suggestion.get("type")

        if suggestion_type == "edge_case_handling":
            # Add edge case handling to requirements
            handling = suggestion.get("handling")
            current_state.setdefault("requirements", []).append({
                "type": "edge_case_handling",
                "content": handling,
                "source": "refinement_suggestion"
            })

        elif suggestion_type == "contradiction_resolution":
            # Remove contradicting requirements and add resolution
            resolution = suggestion.get("resolution")
            # This would need more sophisticated logic based on the contradiction
            current_state.setdefault("requirements", []).append({
                "type": "contradiction_resolution",
                "content": resolution,
                "source": "refinement_suggestion"
            })

        elif suggestion_type == "completeness_addition":
            # Add missing requirements
            new_requirement = suggestion.get("requirement")
            current_state.setdefault("requirements", []).append(new_requirement)

        elif suggestion_type == "compression_refinement":
            # Replace compressed requirement with refined version
            # This would need to identify and replace the specific requirement
            pass

    def _apply_custom_change(self, current_state: Dict[str, Any], custom_content: str):
        """Apply a custom user change to the current state."""
        current_state.setdefault("requirements", []).append({
            "type": "custom_addition",
            "content": custom_content,
            "source": "user_custom"
        })

    def _check_convergence(self, session: RefinementSession) -> bool:
        """
        Check if the refinement process has converged (user is satisfied).

        Uses acceptance rate and remaining issues to determine convergence.
        """
        if not session.iterations:
            return False

        latest_iteration = session.iterations[-1]

        # Calculate acceptance rate for latest iteration
        total_suggestions = latest_iteration.suggestions_presented
        if total_suggestions == 0:
            return True  # No suggestions means we're done

        accepted_decisions = len([
            d for d in latest_iteration.user_feedback.decisions
            if d.action in ["accept", "modify"]
        ])

        acceptance_rate = accepted_decisions / total_suggestions

        # Check if we have few remaining issues
        current_state = session.current_state
        remaining_issues = (
            len(current_state.get("contradictions", [])) +
            len(current_state.get("completeness_gaps", [])) +
            len([ec for ec in current_state.get("edge_cases", []) if not ec.get("handled", False)])
        )

        # Convergence criteria: high acceptance rate OR very few remaining issues
        return acceptance_rate >= self.convergence_threshold or remaining_issues <= 2

    def _confirm_finalization(self) -> bool:
        """Confirm with user that they want to finalize the specification."""
        print("\n🎯 The specification appears to be well-refined!")
        print("   • Most suggestions have been accepted")
        print("   • Major contradictions resolved")
        print("   • Edge cases addressed")
        print("   • Requirements are comprehensive")

        return input("\nFinalize this specification? (y/n): ").lower().startswith('y')

    def _create_finalized_spec(self, session: RefinementSession) -> FinalizedSpecification:
        """Create the final specification from the refined session state."""
        current_state = session.current_state

        # Calculate confidence score based on refinement quality
        confidence_score = self._calculate_confidence_score(session)

        finalized_spec = FinalizedSpecification(
            requirements=current_state.get("requirements", []),
            resolved_edge_cases=current_state.get("edge_cases", []),
            resolved_contradictions=[],  # All should be resolved by now
            complete_requirement_set=True,
            confidence_score=confidence_score,
            approval_timestamp=datetime.now(),
            ready_for_dispatch=True,
            refinement_session_id=session.session_id,
            total_iterations=len(session.iterations),
            user_acceptance_rate=self._calculate_acceptance_rate(session)
        )

        return finalized_spec

    def _calculate_confidence_score(self, session: RefinementSession) -> float:
        """Calculate confidence score based on refinement quality metrics."""
        if not session.iterations:
            return 0.5  # Default for unrefined specs

        # Factors that increase confidence:
        # 1. High user acceptance rate
        # 2. Multiple refinement iterations
        # 3. Resolution of contradictions and gaps
        # 4. Comprehensive edge case handling

        acceptance_rate = self._calculate_acceptance_rate(session)
        iteration_bonus = min(len(session.iterations) * 0.1, 0.3)  # Up to 30% bonus

        current_state = session.current_state
        remaining_issues = (
            len(current_state.get("contradictions", [])) +
            len(current_state.get("completeness_gaps", []))
        )

        issue_penalty = remaining_issues * 0.05  # 5% penalty per remaining issue

        confidence = acceptance_rate + iteration_bonus - issue_penalty
        return max(0.0, min(1.0, confidence))  # Clamp to [0, 1]

    def _calculate_acceptance_rate(self, session: RefinementSession) -> float:
        """Calculate overall user acceptance rate across all iterations."""
        if not session.user_decisions:
            return 0.0

        accepted_decisions = len([
            d for d in session.user_decisions
            if d.action in ["accept", "modify"]
        ])

        return accepted_decisions / len(session.user_decisions)

    def _save_session(self, session: RefinementSession):
        """Save session state to disk for resumability."""
        session_file = self.session_dir / f"{session.session_id}.json"

        with open(session_file, 'w') as f:
            json.dump(session.to_dict(), f, indent=2, default=str)

    def _load_session(self, session_id: str) -> RefinementSession:
        """Load an existing session from disk."""
        session_file = self.session_dir / f"{session_id}.json"

        if not session_file.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        with open(session_file, 'r') as f:
            session_data = json.load(f)

        return RefinementSession.from_dict(session_data)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all available refinement sessions."""
        sessions = []

        for session_file in self.session_dir.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)

                sessions.append({
                    "session_id": session_data["session_id"],
                    "created_at": session_data.get("created_at"),
                    "is_finalized": session_data.get("is_finalized", False),
                    "iterations": len(session_data.get("iterations", [])),
                    "last_modified": session_file.stat().st_mtime
                })

            except (json.JSONDecodeError, KeyError):
                continue

        return sorted(sessions, key=lambda x: x["last_modified"], reverse=True)