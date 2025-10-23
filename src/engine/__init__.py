"""
Specification Engine - Phase 2 of the Specify system.

This package provides the sophisticated intelligence layer that takes parsed prompts
and makes them bulletproof through comprehensive analysis and refinement.

The specification engine uses a hybrid approach combining:
- Rule-based processing for speed and reliability
- LLM integration for intelligent reasoning
- Extensible plugin architecture for customization

Key Components:
- SpecificationEngine: Main orchestrator
- Processors: EdgeCaseDetector, RequirementCompressor, ContradictionFinder, CompletenessValidator
- Models: Data structures for refined specifications
- Rules: Extensible rule engine for pattern matching
- Config: Configuration management
- Plugins: Plugin system for extensibility

Usage:
    from src.engine import SpecificationEngine
    from src.analyzer.models import AnalysisResult

    # Create engine
    engine = SpecificationEngine()

    # Refine specification
    refined_spec = engine.refine_specification(analysis_result)

    # Get results
    print(refined_spec.summary())
"""

from .specification_engine import SpecificationEngine
from .models import (
    RefinedSpecification, EdgeCase, CompressedRequirement,
    Contradiction, CompletenessGap, ProcessingMetrics,
    Severity, EdgeCaseCategory
)
from .processors import (
    EdgeCaseDetector, RequirementCompressor,
    ContradictionFinder, CompletenessValidator
)
from .config import (
    EngineConfig, ProcessorConfig, LLMConfig, ProcessorMode,
    ConfigManager, get_config, set_config_path, update_config
)
from .plugins import (
    PluginManager, PluginInterface, ProcessorPlugin, RulePlugin, ValidatorPlugin,
    get_plugin_manager, register_plugin, load_plugins_from_directory
)
from .rules import RuleEngine, Rule, RuleResult

__version__ = "2.0.0"

__all__ = [
    # Main engine
    'SpecificationEngine',

    # Data models
    'RefinedSpecification',
    'EdgeCase',
    'CompressedRequirement',
    'Contradiction',
    'CompletenessGap',
    'ProcessingMetrics',
    'Severity',
    'EdgeCaseCategory',

    # Processors
    'EdgeCaseDetector',
    'RequirementCompressor',
    'ContradictionFinder',
    'CompletenessValidator',

    # Configuration
    'EngineConfig',
    'ProcessorConfig',
    'LLMConfig',
    'ProcessorMode',
    'ConfigManager',
    'get_config',
    'set_config_path',
    'update_config',

    # Plugin system
    'PluginManager',
    'PluginInterface',
    'ProcessorPlugin',
    'RulePlugin',
    'ValidatorPlugin',
    'get_plugin_manager',
    'register_plugin',
    'load_plugins_from_directory',

    # Rule engine
    'RuleEngine',
    'Rule',
    'RuleResult',
]


def create_engine(config_path: str = None, **config_overrides) -> SpecificationEngine:
    """
    Create a configured specification engine.

    Args:
        config_path: Path to configuration file
        **config_overrides: Configuration overrides

    Returns:
        Configured SpecificationEngine instance
    """
    if config_path:
        set_config_path(config_path)

    if config_overrides:
        update_config(config_overrides)

    return SpecificationEngine()


def quick_refine(analysis_result, mode: str = "balanced") -> RefinedSpecification:
    """
    Quick refinement with minimal configuration.

    Args:
        analysis_result: AnalysisResult from Phase 1
        mode: Processing mode (fast, balanced, intelligent)

    Returns:
        RefinedSpecification
    """
    # Set processing mode
    update_config({"mode": mode})

    # Create and run engine
    engine = SpecificationEngine()
    return engine.refine_specification(analysis_result)


def get_engine_info() -> dict:
    """Get information about the engine and its capabilities."""
    engine = SpecificationEngine()

    return {
        "version": __version__,
        "statistics": engine.get_statistics(),
        "health": engine.health_check(),
        "supported_modes": [mode.value for mode in ProcessorMode],
        "processors": [
            "EdgeCaseDetector",
            "RequirementCompressor",
            "ContradictionFinder",
            "CompletenessValidator"
        ]
    }