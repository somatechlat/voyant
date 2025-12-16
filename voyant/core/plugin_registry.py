"""
Plugin Registry for Artifact Generators

Implements the design from CANONICAL_ARCHITECTURE.md Section 7.

Each generator:
- Receives a context dict (job_id, source, tables, flags, paths)
- Returns a dict of artifact_key -> file_path
- Is either "core" (fail-fast) or "extended" (isolate failures)
- Can be gated by a feature flag

Execution patterns:
- Core generators: execution stops on first failure
- Extended generators: failures are logged, execution continues

Usage:
    from voyant.core.plugin_registry import (
        register, run_generators, list_generators,
        GeneratorContext, ArtifactResult
    )
    
    @register("my_generator", is_core=False, feature_flag="enable_my_feature")
    def generate_my_artifact(ctx: GeneratorContext) -> ArtifactResult:
        # Generate artifact...
        return {"my_artifact": "/path/to/artifact.json"}
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# Type Definitions
# =============================================================================

# Context passed to each generator
GeneratorContext = Dict[str, Any]
"""
Expected context keys:
- job_id: str - Unique job identifier
- tenant_id: str - Tenant namespace
- artifacts_root: str - Base path for artifacts
- tables: List[str] - Tables involved in analysis
- kpis: List[dict] - KPI definitions
- flags: Dict[str, bool] - Feature flags
"""

# Result returned by generator: artifact_key -> file_path
ArtifactResult = Dict[str, str]


@dataclass
class GeneratorDefinition:
    """Definition of an artifact generator."""
    name: str
    handler: Callable[[GeneratorContext], ArtifactResult]
    is_core: bool = False
    feature_flag: Optional[str] = None
    order: int = 100  # Lower = earlier execution
    description: str = ""


# =============================================================================
# Registry
# =============================================================================

# Global registry of generators
_REGISTRY: List[GeneratorDefinition] = []


def register(
    name: str,
    is_core: bool = False,
    feature_flag: Optional[str] = None,
    order: int = 100,
    description: str = "",
):
    """
    Decorator to register an artifact generator.
    
    Args:
        name: Unique generator name (e.g., "profile", "quality", "charts")
        is_core: If True, failure stops the pipeline (fail-fast)
        feature_flag: Settings field name to check (e.g., "enable_quality")
        order: Execution order (lower runs first, default 100)
        description: Human-readable description
    
    Example:
        @register("profile", is_core=True, order=10)
        def generate_profile(ctx):
            return {"profile": "/path/profile.json"}
    """
    def decorator(fn: Callable[[GeneratorContext], ArtifactResult]):
        _REGISTRY.append(GeneratorDefinition(
            name=name,
            handler=fn,
            is_core=is_core,
            feature_flag=feature_flag,
            order=order,
            description=description or fn.__doc__ or "",
        ))
        # Sort by order after each registration
        _REGISTRY.sort(key=lambda g: g.order)
        logger.debug(f"Registered generator: {name} (core={is_core}, order={order})")
        return fn
    return decorator


def list_generators() -> List[Dict[str, Any]]:
    """List all registered generators with their metadata."""
    return [
        {
            "name": g.name,
            "is_core": g.is_core,
            "feature_flag": g.feature_flag,
            "order": g.order,
            "description": g.description,
        }
        for g in _REGISTRY
    ]


def get_generator(name: str) -> Optional[GeneratorDefinition]:
    """Get a specific generator by name."""
    for g in _REGISTRY:
        if g.name == name:
            return g
    return None


def clear_registry():
    """Clear all registered generators (for testing)."""
    _REGISTRY.clear()


# =============================================================================
# Execution Engine
# =============================================================================

@dataclass
class GeneratorResult:
    """Result of a single generator execution."""
    name: str
    success: bool
    artifacts: ArtifactResult = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0


@dataclass
class PipelineResult:
    """Result of running all generators."""
    success: bool
    artifacts: ArtifactResult
    results: List[GeneratorResult]
    failed_core: Optional[str] = None  # Name of failed core generator


def run_generators(
    context: GeneratorContext,
    settings: Optional[Any] = None,
) -> PipelineResult:
    """
    Execute all registered generators in order.
    
    Args:
        context: Generator context (job_id, tables, etc.)
        settings: Optional settings object for feature flag checks.
                  If None, will import from config.
    
    Returns:
        PipelineResult with all artifacts and individual results
    """
    if settings is None:
        from voyant.core.config import get_settings
        settings = get_settings()
    
    all_artifacts: ArtifactResult = {}
    results: List[GeneratorResult] = []
    failed_core: Optional[str] = None
    
    for gen in _REGISTRY:
        # Check feature flag
        if gen.feature_flag:
            flag_value = getattr(settings, gen.feature_flag, True)
            if not flag_value:
                logger.debug(f"Skipping {gen.name}: feature flag {gen.feature_flag} is disabled")
                continue
        
        start = datetime.utcnow()
        
        try:
            artifacts = gen.handler(context)
            duration = (datetime.utcnow() - start).total_seconds() * 1000
            
            all_artifacts.update(artifacts)
            results.append(GeneratorResult(
                name=gen.name,
                success=True,
                artifacts=artifacts,
                duration_ms=duration,
            ))
            logger.info(f"Generator {gen.name} completed in {duration:.1f}ms")
            
        except Exception as e:
            duration = (datetime.utcnow() - start).total_seconds() * 1000
            error_msg = str(e)
            
            results.append(GeneratorResult(
                name=gen.name,
                success=False,
                error=error_msg,
                duration_ms=duration,
            ))
            
            if gen.is_core:
                # Core generator failed - stop pipeline
                logger.error(f"Core generator {gen.name} failed: {e}")
                failed_core = gen.name
                break
            else:
                # Extended generator - log and continue
                logger.warning(f"Extended generator {gen.name} failed (continuing): {e}")
    
    return PipelineResult(
        success=failed_core is None,
        artifacts=all_artifacts,
        results=results,
        failed_core=failed_core,
    )


# =============================================================================
# Built-in Generators (Basic implementations - full logic in analyze.py)
# =============================================================================
#
# Note: These are basic registrations. The actual implementations will be in
# modules under voyant.analyze.* as they are built out.
# These registrations provide the canonical ordering and feature flag mapping.

# Order: profile (10) -> kpi (20) -> sufficiency (30) -> quality (40) 
#        -> drift (50) -> charts (60) -> narrative (70)

# register("profile", is_core=True, order=10, description="Data profiling (ydata-profiling)")
# register("kpi", is_core=True, order=20, description="KPI SQL execution")
# register("sufficiency", is_core=True, order=30, description="Sufficiency scoring")
# register("quality", is_core=False, order=40, feature_flag="enable_quality")
# register("drift", is_core=False, order=50, feature_flag="enable_quality")
# register("charts", is_core=False, order=60, feature_flag="enable_charts")
# register("narrative", is_core=False, order=70, feature_flag="enable_narrative")
