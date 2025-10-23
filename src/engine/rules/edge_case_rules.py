"""
Rule definitions for edge case detection.

This module contains rule patterns for detecting various types of edge cases
in requirements and specifications.
"""

from typing import List, Dict, Any
from .rule_engine import Rule, RegexRule, KeywordRule, CustomRule, RuleResult
from ..models import Severity, EdgeCaseCategory


def _check_input_validation_complexity(text: str, context: Dict[str, Any]) -> RuleResult:
    """Custom rule to detect complex input validation scenarios."""
    complexity_indicators = [
        "multiple inputs", "nested data", "array", "list", "json", "xml",
        "file upload", "image", "video", "binary", "concurrent", "batch"
    ]

    found_indicators = [indicator for indicator in complexity_indicators
                       if indicator.lower() in text.lower()]

    if found_indicators:
        confidence = min(0.9, len(found_indicators) * 0.3)
        return RuleResult(
            rule_id="input_validation_complexity",
            matched=True,
            confidence=confidence,
            severity=Severity.MEDIUM,
            message=f"Complex input validation scenario detected: {', '.join(found_indicators)}",
            metadata={"indicators": found_indicators, "category": EdgeCaseCategory.INPUT_VALIDATION.value}
        )

    return RuleResult("input_validation_complexity", False)


def _check_scale_implications(text: str, context: Dict[str, Any]) -> RuleResult:
    """Custom rule to detect scale and performance implications."""
    scale_keywords = [
        "million", "thousand", "large", "big", "scale", "performance",
        "fast", "slow", "timeout", "memory", "cpu", "database",
        "concurrent", "parallel", "distributed"
    ]

    found_keywords = [kw for kw in scale_keywords if kw.lower() in text.lower()]

    if found_keywords:
        # Check for specific scale indicators
        has_numbers = any(char.isdigit() for char in text)
        has_performance_terms = any(term in text.lower() for term in ["fast", "slow", "performance", "speed"])

        confidence = 0.6
        if has_numbers:
            confidence += 0.2
        if has_performance_terms:
            confidence += 0.2

        confidence = min(0.95, confidence)

        return RuleResult(
            rule_id="scale_implications",
            matched=True,
            confidence=confidence,
            severity=Severity.HIGH if has_performance_terms else Severity.MEDIUM,
            message=f"Scale/performance implications detected: {', '.join(found_keywords)}",
            metadata={"keywords": found_keywords, "category": EdgeCaseCategory.PERFORMANCE.value}
        )

    return RuleResult("scale_implications", False)


def _check_error_handling_gaps(text: str, context: Dict[str, Any]) -> RuleResult:
    """Custom rule to detect missing error handling considerations."""
    error_keywords = ["error", "exception", "fail", "invalid", "wrong"]

    # Look for operations that need error handling
    operation_patterns = [
        r"\b(save|store|write|create|update|delete|remove)\b",
        r"\b(send|receive|transmit|download|upload)\b",
        r"\b(connect|authenticate|login|verify)\b",
        r"\b(parse|validate|process|convert)\b"
    ]

    import re
    has_operations = any(re.search(pattern, text, re.IGNORECASE) for pattern in operation_patterns)
    has_error_handling = any(keyword in text.lower() for keyword in error_keywords)

    if has_operations and not has_error_handling:
        return RuleResult(
            rule_id="error_handling_gaps",
            matched=True,
            confidence=0.8,
            severity=Severity.HIGH,
            message="Operations detected without explicit error handling considerations",
            metadata={"category": EdgeCaseCategory.ERROR_STATES.value}
        )

    return RuleResult("error_handling_gaps", False)


# Pre-defined rule sets for edge case detection
EDGE_CASE_RULES: List[Rule] = [
    # Input validation rules
    RegexRule(
        "empty_null_zero",
        r"\b(empty|null|zero|none|undefined|missing)\b",
        "Detects mentions of empty, null, or zero values",
        Severity.MEDIUM,
        confidence=0.8
    ),

    KeywordRule(
        "boundary_conditions",
        ["minimum", "maximum", "limit", "boundary", "edge", "overflow", "underflow"],
        "Detects boundary condition indicators",
        Severity.MEDIUM,
        confidence=0.7
    ),

    RegexRule(
        "concurrent_access",
        r"\b(concurrent|parallel|simultaneous|multiple users|race condition|deadlock|lock)\b",
        "Detects concurrency-related terms",
        Severity.HIGH,
        confidence=0.9
    ),

    # Security-related edge cases
    KeywordRule(
        "security_considerations",
        ["authentication", "authorization", "permission", "access", "security", "encrypt", "decrypt", "password"],
        "Detects security-related requirements",
        Severity.HIGH,
        confidence=0.8
    ),

    # Performance edge cases
    RegexRule(
        "performance_requirements",
        r"\b(performance|speed|fast|slow|latency|throughput|response time|timeout)\b",
        "Detects performance-related requirements",
        Severity.MEDIUM,
        confidence=0.7
    ),

    # Integration edge cases
    KeywordRule(
        "integration_points",
        ["API", "service", "external", "third-party", "integration", "webhook", "callback"],
        "Detects integration points that may have edge cases",
        Severity.MEDIUM,
        confidence=0.8
    ),

    # File handling edge cases
    RegexRule(
        "file_operations",
        r"\b(file|upload|download|import|export|csv|json|xml|pdf)\b",
        "Detects file operations that need edge case handling",
        Severity.MEDIUM,
        confidence=0.8
    ),

    # Data validation edge cases
    RegexRule(
        "data_validation",
        r"\b(validate|validation|format|pattern|regex|email|phone|url|date)\b",
        "Detects data validation requirements",
        Severity.MEDIUM,
        confidence=0.8
    ),

    # Network and connectivity edge cases
    KeywordRule(
        "network_operations",
        ["network", "internet", "connection", "offline", "online", "sync", "async"],
        "Detects network operations that may fail",
        Severity.MEDIUM,
        confidence=0.8
    ),

    # Custom rules for complex scenarios
    CustomRule(
        "input_validation_complexity",
        _check_input_validation_complexity,
        "Detects complex input validation scenarios",
        Severity.MEDIUM
    ),

    CustomRule(
        "scale_implications",
        _check_scale_implications,
        "Detects scale and performance implications",
        Severity.HIGH
    ),

    CustomRule(
        "error_handling_gaps",
        _check_error_handling_gaps,
        "Detects missing error handling considerations",
        Severity.HIGH
    )
]


# Categorized rule groups for specific edge case types
INPUT_VALIDATION_RULES = [
    "empty_null_zero",
    "data_validation",
    "input_validation_complexity"
]

PERFORMANCE_RULES = [
    "performance_requirements",
    "scale_implications",
    "concurrent_access"
]

SECURITY_RULES = [
    "security_considerations"
]

INTEGRATION_RULES = [
    "integration_points",
    "network_operations",
    "file_operations"
]

ERROR_HANDLING_RULES = [
    "error_handling_gaps"
]

# Map edge case categories to rule groups
EDGE_CASE_RULE_CATEGORIES = {
    EdgeCaseCategory.INPUT_VALIDATION: INPUT_VALIDATION_RULES,
    EdgeCaseCategory.PERFORMANCE: PERFORMANCE_RULES,
    EdgeCaseCategory.SECURITY: SECURITY_RULES,
    EdgeCaseCategory.INTEGRATION: INTEGRATION_RULES,
    EdgeCaseCategory.ERROR_STATES: ERROR_HANDLING_RULES,
    EdgeCaseCategory.BOUNDARY_CONDITIONS: ["boundary_conditions"],
    EdgeCaseCategory.CONCURRENCY: ["concurrent_access"]
}