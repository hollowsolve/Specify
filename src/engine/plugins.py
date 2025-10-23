"""
Plugin system for the specification engine.

This module provides a plugin architecture that allows extending the
specification engine with custom processors and rules.
"""

import importlib
import inspect
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Type, Optional, Callable
from dataclasses import dataclass
from pathlib import Path

from .models import AnalysisResult, RefinedSpecification
from .rules.rule_engine import Rule


@dataclass
class PluginInfo:
    """Information about a registered plugin."""
    name: str
    version: str
    description: str
    author: str
    plugin_type: str
    module_path: str
    enabled: bool = True


class PluginInterface(ABC):
    """Base interface for all plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description."""
        pass

    @property
    def author(self) -> str:
        """Plugin author."""
        return "Unknown"

    @property
    def plugin_type(self) -> str:
        """Type of plugin."""
        return "generic"

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the plugin with configuration."""
        pass

    def cleanup(self) -> None:
        """Cleanup resources when plugin is unloaded."""
        pass


class ProcessorPlugin(PluginInterface):
    """Base class for processor plugins."""

    @property
    def plugin_type(self) -> str:
        return "processor"

    @abstractmethod
    def process(self, analysis: AnalysisResult, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the analysis result and return processing results.

        Args:
            analysis: The analysis result from Phase 1
            context: Additional context for processing

        Returns:
            Dictionary containing processing results
        """
        pass

    def get_priority(self) -> int:
        """
        Get the priority of this processor (lower = runs first).

        Returns:
            Priority value (default: 100)
        """
        return 100


class RulePlugin(PluginInterface):
    """Base class for rule plugins."""

    @property
    def plugin_type(self) -> str:
        return "rule"

    @abstractmethod
    def get_rules(self) -> List[Rule]:
        """
        Get the rules provided by this plugin.

        Returns:
            List of Rule objects
        """
        pass

    def get_rule_categories(self) -> Dict[str, List[str]]:
        """
        Get rule categories provided by this plugin.

        Returns:
            Dictionary mapping category names to rule IDs
        """
        return {}


class ValidatorPlugin(PluginInterface):
    """Base class for validation plugins."""

    @property
    def plugin_type(self) -> str:
        return "validator"

    @abstractmethod
    def validate_specification(self, specification: RefinedSpecification) -> List[Dict[str, Any]]:
        """
        Validate a refined specification.

        Args:
            specification: The refined specification to validate

        Returns:
            List of validation issues
        """
        pass


class PluginManager:
    """
    Manager for loading, registering, and executing plugins.

    The plugin manager provides a centralized way to manage plugins
    for the specification engine.
    """

    def __init__(self):
        self.plugins: Dict[str, PluginInterface] = {}
        self.plugin_info: Dict[str, PluginInfo] = {}
        self.processor_plugins: List[ProcessorPlugin] = []
        self.rule_plugins: List[RulePlugin] = []
        self.validator_plugins: List[ValidatorPlugin] = []

    def load_plugins_from_directory(self, directory: str) -> None:
        """Load all plugins from a directory."""
        if not os.path.exists(directory):
            return

        plugin_dir = Path(directory)

        # Look for Python files
        for py_file in plugin_dir.glob("*.py"):
            if py_file.name.startswith("_"):  # Skip private files
                continue

            try:
                self._load_plugin_from_file(str(py_file))
            except Exception as e:
                print(f"Warning: Failed to load plugin from {py_file}: {e}")

        # Look for plugin packages
        for subdir in plugin_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("_"):
                init_file = subdir / "__init__.py"
                if init_file.exists():
                    try:
                        self._load_plugin_from_package(str(subdir))
                    except Exception as e:
                        print(f"Warning: Failed to load plugin package {subdir}: {e}")

    def _load_plugin_from_file(self, file_path: str) -> None:
        """Load a plugin from a Python file."""
        spec = importlib.util.spec_from_file_location("plugin_module", file_path)
        if spec is None or spec.loader is None:
            return

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self._register_plugins_from_module(module, file_path)

    def _load_plugin_from_package(self, package_path: str) -> None:
        """Load a plugin from a Python package."""
        package_name = os.path.basename(package_path)
        spec = importlib.util.spec_from_file_location(
            package_name,
            os.path.join(package_path, "__init__.py")
        )

        if spec is None or spec.loader is None:
            return

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self._register_plugins_from_module(module, package_path)

    def _register_plugins_from_module(self, module, module_path: str) -> None:
        """Register all plugins found in a module."""
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and
                issubclass(obj, PluginInterface) and
                obj != PluginInterface and
                not inspect.isabstract(obj)):

                try:
                    plugin_instance = obj()
                    self.register_plugin(plugin_instance, module_path)
                except Exception as e:
                    print(f"Warning: Failed to instantiate plugin {name}: {e}")

    def register_plugin(self, plugin: PluginInterface, module_path: str = "") -> None:
        """Register a plugin instance."""
        plugin_name = plugin.name

        if plugin_name in self.plugins:
            print(f"Warning: Plugin {plugin_name} already registered, skipping")
            return

        # Store plugin and info
        self.plugins[plugin_name] = plugin

        self.plugin_info[plugin_name] = PluginInfo(
            name=plugin.name,
            version=plugin.version,
            description=plugin.description,
            author=plugin.author,
            plugin_type=plugin.plugin_type,
            module_path=module_path
        )

        # Add to type-specific lists
        if isinstance(plugin, ProcessorPlugin):
            self.processor_plugins.append(plugin)
            # Sort by priority
            self.processor_plugins.sort(key=lambda p: p.get_priority())

        elif isinstance(plugin, RulePlugin):
            self.rule_plugins.append(plugin)

        elif isinstance(plugin, ValidatorPlugin):
            self.validator_plugins.append(plugin)

        print(f"Registered plugin: {plugin_name} ({plugin.plugin_type})")

    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a plugin."""
        if plugin_name not in self.plugins:
            return

        plugin = self.plugins[plugin_name]

        # Call cleanup
        try:
            plugin.cleanup()
        except Exception as e:
            print(f"Warning: Plugin {plugin_name} cleanup failed: {e}")

        # Remove from type-specific lists
        if isinstance(plugin, ProcessorPlugin):
            self.processor_plugins = [p for p in self.processor_plugins if p.name != plugin_name]
        elif isinstance(plugin, RulePlugin):
            self.rule_plugins = [p for p in self.rule_plugins if p.name != plugin_name]
        elif isinstance(plugin, ValidatorPlugin):
            self.validator_plugins = [p for p in self.validator_plugins if p.name != plugin_name]

        # Remove from main registry
        del self.plugins[plugin_name]
        del self.plugin_info[plugin_name]

        print(f"Unregistered plugin: {plugin_name}")

    def enable_plugin(self, plugin_name: str) -> None:
        """Enable a plugin."""
        if plugin_name in self.plugin_info:
            self.plugin_info[plugin_name].enabled = True

    def disable_plugin(self, plugin_name: str) -> None:
        """Disable a plugin."""
        if plugin_name in self.plugin_info:
            self.plugin_info[plugin_name].enabled = False

    def get_enabled_plugins(self, plugin_type: Optional[str] = None) -> List[PluginInterface]:
        """Get all enabled plugins, optionally filtered by type."""
        enabled_plugins = []

        for plugin_name, plugin in self.plugins.items():
            if self.plugin_info[plugin_name].enabled:
                if plugin_type is None or plugin.plugin_type == plugin_type:
                    enabled_plugins.append(plugin)

        return enabled_plugins

    def get_processor_plugins(self) -> List[ProcessorPlugin]:
        """Get all enabled processor plugins."""
        return [p for p in self.processor_plugins
                if self.plugin_info[p.name].enabled]

    def get_rule_plugins(self) -> List[RulePlugin]:
        """Get all enabled rule plugins."""
        return [p for p in self.rule_plugins
                if self.plugin_info[p.name].enabled]

    def get_validator_plugins(self) -> List[ValidatorPlugin]:
        """Get all enabled validator plugins."""
        return [p for p in self.validator_plugins
                if self.plugin_info[p.name].enabled]

    def initialize_plugins(self, config: Dict[str, Any]) -> None:
        """Initialize all enabled plugins with configuration."""
        for plugin_name, plugin in self.plugins.items():
            if self.plugin_info[plugin_name].enabled:
                try:
                    plugin_config = config.get(f"plugin_{plugin_name}", {})
                    plugin.initialize(plugin_config)
                except Exception as e:
                    print(f"Warning: Failed to initialize plugin {plugin_name}: {e}")

    def get_plugin_info(self) -> Dict[str, PluginInfo]:
        """Get information about all registered plugins."""
        return self.plugin_info.copy()

    def get_plugin_statistics(self) -> Dict[str, Any]:
        """Get statistics about registered plugins."""
        total_plugins = len(self.plugins)
        enabled_plugins = sum(1 for info in self.plugin_info.values() if info.enabled)

        type_counts = {}
        for info in self.plugin_info.values():
            plugin_type = info.plugin_type
            type_counts[plugin_type] = type_counts.get(plugin_type, 0) + 1

        return {
            "total_plugins": total_plugins,
            "enabled_plugins": enabled_plugins,
            "disabled_plugins": total_plugins - enabled_plugins,
            "type_distribution": type_counts,
            "plugin_types": list(type_counts.keys())
        }


# Global plugin manager instance
_plugin_manager = PluginManager()

def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager."""
    return _plugin_manager

def register_plugin(plugin: PluginInterface) -> None:
    """Register a plugin with the global manager."""
    _plugin_manager.register_plugin(plugin)

def load_plugins_from_directory(directory: str) -> None:
    """Load plugins from a directory using the global manager."""
    _plugin_manager.load_plugins_from_directory(directory)