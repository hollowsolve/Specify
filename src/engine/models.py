"""
Data models for the specification engine.

This module defines the data structures used to represent refined specifications
and their components after processing through the specification engine.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyzer.models import AnalysisResult


class Severity(Enum):
    """Severity levels for issues found during specification processing."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EdgeCaseCategory(Enum):
    """Categories of edge cases that can be detected."""
    INPUT_VALIDATION = "input_validation"
    BOUNDARY_CONDITIONS = "boundary_conditions"
    ERROR_STATES = "error_states"
    CONCURRENCY = "concurrency"
    PERFORMANCE = "performance"
    SECURITY = "security"
    INTEGRATION = "integration"


@dataclass
class EdgeCase:
    """
    Represents an edge case identified during specification analysis.

    Attributes:
        category: The category of edge case
        description: Description of the edge case
        suggested_handling: Recommended approach to handle this edge case
        severity: How critical this edge case is
        confidence: Confidence score (0.0-1.0) in the detection
    """
    category: EdgeCaseCategory
    description: str
    suggested_handling: str
    severity: Severity
    confidence: float = 0.0

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


@dataclass
class CompressedRequirement:
    """
    Represents a requirement that has been compressed or merged.

    Attributes:
        compressed_text: The concise version of the requirement
        original_requirements: List of original requirement texts that were merged
        compression_ratio: How much the requirement was compressed (0.0-1.0)
        semantic_preserved: Whether semantic meaning was preserved
    """
    compressed_text: str
    original_requirements: List[str]
    compression_ratio: float = 0.0
    semantic_preserved: bool = True

    def __post_init__(self):
        if not 0.0 <= self.compression_ratio <= 1.0:
            raise ValueError("Compression ratio must be between 0.0 and 1.0")
        if not self.original_requirements:
            raise ValueError("Must have at least one original requirement")


@dataclass
class Contradiction:
    """
    Represents a contradiction found between requirements.

    Attributes:
        requirement_1: First conflicting requirement
        requirement_2: Second conflicting requirement
        explanation: Explanation of why they contradict
        severity: How serious the contradiction is
        suggested_resolution: Recommended way to resolve the contradiction
    """
    requirement_1: str
    requirement_2: str
    explanation: str
    severity: Severity
    suggested_resolution: str
    confidence: float = 0.0

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


@dataclass
class CompletenessGap:
    """
    Represents a gap in the completeness of requirements.

    Attributes:
        category: The category of missing requirement
        description: Description of what's missing
        suggested_requirement: Suggested requirement to fill the gap
        importance: How important this gap is to address
    """
    category: str
    description: str
    suggested_requirement: str
    importance: Severity
    confidence: float = 0.0

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


@dataclass
class ProcessingMetrics:
    """
    Metrics about the processing performed by the specification engine.

    Attributes:
        processing_time_seconds: Total processing time
        tokens_used: Approximate tokens used for LLM calls
        processors_run: List of processors that were executed
        total_issues_found: Total number of issues identified
    """
    processing_time_seconds: float = 0.0
    tokens_used: int = 0
    processors_run: List[str] = field(default_factory=list)
    total_issues_found: int = 0


@dataclass
class RefinedSpecification:
    """
    The refined specification produced by the specification engine.

    This is the main output containing all the intelligence gathered about
    the original prompt and requirements.

    Attributes:
        original_analysis: The original analysis result from Phase 1
        edge_cases: List of edge cases identified
        compressed_requirements: List of compressed/optimized requirements
        contradictions: List of contradictions found
        completeness_gaps: List of gaps in requirement completeness
        confidence_score: Overall confidence in the refined specification (0.0-1.0)
        processing_metrics: Metrics about the processing performed
        metadata: Additional metadata about the processing
    """
    original_analysis: AnalysisResult
    edge_cases: List[EdgeCase] = field(default_factory=list)
    compressed_requirements: List[CompressedRequirement] = field(default_factory=list)
    contradictions: List[Contradiction] = field(default_factory=list)
    completeness_gaps: List[CompletenessGap] = field(default_factory=list)
    confidence_score: float = 0.0
    processing_metrics: ProcessingMetrics = field(default_factory=ProcessingMetrics)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the refined specification to a dictionary representation."""
        return {
            "original_analysis": self.original_analysis.to_dict(),
            "edge_cases": [
                {
                    "category": edge_case.category.value,
                    "description": edge_case.description,
                    "suggested_handling": edge_case.suggested_handling,
                    "severity": edge_case.severity.value,
                    "confidence": edge_case.confidence
                }
                for edge_case in self.edge_cases
            ],
            "compressed_requirements": [
                {
                    "compressed_text": req.compressed_text,
                    "original_requirements": req.original_requirements,
                    "compression_ratio": req.compression_ratio,
                    "semantic_preserved": req.semantic_preserved
                }
                for req in self.compressed_requirements
            ],
            "contradictions": [
                {
                    "requirement_1": contradiction.requirement_1,
                    "requirement_2": contradiction.requirement_2,
                    "explanation": contradiction.explanation,
                    "severity": contradiction.severity.value,
                    "suggested_resolution": contradiction.suggested_resolution,
                    "confidence": contradiction.confidence
                }
                for contradiction in self.contradictions
            ],
            "completeness_gaps": [
                {
                    "category": gap.category,
                    "description": gap.description,
                    "suggested_requirement": gap.suggested_requirement,
                    "importance": gap.importance.value,
                    "confidence": gap.confidence
                }
                for gap in self.completeness_gaps
            ],
            "confidence_score": self.confidence_score,
            "processing_metrics": {
                "processing_time_seconds": self.processing_metrics.processing_time_seconds,
                "tokens_used": self.processing_metrics.tokens_used,
                "processors_run": self.processing_metrics.processors_run,
                "total_issues_found": self.processing_metrics.total_issues_found
            },
            "metadata": self.metadata
        }

    def summary(self) -> str:
        """Generate a human-readable summary of the refined specification."""
        total_issues = (
            len(self.edge_cases) +
            len(self.contradictions) +
            len(self.completeness_gaps)
        )

        return f"""
Refined Specification Summary:
=============================
Original Intent: {self.original_analysis.intent}

Processing Results:
- Edge Cases Identified: {len(self.edge_cases)}
- Requirements Compressed: {len(self.compressed_requirements)}
- Contradictions Found: {len(self.contradictions)}
- Completeness Gaps: {len(self.completeness_gaps)}

Overall Confidence: {self.confidence_score:.2f}
Total Issues Found: {total_issues}
Processing Time: {self.processing_metrics.processing_time_seconds:.2f}s

Critical Issues: {sum(1 for ec in self.edge_cases if ec.severity == Severity.CRITICAL) + sum(1 for c in self.contradictions if c.severity == Severity.CRITICAL)}
High Priority Items: {sum(1 for ec in self.edge_cases if ec.severity == Severity.HIGH) + sum(1 for c in self.contradictions if c.severity == Severity.HIGH) + sum(1 for gap in self.completeness_gaps if gap.importance == Severity.HIGH)}
"""

    def get_high_priority_issues(self) -> List[str]:
        """Get a list of high-priority issues that need immediate attention."""
        issues = []

        # High/Critical edge cases
        for edge_case in self.edge_cases:
            if edge_case.severity in [Severity.HIGH, Severity.CRITICAL]:
                issues.append(f"Edge Case: {edge_case.description}")

        # High/Critical contradictions
        for contradiction in self.contradictions:
            if contradiction.severity in [Severity.HIGH, Severity.CRITICAL]:
                issues.append(f"Contradiction: {contradiction.explanation}")

        # High/Critical completeness gaps
        for gap in self.completeness_gaps:
            if gap.importance in [Severity.HIGH, Severity.CRITICAL]:
                issues.append(f"Missing Requirement: {gap.description}")

        return issues

    def get_compression_savings(self) -> float:
        """Calculate the overall compression savings achieved."""
        if not self.compressed_requirements:
            return 0.0

        total_original_length = sum(
            sum(len(req) for req in comp_req.original_requirements)
            for comp_req in self.compressed_requirements
        )

        total_compressed_length = sum(
            len(comp_req.compressed_text)
            for comp_req in self.compressed_requirements
        )

        if total_original_length == 0:
            return 0.0

        return 1.0 - (total_compressed_length / total_original_length)