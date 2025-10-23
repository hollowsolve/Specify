"""
Edge case detection processor.

This module implements sophisticated edge case detection using a hybrid
approach combining rule-based patterns with LLM intelligence.
"""

import time
from typing import List, Dict, Any, Optional
from ..models import AnalysisResult, EdgeCase, EdgeCaseCategory, Severity
from ..rules import RuleEngine, EDGE_CASE_RULES, EDGE_CASE_RULE_CATEGORIES
from ..config import ProcessorConfig, ProcessorMode, get_config
from ..plugins import get_plugin_manager


class EdgeCaseDetector:
    """
    Sophisticated edge case detection using hybrid rule-based + LLM approach.

    This processor identifies potential edge cases that need to be considered
    in the implementation by combining fast rule-based pattern matching
    with intelligent LLM analysis.
    """

    def __init__(self, config: Optional[ProcessorConfig] = None):
        self.config = config or get_config().edge_case_detector
        self.rule_engine = RuleEngine()
        self._setup_rules()

    def _setup_rules(self) -> None:
        """Setup the rule engine with edge case detection rules."""
        # Register core rules
        self.rule_engine.register_rules(EDGE_CASE_RULES, "edge_cases")

        # Load plugin rules
        plugin_manager = get_plugin_manager()
        for rule_plugin in plugin_manager.get_rule_plugins():
            try:
                plugin_rules = rule_plugin.get_rules()
                plugin_categories = rule_plugin.get_rule_categories()

                for rule in plugin_rules:
                    category = "plugin_" + rule_plugin.name
                    self.rule_engine.register_rule(rule, category)

                # Register plugin categories
                for category, rule_ids in plugin_categories.items():
                    self.rule_engine.rule_categories[f"plugin_{category}"] = rule_ids

            except Exception as e:
                print(f"Warning: Failed to load rules from plugin {rule_plugin.name}: {e}")

    def detect_edge_cases(self, analysis: AnalysisResult, context: Dict[str, Any] = None) -> List[EdgeCase]:
        """
        Detect edge cases in the analysis result.

        Args:
            analysis: The analysis result from Phase 1
            context: Additional context for edge case detection

        Returns:
            List of detected edge cases
        """
        if not self.config.enabled:
            return []

        context = context or {}
        edge_cases = []

        start_time = time.time()

        try:
            # Phase 1: Rule-based detection (fast)
            rule_based_cases = self._detect_rule_based_edge_cases(analysis, context)
            edge_cases.extend(rule_based_cases)

            # Phase 2: LLM-based detection (intelligent)
            if self.config.mode in [ProcessorMode.BALANCED, ProcessorMode.INTELLIGENT]:
                llm_cases = self._detect_llm_edge_cases(analysis, context, rule_based_cases)
                edge_cases.extend(llm_cases)

            # Phase 3: Plugin-based detection
            plugin_cases = self._detect_plugin_edge_cases(analysis, context)
            edge_cases.extend(plugin_cases)

            # Filter and deduplicate
            edge_cases = self._filter_and_deduplicate(edge_cases)

        except Exception as e:
            print(f"Error in edge case detection: {e}")

        processing_time = time.time() - start_time
        print(f"Edge case detection completed in {processing_time:.2f}s, found {len(edge_cases)} edge cases")

        return edge_cases

    def _detect_rule_based_edge_cases(self, analysis: AnalysisResult, context: Dict[str, Any]) -> List[EdgeCase]:
        """Detect edge cases using rule-based patterns."""
        edge_cases = []

        # Combine all text for analysis
        all_text = f"{analysis.intent}. {' '.join(analysis.explicit_requirements)}. {' '.join(analysis.implicit_assumptions)}"

        # Apply rules to different text components
        contexts = [
            ("intent", analysis.intent),
            ("requirements", " ".join(analysis.explicit_requirements)),
            ("assumptions", " ".join(analysis.implicit_assumptions)),
            ("ambiguities", " ".join(analysis.ambiguities)),
            ("combined", all_text)
        ]

        for context_name, text in contexts:
            if not text.strip():
                continue

            rule_context = {**context, "text_context": context_name}
            results = self.rule_engine.apply_rules(text, rule_context, category="edge_cases")

            for result in results:
                if result.matched and result.confidence >= self.config.confidence_threshold:
                    edge_case = self._rule_result_to_edge_case(result, text, context_name)
                    if edge_case:
                        edge_cases.append(edge_case)

        return edge_cases

    def _detect_llm_edge_cases(self, analysis: AnalysisResult, context: Dict[str, Any],
                             rule_based_cases: List[EdgeCase]) -> List[EdgeCase]:
        """Detect edge cases using LLM intelligence."""
        llm_config = get_config().llm

        if not llm_config.enabled:
            return []

        try:
            # Prepare prompt for LLM
            prompt = self._build_llm_prompt(analysis, rule_based_cases, context)

            # Call LLM (simplified - in real implementation would use actual LLM client)
            llm_response = self._call_llm(prompt, llm_config)

            # Parse LLM response into edge cases
            return self._parse_llm_response(llm_response)

        except Exception as e:
            print(f"LLM edge case detection failed: {e}")
            return []

    def _detect_plugin_edge_cases(self, analysis: AnalysisResult, context: Dict[str, Any]) -> List[EdgeCase]:
        """Detect edge cases using processor plugins."""
        edge_cases = []

        plugin_manager = get_plugin_manager()
        for processor_plugin in plugin_manager.get_processor_plugins():
            try:
                plugin_context = {**context, "processor": "edge_case_detector"}
                plugin_results = processor_plugin.process(analysis, plugin_context)

                # Extract edge cases from plugin results
                if "edge_cases" in plugin_results:
                    plugin_edge_cases = plugin_results["edge_cases"]
                    for case_data in plugin_edge_cases:
                        edge_case = self._plugin_data_to_edge_case(case_data, processor_plugin.name)
                        if edge_case:
                            edge_cases.append(edge_case)

            except Exception as e:
                print(f"Plugin {processor_plugin.name} edge case detection failed: {e}")

        return edge_cases

    def _rule_result_to_edge_case(self, result, text: str, context_name: str) -> Optional[EdgeCase]:
        """Convert a rule result to an EdgeCase object."""
        try:
            # Determine category from metadata or rule characteristics
            category = EdgeCaseCategory.INPUT_VALIDATION  # Default

            if "category" in result.metadata:
                try:
                    category = EdgeCaseCategory(result.metadata["category"])
                except ValueError:
                    pass

            # Generate suggested handling based on rule and category
            suggested_handling = self._generate_suggested_handling(result, category, text)

            return EdgeCase(
                category=category,
                description=result.message,
                suggested_handling=suggested_handling,
                severity=result.severity,
                confidence=result.confidence
            )

        except Exception as e:
            print(f"Error converting rule result to edge case: {e}")
            return None

    def _generate_suggested_handling(self, result, category: EdgeCaseCategory, text: str) -> str:
        """Generate suggested handling for an edge case."""
        base_suggestions = {
            EdgeCaseCategory.INPUT_VALIDATION: "Implement comprehensive input validation with clear error messages",
            EdgeCaseCategory.BOUNDARY_CONDITIONS: "Define and test boundary values and limits",
            EdgeCaseCategory.ERROR_STATES: "Implement proper error handling and recovery mechanisms",
            EdgeCaseCategory.CONCURRENCY: "Consider thread safety and concurrent access patterns",
            EdgeCaseCategory.PERFORMANCE: "Define performance requirements and implement monitoring",
            EdgeCaseCategory.SECURITY: "Implement security controls and access restrictions",
            EdgeCaseCategory.INTEGRATION: "Define integration contracts and error handling"
        }

        base_suggestion = base_suggestions.get(category, "Consider this edge case in implementation")

        # Enhance suggestion based on rule metadata
        if "keywords_found" in result.metadata:
            keywords = result.metadata["keywords_found"]
            if "empty" in keywords or "null" in keywords:
                base_suggestion += ". Handle empty/null inputs gracefully"
            if "concurrent" in keywords:
                base_suggestion += ". Implement proper locking mechanisms"
            if "performance" in keywords:
                base_suggestion += ". Set performance benchmarks and monitoring"

        return base_suggestion

    def _build_llm_prompt(self, analysis: AnalysisResult, rule_based_cases: List[EdgeCase],
                         context: Dict[str, Any]) -> str:
        """Build prompt for LLM edge case detection."""
        rule_summaries = []
        for case in rule_based_cases:
            rule_summaries.append(f"- {case.category.value}: {case.description}")

        rule_summary = "\n".join(rule_summaries) if rule_summaries else "None detected by rules"

        prompt = f"""
Analyze the following software requirements for potential edge cases that need consideration:

INTENT: {analysis.intent}

EXPLICIT REQUIREMENTS:
{chr(10).join(f"- {req}" for req in analysis.explicit_requirements)}

IMPLICIT ASSUMPTIONS:
{chr(10).join(f"- {assumption}" for assumption in analysis.implicit_assumptions)}

AMBIGUITIES:
{chr(10).join(f"- {ambiguity}" for ambiguity in analysis.ambiguities)}

EDGE CASES ALREADY DETECTED BY RULES:
{rule_summary}

Please identify additional edge cases that might not be caught by simple pattern matching. Focus on:
1. Complex interaction scenarios
2. Unusual data combinations
3. System integration points
4. Performance under stress
5. Security vulnerabilities
6. User experience edge cases

For each edge case, provide:
- Category (input_validation, boundary_conditions, error_states, concurrency, performance, security, integration)
- Description of the edge case
- Suggested handling approach
- Severity (low, medium, high, critical)
- Confidence level (0.0-1.0)

Format as JSON array of objects.
"""

        return prompt

    def _call_llm(self, prompt: str, llm_config) -> str:
        """
        Call LLM for edge case detection.

        Note: This is a simplified implementation. In a real system,
        this would integrate with actual LLM providers like Anthropic Claude.
        """
        # Placeholder for actual LLM integration
        # In reality, this would use anthropic, openai, or other LLM clients

        # Simulated LLM response for demonstration
        return '''[
  {
    "category": "error_states",
    "description": "Network connectivity loss during data processing",
    "suggested_handling": "Implement retry mechanisms and offline mode capabilities",
    "severity": "high",
    "confidence": 0.8
  },
  {
    "category": "performance",
    "description": "Memory exhaustion with large data sets",
    "suggested_handling": "Implement streaming processing and memory limits",
    "severity": "medium",
    "confidence": 0.7
  }
]'''

    def _parse_llm_response(self, response: str) -> List[EdgeCase]:
        """Parse LLM response into EdgeCase objects."""
        try:
            import json
            edge_case_data = json.loads(response)

            edge_cases = []
            for case_data in edge_case_data:
                try:
                    category = EdgeCaseCategory(case_data.get("category", "input_validation"))
                    severity = Severity(case_data.get("severity", "medium"))

                    edge_case = EdgeCase(
                        category=category,
                        description=case_data.get("description", ""),
                        suggested_handling=case_data.get("suggested_handling", ""),
                        severity=severity,
                        confidence=float(case_data.get("confidence", 0.5))
                    )

                    edge_cases.append(edge_case)

                except (ValueError, TypeError) as e:
                    print(f"Error parsing LLM edge case: {e}")

            return edge_cases

        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            return []

    def _plugin_data_to_edge_case(self, case_data: Dict[str, Any], plugin_name: str) -> Optional[EdgeCase]:
        """Convert plugin data to EdgeCase object."""
        try:
            category = EdgeCaseCategory(case_data.get("category", "input_validation"))
            severity = Severity(case_data.get("severity", "medium"))

            description = case_data.get("description", "")
            if plugin_name:
                description = f"[{plugin_name}] {description}"

            return EdgeCase(
                category=category,
                description=description,
                suggested_handling=case_data.get("suggested_handling", "Consider this edge case"),
                severity=severity,
                confidence=float(case_data.get("confidence", 0.5))
            )

        except (ValueError, TypeError) as e:
            print(f"Error converting plugin data to edge case: {e}")
            return None

    def _filter_and_deduplicate(self, edge_cases: List[EdgeCase]) -> List[EdgeCase]:
        """Filter and deduplicate edge cases."""
        if not edge_cases:
            return []

        # Filter by confidence threshold
        filtered_cases = [
            case for case in edge_cases
            if case.confidence >= self.config.confidence_threshold
        ]

        # Simple deduplication based on description similarity
        deduplicated = []
        for case in filtered_cases:
            is_duplicate = False
            for existing in deduplicated:
                if self._are_similar_edge_cases(case, existing):
                    # Keep the one with higher confidence
                    if case.confidence > existing.confidence:
                        deduplicated.remove(existing)
                        deduplicated.append(case)
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduplicated.append(case)

        # Limit results
        if self.config.max_results > 0:
            # Sort by severity and confidence
            severity_order = {Severity.CRITICAL: 4, Severity.HIGH: 3, Severity.MEDIUM: 2, Severity.LOW: 1}
            deduplicated.sort(
                key=lambda x: (severity_order.get(x.severity, 0), x.confidence),
                reverse=True
            )
            deduplicated = deduplicated[:self.config.max_results]

        return deduplicated

    def _are_similar_edge_cases(self, case1: EdgeCase, case2: EdgeCase) -> bool:
        """Check if two edge cases are similar enough to be considered duplicates."""
        # Simple similarity check based on category and description keywords
        if case1.category != case2.category:
            return False

        # Extract key words from descriptions
        def get_key_words(text: str) -> set:
            words = text.lower().split()
            # Filter out common words
            common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
            return {word for word in words if len(word) > 3 and word not in common_words}

        words1 = get_key_words(case1.description)
        words2 = get_key_words(case2.description)

        if not words1 or not words2:
            return False

        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        similarity = intersection / union if union > 0 else 0

        return similarity > 0.6  # 60% similarity threshold

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the edge case detector."""
        rule_stats = self.rule_engine.get_rule_statistics()

        return {
            "config": {
                "enabled": self.config.enabled,
                "mode": self.config.mode.value,
                "confidence_threshold": self.config.confidence_threshold,
                "max_results": self.config.max_results
            },
            "rules": rule_stats,
            "categories": list(EdgeCaseCategory),
            "severities": list(Severity)
        }