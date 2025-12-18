"""
Plugin Registry for Artifact Generators

Implements the "Platform of Platforms" design pattern.
Reference: docs/CANONICAL_ARCHITECTURE.md Section 7.

Seven personas applied:
- PhD Developer: Dependency injection, Singleton pattern, ABC interfaces
- PhD Analyst: Categorized plugins for targeted execution
- PhD QA Engineer: Robust error isolation and typing
- ISO Documenter: Self-describing plugins
- Security Auditor: Explicit execution contexts
- Performance Engineer: Lazy loading of heavyweight plugins
- UX Consultant: Metadata-driven UI discovery

Usage:
    from voyant.core.plugin_registry import (
        register_plugin, GeneratorPlugin, PluginCategory,
        dget_registry
    )
    
    @register_plugin(
        name="my_viz",
        category=PluginCategory.VISUALIZATION,
        description="My Visualization"
    )
    class MyGenerator(GeneratorPlugin):
        def generate(self, context: Dict[str, Any]) -> Dict[str, Any]:
            ...
"""
from __future__ import annotations

import logging
import abc
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class PluginCategory(str, Enum):
    """Category of the plugin for UI grouping and execution filtering."""
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
    is_core: bool  # If True, failure halts the pipeline (fail-fast)
    feature_flag: Optional[str] = None
    order: int = 100


class VoyantPlugin(abc.ABC):
    """Abstract base class for all plugins."""
    
    def get_name(self) -> str:
        """Return the unique name of this plugin."""
        return self.__class__.__name__

class GeneratorPlugin(VoyantPlugin):
    """
    Abstract base class for artifact generators.
    """
    @abc.abstractmethod
    def generate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate artifacts."""
        pass

class AnalyzerPlugin(VoyantPlugin):
    """
    Abstract base class for data analyzers.
    """
    @abc.abstractmethod
    def analyze(self, data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze data and return insights."""
        pass

class PluginRegistry:
    """
    Central registry for all plugins.
    
    Implements a Singleton pattern to ensure a single source of truth.
    """
    _instance: Optional[PluginRegistry] = None
    
    def __init__(self):
        # Maps name -> Plugin Class
        self._plugins: Dict[str, Type[VoyantPlugin]] = {}
        # Maps name -> PluginMetadata
        self._metadata: Dict[str, PluginMetadata] = {}
        # Maps name -> Instantiated Plugin (Lazy Cache)
        self._instances: Dict[str, VoyantPlugin] = {}
    
    @classmethod
    def get_instance(cls) -> PluginRegistry:
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
        order: int = 100
    ):
        """Register a new plugin class."""
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
            order=order
        )
        # Clear instance cache if re-registering
        if name in self._instances:
            del self._instances[name]
            
        logger.debug(f"Registered plugin: {name} ({category.value})")
    
    def get_plugin_instance(self, name: str) -> Optional[VoyantPlugin]:
        """Get or create a singleton instance of the plugin."""
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
        """Get metadata for all registered plugins, sorted by order."""
        meta_list = list(self._metadata.values())
        return sorted(meta_list, key=lambda m: m.order)
        
    def get_plugins_by_category(self, category: PluginCategory) -> List[PluginMetadata]:
        """Get plugins filtered by category."""
        return [m for m in self.get_all_metadata() if m.category == category]

    def clear(self):
        """Clear registry (useful for testing)."""
        self._plugins.clear()
        self._metadata.clear()
        self._instances.clear()


# =============================================================================
# Public Decorators & Helpers
# =============================================================================

def register_plugin(
    name: str,
    category: PluginCategory = PluginCategory.OTHER,
    version: str = "1.0.0",
    description: str = "",
    is_core: bool = False,
    feature_flag: Optional[str] = None,
    order: int = 100
):
    """
    Decorator to register a class as a plugin.
    
    Usage:
        @register_plugin(name="my_plugin", category=PluginCategory.REPORT)
        class MyPlugin(GeneratorPlugin): ...
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
            order=order
        )
        return cls_obj
    return wrapper


def get_generators() -> List[PluginMetadata]:
    """Retrieves all available generator metadata."""
    # Filter for Generators only
    registry = PluginRegistry.get_instance()
    all_meta = registry.get_all_metadata()
    # Check class type of registered plugin?
    # Metadata doesn't store class type directly, but registry._plugins does.
    # simpler: just strictly use category or check inheritance if needed.
    # For now, let's rely on the fact that we might want all plugins or filter by cat.
    # But wait, get_generators was used assuming everything is a generator.
    # Now we have mixed. We should filter.
    
    # Ideally we filter by inheritance, but metadata is lightweight.
    # Let's check the _plugins dict.
    gens = []
    for meta in all_meta:
        cls = registry._plugins.get(meta.name)
        if cls and issubclass(cls, GeneratorPlugin):
            gens.append(meta)
    return gens


def get_analyzers() -> List[PluginMetadata]:
    """Retrieves all available analyzer metadata."""
    registry = PluginRegistry.get_instance()
    all_meta = registry.get_all_metadata()
    analyzers = []
    for meta in all_meta:
        cls = registry._plugins.get(meta.name)
        if cls and issubclass(cls, AnalyzerPlugin):
            analyzers.append(meta)
    return analyzers


def get_plugin(name: str) -> Optional[GeneratorPlugin]:
    """Retrieves an instantiated plugin by name."""
    return PluginRegistry.get_instance().get_plugin_instance(name)


def reset_registry():
    """Reset the registry (testing)."""
    PluginRegistry.get_instance().clear()
