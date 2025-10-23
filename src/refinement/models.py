"""
Data models for the interactive refinement system.

This module defines the core data structures used throughout the refinement process,
including session management, user feedback, and finalized specifications.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import json


class UserDecisionAction(Enum):
    """Possible actions a user can take on a suggestion."""
    ACCEPT = "accept"
    REJECT = "reject"
    MODIFY = "modify"
    CUSTOM = "custom"
    CLARIFY = "clarify"


@dataclass
class UserDecision:
    """Represents a single user decision on a suggestion."""
    suggestion_id: str
    suggestion: Dict[str, Any]
    action: UserDecisionAction
    reasoning: Optional[str] = None
    modification: Optional[Dict[str, Any]] = None
    custom_content: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "suggestion": self.suggestion,
            "action": self.action.value,
            "reasoning": self.reasoning,
            "modification": self.modification,
            "custom_content": self.custom_content,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserDecision':
        return cls(
            suggestion_id=data["suggestion_id"],
            suggestion=data["suggestion"],
            action=UserDecisionAction(data["action"]),
            reasoning=data.get("reasoning"),
            modification=data.get("modification"),
            custom_content=data.get("custom_content"),
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


@dataclass
class UserFeedback:
    """Collection of user decisions for a refinement iteration."""
    decisions: List[UserDecision]
    overall_satisfaction: Optional[int] = None  # 1-5 scale
    additional_comments: Optional[str] = None
    wants_to_continue: bool = True

    def get_acceptance_rate(self) -> float:
        """Calculate the percentage of accepted/modified suggestions."""
        if not self.decisions:
            return 0.0

        accepted = len([
            d for d in self.decisions
            if d.action in [UserDecisionAction.ACCEPT, UserDecisionAction.MODIFY]
        ])

        return accepted / len(self.decisions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decisions": [d.to_dict() for d in self.decisions],
            "overall_satisfaction": self.overall_satisfaction,
            "additional_comments": self.additional_comments,
            "wants_to_continue": self.wants_to_continue
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserFeedback':
        return cls(
            decisions=[UserDecision.from_dict(d) for d in data["decisions"]],
            overall_satisfaction=data.get("overall_satisfaction"),
            additional_comments=data.get("additional_comments"),
            wants_to_continue=data.get("wants_to_continue", True)
        )


@dataclass
class RefinementIteration:
    """Represents one complete iteration of the refinement loop."""
    iteration_number: int
    suggestions_presented: int
    user_feedback: UserFeedback
    changes_applied: int
    timestamp: datetime
    duration_seconds: Optional[float] = None

    def get_metrics(self) -> Dict[str, Any]:
        """Get key metrics for this iteration."""
        return {
            "iteration": self.iteration_number,
            "suggestions_count": self.suggestions_presented,
            "acceptance_rate": self.user_feedback.get_acceptance_rate(),
            "changes_applied": self.changes_applied,
            "user_satisfaction": self.user_feedback.overall_satisfaction,
            "duration": self.duration_seconds
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration_number": self.iteration_number,
            "suggestions_presented": self.suggestions_presented,
            "user_feedback": self.user_feedback.to_dict(),
            "changes_applied": self.changes_applied,
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": self.duration_seconds
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RefinementIteration':
        return cls(
            iteration_number=data["iteration_number"],
            suggestions_presented=data["suggestions_presented"],
            user_feedback=UserFeedback.from_dict(data["user_feedback"]),
            changes_applied=data["changes_applied"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            duration_seconds=data.get("duration_seconds")
        )


@dataclass
class RefinementSession:
    """
    Represents a complete refinement session.

    This tracks the entire journey from initial refined specification
    through multiple iterations to final approval.
    """
    session_id: str
    original_spec: Any  # RefinedSpecification from Phase 2
    iterations: List[RefinementIteration]
    user_decisions: List[UserDecision]
    current_state: Dict[str, Any]
    is_finalized: bool = False
    finalized_spec: Optional['FinalizedSpecification'] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def get_session_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics for the entire session."""
        if not self.iterations:
            return {
                "total_iterations": 0,
                "overall_acceptance_rate": 0.0,
                "total_changes": 0,
                "is_finalized": self.is_finalized
            }

        total_suggestions = sum(i.suggestions_presented for i in self.iterations)
        total_accepted = len([
            d for d in self.user_decisions
            if d.action in [UserDecisionAction.ACCEPT, UserDecisionAction.MODIFY]
        ])

        acceptance_rate = total_accepted / len(self.user_decisions) if self.user_decisions else 0.0

        return {
            "session_id": self.session_id,
            "total_iterations": len(self.iterations),
            "total_suggestions": total_suggestions,
            "total_decisions": len(self.user_decisions),
            "overall_acceptance_rate": acceptance_rate,
            "total_changes": sum(i.changes_applied for i in self.iterations),
            "is_finalized": self.is_finalized,
            "confidence_score": self.finalized_spec.confidence_score if self.finalized_spec else None,
            "session_duration": (self.updated_at - self.created_at).total_seconds()
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "original_spec": self.original_spec.to_dict() if hasattr(self.original_spec, 'to_dict') else str(self.original_spec),
            "iterations": [i.to_dict() for i in self.iterations],
            "user_decisions": [d.to_dict() for d in self.user_decisions],
            "current_state": self.current_state,
            "is_finalized": self.is_finalized,
            "finalized_spec": self.finalized_spec.to_dict() if self.finalized_spec else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RefinementSession':
        # Note: This is a simplified version - in practice you'd need to properly
        # reconstruct the original_spec based on its actual type
        session = cls(
            session_id=data["session_id"],
            original_spec=data["original_spec"],  # Simplified
            iterations=[RefinementIteration.from_dict(i) for i in data["iterations"]],
            user_decisions=[UserDecision.from_dict(d) for d in data["user_decisions"]],
            current_state=data["current_state"],
            is_finalized=data["is_finalized"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )

        if data.get("finalized_spec"):
            session.finalized_spec = FinalizedSpecification.from_dict(data["finalized_spec"])

        return session


@dataclass
class FinalizedSpecification:
    """
    The final, user-approved specification ready for execution planning.

    This represents the end result of the refinement process - a specification
    that has been thoroughly reviewed, refined, and approved by the user.
    """
    requirements: List[Dict[str, Any]]
    resolved_edge_cases: List[Dict[str, Any]]
    resolved_contradictions: List[Dict[str, Any]]
    complete_requirement_set: bool
    confidence_score: float  # 0.0 to 1.0
    approval_timestamp: datetime
    refinement_session_id: str
    total_iterations: int
    user_acceptance_rate: float
    ready_for_dispatch: bool = True

    # Optional export metadata
    export_formats: List[str] = field(default_factory=lambda: ["json"])
    tags: List[str] = field(default_factory=list)

    def get_execution_readiness(self) -> Dict[str, Any]:
        """Assess readiness for execution planning (Phase 4)."""
        readiness_score = self.confidence_score

        # Penalize if not complete
        if not self.complete_requirement_set:
            readiness_score *= 0.8

        # Penalize if low user acceptance
        if self.user_acceptance_rate < 0.7:
            readiness_score *= 0.9

        # Penalize if unresolved contradictions
        if self.resolved_contradictions:
            unresolved = len([c for c in self.resolved_contradictions if not c.get("resolved", False)])
            if unresolved > 0:
                readiness_score *= (1.0 - unresolved * 0.1)

        return {
            "ready_for_execution": readiness_score >= 0.8 and self.ready_for_dispatch,
            "readiness_score": readiness_score,
            "blockers": self._identify_execution_blockers(),
            "recommendations": self._get_execution_recommendations()
        }

    def _identify_execution_blockers(self) -> List[str]:
        """Identify any remaining blockers for execution."""
        blockers = []

        if not self.complete_requirement_set:
            blockers.append("Incomplete requirement set")

        if self.confidence_score < 0.6:
            blockers.append("Low confidence score")

        unresolved_contradictions = len([
            c for c in self.resolved_contradictions
            if not c.get("resolved", False)
        ])
        if unresolved_contradictions > 0:
            blockers.append(f"{unresolved_contradictions} unresolved contradictions")

        if self.user_acceptance_rate < 0.5:
            blockers.append("Low user acceptance rate")

        return blockers

    def _get_execution_recommendations(self) -> List[str]:
        """Get recommendations for execution planning."""
        recommendations = []

        if self.confidence_score >= 0.9:
            recommendations.append("High confidence - proceed with full execution planning")
        elif self.confidence_score >= 0.8:
            recommendations.append("Good confidence - consider pilot implementation")
        else:
            recommendations.append("Consider additional refinement before execution")

        if len(self.requirements) > 50:
            recommendations.append("Large specification - consider phased implementation")

        if len(self.resolved_edge_cases) > 20:
            recommendations.append("Many edge cases - prioritize robust error handling")

        return recommendations

    def to_execution_graph(self) -> Dict[str, Any]:
        """
        Convert to format suitable for execution planning (Phase 4).

        This method prepares the finalized specification for consumption
        by the execution planning system.
        """
        return {
            "requirements": self.requirements,
            "constraints": {
                "edge_cases": self.resolved_edge_cases,
                "resolved_issues": self.resolved_contradictions
            },
            "metadata": {
                "confidence": self.confidence_score,
                "refinement_quality": self.user_acceptance_rate,
                "specification_id": self.refinement_session_id,
                "finalized_at": self.approval_timestamp.isoformat()
            },
            "execution_hints": {
                "priority_requirements": self._identify_priority_requirements(),
                "risk_areas": self._identify_risk_areas(),
                "validation_points": self._identify_validation_points()
            }
        }

    def _identify_priority_requirements(self) -> List[Dict[str, Any]]:
        """Identify high-priority requirements for execution planning."""
        # This would use more sophisticated logic in practice
        return [req for req in self.requirements if req.get("priority", "medium") == "high"]

    def _identify_risk_areas(self) -> List[str]:
        """Identify areas of higher implementation risk."""
        risk_areas = []

        # Requirements with many associated edge cases
        edge_case_counts = {}
        for edge_case in self.resolved_edge_cases:
            related_req = edge_case.get("related_requirement")
            if related_req:
                edge_case_counts[related_req] = edge_case_counts.get(related_req, 0) + 1

        high_risk_reqs = [req for req, count in edge_case_counts.items() if count >= 3]
        if high_risk_reqs:
            risk_areas.append(f"Requirements with many edge cases: {', '.join(high_risk_reqs)}")

        # Recently modified requirements
        recent_changes = [
            req for req in self.requirements
            if req.get("source") in ["refinement_suggestion", "user_custom"]
        ]
        if recent_changes:
            risk_areas.append("Recently added/modified requirements need extra validation")

        return risk_areas

    def _identify_validation_points(self) -> List[str]:
        """Identify key validation points for testing."""
        validation_points = []

        # Each resolved edge case should have validation
        for edge_case in self.resolved_edge_cases:
            if edge_case.get("handling"):
                validation_points.append(f"Edge case: {edge_case.get('description', 'Unknown')}")

        # Each high-confidence requirement should be validated
        high_conf_reqs = [
            req for req in self.requirements
            if req.get("confidence", 0.5) >= 0.8
        ]
        for req in high_conf_reqs:
            validation_points.append(f"High-priority: {req.get('content', 'Unknown')}")

        return validation_points

    def export_to_format(self, format_type: str) -> str:
        """Export the finalized specification to various formats."""
        if format_type == "json":
            return json.dumps(self.to_dict(), indent=2, default=str)
        elif format_type == "markdown":
            return self._to_markdown()
        elif format_type == "yaml":
            import yaml
            return yaml.dump(self.to_dict(), default_flow_style=False)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

    def _to_markdown(self) -> str:
        """Export to markdown format for documentation."""
        md = f"""# Finalized Specification

**Session ID:** {self.refinement_session_id}
**Finalized:** {self.approval_timestamp.strftime('%Y-%m-%d %H:%M:%S')}
**Confidence Score:** {self.confidence_score:.2%}
**User Acceptance Rate:** {self.user_acceptance_rate:.2%}

## Requirements ({len(self.requirements)})

"""
        for i, req in enumerate(self.requirements, 1):
            md += f"{i}. {req.get('content', 'No description')}\n"

        md += f"\n## Resolved Edge Cases ({len(self.resolved_edge_cases)})\n\n"
        for i, edge_case in enumerate(self.resolved_edge_cases, 1):
            md += f"{i}. **{edge_case.get('description', 'Unknown')}**\n"
            if edge_case.get('handling'):
                md += f"   - *Handling:* {edge_case['handling']}\n"

        if self.resolved_contradictions:
            md += f"\n## Resolved Contradictions ({len(self.resolved_contradictions)})\n\n"
            for i, contradiction in enumerate(self.resolved_contradictions, 1):
                md += f"{i}. {contradiction.get('description', 'Unknown')}\n"
                if contradiction.get('resolution'):
                    md += f"   - *Resolution:* {contradiction['resolution']}\n"

        readiness = self.get_execution_readiness()
        md += f"\n## Execution Readiness\n\n"
        md += f"**Ready for Execution:** {'✅ Yes' if readiness['ready_for_execution'] else '❌ No'}\n"
        md += f"**Readiness Score:** {readiness['readiness_score']:.2%}\n"

        if readiness['blockers']:
            md += f"\n**Blockers:**\n"
            for blocker in readiness['blockers']:
                md += f"- {blocker}\n"

        if readiness['recommendations']:
            md += f"\n**Recommendations:**\n"
            for rec in readiness['recommendations']:
                md += f"- {rec}\n"

        return md

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requirements": self.requirements,
            "resolved_edge_cases": self.resolved_edge_cases,
            "resolved_contradictions": self.resolved_contradictions,
            "complete_requirement_set": self.complete_requirement_set,
            "confidence_score": self.confidence_score,
            "approval_timestamp": self.approval_timestamp.isoformat(),
            "ready_for_dispatch": self.ready_for_dispatch,
            "refinement_session_id": self.refinement_session_id,
            "total_iterations": self.total_iterations,
            "user_acceptance_rate": self.user_acceptance_rate,
            "export_formats": self.export_formats,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FinalizedSpecification':
        return cls(
            requirements=data["requirements"],
            resolved_edge_cases=data["resolved_edge_cases"],
            resolved_contradictions=data["resolved_contradictions"],
            complete_requirement_set=data["complete_requirement_set"],
            confidence_score=data["confidence_score"],
            approval_timestamp=datetime.fromisoformat(data["approval_timestamp"]),
            ready_for_dispatch=data.get("ready_for_dispatch", True),
            refinement_session_id=data["refinement_session_id"],
            total_iterations=data["total_iterations"],
            user_acceptance_rate=data["user_acceptance_rate"],
            export_formats=data.get("export_formats", ["json"]),
            tags=data.get("tags", [])
        )