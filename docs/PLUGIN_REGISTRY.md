# Plugin Registry Documentation

## Overview

The Voyant Plugin Registry provides a formal abstraction layer for artifact generators. It enables modular, extensible analytics pipelines where generators can be added, removed, or gated without code changes.

**Reference**: docs/CANONICAL_ARCHITECTURE.md Section 7

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PLUGIN REGISTRY                          │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────────┐  ┌───────────────────┐             │
│  │  Core Generators  │  │Extended Generators│             │
│  │  (fail-fast)      │  │(isolate-failures) │             │
│  ├───────────────────┤  ├───────────────────┤             │
│  │ profile (10)      │  │ quality (40)      │             │
│  │ kpi (20)          │  │ drift (50)        │             │
│  │ sufficiency (30)  │  │ charts (60)       │             │
│  │                   │  │ narrative (70)    │             │
│  └───────────────────┘  └───────────────────┘             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 EXECUTION ENGINE                            │
│  1. Sort by order                                           │
│  2. Check feature flags                                     │
│  3. Execute in sequence                                     │
│  4. Collect artifacts                                       │
│  5. Stop on core failure OR continue on extended failure    │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Registering a Generator

```python
from voyant.core.plugin_registry import register, GeneratorContext, ArtifactResult

@register(
    name="my_generator",
    is_core=False,           # True = pipeline stops on failure
    feature_flag="enable_my_feature",  # Settings field to check
    order=75,                # Lower = runs earlier
    description="Generate my custom artifact"
)
def generate_my_artifact(ctx: GeneratorContext) -> ArtifactResult:
    """
    Generate a custom artifact.
    
    Args:
        ctx: Context dict with job_id, tenant_id, tables, kpis, flags, artifacts_root
    
    Returns:
        Dict of artifact_key -> file_path
    """
    job_id = ctx["job_id"]
    output_path = f"{ctx['artifacts_root']}/{job_id}/my_artifact.json"
    
    # Generate artifact...
    with open(output_path, "w") as f:
        f.write('{"result": "success"}')
    
    return {"my_artifact": output_path}
```

### Running the Pipeline

```python
from voyant.core.plugin_registry import run_generators

result = run_generators({
    "job_id": "job_123",
    "tenant_id": "acme",
    "artifacts_root": "/artifacts",
    "tables": ["customers", "orders"],
    "kpis": [{"name": "revenue", "sql": "SELECT SUM(amount)..."}],
    "flags": {},
})

if result.success:
    print(f"Generated artifacts: {result.artifacts}")
else:
    print(f"Pipeline failed at: {result.failed_core}")
```

## Generator Context

The `GeneratorContext` dict contains:

| Key | Type | Description |
|-----|------|-------------|
| `job_id` | str | Unique job identifier |
| `tenant_id` | str | Tenant namespace |
| `artifacts_root` | str | Base path for writing artifacts |
| `tables` | List[str] | Tables involved in analysis |
| `kpis` | List[dict] | KPI definitions from request |
| `flags` | Dict[str, bool] | Feature flags |

## Generator Types

### Core Generators

- **Execution**: Fail-fast (pipeline stops on first failure)
- **Use case**: Essential artifacts that must be generated
- **Examples**: profile, kpi, sufficiency

```python
@register("profile", is_core=True, order=10)
def generate_profile(ctx):
    # Must succeed for pipeline to continue
    ...
```

### Extended Generators

- **Execution**: Isolate-failures (pipeline continues on failure)
- **Use case**: Optional artifacts that enhance analysis
- **Examples**: quality, drift, charts, narrative

```python
@register("charts", is_core=False, feature_flag="enable_charts", order=60)
def generate_charts(ctx):
    # Failure is logged but doesn't stop pipeline
    ...
```

## Feature Flag Gating

Generators can be gated by feature flags from settings:

```python
# In voyant/core/config.py
class Settings:
    enable_quality: bool = Field(default=True)
    enable_charts: bool = Field(default=True)
    enable_narrative: bool = Field(default=True)

# Generator registration
@register("quality", feature_flag="enable_quality")
def generate_quality(ctx):
    ...
```

To disable at runtime:
```bash
VOYANT_ENABLE_CHARTS=0 docker compose up
```

## Execution Order

Generators run in order defined by the `order` parameter:

| Order | Generator | Type |
|-------|-----------|------|
| 10 | profile | Core |
| 20 | kpi | Core |
| 30 | sufficiency | Core |
| 40 | quality | Extended |
| 50 | drift | Extended |
| 60 | charts | Extended |
| 70 | narrative | Extended |

## Result Types

### PipelineResult

```python
@dataclass
class PipelineResult:
    success: bool              # True if no core generator failed
    artifacts: Dict[str, str]  # artifact_key -> file_path
    results: List[GeneratorResult]  # Individual generator results
    failed_core: Optional[str] # Name of failed core generator (if any)
```

### GeneratorResult

```python
@dataclass
class GeneratorResult:
    name: str                  # Generator name
    success: bool              # True if completed without error
    artifacts: Dict[str, str]  # Artifacts generated
    error: Optional[str]       # Error message (if failed)
    duration_ms: float         # Execution time
```

## API

### `register(name, is_core=False, feature_flag=None, order=100, description="")`

Decorator to register an artifact generator.

### `list_generators() -> List[Dict]`

List all registered generators with metadata.

### `get_generator(name) -> Optional[GeneratorDefinition]`

Get a specific generator by name.

### `run_generators(context, settings=None) -> PipelineResult`

Execute all registered generators in order.

### `clear_registry()`

Clear all registered generators (for testing).

## Best Practices

1. **Order carefully**: Leave gaps (10, 20, 30...) for future generators
2. **Mark core wisely**: Only pipeline-critical generators should be core
3. **Use feature flags**: Enable runtime toggling without code changes
4. **Return all artifacts**: Always return complete artifact dict
5. **Handle errors gracefully**: Provide actionable error messages
6. **Document generators**: Use docstrings for API documentation

## Testing

```python
from voyant.core.plugin_registry import clear_registry, register, run_generators

class TestMyGenerator:
    def setup_method(self):
        clear_registry()  # Start fresh
    
    def test_my_generator(self):
        @register("test_gen")
        def test_gen(ctx):
            return {"out": "/tmp/out.json"}
        
        result = run_generators({"job_id": "test"}, MockSettings())
        assert result.success
        assert "out" in result.artifacts
```
