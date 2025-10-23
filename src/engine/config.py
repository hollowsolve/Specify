"""
Configuration system for the specification engine.

This module provides configuration management for the specification engine,
allowing customization of processors, rules, and behavior.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import json
import os
from pathlib import Path


class ProcessorMode(Enum):
    """Modes for processor execution."""
    FAST = "fast"  # Rule-based only, fastest
    BALANCED = "balanced"  # Rules + limited LLM
    INTELLIGENT = "intelligent"  # Full LLM analysis
    CUSTOM = "custom"  # Custom configuration


@dataclass
class LLMConfig:
    """Configuration for LLM integration."""
    provider: str = "anthropic"  # anthropic, openai, etc.
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4000
    temperature: float = 0.1
    timeout: int = 30
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    enabled: bool = True


@dataclass
class ProcessorConfig:
    """Configuration for individual processors."""
    enabled: bool = True
    mode: ProcessorMode = ProcessorMode.BALANCED
    confidence_threshold: float = 0.5
    max_results: int = 50
    custom_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleConfig:
    """Configuration for rule engine."""
    enabled_categories: List[str] = field(default_factory=lambda: ["all"])
    disabled_rules: List[str] = field(default_factory=list)
    custom_rules_path: Optional[str] = None
    confidence_threshold: float = 0.6


@dataclass
class EngineConfig:
    """Main configuration for the specification engine."""
    # Processing configuration
    mode: ProcessorMode = ProcessorMode.BALANCED
    parallel_processing: bool = True
    max_workers: int = 4
    timeout: int = 300  # seconds

    # LLM configuration
    llm: LLMConfig = field(default_factory=LLMConfig)

    # Processor configurations
    edge_case_detector: ProcessorConfig = field(default_factory=ProcessorConfig)
    requirement_compressor: ProcessorConfig = field(default_factory=ProcessorConfig)
    contradiction_finder: ProcessorConfig = field(default_factory=ProcessorConfig)
    completeness_validator: ProcessorConfig = field(default_factory=ProcessorConfig)

    # Rule configuration
    rules: RuleConfig = field(default_factory=RuleConfig)

    # Output configuration
    include_metadata: bool = True
    include_confidence_scores: bool = True
    min_severity_level: str = "low"  # low, medium, high, critical

    # Plugin configuration
    plugin_directories: List[str] = field(default_factory=list)
    enabled_plugins: List[str] = field(default_factory=list)

    # Custom settings
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "mode": self.mode.value,
            "parallel_processing": self.parallel_processing,
            "max_workers": self.max_workers,
            "timeout": self.timeout,
            "llm": {
                "provider": self.llm.provider,
                "model": self.llm.model,
                "max_tokens": self.llm.max_tokens,
                "temperature": self.llm.temperature,
                "timeout": self.llm.timeout,
                "enabled": self.llm.enabled
            },
            "processors": {
                "edge_case_detector": {
                    "enabled": self.edge_case_detector.enabled,
                    "mode": self.edge_case_detector.mode.value,
                    "confidence_threshold": self.edge_case_detector.confidence_threshold,
                    "max_results": self.edge_case_detector.max_results,
                    "custom_settings": self.edge_case_detector.custom_settings
                },
                "requirement_compressor": {
                    "enabled": self.requirement_compressor.enabled,
                    "mode": self.requirement_compressor.mode.value,
                    "confidence_threshold": self.requirement_compressor.confidence_threshold,
                    "max_results": self.requirement_compressor.max_results,
                    "custom_settings": self.requirement_compressor.custom_settings
                },
                "contradiction_finder": {
                    "enabled": self.contradiction_finder.enabled,
                    "mode": self.contradiction_finder.mode.value,
                    "confidence_threshold": self.contradiction_finder.confidence_threshold,
                    "max_results": self.contradiction_finder.max_results,
                    "custom_settings": self.contradiction_finder.custom_settings
                },
                "completeness_validator": {
                    "enabled": self.completeness_validator.enabled,
                    "mode": self.completeness_validator.mode.value,
                    "confidence_threshold": self.completeness_validator.confidence_threshold,
                    "max_results": self.completeness_validator.max_results,
                    "custom_settings": self.completeness_validator.custom_settings
                }
            },
            "rules": {
                "enabled_categories": self.rules.enabled_categories,
                "disabled_rules": self.rules.disabled_rules,
                "custom_rules_path": self.rules.custom_rules_path,
                "confidence_threshold": self.rules.confidence_threshold
            },
            "output": {
                "include_metadata": self.include_metadata,
                "include_confidence_scores": self.include_confidence_scores,
                "min_severity_level": self.min_severity_level
            },
            "plugins": {
                "plugin_directories": self.plugin_directories,
                "enabled_plugins": self.enabled_plugins
            },
            "custom": self.custom
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EngineConfig':
        """Create configuration from dictionary."""
        config = cls()

        # Basic settings
        config.mode = ProcessorMode(data.get("mode", "balanced"))
        config.parallel_processing = data.get("parallel_processing", True)
        config.max_workers = data.get("max_workers", 4)
        config.timeout = data.get("timeout", 300)

        # LLM configuration
        if "llm" in data:
            llm_data = data["llm"]
            config.llm = LLMConfig(
                provider=llm_data.get("provider", "anthropic"),
                model=llm_data.get("model", "claude-3-5-sonnet-20241022"),
                max_tokens=llm_data.get("max_tokens", 4000),
                temperature=llm_data.get("temperature", 0.1),
                timeout=llm_data.get("timeout", 30),
                enabled=llm_data.get("enabled", True)
            )

        # Processor configurations
        if "processors" in data:
            proc_data = data["processors"]

            for proc_name in ["edge_case_detector", "requirement_compressor",
                            "contradiction_finder", "completeness_validator"]:
                if proc_name in proc_data:
                    proc_config = proc_data[proc_name]
                    processor_config = ProcessorConfig(
                        enabled=proc_config.get("enabled", True),
                        mode=ProcessorMode(proc_config.get("mode", "balanced")),
                        confidence_threshold=proc_config.get("confidence_threshold", 0.5),
                        max_results=proc_config.get("max_results", 50),
                        custom_settings=proc_config.get("custom_settings", {})
                    )
                    setattr(config, proc_name, processor_config)

        # Rule configuration
        if "rules" in data:
            rules_data = data["rules"]
            config.rules = RuleConfig(
                enabled_categories=rules_data.get("enabled_categories", ["all"]),
                disabled_rules=rules_data.get("disabled_rules", []),
                custom_rules_path=rules_data.get("custom_rules_path"),
                confidence_threshold=rules_data.get("confidence_threshold", 0.6)
            )

        # Output configuration
        if "output" in data:
            output_data = data["output"]
            config.include_metadata = output_data.get("include_metadata", True)
            config.include_confidence_scores = output_data.get("include_confidence_scores", True)
            config.min_severity_level = output_data.get("min_severity_level", "low")

        # Plugin configuration
        if "plugins" in data:
            plugin_data = data["plugins"]
            config.plugin_directories = plugin_data.get("plugin_directories", [])
            config.enabled_plugins = plugin_data.get("enabled_plugins", [])

        # Custom settings
        config.custom = data.get("custom", {})

        return config


class ConfigManager:
    """
    Manager for loading and saving configuration.

    Handles configuration file I/O, environment variable overrides,
    and default configuration management.
    """

    DEFAULT_CONFIG_PATHS = [
        "specify_config.json",
        "~/.specify/config.json",
        "/etc/specify/config.json"
    ]

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self._config: Optional[EngineConfig] = None

    def load_config(self) -> EngineConfig:
        """Load configuration from file or create default."""
        if self._config is not None:
            return self._config

        # Try to load from specified path or default paths
        config_data = {}

        if self.config_path:
            config_data = self._load_config_file(self.config_path)
        else:
            for path in self.DEFAULT_CONFIG_PATHS:
                expanded_path = os.path.expanduser(path)
                if os.path.exists(expanded_path):
                    config_data = self._load_config_file(expanded_path)
                    self.config_path = expanded_path
                    break

        # Apply environment variable overrides
        config_data = self._apply_env_overrides(config_data)

        # Create configuration object
        if config_data:
            self._config = EngineConfig.from_dict(config_data)
        else:
            self._config = EngineConfig()  # Default configuration

        return self._config

    def save_config(self, config: EngineConfig, path: Optional[str] = None) -> None:
        """Save configuration to file."""
        save_path = path or self.config_path or "specify_config.json"

        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

        with open(save_path, 'w') as f:
            json.dump(config.to_dict(), f, indent=2)

        self.config_path = save_path
        self._config = config

    def _load_config_file(self, path: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load config file {path}: {e}")
            return {}

    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        # Environment variable mappings
        env_mappings = {
            "SPECIFY_MODE": ["mode"],
            "SPECIFY_LLM_PROVIDER": ["llm", "provider"],
            "SPECIFY_LLM_MODEL": ["llm", "model"],
            "SPECIFY_LLM_API_KEY": ["llm", "api_key"],
            "SPECIFY_MAX_WORKERS": ["max_workers"],
            "SPECIFY_TIMEOUT": ["timeout"],
            "SPECIFY_PARALLEL": ["parallel_processing"]
        }

        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Navigate to the nested dictionary location
                current = config_data
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]

                # Set the value, converting types as needed
                final_key = config_path[-1]
                if final_key in ["max_workers", "timeout"]:
                    current[final_key] = int(value)
                elif final_key == "parallel_processing":
                    current[final_key] = value.lower() in ("true", "1", "yes")
                else:
                    current[final_key] = value

        return config_data

    def get_config(self) -> EngineConfig:
        """Get current configuration, loading if necessary."""
        return self.load_config()

    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values."""
        config = self.get_config()
        current_dict = config.to_dict()

        # Deep merge updates
        def deep_merge(base, updates):
            for key, value in updates.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    deep_merge(base[key], value)
                else:
                    base[key] = value

        deep_merge(current_dict, updates)

        # Create new config and save
        self._config = EngineConfig.from_dict(current_dict)
        if self.config_path:
            self.save_config(self._config)


# Global configuration manager instance
_config_manager = ConfigManager()

def get_config() -> EngineConfig:
    """Get the global configuration."""
    return _config_manager.get_config()

def set_config_path(path: str) -> None:
    """Set the configuration file path."""
    global _config_manager
    _config_manager = ConfigManager(path)

def update_config(updates: Dict[str, Any]) -> None:
    """Update the global configuration."""
    _config_manager.update_config(updates)

def save_config(config: EngineConfig, path: Optional[str] = None) -> None:
    """Save configuration to file."""
    _config_manager.save_config(config, path)