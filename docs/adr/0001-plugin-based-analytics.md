# 1. Plugin Based Analytics

Date: 2025-12-17

## Status

Accepted

## Context

The initial Voyant architecture focused on "Artifact Generation" (visualizations, reports) via `GeneratorPlugin`. As we entered Phase 8 (Advanced Analytics), we needed to support components that produce *insights* (anomalies, forecasts) rather than just static artifacts. These components have different input requirements (raw data) and output structures (structured inference data).

## Decision

We decided to extend the `PluginRegistry` pattern to support a broader class of plugins.
1. Confirmed `PluginRegistry` as the central singleton for extension.
2. Introduced `VoyantPlugin` as the base abstract class.
3. Renamed/Refactored existing `GeneratorPlugin` to inherit from `VoyantPlugin`.
4. Introduced `AnalyzerPlugin` for components that accept data and return analysis results.

## Consequences

### Positive
- **Extensibility**: New analytical capabilities can be added without modifying core workflows.
- **Workflow Integration**: Specific Temporal activities (`run_analyzers`) can target just the analysis phase.
- **Consistency**: Analytics and Generation share the same registration, metadata, and discovery mechanism.

### Negative
- **Complexity**: The registry now manages multiple types, requiring explicit filtering (`get_generators` vs `get_analyzers`).
