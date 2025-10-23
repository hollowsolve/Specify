"""
Processor modules for the specification engine.

This package contains the core processors that analyze and refine
specification data using hybrid rule-based and LLM approaches.
"""

from .edge_case_detector import EdgeCaseDetector
from .requirement_compressor import RequirementCompressor
from .contradiction_finder import ContradictionFinder
from .completeness_validator import CompletenessValidator

__all__ = [
    'EdgeCaseDetector',
    'RequirementCompressor',
    'ContradictionFinder',
    'CompletenessValidator'
]