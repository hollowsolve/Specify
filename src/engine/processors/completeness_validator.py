"""
Completeness validation processor.

This module implements comprehensive gap analysis to identify missing
requirements across standard software requirement categories.
"""

import time
from typing import List, Dict, Any, Set, Optional
from ..models import AnalysisResult, CompletenessGap, Severity
from ..rules import RuleEngine, COMPLETENESS_RULES, REQUIREMENT_CATEGORIES, CATEGORY_PRIORITY
from ..config import ProcessorConfig, ProcessorMode, get_config


class CompletenessValidator:
    """
    Comprehensive completeness validation using hybrid rule-based + LLM approach.

    This processor identifies gaps in requirement completeness by checking
    against standard software requirement categories and using intelligent
    analysis to suggest missing requirements.
    """

    def __init__(self, config: Optional[ProcessorConfig] = None):
        self.config = config or get_config().completeness_validator
        self.rule_engine = RuleEngine()
        self._setup_rules()

        # Standard requirement categories to check
        self.requirement_categories = REQUIREMENT_CATEGORIES
        self.category_priority = CATEGORY_PRIORITY

        # Additional domain-specific categories
        self.domain_categories = {
            "web_application": {
                "authentication": ["login", "logout", "session", "password", "user"],
                "navigation": ["menu", "link", "page", "route", "url"],
                "responsive_design": ["mobile", "tablet", "desktop", "responsive", "screen"],
                "accessibility": ["wcag", "aria", "screen reader", "keyboard", "contrast"]
            },
            "api_service": {
                "endpoints": ["api", "endpoint", "route", "path", "method"],
                "data_format": ["json", "xml", "request", "response", "schema"],
                "rate_limiting": ["throttle", "limit", "quota", "rate", "concurrency"],
                "versioning": ["version", "compatibility", "deprecated", "migration"]
            },
            "data_processing": {
                "data_sources": ["input", "source", "import", "file", "database"],
                "transformation": ["transform", "process", "convert", "parse", "validate"],
                "data_quality": ["validation", "cleansing", "duplicate", "integrity"],
                "output_formats": ["export", "output", "format", "destination"]
            }
        }

    def _setup_rules(self) -> None:
        """Setup the rule engine with completeness validation rules."""
        # Register core completeness rules
        self.rule_engine.register_rules(COMPLETENESS_RULES, "completeness")

    def validate_completeness(self, analysis: AnalysisResult, context: Dict[str, Any] = None) -> List[CompletenessGap]:
        """
        Validate completeness of requirements and identify gaps.

        Args:
            analysis: The analysis result from Phase 1
            context: Additional context for completeness validation

        Returns:
            List of identified completeness gaps
        """
        if not self.config.enabled:
            return []

        context = context or {}
        gaps = []

        start_time = time.time()

        try:
            # Phase 1: Rule-based gap detection
            rule_gaps = self._detect_rule_based_gaps(analysis, context)
            gaps.extend(rule_gaps)

            # Phase 2: Category-based completeness check
            category_gaps = self._check_category_completeness(analysis, context)
            gaps.extend(category_gaps)

            # Phase 3: Domain-specific gap detection
            domain_gaps = self._detect_domain_specific_gaps(analysis, context)
            gaps.extend(domain_gaps)

            # Phase 4: LLM-based gap analysis (if enabled)
            if self.config.mode in [ProcessorMode.BALANCED, ProcessorMode.INTELLIGENT]:
                llm_gaps = self._detect_llm_gaps(analysis, context, gaps)
                gaps.extend(llm_gaps)

            # Filter and prioritize
            gaps = self._filter_and_prioritize_gaps(gaps)

        except Exception as e:
            print(f"Error in completeness validation: {e}")

        processing_time = time.time() - start_time
        print(f"Completeness validation completed in {processing_time:.2f}s, found {len(gaps)} gaps")

        return gaps

    def _detect_rule_based_gaps(self, analysis: AnalysisResult, context: Dict[str, Any]) -> List[CompletenessGap]:
        """Detect gaps using rule-based patterns."""
        gaps = []

        # Combine all text for analysis
        all_text = f"{analysis.intent}. {' '.join(analysis.explicit_requirements)}. {' '.join(analysis.implicit_assumptions)}"

        # Apply completeness rules
        results = self.rule_engine.apply_rules(all_text, context, category="completeness")

        for result in results:
            if result.matched and result.confidence >= self.config.confidence_threshold:
                gap = self._rule_result_to_gap(result, analysis)
                if gap:
                    gaps.append(gap)

        return gaps

    def _check_category_completeness(self, analysis: AnalysisResult, context: Dict[str, Any]) -> List[CompletenessGap]:
        """Check completeness against standard requirement categories."""
        gaps = []

        # Combine all requirements for analysis
        all_requirements = analysis.explicit_requirements + analysis.implicit_assumptions
        all_text = f"{analysis.intent}. {' '.join(all_requirements)}"

        # Check each category
        for category_name, category_info in self.requirement_categories.items():
            category_coverage = self._assess_category_coverage(all_text, category_info)

            if category_coverage["covered"]:
                # Category is mentioned, check for missing specs
                missing_specs = self._find_missing_specifications(all_text, category_info, category_coverage)
                for missing_spec in missing_specs:
                    gap = CompletenessGap(
                        category=category_name,
                        description=f"Missing {missing_spec} specification for {category_name}",
                        suggested_requirement=f"Define {missing_spec} for {category_info['description']}",
                        importance=self.category_priority.get(category_name, Severity.LOW),
                        confidence=0.7
                    )
                    gaps.append(gap)
            else:
                # Category not covered at all, check if it's needed
                if self._is_category_needed(all_text, category_info):
                    gap = CompletenessGap(
                        category=category_name,
                        description=f"No {category_name} requirements specified",
                        suggested_requirement=f"Consider adding {category_info['description']} requirements",
                        importance=self.category_priority.get(category_name, Severity.LOW),
                        confidence=0.6
                    )
                    gaps.append(gap)

        return gaps

    def _assess_category_coverage(self, text: str, category_info: Dict[str, Any]) -> Dict[str, Any]:
        """Assess how well a category is covered in the text."""
        text_lower = text.lower()
        indicators = category_info.get("indicators", [])

        # Check for category indicators
        found_indicators = [indicator for indicator in indicators if indicator in text_lower]

        coverage = {
            "covered": len(found_indicators) > 0,
            "indicators_found": found_indicators,
            "coverage_score": len(found_indicators) / len(indicators) if indicators else 0
        }

        return coverage

    def _find_missing_specifications(self, text: str, category_info: Dict[str, Any],
                                   coverage: Dict[str, Any]) -> List[str]:
        """Find missing specifications within a covered category."""
        text_lower = text.lower()
        required_specs = category_info.get("required_specs", [])

        missing_specs = []
        for spec in required_specs:
            # Check if specification is mentioned
            spec_keywords = self._get_spec_keywords(spec)
            if not any(keyword in text_lower for keyword in spec_keywords):
                missing_specs.append(spec)

        return missing_specs

    def _get_spec_keywords(self, spec: str) -> List[str]:
        """Get keywords to look for when checking specification coverage."""
        keyword_map = {
            "format": ["format", "structure", "schema", "type"],
            "type": ["type", "datatype", "format", "kind"],
            "validation": ["validate", "check", "verify", "constraint", "rule"],
            "constraints": ["constraint", "limit", "rule", "restriction"],
            "error_types": ["error", "exception", "failure", "invalid"],
            "error_messages": ["message", "text", "description", "notification"],
            "recovery": ["recovery", "fallback", "retry", "rollback"],
            "response_time": ["time", "latency", "speed", "performance"],
            "throughput": ["throughput", "capacity", "volume", "rate"],
            "scalability": ["scale", "scalability", "growth", "load"],
            "resource_usage": ["memory", "cpu", "disk", "resource"],
            "authentication": ["auth", "login", "credential", "identity"],
            "authorization": ["permission", "access", "role", "privilege"],
            "encryption": ["encrypt", "crypto", "secure", "cipher"],
            "data_protection": ["protection", "privacy", "confidential", "secure"]
        }

        return keyword_map.get(spec, [spec])

    def _is_category_needed(self, text: str, category_info: Dict[str, Any]) -> bool:
        """Determine if a category is needed based on the text content."""
        text_lower = text.lower()

        # Use heuristics to determine if category is needed
        need_indicators = {
            "functional": True,  # Always needed
            "input_specification": ["input", "parameter", "data", "field"],
            "output_specification": ["output", "result", "response", "return"],
            "error_handling": ["process", "operation", "action", "function"],
            "performance": ["fast", "slow", "performance", "time", "scale"],
            "security": ["user", "data", "access", "system", "secure"],
            "validation": ["input", "data", "form", "field"],
            "user_interface": ["interface", "ui", "screen", "display"],
            "integration": ["api", "external", "service", "integration"],
            "configuration": ["system", "application", "environment"],
            "monitoring": ["operation", "process", "system", "service"],
            "maintenance": ["system", "application", "data", "backup"]
        }

        category_name = category_info.get("description", "").split()[0].lower().replace(",", "")

        indicators = need_indicators.get(category_name, [])
        if indicators is True:
            return True
        if not indicators:
            return False

        return any(indicator in text_lower for indicator in indicators)

    def _detect_domain_specific_gaps(self, analysis: AnalysisResult, context: Dict[str, Any]) -> List[CompletenessGap]:
        """Detect domain-specific completeness gaps."""
        gaps = []

        # Determine likely domain from the analysis
        detected_domain = self._detect_domain(analysis)

        if detected_domain and detected_domain in self.domain_categories:
            domain_categories = self.domain_categories[detected_domain]
            all_text = f"{analysis.intent}. {' '.join(analysis.explicit_requirements + analysis.implicit_assumptions)}"

            for category_name, keywords in domain_categories.items():
                if not any(keyword.lower() in all_text.lower() for keyword in keywords):
                    gap = CompletenessGap(
                        category=f"{detected_domain}_{category_name}",
                        description=f"No {category_name} requirements for {detected_domain}",
                        suggested_requirement=f"Consider adding {category_name} requirements",
                        importance=Severity.MEDIUM,
                        confidence=0.6
                    )
                    gaps.append(gap)

        return gaps

    def _detect_domain(self, analysis: AnalysisResult) -> Optional[str]:
        """Detect the likely domain of the software being specified."""
        all_text = f"{analysis.intent}. {' '.join(analysis.explicit_requirements + analysis.implicit_assumptions)}".lower()

        domain_indicators = {
            "web_application": ["web", "website", "browser", "html", "css", "javascript", "http", "url"],
            "api_service": ["api", "service", "rest", "graphql", "endpoint", "microservice"],
            "data_processing": ["data", "process", "transform", "etl", "pipeline", "analytics"]
        }

        domain_scores = {}
        for domain, indicators in domain_indicators.items():
            score = sum(1 for indicator in indicators if indicator in all_text)
            if score > 0:
                domain_scores[domain] = score

        if domain_scores:
            return max(domain_scores, key=domain_scores.get)

        return None

    def _detect_llm_gaps(self, analysis: AnalysisResult, context: Dict[str, Any],
                        existing_gaps: List[CompletenessGap]) -> List[CompletenessGap]:
        """Detect completeness gaps using LLM intelligence."""
        llm_config = get_config().llm

        if not llm_config.enabled:
            return []

        try:
            # Build prompt for LLM
            prompt = self._build_llm_completeness_prompt(analysis, existing_gaps, context)

            # Call LLM
            llm_response = self._call_llm_for_completeness(prompt, llm_config)

            # Parse response
            return self._parse_llm_completeness_response(llm_response)

        except Exception as e:
            print(f"LLM completeness detection failed: {e}")
            return []

    def _build_llm_completeness_prompt(self, analysis: AnalysisResult,
                                     existing_gaps: List[CompletenessGap],
                                     context: Dict[str, Any]) -> str:
        """Build prompt for LLM completeness analysis."""
        existing_summary = []
        for gap in existing_gaps:
            existing_summary.append(f"- {gap.category}: {gap.description}")

        existing_text = "\n".join(existing_summary) if existing_summary else "None detected by rules"

        prompt = f"""
Analyze the following software requirements for completeness gaps:

INTENT: {analysis.intent}

EXPLICIT REQUIREMENTS:
{chr(10).join(f"- {req}" for req in analysis.explicit_requirements)}

IMPLICIT ASSUMPTIONS:
{chr(10).join(f"- {assumption}" for assumption in analysis.implicit_assumptions)}

GAPS ALREADY DETECTED:
{existing_text}

Please identify additional completeness gaps. Consider these categories:
1. Functional requirements - what the system should do
2. Non-functional requirements - performance, security, usability
3. Input/output specifications - data formats, validation
4. Error handling - what happens when things go wrong
5. Integration requirements - how it connects to other systems
6. User experience - accessibility, internationalization
7. Operational requirements - monitoring, logging, backup
8. Business requirements - compliance, regulations

For each gap, provide:
- Category name
- Description of what's missing
- Suggested requirement to fill the gap
- Importance (low, medium, high, critical)
- Confidence level (0.0-1.0)

Focus on gaps that are likely to cause problems if not addressed.
Format as JSON array of objects.
"""

        return prompt

    def _call_llm_for_completeness(self, prompt: str, llm_config) -> str:
        """Call LLM for completeness analysis."""
        # Placeholder for actual LLM integration
        # Simulated response for demonstration
        return '''[
  {
    "category": "error_handling",
    "description": "No error handling specified for data validation failures",
    "suggested_requirement": "Define error messages and recovery procedures for invalid input data",
    "importance": "high",
    "confidence": 0.9
  },
  {
    "category": "performance",
    "description": "No performance requirements or SLA defined",
    "suggested_requirement": "Specify response time requirements and throughput expectations",
    "importance": "medium",
    "confidence": 0.8
  }
]'''

    def _parse_llm_completeness_response(self, response: str) -> List[CompletenessGap]:
        """Parse LLM response into CompletenessGap objects."""
        try:
            import json
            gap_data = json.loads(response)

            gaps = []
            for data in gap_data:
                try:
                    importance = Severity(data.get("importance", "medium"))

                    gap = CompletenessGap(
                        category=data.get("category", "unknown"),
                        description=data.get("description", ""),
                        suggested_requirement=data.get("suggested_requirement", ""),
                        importance=importance,
                        confidence=float(data.get("confidence", 0.5))
                    )

                    gaps.append(gap)

                except (ValueError, TypeError) as e:
                    print(f"Error parsing LLM gap: {e}")

            return gaps

        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            return []

    def _rule_result_to_gap(self, result, analysis: AnalysisResult) -> Optional[CompletenessGap]:
        """Convert a rule result to a CompletenessGap object."""
        try:
            # Extract category from metadata or infer from rule
            category = result.metadata.get("category", "general")

            # Generate suggested requirement based on the gap
            suggested_requirement = self._generate_suggested_requirement(result, category)

            return CompletenessGap(
                category=category,
                description=result.message,
                suggested_requirement=suggested_requirement,
                importance=result.severity,
                confidence=result.confidence
            )

        except Exception as e:
            print(f"Error converting rule result to gap: {e}")
            return None

    def _generate_suggested_requirement(self, result, category: str) -> str:
        """Generate a suggested requirement to fill a gap."""
        suggestion_templates = {
            "input_specification": "Define input data format, validation rules, and constraints",
            "output_specification": "Specify output format, structure, and content requirements",
            "error_handling": "Define error types, error messages, and recovery procedures",
            "performance": "Specify performance requirements including response time and throughput",
            "security": "Define security controls, access restrictions, and data protection measures",
            "validation": "Specify data validation rules and error handling for invalid inputs",
            "authentication": "Define authentication requirements and user access controls",
            "data_persistence": "Specify data storage, backup, and recovery requirements",
            "api_documentation": "Define API documentation and specification requirements"
        }

        base_suggestion = suggestion_templates.get(category, "Consider adding requirements for this area")

        # Enhance based on rule metadata
        if hasattr(result, 'metadata') and result.metadata:
            if "keywords_found" in result.metadata:
                keywords = result.metadata["keywords_found"]
                if "performance" in keywords:
                    base_suggestion += ". Include SLA and performance benchmarks"
                if "security" in keywords:
                    base_suggestion += ". Include security controls and compliance requirements"

        return base_suggestion

    def _filter_and_prioritize_gaps(self, gaps: List[CompletenessGap]) -> List[CompletenessGap]:
        """Filter and prioritize completeness gaps."""
        if not gaps:
            return []

        # Filter by confidence threshold
        filtered_gaps = [
            gap for gap in gaps
            if gap.confidence >= self.config.confidence_threshold
        ]

        # Deduplicate similar gaps
        deduplicated = []
        for gap in filtered_gaps:
            is_duplicate = False
            for existing in deduplicated:
                if self._are_similar_gaps(gap, existing):
                    # Keep the one with higher confidence
                    if gap.confidence > existing.confidence:
                        deduplicated.remove(existing)
                        deduplicated.append(gap)
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduplicated.append(gap)

        # Sort by importance and confidence
        importance_order = {Severity.CRITICAL: 4, Severity.HIGH: 3, Severity.MEDIUM: 2, Severity.LOW: 1}
        deduplicated.sort(
            key=lambda x: (importance_order.get(x.importance, 0), x.confidence),
            reverse=True
        )

        # Limit results
        if self.config.max_results > 0:
            deduplicated = deduplicated[:self.config.max_results]

        return deduplicated

    def _are_similar_gaps(self, gap1: CompletenessGap, gap2: CompletenessGap) -> bool:
        """Check if two gaps are similar enough to be considered duplicates."""
        # Same category is a strong indicator
        if gap1.category == gap2.category:
            return True

        # Check description similarity
        desc1_words = set(gap1.description.lower().split())
        desc2_words = set(gap2.description.lower().split())

        if desc1_words and desc2_words:
            intersection = len(desc1_words.intersection(desc2_words))
            union = len(desc1_words.union(desc2_words))
            similarity = intersection / union if union > 0 else 0

            if similarity > 0.6:  # 60% similarity threshold
                return True

        return False

    def get_completeness_score(self, analysis: AnalysisResult, gaps: List[CompletenessGap]) -> Dict[str, Any]:
        """Calculate a completeness score based on detected gaps."""
        total_categories = len(self.requirement_categories)
        critical_gaps = sum(1 for gap in gaps if gap.importance == Severity.CRITICAL)
        high_gaps = sum(1 for gap in gaps if gap.importance == Severity.HIGH)
        medium_gaps = sum(1 for gap in gaps if gap.importance == Severity.MEDIUM)
        low_gaps = sum(1 for gap in gaps if gap.importance == Severity.LOW)

        # Calculate weighted score (lower is better)
        gap_penalty = (critical_gaps * 4) + (high_gaps * 3) + (medium_gaps * 2) + (low_gaps * 1)
        max_possible_penalty = total_categories * 4  # If all categories had critical gaps

        completeness_score = max(0.0, 1.0 - (gap_penalty / max_possible_penalty)) if max_possible_penalty > 0 else 1.0

        return {
            "completeness_score": completeness_score,
            "total_gaps": len(gaps),
            "gap_breakdown": {
                "critical": critical_gaps,
                "high": high_gaps,
                "medium": medium_gaps,
                "low": low_gaps
            },
            "categories_checked": total_categories,
            "recommendation": self._get_completeness_recommendation(completeness_score, gaps)
        }

    def _get_completeness_recommendation(self, score: float, gaps: List[CompletenessGap]) -> str:
        """Get recommendation based on completeness score."""
        if score >= 0.9:
            return "Excellent completeness. Minor gaps detected."
        elif score >= 0.8:
            return "Good completeness. Address high-priority gaps."
        elif score >= 0.6:
            return "Moderate completeness. Several important gaps need attention."
        elif score >= 0.4:
            return "Low completeness. Significant gaps in requirements."
        else:
            return "Poor completeness. Major requirements are missing."

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the completeness validator."""
        rule_stats = self.rule_engine.get_rule_statistics()

        return {
            "config": {
                "enabled": self.config.enabled,
                "mode": self.config.mode.value,
                "confidence_threshold": self.config.confidence_threshold,
                "max_results": self.config.max_results
            },
            "rules": rule_stats,
            "categories_count": len(self.requirement_categories),
            "domain_categories_count": len(self.domain_categories),
            "supported_domains": list(self.domain_categories.keys()),
            "importance_levels": [importance.value for importance in Severity]
        }