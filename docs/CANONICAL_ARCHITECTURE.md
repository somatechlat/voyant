# Canonical Architecture: Universal Data Box (UDB)

_Revision: 2025-10-02_

## 1. Purpose
Provide a stable, technology-agnostic reference model for how UDB ingests, normalizes, analyzes, and serves heterogeneous data with minimal operational overhead while remaining extensible. This canonical view decouples “what the platform does” from “current implementation details,” enabling incremental replacement and plug-ins.

## 2. Architectural Principles
| Principle | Description | Examples |
|-----------|-------------|----------|
| Single Entry Surface | One API/agent interface for all lifecycle operations | FastAPI REST + (future) MCP server |
| Progressive Capability | Core vs. Extended tiers via feature flags | Profiling core; drift optional |
| Idempotent Runs | Re-running analysis yields deterministic artifact set | Job-scoped artifact directory |
| Pluggable Analytics | Artifact generators are composable functions | KPI, profile, drift, charts registry |
| Observability by Default | Metrics/logs/traces standardized and correlated | Prometheus, JSON logs, spans |
| Secure-by-Guardrails | Hard constraints instead of post-hoc filtering | SQL validator, RBAC, rate limiting |
| Data Locality First | Process close to storage; avoid premature distribution | DuckDB local analytical file |
| Minimal External Dependencies | Only adopt infra when required by scale | Kafka optional, orchestrator optional |

## 3. Layer Model
```
+-----------------------------------------------------------+
| Experience Layer                                          |
|  - REST API  - MCP Tools  - CLI (future)                  |
+------------------------+----------------------------------+
| Control & Orchestration | Job Store | Feature Flags       |
+------------------------+----------------------------------+
| Ingestion Layer: Connectors (Airbyte) | Upload | Docs     |
+-----------------------------------------------------------+
| Storage & Modeling: DuckDB | Views | Fragment Tables      |
+-----------------------------------------------------------+
| Analysis Layer: Profiling | KPI | Quality | Drift | Charts|
+-----------------------------------------------------------+
| Artifact Layer: File System (HTML/JSON/PNG/CSV)           |
+-----------------------------------------------------------+
| Observability & Security: Metrics | Events | Tracing | ACL |
+-----------------------------------------------------------+
| Platform Ops: Pruning | Secrets | Scheduling (Optional)   |
+-----------------------------------------------------------+
```

## 4. Core vs Extended Feature Matrix
| Capability | Core | Extended | Notes |
|------------|------|----------|-------|
| Airbyte sync | ✅ | – | Required for multi-source ingestion |
| File upload (structured) | ✅ | – | CSV/Parquet/XLSX ingested to DuckDB |
| Unstructured docs | – | ✅ | `unstructured` library → fragments table |
| Profiling (EDA) | ✅ | – | ydata-profiling HTML & JSON |
| KPI engine | ✅ | – | SQL-based metrics + masking |
| Sufficiency scoring | ✅ | – | Coverage / cleanliness / joinability / freshness |
| Quality & drift | – | ✅ | Evidently; baseline mgmt |
| Charts | – | ✅ | Plotly spec or heuristic |
| Narrative summary | – | ✅ | Derived from KPI + profile deltas |
| Events (Kafka) | – | ✅ | job.created/state.changed/analyze.* |
| Metrics (basic) | ✅ | – | Job counts, durations |
| Metrics (full) | – | ✅ | Quality, ingest, OAuth, prune |
| Tracing | – | ✅ | OpenTelemetry spans |
| RBAC | ✅ | – | Header-driven (disable for minimal mode) |
| Rate limiting | ✅ | – | In-memory bucket, optional disable |
| Pruning endpoint | ✅ | – | Manual cleanup |
| Prune scheduler | – | ✅ | Interval-based maintenance |

## 5. Data Lifecycle (Canonical Flow)
1. Discover or select source(s).
2. Initiate sync (connector → DuckDB tables).
3. (Optional) Ingest uploaded / unstructured data.
4. Apply virtual modeling (views / joins).
5. Run analysis pipeline (profiling → KPI → scoring → optional quality/drift → charts → narrative).
6. Persist artifacts & manifest.
7. Emit metrics/events; update job store.
8. Serve response + artifact links.

## 6. Artifact Taxonomy
| Type | Purpose | Example Filename |
|------|---------|------------------|
| Profile HTML | Human exploration | `profile.html` |
| Profile JSON | Machine parsing | `profile.json` |
| Quality HTML/JSON | Data health view | `quality.html` / `quality.json` |
| Drift HTML/JSON | Distribution change | `drift.html` / `drift.json` |
| KPI JSON | Tabular metrics | `kpis.json` |
| KPI Chart(s) | Visual summaries | `chart_*.html` |
| Sufficiency JSON | Readiness scoring | `sufficiency.json` |
| Narrative TXT/MD | Human summary | `narrative.txt` |
| Manifest JSON | Inventory | `manifest.json` |

## 7. Plugin / Generator Registry (Design)
```python
# pseudo
ARTIFACT_GENERATORS: list[Callable[Context, Result]] = []

def register(fn):
    ARTIFACT_GENERATORS.append(fn)

# Core registrations
register(generate_profile)
register(generate_kpis)
register(generate_sufficiency)

# Extended registrations (conditional)
if flags.quality:
    register(generate_quality)
    register(generate_drift)
if flags.charts:
    register(generate_charts)
if flags.narrative:
    register(generate_narrative)
```
Execution engine: iterate in declared order; each returns a dict of artifact keys → file paths + metadata. Fail-fast or continue-on-error configurable (default: fail-fast for core, isolate extended failures).

## 8. Feature Flag Specification
| Env Var | Type | Default | Controls |
|---------|------|---------|----------|
| UDB_ENABLE_QUALITY | bool | 1 | Quality + drift generation |
| UDB_ENABLE_CHARTS | bool | 1 | Plotly chart generation |
| UDB_ENABLE_UNSTRUCTURED | bool | 0 | Document → fragment ingestion |
| UDB_ENABLE_EVENTS | bool | 0 | Kafka event emitter activation |
| UDB_ENABLE_TRACING | bool | 0 | Register OTEL provider |
| UDB_ENABLE_RBAC | bool | 1 | Role enforcement middleware |
| UDB_METRICS_MODE | str | `full` | `off|basic|full` metric registration |
| UDB_ENABLE_NARRATIVE | bool | 1 | Narrative step |
| UDB_PRUNE_INTERVAL_SECONDS | int | 0 | Background prune loop (0 disables) |

## 9. Security & Isolation Model
| Domain | Mechanism |
|--------|-----------|
| SQL Guard | Allow-list of read-only constructs; auto LIMIT injection |
| RBAC | Request header or auth layer assigns role (viewer/analyst/admin) |
| Tenant Isolation | Namespaced job IDs + artifact roots + optionally table prefix `t_<tenant>__` |
| Secrets | Encrypted at rest (Fernet) or plain fallback; per-tenant keys |
| PII Masking | Regex pattern substitution in KPI result cells |
| Rate Limiting | Fixed window sliding deque (in-memory) |
| OAuth Tokens | Stored in secret store under tenant scope |

## 10. Observability Canon
| Signal | Implementation | Cardinality Control |
|--------|----------------|---------------------|
| Metrics | Prometheus client | Label sets constrained (type,state,status,provider) |
| Events | Kafka topic(s) or no-op | Strict schema (envelope + extra keys) |
| Traces | OpenTelemetry spans (conditional) | Span names stable (`analyze.request`, `kpi.execute`) |
| Logs | JSON structured w/ correlation + tenant | Logger name `udb` |

## 11. Scaling Strategy
| Axis | First Response | Second Phase | Later Evolution |
|------|---------------|--------------|-----------------|
| Source Volume | Multiple sync jobs sequential | Async queue + worker | External orchestrator (if needed) |
| Concurrency | Single pod | Replicated API + shared DuckDB (serialized writes) | Warehouse abstraction / MotherDuck |
| Artifact Growth | Manual prune | Scheduled prune | Tiered storage (object store) |
| Data Variety | Airbyte connectors | Custom lightweight loaders | Schema registry / contracts |
| Latency Pressure | In-process pipeline | Parallelizable phases (profiling + KPIs) | Pre-computed materializations |

## 12. Failure Handling Matrix
| Failure Point | Detection | Response | Event |
|---------------|----------|----------|-------|
| Sync timeout | Poll loop > threshold | Mark job `timeout` | `job.state.changed` (timeout) |
| Analyze exception | Try/except in pipeline | Job `failed`, 500 error | `job.analyze.failed` |
| Quality generator error | Scoped exception | Mark quality status `error`, continue | Completed event includes status |
| Chart failure | Logged; skip artifact | Continue | Completed event artifactCounts reflects absence |
| Prune error | Logged only | Continue loop | None (non-critical) |

## 13. Data Retention & Lifecycle
| Element | Retention Model |
|---------|-----------------|
| Artifacts | Time-based prune (days) configurable env var |
| Secrets | Rotated externally (future hook) |
| Baselines | Regenerated on demand; versioning planned |
| Logs | External aggregation (e.g., Loki / ELK) |

## 14. Extensibility Playbook
Add new analysis module:
1. Implement generator function (context → dict[str, ArtifactMeta]).
2. Register behind feature flag.
3. Add Prometheus counter/histogram if needed.
4. Extend event schema if externally meaningful.
5. Update canonical docs + STATUS version delta.

## 15. Migration Guardrails
| Change Type | Approach |
|-------------|----------|
| Breaking API | Version via URL segment or Accept header |
| Artifact Schema | Include manifest version; keep backward file names | 
| Metrics Labels | Avoid churn; deprecate with parallel emission window | 
| Event Fields | Additive only; version envelope if removal required | 

## 16. Open Questions / Future Decisions
| Topic | Pending Decision |
|-------|------------------|
| Multi-tenant auth integration | External IdP vs internal RBAC-only |
| Baseline storage medium | DuckDB vs object store JSON vs Postgres |
| Async job queue | Redis streams vs lightweight internal queue |
| Forecasting / anomaly layer | Built-in vs plugin marketplace |

## 17. Reference Implementation Alignment
Current codebase already implements ~80% of canonical core & extended layers. Gaps to align fully:
- Formal plugin registry abstraction.
- Sufficiency scoring module + artifact.
- Metrics mode gating (basic vs full).
- Unified feature flag evaluation in settings.

## 18. Glossary
| Term | Meaning |
|------|--------|
| Artifact | Persisted output of a pipeline stage (HTML/JSON/etc.) |
| Baseline | Stored reference stats for comparative analysis (quality/drift) |
| Generator | Modular function producing one or more artifacts |
| Sufficiency | Composite readiness score evaluating dataset usability |

---
This document supersedes or augments high-level design sketches; future structural changes should update both this and the roadmap.
