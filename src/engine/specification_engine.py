"""
Main specification engine orchestrator.

This module provides the central SpecificationEngine class that orchestrates
all processors in sequence to transform analysis results into refined specifications.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Callable
import traceback

from .models import (
    AnalysisResult, RefinedSpecification, ProcessingMetrics,
    EdgeCase, CompressedRequirement, Contradiction, CompletenessGap
)
from .processors import (
    EdgeCaseDetector, RequirementCompressor,
    ContradictionFinder, CompletenessValidator
)
from .config import EngineConfig, ProcessorMode, get_config
from .plugins import get_plugin_manager


class SpecificationEngine:
    """
    Main orchestrator for the specification engine.

    The SpecificationEngine takes AnalysisResult from Phase 1 and orchestrates
    all processors in sequence to produce a RefinedSpecification with comprehensive
    intelligence about the original prompt.
    """

    def __init__(self, config: Optional[EngineConfig] = None):
        """
        Initialize the specification engine.

        Args:
            config: Engine configuration. If None, uses global configuration.
        """
        self.config = config or get_config()

        # Initialize processors
        self.edge_case_detector = EdgeCaseDetector(self.config.edge_case_detector)
        self.requirement_compressor = RequirementCompressor(self.config.requirement_compressor)
        self.contradiction_finder = ContradictionFinder(self.config.contradiction_finder)
        self.completeness_validator = CompletenessValidator(self.config.completeness_validator)

        # Plugin manager
        self.plugin_manager = get_plugin_manager()

        # Processing state
        self._processing_state = {}

    def refine_specification(self, analysis: AnalysisResult, context: Dict[str, Any] = None) -> RefinedSpecification:
        """
        Refine a specification by running all processors.

        Args:
            analysis: The analysis result from Phase 1
            context: Additional context for processing

        Returns:
            RefinedSpecification with comprehensive analysis
        """
        context = context or {}
        start_time = time.time()

        # Initialize processing metrics
        metrics = ProcessingMetrics()
        processors_run = []

        # Initialize result containers
        edge_cases: List[EdgeCase] = []
        compressed_requirements: List[CompressedRequirement] = []
        contradictions: List[Contradiction] = []
        completeness_gaps: List[CompletenessGap] = []

        try:
            print(f"Starting specification refinement for: {analysis.intent[:100]}...")

            # Determine processing mode
            if self.config.parallel_processing and self.config.max_workers > 1:
                results = self._process_in_parallel(analysis, context)
            else:
                results = self._process_sequentially(analysis, context)

            # Extract results
            edge_cases = results.get("edge_cases", [])
            compressed_requirements = results.get("compressed_requirements", [])
            contradictions = results.get("contradictions", [])
            completeness_gaps = results.get("completeness_gaps", [])
            processors_run = results.get("processors_run", [])

            # Run plugin processors
            plugin_results = self._run_plugin_processors(analysis, context)
            if plugin_results:
                self._merge_plugin_results(plugin_results, results)

            # Calculate overall confidence score
            confidence_score = self._calculate_confidence_score(
                edge_cases, compressed_requirements, contradictions, completeness_gaps
            )

            # Update metrics
            processing_time = time.time() - start_time
            metrics.processing_time_seconds = processing_time
            metrics.processors_run = processors_run
            metrics.total_issues_found = len(edge_cases) + len(contradictions) + len(completeness_gaps)

            print(f"Specification refinement completed in {processing_time:.2f}s")
            print(f"Found: {len(edge_cases)} edge cases, {len(contradictions)} contradictions, "
                  f"{len(completeness_gaps)} gaps, {len(compressed_requirements)} compressions")

        except Exception as e:
            print(f"Error during specification refinement: {e}")
            traceback.print_exc()
            confidence_score = 0.0
            metrics.processing_time_seconds = time.time() - start_time

        # Create refined specification
        refined_spec = RefinedSpecification(
            original_analysis=analysis,
            edge_cases=edge_cases,
            compressed_requirements=compressed_requirements,
            contradictions=contradictions,
            completeness_gaps=completeness_gaps,
            confidence_score=confidence_score,
            processing_metrics=metrics,
            metadata={
                "engine_version": "2.0.0",
                "processing_mode": self.config.mode.value,
                "timestamp": time.time(),
                "config_hash": hash(str(self.config.to_dict()))
            }
        )

        return refined_spec

    def _process_sequentially(self, analysis: AnalysisResult, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process all components sequentially."""
        results = {
            "edge_cases": [],
            "compressed_requirements": [],
            "contradictions": [],
            "completeness_gaps": [],
            "processors_run": []
        }

        # Edge case detection
        if self.edge_case_detector.config.enabled:
            try:
                print("Running edge case detection...")
                edge_cases = self.edge_case_detector.detect_edge_cases(analysis, context)
                results["edge_cases"] = edge_cases
                results["processors_run"].append("EdgeCaseDetector")
                print(f"Edge case detection: found {len(edge_cases)} edge cases")
            except Exception as e:
                print(f"Edge case detection failed: {e}")

        # Requirement compression
        if self.requirement_compressor.config.enabled:
            try:
                print("Running requirement compression...")
                compressed_requirements = self.requirement_compressor.compress_requirements(analysis, context)
                results["compressed_requirements"] = compressed_requirements
                results["processors_run"].append("RequirementCompressor")
                print(f"Requirement compression: compressed {len(compressed_requirements)} requirement groups")
            except Exception as e:
                print(f"Requirement compression failed: {e}")

        # Contradiction detection
        if self.contradiction_finder.config.enabled:
            try:
                print("Running contradiction detection...")
                contradictions = self.contradiction_finder.find_contradictions(analysis, context)
                results["contradictions"] = contradictions
                results["processors_run"].append("ContradictionFinder")
                print(f"Contradiction detection: found {len(contradictions)} contradictions")
            except Exception as e:
                print(f"Contradiction detection failed: {e}")

        # Completeness validation
        if self.completeness_validator.config.enabled:
            try:
                print("Running completeness validation...")
                completeness_gaps = self.completeness_validator.validate_completeness(analysis, context)
                results["completeness_gaps"] = completeness_gaps
                results["processors_run"].append("CompletenessValidator")
                print(f"Completeness validation: found {len(completeness_gaps)} gaps")
            except Exception as e:
                print(f"Completeness validation failed: {e}")

        return results

    def _process_in_parallel(self, analysis: AnalysisResult, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process all components in parallel."""
        results = {
            "edge_cases": [],
            "compressed_requirements": [],
            "contradictions": [],
            "completeness_gaps": [],
            "processors_run": []
        }

        # Define processor tasks
        tasks = []

        if self.edge_case_detector.config.enabled:
            tasks.append(("EdgeCaseDetector", self.edge_case_detector.detect_edge_cases, "edge_cases"))

        if self.requirement_compressor.config.enabled:
            tasks.append(("RequirementCompressor", self.requirement_compressor.compress_requirements, "compressed_requirements"))

        if self.contradiction_finder.config.enabled:
            tasks.append(("ContradictionFinder", self.contradiction_finder.find_contradictions, "contradictions"))

        if self.completeness_validator.config.enabled:
            tasks.append(("CompletenessValidator", self.completeness_validator.validate_completeness, "completeness_gaps"))

        # Execute tasks in parallel
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all tasks
            future_to_task = {}
            for processor_name, processor_func, result_key in tasks:
                future = executor.submit(processor_func, analysis, context)
                future_to_task[future] = (processor_name, result_key)

            # Collect results as they complete
            for future in as_completed(future_to_task, timeout=self.config.timeout):
                processor_name, result_key = future_to_task[future]
                try:
                    result = future.result()
                    results[result_key] = result
                    results["processors_run"].append(processor_name)
                    print(f"{processor_name}: completed with {len(result) if result else 0} results")
                except Exception as e:
                    print(f"{processor_name} failed: {e}")

        return results

    def _run_plugin_processors(self, analysis: AnalysisResult, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run plugin processors."""
        plugin_results = {}

        processor_plugins = self.plugin_manager.get_processor_plugins()
        if not processor_plugins:
            return plugin_results

        print(f"Running {len(processor_plugins)} plugin processors...")

        for plugin in processor_plugins:
            try:
                plugin_context = {**context, "engine": "specification_engine"}
                result = plugin.process(analysis, plugin_context)
                plugin_results[plugin.name] = result
                print(f"Plugin {plugin.name}: completed")
            except Exception as e:
                print(f"Plugin {plugin.name} failed: {e}")

        return plugin_results

    def _merge_plugin_results(self, plugin_results: Dict[str, Any], main_results: Dict[str, Any]) -> None:
        """Merge plugin results into main results."""
        for plugin_name, plugin_result in plugin_results.items():
            if not isinstance(plugin_result, dict):
                continue

            # Merge different types of results
            for result_type in ["edge_cases", "compressed_requirements", "contradictions", "completeness_gaps"]:
                if result_type in plugin_result:
                    plugin_items = plugin_result[result_type]
                    if plugin_items and isinstance(plugin_items, list):
                        if result_type not in main_results:
                            main_results[result_type] = []
                        main_results[result_type].extend(plugin_items)

    def _calculate_confidence_score(self, edge_cases: List[EdgeCase],
                                   compressed_requirements: List[CompressedRequirement],
                                   contradictions: List[Contradiction],
                                   completeness_gaps: List[CompletenessGap]) -> float:
        """Calculate overall confidence score for the refined specification."""
        total_items = len(edge_cases) + len(compressed_requirements) + len(contradictions) + len(completeness_gaps)

        if total_items == 0:
            return 0.8  # Default confidence when no issues found

        # Calculate weighted confidence based on individual confidences and severities
        total_weight = 0.0
        weighted_confidence = 0.0

        # Edge cases
        for edge_case in edge_cases:
            weight = self._get_severity_weight(edge_case.severity)
            weighted_confidence += edge_case.confidence * weight
            total_weight += weight

        # Compressed requirements (positive signal)
        for req in compressed_requirements:
            weight = 1.0  # Compression is generally positive
            # Assume high confidence for successful compression
            weighted_confidence += 0.9 * weight
            total_weight += weight

        # Contradictions (negative signal)
        for contradiction in contradictions:
            weight = self._get_severity_weight(contradiction.severity) * 1.5  # Contradictions are more serious
            weighted_confidence += contradiction.confidence * weight
            total_weight += weight

        # Completeness gaps
        for gap in completeness_gaps:
            weight = self._get_severity_weight(gap.importance)
            weighted_confidence += gap.confidence * weight
            total_weight += weight

        if total_weight == 0:
            return 0.8

        # Calculate average weighted confidence
        average_confidence = weighted_confidence / total_weight

        # Apply penalty for high-severity issues
        critical_issues = sum(1 for ec in edge_cases if ec.severity.value == "critical") + \
                         sum(1 for c in contradictions if c.severity.value == "critical") + \
                         sum(1 for g in completeness_gaps if g.importance.value == "critical")

        if critical_issues > 0:
            penalty = min(0.3, critical_issues * 0.1)  # Up to 30% penalty
            average_confidence *= (1.0 - penalty)

        return max(0.0, min(1.0, average_confidence))

    def _get_severity_weight(self, severity) -> float:
        """Get weight for severity level."""
        weights = {
            "critical": 3.0,
            "high": 2.0,
            "medium": 1.0,
            "low": 0.5
        }
        return weights.get(severity.value if hasattr(severity, 'value') else str(severity), 1.0)

    def validate_result(self, refined_spec: RefinedSpecification) -> Dict[str, Any]:
        """
        Validate the refined specification using validator plugins.

        Args:
            refined_spec: The refined specification to validate

        Returns:
            Validation results
        """
        validation_results = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "validator_results": {}
        }

        validator_plugins = self.plugin_manager.get_validator_plugins()

        for validator in validator_plugins:
            try:
                issues = validator.validate_specification(refined_spec)
                validation_results["validator_results"][validator.name] = issues

                for issue in issues:
                    if issue.get("severity") in ["critical", "high"]:
                        validation_results["issues"].append(issue)
                        validation_results["valid"] = False
                    else:
                        validation_results["warnings"].append(issue)

            except Exception as e:
                print(f"Validator {validator.name} failed: {e}")
                validation_results["warnings"].append({
                    "validator": validator.name,
                    "message": f"Validation failed: {e}",
                    "severity": "medium"
                })

        return validation_results

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the engine and its components."""
        return {
            "engine": {
                "version": "2.0.0",
                "config": {
                    "mode": self.config.mode.value,
                    "parallel_processing": self.config.parallel_processing,
                    "max_workers": self.config.max_workers,
                    "timeout": self.config.timeout
                }
            },
            "processors": {
                "edge_case_detector": self.edge_case_detector.get_statistics(),
                "requirement_compressor": self.requirement_compressor.get_statistics(),
                "contradiction_finder": self.contradiction_finder.get_statistics(),
                "completeness_validator": self.completeness_validator.get_statistics()
            },
            "plugins": self.plugin_manager.get_plugin_statistics()
        }

    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on all engine components."""
        health = {
            "status": "healthy",
            "components": {},
            "issues": []
        }

        # Check processors
        processors = {
            "edge_case_detector": self.edge_case_detector,
            "requirement_compressor": self.requirement_compressor,
            "contradiction_finder": self.contradiction_finder,
            "completeness_validator": self.completeness_validator
        }

        for name, processor in processors.items():
            try:
                # Basic health check - ensure processor is properly configured
                processor_health = {
                    "enabled": processor.config.enabled,
                    "mode": processor.config.mode.value,
                    "confidence_threshold": processor.config.confidence_threshold,
                    "status": "healthy"
                }
                health["components"][name] = processor_health

                if not processor.config.enabled:
                    health["issues"].append(f"{name} is disabled")

            except Exception as e:
                health["components"][name] = {"status": "unhealthy", "error": str(e)}
                health["issues"].append(f"{name}: {e}")
                health["status"] = "degraded"

        # Check plugins
        try:
            plugin_stats = self.plugin_manager.get_plugin_statistics()
            health["components"]["plugins"] = {
                "total": plugin_stats["total_plugins"],
                "enabled": plugin_stats["enabled_plugins"],
                "status": "healthy"
            }

            if plugin_stats["disabled_plugins"] > 0:
                health["issues"].append(f"{plugin_stats['disabled_plugins']} plugins are disabled")

        except Exception as e:
            health["components"]["plugins"] = {"status": "unhealthy", "error": str(e)}
            health["issues"].append(f"Plugin system: {e}")
            health["status"] = "degraded"

        # Check LLM configuration
        try:
            llm_config = self.config.llm
            health["components"]["llm"] = {
                "enabled": llm_config.enabled,
                "provider": llm_config.provider,
                "model": llm_config.model,
                "status": "healthy" if llm_config.enabled else "disabled"
            }

            if not llm_config.enabled:
                health["issues"].append("LLM is disabled - limited intelligence capabilities")

        except Exception as e:
            health["components"]["llm"] = {"status": "unhealthy", "error": str(e)}
            health["issues"].append(f"LLM configuration: {e}")
            health["status"] = "degraded"

        # Overall status
        if any(comp.get("status") == "unhealthy" for comp in health["components"].values()):
            health["status"] = "unhealthy"

        return health

    def shutdown(self) -> None:
        """Gracefully shutdown the engine."""
        print("Shutting down specification engine...")

        # Cleanup plugins
        try:
            for plugin_name in list(self.plugin_manager.plugins.keys()):
                self.plugin_manager.unregister_plugin(plugin_name)
        except Exception as e:
            print(f"Error during plugin cleanup: {e}")

        print("Specification engine shutdown complete")