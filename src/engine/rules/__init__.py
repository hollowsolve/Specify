"""
Extensible rule system for the specification engine.

This module provides the foundation for rule-based processing in the
specification engine, allowing for extensible and customizable rule patterns.
"""

from .rule_engine import RuleEngine, Rule, RuleResult
from .edge_case_rules import EDGE_CASE_RULES, EDGE_CASE_RULE_CATEGORIES
from .completeness_rules import COMPLETENESS_RULES, REQUIREMENT_CATEGORIES, CATEGORY_PRIORITY
from .contradiction_rules import CONTRADICTION_PATTERNS, find_contradiction_patterns

__all__ = [
    'RuleEngine',
    'Rule',
    'RuleResult',
    'EDGE_CASE_RULES',
    'EDGE_CASE_RULE_CATEGORIES',
    'COMPLETENESS_RULES',
    'REQUIREMENT_CATEGORIES',
    'CATEGORY_PRIORITY',
    'CONTRADICTION_PATTERNS',
    'find_contradiction_patterns'
]