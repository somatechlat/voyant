"""
Generation Activities

Temporal activities for executing artifact generators.
Adheres to Vibe Coding Rules: Uses Plugin Registry for extensibility.
"""
import logging
from typing import Any, Dict, List

from temporalio import activity

from voyant.core.plugin_registry import get_generators, PluginCategory
from voyant.core.errors import ArtifactGenerationError

logger = logging.getLogger(__name__)

class GenerationActivities:
    """Activities for generating artifacts."""
    
    def __init__(self):
        pass
        
    @activity.defn
    def run_generators(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all registered artifact generators.
        
        Args:
            params: Dict containing context (e.g. table_name, job_id)
            
        Returns:
            Dict of generated artifacts {generator_name: result}
        """
        results = {}
        errors = []
        
        # Get all generator metadata
        generator_infos = get_generators()
        
        if not generator_infos:
            activity.logger.warning("No generator plugins registered")
            return {}
            
        activity.logger.info(f"Running {len(generator_infos)} generators")
        
        for info in generator_infos:
            # Check feature flag if present
            if info.feature_flag:
                # In a real impl, we'd check settings here. For now assuming enabled or passed in params
                pass

            try:
                # Load plugin instance (lazy)
                from voyant.core.plugin_registry import get_plugin
                generator = get_plugin(info.name)
                
                if not generator:
                    activity.logger.error(f"Failed to load generator {info.name}")
                    continue
                
                # Execute generation
                activity.logger.info(f"Executing generator: {info.name} ({info.category.value})")
                result = generator.generate(params)
                results[info.name] = result
                
            except Exception as e:
                error_msg = f"Generator {info.name} failed: {e}"
                activity.logger.error(error_msg)
                errors.append(error_msg)
                
                # Fail fast if core plugin
                if info.is_core:
                    activity.logger.error(f"Core generator {info.name} failed - halting pipeline")
                    raise activity.ApplicationError(f"Core generator failed: {error_msg}")

        if errors:
            results["_errors"] = errors
            
        return results
