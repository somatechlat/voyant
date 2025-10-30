# Sprint: Analysis Enhancement & Guardrails (Parallel Batch)

Objective: Rapidly elevate analytical depth, observability, and safety in a single accelerated batch rather than serialized sprints.

## Completed Deliverables
- KPI Engine: Multi-query execution with validation, timing, truncation.
- Chart Generation: Heuristic + spec-based Plotly HTML artifacts.
- PII Masking: Email + SSN-like + 9-digit heuristic obfuscation.
- Quality & Drift: Evidently DataQuality + DataDrift presets with baseline snapshot and HTML/JSON artifacts.
- Profiling: ydata-profiling minimal profile (HTML + JSON).
- `/sql` Endpoint Guard: Statement validator (SELECT/WITH/CREATE VIEW only) + auto LIMIT.
- Kafka Events: job.created, job.state.changed, job.analyze.completed.
- OpenTelemetry Tracing: Spans for analyze pipeline stages.

## Artifact Schema (Analyze Response)
```
artifacts: {
  profileHtml, profileJson,
  qualityHtml, qualityJson,
  driftHtml, driftJson,
  charts: [],
  charts_extra?: [...],
}
```

## Event Enrichment
All events include jobId and type. Analyze completion adds kpiRows count. Future: attach drift summary deltas.

## Parallelization Strategy
| Track | Focus | Result |
|-------|-------|--------|
| Analysis Core | KPI + Charts + Profiling | Unified artifact bundle |
| Quality Guard | Drift + Quality + Baseline persistence | Non-blocking, optional |
| Observability | Metrics + Tracing + Kafka | Cross-cut instrumentation |
| Safety | PII masking + SQL guard | Reduced exfiltration risk |

## Remaining Enhancements (Next Parallel Batch)
1. Rate limiting decorator on high-cost endpoints.
2. Extended metrics (kpi_count_total, quality_runs_total, drift_runs_total, analyze_duration_seconds histogram).
3. Narrative summarizer synthesizing KPI + drift signals.
4. Grafana example dashboard JSON.
5. Tenant scoping & schema naming (early slice from Security sprint).

## Technical Notes
- Baseline stored at `/artifacts/baseline/baseline.parquet`; future: version & per-table.
- Tracing conditional on `OTEL_EXPORTER_OTLP_ENDPOINT` env var.
- KPI execution uses single DuckDB connection; future: concurrency gating for heavy queries.
- Chart heuristic prioritizes time series, categorical distribution, numeric histogram.

## Risks & Mitigations
- Large profiles: enforced 50k row limit; consider sampling strategies.
- Baseline drift over time: add scheduled refresh or time-windowed baselines.
- PII masking false negatives: introduce configurable regex registry.

## Next Batch Exit Criteria
- All added metrics visible in /metrics.
- 429 response after exceeding configured rate on /sql test.
- Narrative summary non-empty when at least one KPI + drift artifact present.

---
This sprint intentionally batched to exploit shared context and minimize redundant file churn.
