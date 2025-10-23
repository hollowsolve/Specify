"""
Rule definitions for completeness validation.

This module contains rules for detecting gaps in requirement completeness
across standard software requirement categories.
"""

from typing import List, Dict, Any
from .rule_engine import Rule, RegexRule, KeywordRule, CustomRule, RuleResult
from ..models import Severity


def _check_authentication_requirements(text: str, context: Dict[str, Any]) -> RuleResult:
    """Check if authentication requirements are specified when needed."""
    user_keywords = ["user", "login", "account", "profile", "member"]
    auth_keywords = ["authentication", "login", "password", "credential", "token", "session"]

    has_user_concepts = any(keyword in text.lower() for keyword in user_keywords)
    has_auth_concepts = any(keyword in text.lower() for keyword in auth_keywords)

    if has_user_concepts and not has_auth_concepts:
        return RuleResult(
            rule_id="missing_authentication",
            matched=True,
            confidence=0.8,
            severity=Severity.HIGH,
            message="User-related functionality detected without authentication requirements",
            metadata={"category": "authentication"}
        )

    return RuleResult("missing_authentication", False)


def _check_data_persistence_requirements(text: str, context: Dict[str, Any]) -> RuleResult:
    """Check if data persistence requirements are specified when needed."""
    data_keywords = ["save", "store", "data", "record", "information", "create", "update", "delete"]
    persistence_keywords = ["database", "storage", "persist", "save", "backup", "recovery"]

    has_data_operations = any(keyword in text.lower() for keyword in data_keywords)
    has_persistence_specs = any(keyword in text.lower() for keyword in persistence_keywords)

    if has_data_operations and not has_persistence_specs:
        return RuleResult(
            rule_id="missing_data_persistence",
            matched=True,
            confidence=0.7,
            severity=Severity.MEDIUM,
            message="Data operations detected without persistence requirements",
            metadata={"category": "data_persistence"}
        )

    return RuleResult("missing_data_persistence", False)


def _check_api_documentation_requirements(text: str, context: Dict[str, Any]) -> RuleResult:
    """Check if API documentation requirements are specified for API endpoints."""
    api_keywords = ["api", "endpoint", "service", "rest", "graphql", "webhook"]
    doc_keywords = ["documentation", "docs", "swagger", "openapi", "spec", "schema"]

    has_api_concepts = any(keyword in text.lower() for keyword in api_keywords)
    has_doc_concepts = any(keyword in text.lower() for keyword in doc_keywords)

    if has_api_concepts and not has_doc_concepts:
        return RuleResult(
            rule_id="missing_api_documentation",
            matched=True,
            confidence=0.8,
            severity=Severity.MEDIUM,
            message="API functionality detected without documentation requirements",
            metadata={"category": "documentation"}
        )

    return RuleResult("missing_api_documentation", False)


# Pre-defined rules for completeness validation
COMPLETENESS_RULES: List[Rule] = [
    # Input specification rules
    RegexRule(
        "input_format_missing",
        r"\b(input|data|parameter|field)\b(?!.*\b(format|type|structure|schema)\b)",
        "Detects input mentions without format specification",
        Severity.MEDIUM,
        confidence=0.6
    ),

    # Output specification rules
    RegexRule(
        "output_format_missing",
        r"\b(output|result|response|return)\b(?!.*\b(format|type|structure|schema)\b)",
        "Detects output mentions without format specification",
        Severity.MEDIUM,
        confidence=0.6
    ),

    # Error handling requirements
    KeywordRule(
        "error_handling_missing",
        ["operation", "process", "function", "method", "action"],
        "Detects operations that may need error handling",
        Severity.MEDIUM,
        confidence=0.5
    ),

    # Performance requirements
    RegexRule(
        "performance_specs_missing",
        r"\b(process|calculate|compute|generate|load|search)\b(?!.*\b(time|speed|performance|latency|timeout)\b)",
        "Detects operations without performance specifications",
        Severity.LOW,
        confidence=0.5
    ),

    # Security requirements
    KeywordRule(
        "security_missing",
        ["data", "information", "user", "account", "system"],
        "Detects concepts that may need security considerations",
        Severity.MEDIUM,
        confidence=0.4
    ),

    # Validation requirements
    RegexRule(
        "validation_missing",
        r"\b(input|data|form|field)\b(?!.*\b(valid|validate|check|verify)\b)",
        "Detects inputs without validation requirements",
        Severity.MEDIUM,
        confidence=0.6
    ),

    # User interface requirements
    KeywordRule(
        "ui_specs_missing",
        ["display", "show", "interface", "screen", "page", "form"],
        "Detects UI elements that may need detailed specifications",
        Severity.LOW,
        confidence=0.4
    ),

    # Configuration requirements
    KeywordRule(
        "config_missing",
        ["system", "application", "service", "environment"],
        "Detects systems that may need configuration requirements",
        Severity.LOW,
        confidence=0.3
    ),

    # Monitoring and logging requirements
    KeywordRule(
        "monitoring_missing",
        ["operation", "process", "transaction", "request"],
        "Detects operations that may need monitoring/logging",
        Severity.LOW,
        confidence=0.3
    ),

    # Custom completeness rules
    CustomRule(
        "missing_authentication",
        _check_authentication_requirements,
        "Checks for missing authentication requirements",
        Severity.HIGH
    ),

    CustomRule(
        "missing_data_persistence",
        _check_data_persistence_requirements,
        "Checks for missing data persistence requirements",
        Severity.MEDIUM
    ),

    CustomRule(
        "missing_api_documentation",
        _check_api_documentation_requirements,
        "Checks for missing API documentation requirements",
        Severity.MEDIUM
    )
]


# Standard requirement categories for completeness checking
REQUIREMENT_CATEGORIES = {
    "functional": {
        "description": "What the system should do",
        "indicators": ["function", "feature", "capability", "behavior", "action", "process"],
        "required_specs": ["input", "output", "behavior", "rules"]
    },
    "input_specification": {
        "description": "Input data and parameters",
        "indicators": ["input", "parameter", "data", "field", "value"],
        "required_specs": ["format", "type", "validation", "constraints"]
    },
    "output_specification": {
        "description": "Output data and results",
        "indicators": ["output", "result", "response", "return", "generate"],
        "required_specs": ["format", "type", "structure", "content"]
    },
    "error_handling": {
        "description": "Error and exception handling",
        "indicators": ["error", "exception", "fail", "invalid", "wrong"],
        "required_specs": ["error_types", "error_messages", "recovery", "fallback"]
    },
    "performance": {
        "description": "Performance and scalability requirements",
        "indicators": ["performance", "speed", "time", "scale", "load"],
        "required_specs": ["response_time", "throughput", "scalability", "resource_usage"]
    },
    "security": {
        "description": "Security and privacy requirements",
        "indicators": ["security", "authentication", "authorization", "privacy", "access"],
        "required_specs": ["authentication", "authorization", "encryption", "data_protection"]
    },
    "validation": {
        "description": "Data validation requirements",
        "indicators": ["validate", "check", "verify", "correct", "valid"],
        "required_specs": ["validation_rules", "error_messages", "constraints"]
    },
    "user_interface": {
        "description": "User interface requirements",
        "indicators": ["interface", "ui", "display", "show", "screen", "form"],
        "required_specs": ["layout", "interaction", "accessibility", "responsiveness"]
    },
    "integration": {
        "description": "Integration and API requirements",
        "indicators": ["api", "integration", "external", "service", "webhook"],
        "required_specs": ["endpoints", "protocols", "data_format", "authentication"]
    },
    "configuration": {
        "description": "Configuration and deployment requirements",
        "indicators": ["config", "setting", "environment", "deployment"],
        "required_specs": ["parameters", "environment_variables", "deployment_target"]
    },
    "monitoring": {
        "description": "Monitoring and logging requirements",
        "indicators": ["monitor", "log", "track", "audit", "report"],
        "required_specs": ["metrics", "logging_level", "alerting", "reporting"]
    },
    "maintenance": {
        "description": "Maintenance and support requirements",
        "indicators": ["maintain", "update", "support", "backup", "recovery"],
        "required_specs": ["update_mechanism", "backup_strategy", "recovery_procedures"]
    }
}


# Priority levels for different requirement categories
CATEGORY_PRIORITY = {
    "functional": Severity.HIGH,
    "input_specification": Severity.HIGH,
    "output_specification": Severity.HIGH,
    "error_handling": Severity.HIGH,
    "security": Severity.HIGH,
    "validation": Severity.MEDIUM,
    "performance": Severity.MEDIUM,
    "integration": Severity.MEDIUM,
    "user_interface": Severity.LOW,
    "configuration": Severity.LOW,
    "monitoring": Severity.LOW,
    "maintenance": Severity.LOW
}