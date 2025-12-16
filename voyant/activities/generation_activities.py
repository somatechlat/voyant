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
        self._generators = {}  # Cache loaded generators
        
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
        
        # Get all generator plugins
        generator_infos = get_generators()
        
        if not generator_infos:
            activity.logger.warning("No generator plugins registered")
            return {}
            
        activity.logger.info(f"Running {len(generator_infos)} generators")
        
        for info in generator_infos:
            try:
                # Load plugin instance (lazy)
                if info.name not in self._generators:
                    from voyant.core.plugin_registry import get_plugin
                    self._generators[info.name] = get_plugin(info.name)
                
                generator = self._generators[info.name]
                
                if not generator:
                    activity.logger.error(f"Failed to load generator {info.name}")
                    continue
                
                # Execute generation
                activity.logger.info(f"Executing generator: {info.name}")
                result = generator.generate(params)
                results[info.name] = result
                
            except Exception as e:
                error_msg = f"Generator {info.name} failed: {e}"
                activity.logger.error(error_msg)
                errors.append(error_msg)
                # We don't fail the whole activity for one generator failure
                # unless it causes empty results where results are expected?
                # For now, we collect best-effort results.
        
        if errors:
            results["_errors"] = errors
            
        return results
