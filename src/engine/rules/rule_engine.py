"""
Core rule engine for extensible rule-based processing.

This module provides the foundation for rule-based processing in the
specification engine.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable, Pattern
from enum import Enum

from ..models import Severity


class RuleType(Enum):
    """Types of rules supported by the rule engine."""
    REGEX = "regex"
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    LOGICAL = "logical"
    CUSTOM = "custom"


@dataclass
class RuleResult:
    """
    Result of applying a rule to some text or data.

    Attributes:
        rule_id: Identifier of the rule that produced this result
        matched: Whether the rule matched
        confidence: Confidence score (0.0-1.0)
        severity: Severity level if the rule indicates an issue
        message: Human-readable message about the match
        metadata: Additional data about the match
    """
    rule_id: str
    matched: bool
    confidence: float = 0.0
    severity: Severity = Severity.LOW
    message: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


class Rule(ABC):
    """
    Abstract base class for all rules in the rule engine.

    Rules are the building blocks of the specification engine's intelligence.
    They can be regex-based for speed or semantic-based for intelligence.
    """

    def __init__(self, rule_id: str, rule_type: RuleType, description: str,
                 severity: Severity = Severity.LOW, enabled: bool = True):
        self.rule_id = rule_id
        self.rule_type = rule_type
        self.description = description
        self.severity = severity
        self.enabled = enabled

    @abstractmethod
    def apply(self, text: str, context: Dict[str, Any] = None) -> RuleResult:
        """
        Apply the rule to the given text.

        Args:
            text: The text to analyze
            context: Additional context for rule evaluation

        Returns:
            RuleResult indicating whether the rule matched and details
        """
        pass

    def __repr__(self) -> str:
        return f"Rule(id={self.rule_id}, type={self.rule_type.value}, enabled={self.enabled})"


class RegexRule(Rule):
    """
    A rule based on regular expression matching.

    Fast and efficient for pattern-based detection.
    """

    def __init__(self, rule_id: str, pattern: str, description: str,
                 severity: Severity = Severity.LOW, flags: int = 0,
                 confidence: float = 0.8, enabled: bool = True):
        super().__init__(rule_id, RuleType.REGEX, description, severity, enabled)
        self.pattern: Pattern = re.compile(pattern, flags)
        self.confidence = confidence

    def apply(self, text: str, context: Dict[str, Any] = None) -> RuleResult:
        if not self.enabled:
            return RuleResult(self.rule_id, False)

        match = self.pattern.search(text)
        if match:
            return RuleResult(
                rule_id=self.rule_id,
                matched=True,
                confidence=self.confidence,
                severity=self.severity,
                message=f"Pattern matched: {self.description}",
                metadata={"match": match.group(), "start": match.start(), "end": match.end()}
            )

        return RuleResult(self.rule_id, False)


class KeywordRule(Rule):
    """
    A rule based on keyword matching.

    Simple but effective for detecting specific terms or phrases.
    """

    def __init__(self, rule_id: str, keywords: List[str], description: str,
                 severity: Severity = Severity.LOW, case_sensitive: bool = False,
                 confidence: float = 0.7, enabled: bool = True):
        super().__init__(rule_id, RuleType.KEYWORD, description, severity, enabled)
        self.keywords = keywords
        self.case_sensitive = case_sensitive
        self.confidence = confidence

    def apply(self, text: str, context: Dict[str, Any] = None) -> RuleResult:
        if not self.enabled:
            return RuleResult(self.rule_id, False)

        check_text = text if self.case_sensitive else text.lower()
        keywords_to_check = self.keywords if self.case_sensitive else [kw.lower() for kw in self.keywords]

        found_keywords = []
        for keyword in keywords_to_check:
            if keyword in check_text:
                found_keywords.append(keyword)

        if found_keywords:
            return RuleResult(
                rule_id=self.rule_id,
                matched=True,
                confidence=self.confidence,
                severity=self.severity,
                message=f"Keywords found: {', '.join(found_keywords)}",
                metadata={"keywords_found": found_keywords}
            )

        return RuleResult(self.rule_id, False)


class CustomRule(Rule):
    """
    A rule with custom logic provided by a callable.

    Maximum flexibility for complex rule logic.
    """

    def __init__(self, rule_id: str, func: Callable[[str, Dict[str, Any]], RuleResult],
                 description: str, severity: Severity = Severity.LOW, enabled: bool = True):
        super().__init__(rule_id, RuleType.CUSTOM, description, severity, enabled)
        self.func = func

    def apply(self, text: str, context: Dict[str, Any] = None) -> RuleResult:
        if not self.enabled:
            return RuleResult(self.rule_id, False)

        return self.func(text, context or {})


class RuleEngine:
    """
    Engine for managing and executing rules.

    The rule engine provides a centralized way to manage rule execution,
    configuration, and results aggregation.
    """

    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self.rule_categories: Dict[str, List[str]] = {}

    def register_rule(self, rule: Rule, category: str = "default") -> None:
        """Register a rule with the engine."""
        self.rules[rule.rule_id] = rule

        if category not in self.rule_categories:
            self.rule_categories[category] = []
        self.rule_categories[category].append(rule.rule_id)

    def register_rules(self, rules: List[Rule], category: str = "default") -> None:
        """Register multiple rules at once."""
        for rule in rules:
            self.register_rule(rule, category)

    def enable_rule(self, rule_id: str) -> None:
        """Enable a specific rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True

    def disable_rule(self, rule_id: str) -> None:
        """Disable a specific rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False

    def enable_category(self, category: str) -> None:
        """Enable all rules in a category."""
        if category in self.rule_categories:
            for rule_id in self.rule_categories[category]:
                self.enable_rule(rule_id)

    def disable_category(self, category: str) -> None:
        """Disable all rules in a category."""
        if category in self.rule_categories:
            for rule_id in self.rule_categories[category]:
                self.disable_rule(rule_id)

    def apply_rules(self, text: str, context: Dict[str, Any] = None,
                   category: str = None, rule_ids: List[str] = None) -> List[RuleResult]:
        """
        Apply rules to text and return results.

        Args:
            text: Text to analyze
            context: Additional context for rule evaluation
            category: Only apply rules from this category
            rule_ids: Only apply these specific rules

        Returns:
            List of RuleResult objects
        """
        results = []
        rules_to_apply = self._get_rules_to_apply(category, rule_ids)

        for rule in rules_to_apply:
            try:
                result = rule.apply(text, context)
                results.append(result)
            except Exception as e:
                # Log error but don't fail the entire process
                error_result = RuleResult(
                    rule_id=rule.rule_id,
                    matched=False,
                    message=f"Rule execution failed: {str(e)}",
                    metadata={"error": str(e)}
                )
                results.append(error_result)

        return results

    def get_matched_results(self, results: List[RuleResult]) -> List[RuleResult]:
        """Filter results to only include matches."""
        return [result for result in results if result.matched]

    def get_high_confidence_results(self, results: List[RuleResult],
                                  threshold: float = 0.8) -> List[RuleResult]:
        """Filter results to only include high-confidence matches."""
        return [result for result in results if result.matched and result.confidence >= threshold]

    def get_results_by_severity(self, results: List[RuleResult],
                              severity: Severity) -> List[RuleResult]:
        """Filter results by severity level."""
        return [result for result in results if result.matched and result.severity == severity]

    def _get_rules_to_apply(self, category: str = None,
                          rule_ids: List[str] = None) -> List[Rule]:
        """Get the list of rules to apply based on filters."""
        if rule_ids:
            return [self.rules[rule_id] for rule_id in rule_ids if rule_id in self.rules]

        if category:
            if category in self.rule_categories:
                return [self.rules[rule_id] for rule_id in self.rule_categories[category]]
            else:
                return []

        return list(self.rules.values())

    def get_rule_statistics(self) -> Dict[str, Any]:
        """Get statistics about registered rules."""
        total_rules = len(self.rules)
        enabled_rules = sum(1 for rule in self.rules.values() if rule.enabled)

        severity_counts = {}
        type_counts = {}

        for rule in self.rules.values():
            # Count by severity
            severity_key = rule.severity.value
            severity_counts[severity_key] = severity_counts.get(severity_key, 0) + 1

            # Count by type
            type_key = rule.rule_type.value
            type_counts[type_key] = type_counts.get(type_key, 0) + 1

        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "disabled_rules": total_rules - enabled_rules,
            "categories": list(self.rule_categories.keys()),
            "severity_distribution": severity_counts,
            "type_distribution": type_counts
        }