"""
Rule definitions for contradiction detection.

This module contains patterns and rules for detecting contradictions
and conflicts between requirements.
"""

from typing import List, Dict, Any, Tuple
from .rule_engine import Rule, CustomRule, RuleResult
from ..models import Severity
import re


def _check_conflicting_performance_requirements(text: str, context: Dict[str, Any]) -> RuleResult:
    """Detect conflicting performance requirements."""
    # Look for conflicting speed/performance terms
    fast_terms = ["fast", "quick", "rapid", "immediate", "instant"]
    slow_terms = ["slow", "gradual", "delayed", "batch", "background"]

    fast_found = [term for term in fast_terms if term in text.lower()]
    slow_found = [term for term in slow_terms if term in text.lower()]

    if fast_found and slow_found:
        return RuleResult(
            rule_id="conflicting_performance",
            matched=True,
            confidence=0.7,
            severity=Severity.MEDIUM,
            message=f"Conflicting performance requirements: {fast_found} vs {slow_found}",
            metadata={
                "fast_terms": fast_found,
                "slow_terms": slow_found,
                "type": "performance_conflict"
            }
        )

    return RuleResult("conflicting_performance", False)


def _check_access_control_conflicts(text: str, context: Dict[str, Any]) -> RuleResult:
    """Detect conflicting access control requirements."""
    public_terms = ["public", "open", "accessible", "anonymous", "guest"]
    private_terms = ["private", "restricted", "authenticated", "authorized", "secure"]

    public_found = [term for term in public_terms if term in text.lower()]
    private_found = [term for term in private_terms if term in text.lower()]

    if public_found and private_found:
        # Check if they're referring to the same thing
        sentences = text.split('.')
        conflict_found = False

        for sentence in sentences:
            sentence_lower = sentence.lower()
            has_public = any(term in sentence_lower for term in public_found)
            has_private = any(term in sentence_lower for term in private_found)

            if has_public and has_private:
                conflict_found = True
                break

        if conflict_found:
            return RuleResult(
                rule_id="access_control_conflict",
                matched=True,
                confidence=0.8,
                severity=Severity.HIGH,
                message=f"Conflicting access control requirements: {public_found} vs {private_found}",
                metadata={
                    "public_terms": public_found,
                    "private_terms": private_found,
                    "type": "access_control_conflict"
                }
            )

    return RuleResult("access_control_conflict", False)


def _check_data_format_conflicts(text: str, context: Dict[str, Any]) -> RuleResult:
    """Detect conflicting data format requirements."""
    format_patterns = {
        "json": r"\bjson\b",
        "xml": r"\bxml\b",
        "csv": r"\bcsv\b",
        "binary": r"\bbinary\b",
        "text": r"\btext\b|\bstring\b",
        "number": r"\bnumber\b|\bnumeric\b|\binteger\b"
    }

    found_formats = []
    for format_name, pattern in format_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            found_formats.append(format_name)

    # Check for mutually exclusive formats
    exclusive_pairs = [
        ("json", "xml"),
        ("binary", "text"),
        ("json", "csv"),
        ("xml", "csv")
    ]

    for format1, format2 in exclusive_pairs:
        if format1 in found_formats and format2 in found_formats:
            return RuleResult(
                rule_id="data_format_conflict",
                matched=True,
                confidence=0.6,
                severity=Severity.MEDIUM,
                message=f"Conflicting data format requirements: {format1} vs {format2}",
                metadata={
                    "conflicting_formats": [format1, format2],
                    "all_formats": found_formats,
                    "type": "data_format_conflict"
                }
            )

    return RuleResult("data_format_conflict", False)


def _check_synchronous_async_conflicts(text: str, context: Dict[str, Any]) -> RuleResult:
    """Detect conflicts between synchronous and asynchronous requirements."""
    sync_terms = ["synchronous", "sync", "immediate", "blocking", "wait"]
    async_terms = ["asynchronous", "async", "non-blocking", "background", "queue"]

    sync_found = [term for term in sync_terms if term in text.lower()]
    async_found = [term for term in async_terms if term in text.lower()]

    if sync_found and async_found:
        # Look for same operation being described with both terms
        sentences = text.split('.')
        for sentence in sentences:
            sentence_lower = sentence.lower()
            has_sync = any(term in sentence_lower for term in sync_found)
            has_async = any(term in sentence_lower for term in async_found)

            if has_sync and has_async:
                return RuleResult(
                    rule_id="sync_async_conflict",
                    matched=True,
                    confidence=0.8,
                    severity=Severity.HIGH,
                    message=f"Conflicting execution model: {sync_found} vs {async_found}",
                    metadata={
                        "sync_terms": sync_found,
                        "async_terms": async_found,
                        "type": "execution_model_conflict"
                    }
                )

    return RuleResult("sync_async_conflict", False)


def _check_scalability_conflicts(text: str, context: Dict[str, Any]) -> RuleResult:
    """Detect conflicts in scalability requirements."""
    single_terms = ["single", "one", "individual", "solo"]
    multi_terms = ["multiple", "many", "concurrent", "parallel", "distributed"]

    single_found = [term for term in single_terms if term in text.lower()]
    multi_found = [term for term in multi_terms if term in text.lower()]

    if single_found and multi_found:
        # Check for same resource/operation
        resource_terms = ["user", "request", "process", "instance", "connection"]

        for sentence in text.split('.'):
            sentence_lower = sentence.lower()
            has_single = any(term in sentence_lower for term in single_found)
            has_multi = any(term in sentence_lower for term in multi_found)
            has_resource = any(term in sentence_lower for term in resource_terms)

            if has_single and has_multi and has_resource:
                return RuleResult(
                    rule_id="scalability_conflict",
                    matched=True,
                    confidence=0.7,
                    severity=Severity.MEDIUM,
                    message=f"Conflicting scalability requirements: {single_found} vs {multi_found}",
                    metadata={
                        "single_terms": single_found,
                        "multi_terms": multi_found,
                        "type": "scalability_conflict"
                    }
                )

    return RuleResult("scalability_conflict", False)


def _check_consistency_conflicts(text: str, context: Dict[str, Any]) -> RuleResult:
    """Detect conflicts in data consistency requirements."""
    strong_consistency = ["consistent", "synchronized", "immediate", "realtime"]
    eventual_consistency = ["eventual", "eventually", "asynchronous", "delayed"]

    strong_found = [term for term in strong_consistency if term in text.lower()]
    eventual_found = [term for term in eventual_consistency if term in text.lower()]

    if strong_found and eventual_found:
        return RuleResult(
            rule_id="consistency_conflict",
            matched=True,
            confidence=0.6,
            severity=Severity.MEDIUM,
            message=f"Conflicting consistency requirements: {strong_found} vs {eventual_found}",
            metadata={
                "strong_consistency": strong_found,
                "eventual_consistency": eventual_found,
                "type": "consistency_conflict"
            }
        )

    return RuleResult("consistency_conflict", False)


# Contradiction detection rules
CONTRADICTION_PATTERNS: List[Rule] = [
    CustomRule(
        "conflicting_performance",
        _check_conflicting_performance_requirements,
        "Detects conflicting performance requirements",
        Severity.MEDIUM
    ),

    CustomRule(
        "access_control_conflict",
        _check_access_control_conflicts,
        "Detects conflicting access control requirements",
        Severity.HIGH
    ),

    CustomRule(
        "data_format_conflict",
        _check_data_format_conflicts,
        "Detects conflicting data format requirements",
        Severity.MEDIUM
    ),

    CustomRule(
        "sync_async_conflict",
        _check_synchronous_async_conflicts,
        "Detects conflicts between synchronous and asynchronous requirements",
        Severity.HIGH
    ),

    CustomRule(
        "scalability_conflict",
        _check_scalability_conflicts,
        "Detects conflicting scalability requirements",
        Severity.MEDIUM
    ),

    CustomRule(
        "consistency_conflict",
        _check_consistency_conflicts,
        "Detects conflicting data consistency requirements",
        Severity.MEDIUM
    )
]


# Common contradiction patterns for quick detection
LOGICAL_CONTRADICTIONS = [
    {
        "id": "always_never",
        "pattern": r"\b(always|never)\b.*\b(never|always)\b",
        "description": "Conflicting always/never statements",
        "severity": Severity.HIGH
    },
    {
        "id": "all_none",
        "pattern": r"\b(all|none)\b.*\b(none|all)\b",
        "description": "Conflicting all/none statements",
        "severity": Severity.HIGH
    },
    {
        "id": "required_optional",
        "pattern": r"\b(required|mandatory)\b.*\b(optional|not required)\b",
        "description": "Conflicting required/optional statements",
        "severity": Severity.HIGH
    },
    {
        "id": "enabled_disabled",
        "pattern": r"\b(enabled|disabled)\b.*\b(disabled|enabled)\b",
        "description": "Conflicting enabled/disabled statements",
        "severity": Severity.MEDIUM
    }
]


# Semantic contradiction patterns
SEMANTIC_CONTRADICTIONS = [
    {
        "positive_terms": ["allow", "enable", "permit", "accept"],
        "negative_terms": ["deny", "disable", "reject", "block"],
        "description": "Conflicting allow/deny statements",
        "severity": Severity.HIGH
    },
    {
        "positive_terms": ["create", "add", "insert", "new"],
        "negative_terms": ["delete", "remove", "destroy", "eliminate"],
        "description": "Conflicting create/delete operations",
        "severity": Severity.MEDIUM
    },
    {
        "positive_terms": ["show", "display", "visible", "reveal"],
        "negative_terms": ["hide", "conceal", "invisible", "mask"],
        "description": "Conflicting visibility requirements",
        "severity": Severity.MEDIUM
    }
]


def find_contradiction_patterns(text: str) -> List[Dict[str, Any]]:
    """
    Find contradiction patterns in text using predefined patterns.

    Returns list of found contradictions with details.
    """
    contradictions = []

    # Check logical contradictions
    for pattern_info in LOGICAL_CONTRADICTIONS:
        matches = re.finditer(pattern_info["pattern"], text, re.IGNORECASE)
        for match in matches:
            contradictions.append({
                "type": "logical",
                "pattern_id": pattern_info["id"],
                "description": pattern_info["description"],
                "text_match": match.group(),
                "severity": pattern_info["severity"],
                "position": (match.start(), match.end())
            })

    # Check semantic contradictions
    for semantic_pattern in SEMANTIC_CONTRADICTIONS:
        positive_found = []
        negative_found = []

        for term in semantic_pattern["positive_terms"]:
            if term in text.lower():
                positive_found.append(term)

        for term in semantic_pattern["negative_terms"]:
            if term in text.lower():
                negative_found.append(term)

        if positive_found and negative_found:
            contradictions.append({
                "type": "semantic",
                "description": semantic_pattern["description"],
                "positive_terms": positive_found,
                "negative_terms": negative_found,
                "severity": semantic_pattern["severity"]
            })

    return contradictions