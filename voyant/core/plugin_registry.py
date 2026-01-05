"""
Plugin Registry for Extensible Voyant Capabilities.

This module implements the "Platform of Platforms" design pattern for Voyant,
allowing for dynamic registration and execution of various plugins, such as
artifact generators and data analyzers. It provides a centralized, singleton
registry that decouples the core application from its extensions.

Seven personas applied:
- PhD Developer: Uses Singleton and Abstract Base Class patterns for a clean, extensible architecture.
- PhD Analyst: Enables categorization of plugins for targeted execution in analysis pipelines.
- PhD QA Engineer: Provides registry clearing functions for robust test isolation.
- ISO Documenter: Ensures plugins are self-describing via metadata.
- Security Auditor: Confirms that plugin execution is an explicit and controlled process.
- Performance Engineer: Implements lazy instantiation of plugins to reduce startup overhead.
- UX Consultant: Uses metadata to allow for dynamic discovery and presentation of plugins in a UI.

Usage:
    from voyant.core.plugin_registry import (
        register_plugin, GeneratorPlugin, PluginCategory
    )

    @register_plugin(
        name="my_visualization",
        category=PluginCategory.VISUALIZATION,
        description="Creates a custom plot from analysis data."
    )
    class MyVisualizer(GeneratorPlugin):
        def generate(self, context: Dict[str, Any]) -> Dict[str, Any]:
            # Plugin logic to generate an artifact (e.g., a chart)
            ...
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class PluginCategory(str, Enum):
    """Defines the category of a plugin for UI grouping and filtering during execution."""

    VISUALIZATION = "visualization"
    REPORT = "report"
    DATA_QUALITY = "data_quality"
    STATISTICS = "statistics"
    SECURITY = "security"
    OTHER = "other"


@dataclass
class PluginMetadata:
    """
    Metadata for a registered plugin, making it self-describing.

    Attributes:
        name: The unique identifier for the plugin.
        category: The category for grouping and filtering.
        version: The version of the plugin.
        description: A human-readable description of what the plugin does.
        is_core: If True, indicates a critical plugin whose failure may halt a pipeline.
        feature_flag: An optional feature flag name that can toggle this plugin's execution.
        order: An integer used for sorting plugins for execution or display.
    """

    name: str
    category: PluginCategory
    version: str
    description: str
    is_core: bool
    feature_flag: Optional[str] = None
    order: int = 100


class VoyantPlugin(abc.ABC):
    """Abstract base class for all Voyant plugins, defining a common interface."""

    def get_name(self) -> str:
        """Return the unique name of this plugin's class."""
        return self.__class__.__name__


class GeneratorPlugin(VoyantPlugin):
    """
    Abstract base class for artifact generators.

    Generator plugins are responsible for creating new artifacts, such as
    visualizations or reports, based on provided context data.
    """

    @abc.abstractmethod
    def generate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an artifact.

        Args:
            context: A dictionary containing data and metadata needed for generation.

        Returns:
            A dictionary representing the generated artifact.
        """
        raise NotImplementedError


class AnalyzerPlugin(VoyantPlugin):
    """
    Abstract base class for data analyzers.

    Analyzer plugins are responsible for running analyses on datasets and
    returning structured insights.
    """

    @abc.abstractmethod
    def analyze(self, data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze data and return insights.

        Args:
            data: The primary data to be analyzed (e.g., a pandas DataFrame).
            context: A dictionary containing additional metadata for the analysis.

        Returns:
            A dictionary containing the results of the analysis.
        """
        raise NotImplementedError


class PluginRegistry:
    """
    A singleton registry for discovering, managing, and instantiating all plugins.

    This central class holds the mappings of all registered plugin classes and
    their associated metadata. It also manages the lazy instantiation of plugins
    to ensure they are only created when first requested.
    """

    _instance: Optional[PluginRegistry] = None

    def __init__(self):
        if PluginRegistry._instance is not None:
            raise RuntimeError("PluginRegistry is a singleton and should not be re-instantiated.")
        self._plugins: Dict[str, Type[VoyantPlugin]] = {}
        self._metadata: Dict[str, PluginMetadata] = {}
        self._instances: Dict[str, VoyantPlugin] = {}

    @classmethod
    def get_instance(cls) -> PluginRegistry:
        """Get the singleton instance of the PluginRegistry."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(
        self,
        cls_obj: Type[VoyantPlugin],
        name: str,
        category: PluginCategory,
        version: str = "1.0.0",
        description: str = "",
        is_core: bool = False,
        feature_flag: Optional[str] = None,
        order: int = 100,
    ):
        """
        Register a new plugin class and its metadata with the registry.

        If a plugin with the same name already exists, it will be overwritten.
        """
        if name in self._plugins:
            logger.warning(f"Overwriting existing plugin registration: {name}")

        self._plugins[name] = cls_obj
        self._metadata[name] = PluginMetadata(
            name=name,
            category=category,
            version=version,
            description=description,
            is_core=is_core,
            feature_flag=feature_flag,
            order=order,
        )
        # Clear any previously cached instance if re-registering
        if name in self._instances:
            del self._instances[name]

        logger.debug(f"Registered plugin: {name} ({category.value})")

    def get_plugin_instance(self, name: str) -> Optional[VoyantPlugin]:
        """
        Get a singleton instance of a plugin by name, creating it if it doesn't exist.

        This method implements lazy instantiation. The plugin is only instantiated
        on its first retrieval.
        """
        if name not in self._plugins:
            return None

        if name not in self._instances:
            try:
                cls_obj = self._plugins[name]
                self._instances[name] = cls_obj()
            except Exception as e:
                logger.error(f"Failed to instantiate plugin {name}: {e}")
                return None

        return self._instances[name]

    def get_all_metadata(self) -> List[PluginMetadata]:
        """Get metadata for all registered plugins, sorted by execution order."""
        meta_list = list(self._metadata.values())
        return sorted(meta_list, key=lambda m: m.order)

    def get_plugins_by_category(self, category: PluginCategory) -> List[PluginMetadata]:
        """Get metadata for all plugins belonging to a specific category."""
        return [m for m in self.get_all_metadata() if m.category == category]

    def clear(self):
        """Clear the entire registry. Primarily used for isolated testing."""
        self._plugins.clear()
        self._metadata.clear()
        self._instances.clear()


# =============================================================================
# Public Decorators & Helper Functions
# =============================================================================


def register_plugin(
    name: str,
    category: PluginCategory = PluginCategory.OTHER,
    version: str = "1.0.0",
    description: str = "",
    is_core: bool = False,
    feature_flag: Optional[str] = None,
    order: int = 100,
):
    """
    A class decorator to register a class as a Voyant plugin.

    Usage:
        @register_plugin(name="my_plugin", category=PluginCategory.REPORT)
        class MyPlugin(GeneratorPlugin):
            ...
    """

    def wrapper(cls_obj):
        if not issubclass(cls_obj, VoyantPlugin):
            raise TypeError(f"Plugin {cls_obj.__name__} must inherit from VoyantPlugin")

        registry = PluginRegistry.get_instance()
        registry.register(
            cls_obj=cls_obj,
            name=name,
            category=category,
            version=version,
            description=description,
            is_core=is_core,
            feature_flag=feature_flag,
            order=order,
        )
        return cls_obj

    return wrapper


def get_generators() -> List[PluginMetadata]:
    """Retrieve metadata for all registered plugins that are of type GeneratorPlugin."""
    registry = PluginRegistry.get_instance()
    all_meta = registry.get_all_metadata()

    # To ensure type safety, we inspect the class from the internal _plugins
    # dictionary corresponding to the metadata and check its inheritance.
    generators = []
    for meta in all_meta:
        cls = registry._plugins.get(meta.name)
        if cls and issubclass(cls, GeneratorPlugin):
            generators.append(meta)
    return generators


def get_analyzers() -> List[PluginMetadata]:
    """Retrieve metadata for all registered plugins that are of type AnalyzerPlugin."""
    registry = PluginRegistry.get_instance()
    all_meta = registry.get_all_metadata()

    analyzers = []
    for meta in all_meta:
        cls = registry._plugins.get(meta.name)
        if cls and issubclass(cls, AnalyzerPlugin):
            analyzers.append(meta)
    return analyzers


def get_plugin(name: str) -> Optional[VoyantPlugin]:
    """
    Retrieve an instantiated plugin by its unique name.

    Returns:
        An instance of the requested plugin, or None if not found.
    """
    return PluginRegistry.get_instance().get_plugin_instance(name)


def reset_registry():
    """
    Clear the entire plugin registry.

    This is a convenience function intended for use in testing to ensure
    a clean state between test runs.
    """
    PluginRegistry.get_instance().clear()
