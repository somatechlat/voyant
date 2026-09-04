"""
Plugin Registry for Extensible Voyant Capabilities.

This module implements a plugin registry for Voyant,
allowing for dynamic registration and execution of various plugins, such as
artifact generators and data analyzers. It provides a singleton
registry that decouples the core application from its extensions.

Usage:
    from apps.core.lib.plugin_registry import (
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
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class PluginCategory(StrEnum):

    VISUALIZATION = "visualization"
    REPORT = "report"
    DATA_QUALITY = "data_quality"
    STATISTICS = "statistics"
    SECURITY = "security"
    OTHER = "other"


@dataclass
class PluginMetadata:
    """Metadata for a registered plugin."""

    name: str
    category: PluginCategory
    version: str
    description: str
    is_core: bool
    feature_flag: str | None = None
    order: int = 100


class VoyantPlugin(abc.ABC):

    def get_name(self) -> str:
        return self.__class__.__name__


class GeneratorPlugin(VoyantPlugin):

    @abc.abstractmethod
    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        pass


class AnalyzerPlugin(VoyantPlugin):

    @abc.abstractmethod
    def analyze(self, data: Any, context: dict[str, Any]) -> dict[str, Any]:
        pass


class PluginRegistry:
    """Singleton registry for discovering, managing, and instantiating plugins."""

    _instance: PluginRegistry | None = None

    def __init__(self):
        if PluginRegistry._instance is not None:
            raise RuntimeError(
                "PluginRegistry is a singleton and should not be re-instantiated."
            )
        self._plugins: dict[str, type[VoyantPlugin]] = {}
        self._metadata: dict[str, PluginMetadata] = {}
        self._instances: dict[str, VoyantPlugin] = {}

    @classmethod
    def get_instance(cls) -> PluginRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(
        self,
        cls_obj: type[VoyantPlugin],
        name: str,
        category: PluginCategory,
        version: str = "1.0.0",
        description: str = "",
        is_core: bool = False,
        feature_flag: str | None = None,
        order: int = 100,
    ):
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

    def get_plugin_instance(self, name: str) -> VoyantPlugin | None:
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

    def get_all_metadata(self) -> list[PluginMetadata]:
        meta_list = list(self._metadata.values())
        return sorted(meta_list, key=lambda m: m.order)

    def get_plugins_by_category(self, category: PluginCategory) -> list[PluginMetadata]:
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
    feature_flag: str | None = None,
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


def get_generators() -> list[PluginMetadata]:
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


def get_analyzers() -> list[PluginMetadata]:
    registry = PluginRegistry.get_instance()
    all_meta = registry.get_all_metadata()

    analyzers = []
    for meta in all_meta:
        cls = registry._plugins.get(meta.name)
        if cls and issubclass(cls, AnalyzerPlugin):
            analyzers.append(meta)
    return analyzers


def get_plugin(name: str) -> VoyantPlugin | None:
    return PluginRegistry.get_instance().get_plugin_instance(name)


def reset_registry():
    PluginRegistry.get_instance().clear()
