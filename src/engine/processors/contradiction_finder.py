"""
Contradiction detection processor.

This module implements sophisticated contradiction detection using a hybrid
approach combining rule-based patterns with LLM semantic understanding.
"""

import time
import re
from typing import List, Dict, Any, Tuple, Optional, Set
from itertools import combinations
from ..models import AnalysisResult, Contradiction, Severity
from ..rules import RuleEngine, CONTRADICTION_PATTERNS, find_contradiction_patterns
from ..config import ProcessorConfig, ProcessorMode, get_config


class ContradictionFinder:
    """
    Sophisticated contradiction detection using hybrid rule-based + LLM approach.

    This processor identifies conflicts and contradictions between requirements
    using pattern matching, semantic analysis, and logical reasoning.
    """

    def __init__(self, config: Optional[ProcessorConfig] = None):
        self.config = config or get_config().contradiction_finder
        self.rule_engine = RuleEngine()
        self._setup_rules()

        # Negation patterns for logical contradiction detection
        self.negation_patterns = [
            r"\b(not|no|never|cannot|can't|won't|shouldn't|mustn't)\b",
            r"\b(without|except|unless|disable|prevent|block|deny)\b",
            r"\b(refuse|reject|forbid|prohibit|disallow)\b"
        ]

        # Conflict indicator patterns
        self.conflict_indicators = [
            ("always", "never"),
            ("all", "none"),
            ("required", "optional"),
            ("mandatory", "voluntary"),
            ("public", "private"),
            ("enable", "disable"),
            ("allow", "deny"),
            ("include", "exclude"),
            ("maximum", "minimum"),
            ("before", "after"),
            ("first", "last")
        ]

    def _setup_rules(self) -> None:
        """Setup the rule engine with contradiction detection rules."""
        # Register core contradiction rules
        self.rule_engine.register_rules(CONTRADICTION_PATTERNS, "contradictions")

    def find_contradictions(self, analysis: AnalysisResult, context: Dict[str, Any] = None) -> List[Contradiction]:
        """
        Find contradictions in the analysis result.

        Args:
            analysis: The analysis result from Phase 1
            context: Additional context for contradiction detection

        Returns:
            List of detected contradictions
        """
        if not self.config.enabled:
            return []

        context = context or {}
        contradictions = []

        start_time = time.time()

        try:
            # Collect all textual requirements
            all_requirements = (
                analysis.explicit_requirements +
                analysis.implicit_assumptions
            )

            if len(all_requirements) < 2:
                return []  # Need at least 2 requirements to have contradictions

            # Phase 1: Rule-based contradiction detection
            rule_contradictions = self._detect_rule_based_contradictions(all_requirements, context)
            contradictions.extend(rule_contradictions)

            # Phase 2: Pairwise logical analysis
            logical_contradictions = self._detect_logical_contradictions(all_requirements, context)
            contradictions.extend(logical_contradictions)

            # Phase 3: Semantic contradiction detection
            semantic_contradictions = self._detect_semantic_contradictions(all_requirements, context)
            contradictions.extend(semantic_contradictions)

            # Phase 4: LLM-based contradiction detection (if enabled)
            if self.config.mode in [ProcessorMode.BALANCED, ProcessorMode.INTELLIGENT]:
                llm_contradictions = self._detect_llm_contradictions(analysis, context, contradictions)
                contradictions.extend(llm_contradictions)

            # Filter and deduplicate
            contradictions = self._filter_and_deduplicate(contradictions)

        except Exception as e:
            print(f"Error in contradiction detection: {e}")

        processing_time = time.time() - start_time
        print(f"Contradiction detection completed in {processing_time:.2f}s, found {len(contradictions)} contradictions")

        return contradictions

    def _detect_rule_based_contradictions(self, requirements: List[str], context: Dict[str, Any]) -> List[Contradiction]:
        """Detect contradictions using predefined rule patterns."""
        contradictions = []

        # Apply rules to combined text
        combined_text = " ".join(requirements)
        results = self.rule_engine.apply_rules(combined_text, context, category="contradictions")

        for result in results:
            if result.matched and result.confidence >= self.config.confidence_threshold:
                contradiction = self._rule_result_to_contradiction(result, requirements)
                if contradiction:
                    contradictions.append(contradiction)

        # Use pattern-based detection
        pattern_contradictions = find_contradiction_patterns(combined_text)
        for pattern_contradiction in pattern_contradictions:
            contradiction = self._pattern_to_contradiction(pattern_contradiction, requirements)
            if contradiction:
                contradictions.append(contradiction)

        return contradictions

    def _detect_logical_contradictions(self, requirements: List[str], context: Dict[str, Any]) -> List[Contradiction]:
        """Detect logical contradictions between requirement pairs."""
        contradictions = []

        # Check all pairs of requirements
        for i, req1 in enumerate(requirements):
            for j, req2 in enumerate(requirements[i + 1:], i + 1):
                contradiction = self._analyze_requirement_pair(req1, req2)
                if contradiction:
                    contradictions.append(contradiction)

        return contradictions

    def _detect_semantic_contradictions(self, requirements: List[str], context: Dict[str, Any]) -> List[Contradiction]:
        """Detect semantic contradictions using domain knowledge."""
        contradictions = []

        # Domain-specific contradiction patterns
        domain_patterns = {
            "data_access": {
                "conflicting_terms": [
                    (["read-only", "readonly"], ["write", "update", "modify", "edit"]),
                    (["public"], ["private", "restricted", "confidential"]),
                    (["cached"], ["real-time", "live", "immediate"])
                ]
            },
            "user_interface": {
                "conflicting_terms": [
                    (["visible", "show", "display"], ["hidden", "hide", "invisible"]),
                    (["required", "mandatory"], ["optional", "voluntary"]),
                    (["enabled"], ["disabled", "inactive"])
                ]
            },
            "performance": {
                "conflicting_terms": [
                    (["fast", "quick", "immediate"], ["slow", "delayed", "batch"]),
                    (["synchronous", "blocking"], ["asynchronous", "non-blocking"]),
                    (["single-threaded"], ["multi-threaded", "concurrent"])
                ]
            }
        }

        for domain, patterns in domain_patterns.items():
            for req1, req2 in combinations(requirements, 2):
                for positive_terms, negative_terms in patterns["conflicting_terms"]:
                    if (self._contains_terms(req1, positive_terms) and self._contains_terms(req2, negative_terms)) or \
                       (self._contains_terms(req1, negative_terms) and self._contains_terms(req2, positive_terms)):

                        explanation = f"Semantic contradiction in {domain}: conflicting requirements"
                        contradiction = Contradiction(
                            requirement_1=req1,
                            requirement_2=req2,
                            explanation=explanation,
                            severity=Severity.MEDIUM,
                            suggested_resolution=f"Clarify the {domain} requirements to resolve the conflict",
                            confidence=0.7
                        )
                        contradictions.append(contradiction)

        return contradictions

    def _analyze_requirement_pair(self, req1: str, req2: str) -> Optional[Contradiction]:
        """Analyze a pair of requirements for logical contradictions."""
        req1_lower = req1.lower()
        req2_lower = req2.lower()

        # Check for direct negation patterns
        req1_negated = self._is_negated(req1_lower)
        req2_negated = self._is_negated(req2_lower)

        # Extract key terms for comparison
        req1_terms = self._extract_key_terms(req1_lower)
        req2_terms = self._extract_key_terms(req2_lower)

        # Check for overlapping terms with opposite polarities
        common_terms = req1_terms.intersection(req2_terms)

        if common_terms and (req1_negated != req2_negated):
            explanation = f"Logical contradiction: one requirement negates what the other asserts"
            suggested_resolution = "Review and clarify the conflicting requirements"

            return Contradiction(
                requirement_1=req1,
                requirement_2=req2,
                explanation=explanation,
                severity=Severity.HIGH,
                suggested_resolution=suggested_resolution,
                confidence=0.8
            )

        # Check for explicit conflict indicators
        for term1, term2 in self.conflict_indicators:
            if (term1 in req1_lower and term2 in req2_lower) or (term2 in req1_lower and term1 in req2_lower):
                # Check if they're referring to the same subject
                if self._have_common_subject(req1, req2):
                    explanation = f"Conflicting requirements: {term1} vs {term2}"
                    suggested_resolution = f"Clarify whether the requirement should be {term1} or {term2}"

                    return Contradiction(
                        requirement_1=req1,
                        requirement_2=req2,
                        explanation=explanation,
                        severity=Severity.MEDIUM,
                        suggested_resolution=suggested_resolution,
                        confidence=0.7
                    )

        return None

    def _is_negated(self, text: str) -> bool:
        """Check if a requirement contains negation patterns."""
        for pattern in self.negation_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _extract_key_terms(self, text: str) -> Set[str]:
        """Extract key terms from requirement text."""
        # Remove negation words and common words
        words = re.findall(r'\b\w+\b', text.lower())

        # Filter out common words and negation indicators
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "up", "about", "into", "through",
            "not", "no", "never", "cannot", "can't", "won't", "shouldn't",
            "must", "should", "will", "can", "could", "would", "may", "might"
        }

        key_terms = {word for word in words if len(word) > 2 and word not in stop_words}
        return key_terms

    def _contains_terms(self, text: str, terms: List[str]) -> bool:
        """Check if text contains any of the specified terms."""
        text_lower = text.lower()
        return any(term.lower() in text_lower for term in terms)

    def _have_common_subject(self, req1: str, req2: str) -> bool:
        """Check if two requirements refer to the same subject/entity."""
        # Extract potential subjects (nouns and entities)
        subjects1 = self._extract_subjects(req1)
        subjects2 = self._extract_subjects(req2)

        # Check for overlap
        return bool(subjects1.intersection(subjects2))

    def _extract_subjects(self, text: str) -> Set[str]:
        """Extract potential subjects from requirement text."""
        # Simple heuristic: look for nouns and important entities
        words = re.findall(r'\b\w+\b', text.lower())

        # Common subjects in software requirements
        subject_indicators = [
            "user", "system", "application", "data", "file", "record", "form",
            "page", "screen", "button", "field", "table", "database", "server",
            "client", "api", "service", "function", "method", "component"
        ]

        subjects = {word for word in words if word in subject_indicators}

        # Also include capitalized words (likely entities) from original text
        capitalized = re.findall(r'\b[A-Z][a-z]+\b', text)
        subjects.update(word.lower() for word in capitalized)

        return subjects

    def _detect_llm_contradictions(self, analysis: AnalysisResult, context: Dict[str, Any],
                                  existing_contradictions: List[Contradiction]) -> List[Contradiction]:
        """Detect contradictions using LLM semantic understanding."""
        llm_config = get_config().llm

        if not llm_config.enabled:
            return []

        try:
            # Build prompt for LLM
            prompt = self._build_llm_contradiction_prompt(analysis, existing_contradictions, context)

            # Call LLM
            llm_response = self._call_llm_for_contradictions(prompt, llm_config)

            # Parse response
            return self._parse_llm_contradiction_response(llm_response)

        except Exception as e:
            print(f"LLM contradiction detection failed: {e}")
            return []

    def _build_llm_contradiction_prompt(self, analysis: AnalysisResult,
                                       existing_contradictions: List[Contradiction],
                                       context: Dict[str, Any]) -> str:
        """Build prompt for LLM contradiction detection."""
        existing_summary = []
        for contradiction in existing_contradictions:
            existing_summary.append(f"- {contradiction.explanation}")

        existing_text = "\n".join(existing_summary) if existing_summary else "None detected by rules"

        prompt = f"""
Analyze the following software requirements for logical contradictions and conflicts:

INTENT: {analysis.intent}

EXPLICIT REQUIREMENTS:
{chr(10).join(f"- {req}" for req in analysis.explicit_requirements)}

IMPLICIT ASSUMPTIONS:
{chr(10).join(f"- {assumption}" for assumption in analysis.implicit_assumptions)}

CONTRADICTIONS ALREADY DETECTED:
{existing_text}

Please identify additional contradictions that might not be caught by pattern matching. Look for:
1. Subtle logical conflicts
2. Implicit contradictions in assumptions
3. Conflicts between explicit requirements and implicit assumptions
4. Requirements that contradict the stated intent
5. Mutually exclusive technical constraints

For each contradiction, provide:
- The two conflicting requirements/statements
- Clear explanation of why they contradict
- Severity (low, medium, high, critical)
- Suggested resolution approach
- Confidence level (0.0-1.0)

Format as JSON array of objects.
"""

        return prompt

    def _call_llm_for_contradictions(self, prompt: str, llm_config) -> str:
        """Call LLM for contradiction detection."""
        # Placeholder for actual LLM integration
        # Simulated response for demonstration
        return '''[
  {
    "requirement_1": "User data must be immediately available",
    "requirement_2": "System should cache data for performance",
    "explanation": "Immediate availability conflicts with caching which introduces delay",
    "severity": "medium",
    "suggested_resolution": "Define acceptable delay thresholds for cached data",
    "confidence": 0.8
  }
]'''

    def _parse_llm_contradiction_response(self, response: str) -> List[Contradiction]:
        """Parse LLM response into Contradiction objects."""
        try:
            import json
            contradiction_data = json.loads(response)

            contradictions = []
            for data in contradiction_data:
                try:
                    severity = Severity(data.get("severity", "medium"))

                    contradiction = Contradiction(
                        requirement_1=data.get("requirement_1", ""),
                        requirement_2=data.get("requirement_2", ""),
                        explanation=data.get("explanation", ""),
                        severity=severity,
                        suggested_resolution=data.get("suggested_resolution", ""),
                        confidence=float(data.get("confidence", 0.5))
                    )

                    contradictions.append(contradiction)

                except (ValueError, TypeError) as e:
                    print(f"Error parsing LLM contradiction: {e}")

            return contradictions

        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            return []

    def _rule_result_to_contradiction(self, result, requirements: List[str]) -> Optional[Contradiction]:
        """Convert a rule result to a Contradiction object."""
        try:
            # Try to extract the specific requirements from metadata
            if "conflicting_terms" in result.metadata:
                terms = result.metadata["conflicting_terms"]
                req1, req2 = self._find_requirements_with_terms(requirements, terms)
            else:
                # Fallback: use first two requirements
                req1 = requirements[0] if requirements else "Unknown requirement"
                req2 = requirements[1] if len(requirements) > 1 else "Unknown requirement"

            return Contradiction(
                requirement_1=req1,
                requirement_2=req2,
                explanation=result.message,
                severity=result.severity,
                suggested_resolution=f"Review and resolve the {result.metadata.get('type', 'conflict')}",
                confidence=result.confidence
            )

        except Exception as e:
            print(f"Error converting rule result to contradiction: {e}")
            return None

    def _pattern_to_contradiction(self, pattern_data: Dict[str, Any], requirements: List[str]) -> Optional[Contradiction]:
        """Convert pattern detection result to Contradiction object."""
        try:
            severity = pattern_data.get("severity", Severity.MEDIUM)
            if isinstance(severity, str):
                severity = Severity(severity)

            # Find requirements containing the conflicting terms
            if "positive_terms" in pattern_data and "negative_terms" in pattern_data:
                req1, req2 = self._find_requirements_with_semantic_conflict(
                    requirements,
                    pattern_data["positive_terms"],
                    pattern_data["negative_terms"]
                )
            else:
                req1 = requirements[0] if requirements else "Unknown requirement"
                req2 = requirements[1] if len(requirements) > 1 else "Unknown requirement"

            return Contradiction(
                requirement_1=req1,
                requirement_2=req2,
                explanation=pattern_data["description"],
                severity=severity,
                suggested_resolution="Clarify the conflicting requirements",
                confidence=0.7
            )

        except Exception as e:
            print(f"Error converting pattern to contradiction: {e}")
            return None

    def _find_requirements_with_terms(self, requirements: List[str], terms: List[str]) -> Tuple[str, str]:
        """Find requirements containing specific terms."""
        found_reqs = []

        for req in requirements:
            req_lower = req.lower()
            if any(term.lower() in req_lower for term in terms):
                found_reqs.append(req)

        if len(found_reqs) >= 2:
            return found_reqs[0], found_reqs[1]
        elif len(found_reqs) == 1:
            return found_reqs[0], requirements[0] if requirements[0] != found_reqs[0] else (requirements[1] if len(requirements) > 1 else "Unknown")
        else:
            return (requirements[0] if requirements else "Unknown", requirements[1] if len(requirements) > 1 else "Unknown")

    def _find_requirements_with_semantic_conflict(self, requirements: List[str],
                                                positive_terms: List[str],
                                                negative_terms: List[str]) -> Tuple[str, str]:
        """Find requirements with semantic conflicts."""
        positive_req = None
        negative_req = None

        for req in requirements:
            req_lower = req.lower()
            if any(term.lower() in req_lower for term in positive_terms):
                positive_req = req
            if any(term.lower() in req_lower for term in negative_terms):
                negative_req = req

        return (
            positive_req or (requirements[0] if requirements else "Unknown"),
            negative_req or (requirements[1] if len(requirements) > 1 else "Unknown")
        )

    def _filter_and_deduplicate(self, contradictions: List[Contradiction]) -> List[Contradiction]:
        """Filter and deduplicate contradictions."""
        if not contradictions:
            return []

        # Filter by confidence threshold
        filtered = [
            contradiction for contradiction in contradictions
            if contradiction.confidence >= self.config.confidence_threshold
        ]

        # Deduplicate based on similarity
        deduplicated = []
        for contradiction in filtered:
            is_duplicate = False
            for existing in deduplicated:
                if self._are_similar_contradictions(contradiction, existing):
                    # Keep the one with higher confidence
                    if contradiction.confidence > existing.confidence:
                        deduplicated.remove(existing)
                        deduplicated.append(contradiction)
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduplicated.append(contradiction)

        # Sort by severity and confidence
        severity_order = {Severity.CRITICAL: 4, Severity.HIGH: 3, Severity.MEDIUM: 2, Severity.LOW: 1}
        deduplicated.sort(
            key=lambda x: (severity_order.get(x.severity, 0), x.confidence),
            reverse=True
        )

        # Limit results
        if self.config.max_results > 0:
            deduplicated = deduplicated[:self.config.max_results]

        return deduplicated

    def _are_similar_contradictions(self, contradiction1: Contradiction, contradiction2: Contradiction) -> bool:
        """Check if two contradictions are similar enough to be considered duplicates."""
        # Check if they involve the same requirements (in any order)
        reqs1 = {contradiction1.requirement_1, contradiction1.requirement_2}
        reqs2 = {contradiction2.requirement_1, contradiction2.requirement_2}

        if reqs1 == reqs2:
            return True

        # Check explanation similarity
        explanation1_words = set(contradiction1.explanation.lower().split())
        explanation2_words = set(contradiction2.explanation.lower().split())

        if explanation1_words and explanation2_words:
            intersection = len(explanation1_words.intersection(explanation2_words))
            union = len(explanation1_words.union(explanation2_words))
            similarity = intersection / union if union > 0 else 0

            if similarity > 0.7:  # 70% similarity threshold
                return True

        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the contradiction finder."""
        rule_stats = self.rule_engine.get_rule_statistics()

        return {
            "config": {
                "enabled": self.config.enabled,
                "mode": self.config.mode.value,
                "confidence_threshold": self.config.confidence_threshold,
                "max_results": self.config.max_results
            },
            "rules": rule_stats,
            "conflict_indicators_count": len(self.conflict_indicators),
            "negation_patterns_count": len(self.negation_patterns),
            "severities": [severity.value for severity in Severity]
        }