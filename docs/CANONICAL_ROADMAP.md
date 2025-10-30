# Canonical Roadmap: Universal Data Box (UDB)

_Revision: 2025-10-02_

## 1. Strategic Phases
| Phase | Objective | Outcome Definition |
|-------|-----------|--------------------|
| P0 – Core Path | Ingest (Airbyte) → Analyze (Profile+KPI) | One-call analyze returns stable artifacts |
| P1 – Extended Insights | Add Quality/Drift, Charts, Narrative | Rich artifact bundle + readiness scoring |
| P2 – Operability | Harden observability, pruning, feature flags | Toggleable footprint; CI reliability |
| P3 – Extensibility | Plugin registry + API version hygiene | Easy addition/removal of modules |
| P4 – Scale & Multi-Tenant | Isolation, quotas, concurrency handling | Multiple teams with predictable latency |
| P5 – Governance & Contracts | Baselines, schema contracts, lineage | Trust & reproducibility foundation |
| P6 – Advanced Analytics | Forecasting, anomaly detection, semantic layer | Higher-order intelligence surfaces |

## 2. Milestone Table
| Milestone | Target Contents | Success KPI |
|-----------|-----------------|-------------|
| M1 (Core Alpha) | P0 features + minimal metrics | Analyze success rate >90% sample sources |
| M2 (Insight Beta) | Add P1 + sufficiency scoring | 80% runs generate readiness score |
| M3 (Ops Ready) | Observability parity + flags (P2) | Mean analyze latency < 120s medium dataset |
| M4 (Plugin GA) | Registry + versioned API | Add/remove module without code fork |
| M5 (Tenant Scale) | Multi-tenant isolation + quotas | 95% p95 latency < 140s under 5 tenants |
| M6 (Contracts) | Baseline mgmt + schema drift alerts | <5% contract violations after adoption |
| M7 (Advanced) | Anomaly + forecast prototypes | Pilot customers adopt 2+ advanced modules |

## 3. Detailed Backlog by Phase
### Phase P0 – Core Path (Foundational)
- Airbyte connection + sync polling (existing)
- KPI engine (existing)
- Profiling (existing)
- Artifact manifest (existing)
- Basic metrics (subset selection) → NEED gating
- Add sufficiency scoring (NEW)

### Phase P1 – Extended Insights
- Quality + drift gating (existing logic → behind flag)
- Charts (existing) final spec contract
- Narrative summarizer refinement (existing baseline)
- KPI template library (starter set)

### Phase P2 – Operability
- Metrics mode: off|basic|full implementation
- Feature flag consolidation into settings
- Background prune interval gating (existing scheduler)
- Event schema versioning entrypoint
- Structured failure catalog (error codes JSON)

### Phase P3 – Extensibility
- Plugin generator registry abstraction
- Plugin discovery / registration doc
- Stable artifact key taxonomy tests
- API version negotiation (Accept header plan)

### Phase P4 – Scale & Multi-Tenant
- Tenant quotas (max jobs/day, artifact size caps)
- Concurrency queue (optional Redis streams)
- Table-level namespace analyzer (lint before analyze)
- Cost metrics (CPU time per analyze run)

### Phase P5 – Governance & Contracts
- Data contract definition format (YAML → JSON Schema)
- Contract enforcement hook pre-KPI
- Baseline version store + drift lineage
- Column sensitivity classification (regex + ML later)
- Lineage graph JSON endpoint

### Phase P6 – Advanced Analytics
- Time-series forecasting module (Prophet or statsmodels plugin)
- Anomaly detection (simple z-score → robust algorithm)
- Segment profiling (group-level stats artifact)
- Embedding extraction for unstructured fragments

## 4. Cross-Cutting Concerns Matrix
| Concern | P0 | P1 | P2 | P3 | P4 | P5 | P6 |
|---------|----|----|----|----|----|----|----|
| Security Guardrails | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Feature Flags | – | Partial | Full | Full | Full | Full | Full |
| Metrics Depth | Basic | Full opt-in | Modeled | Modeled | Modeled | Modeled | Modeled |
| Testing Coverage | Core paths | Extended modules | Non-core toggles | Plugin tests | Load/tenant tests | Contract tests | Performance harness |
| Docs | Minimal | Enhanced | Operational | Plugin SDK | Multi-tenant guide | Governance guide | Advanced analytics playbook |

## 5. Risk Register (Forward-Looking)
| Risk | Phase Exposed | Mitigation Strategy |
|------|---------------|---------------------|
| DuckDB write contention | P4+ | Serialize writes; consider remote engine |
| Feature flag drift | P2+ | Central config & test matrix | 
| KPI SQL injection vectors | Always | Validator updates + test fuzzing |
| Artifact bloat | P2+ | Prune + size caps + compression |
| Kafka dependency fragility | P2+ | Default no-op emitter + health gating |
| Schema contract false positives | P5 | Gradual adoption mode + allowlist overrides |

## 6. Decision Log (Abbreviated)
| Decision | Rationale | Date |
|----------|-----------|------|
| Local DuckDB vs warehouse | Faster iteration, low ops | Early |
| Airbyte as sole connector layer | Avoid bespoke connectors | Early |
| Plugin registry (planned) | Future-proof modularity | Planned P3 |
| Events optional | Reduce infra footprint for core usage | Early |

## 7. KPIs by Phase (Execution / Product)
| KPI | Definition | Target (Phase) |
|-----|------------|----------------|
| Analyze Success Rate | succeeded jobs / total analyze jobs | >92% (M2) |
| Median Analyze Duration | median wall time (standard dataset) | <90s (M3) |
| Sufficiency Coverage | runs with sufficiency.json | 100% (M2) |
| Plugin Add Time | Time to add new generator (design→code) | <1 day (M4) |
| Tenant Isolation Defects | Cross-tenant leakage incidents | 0 (M5+) |
| Contract Violation Rate | (#violations / runs w/ contract) | <5% (M6) |
| Advanced Module Adoption | % tenants using >=1 advanced module | 30% (M7) |

## 8. Release Cadence & Versioning
| Release Level | SemVer Bump | Contents |
|---------------|-------------|----------|
| Patch | x.y.Z | Bug fixes / doc only |
| Minor | x.Y.z | New non-breaking modules, artifacts, flags |
| Major | X.y.z | Breaking API / artifact contract change |

Version tags align with milestone completions (M1 → v0.1.0-alpha, M2 → v0.2.0-beta, etc.).

## 9. Implementation Traceability
Link between canonical roadmap and current repo tracked in `STATUS.md` and future `CHANGELOG.md`. Each generator or module must reference phase & decision IDs in header comments (planned enforcement).

## 10. Exit Criteria Per Milestone
| Milestone | Exit Criteria |
|-----------|---------------|
| M1 | Core path green tests; profile + KPI always emitted |
| M2 | Quality/drift + sufficiency behind flags; charts & narrative stable |
| M3 | Metrics mode works; prune scheduler documented; events optional | 
| M4 | Plugin registry active; artifact taxonomy test suite passes | 
| M5 | 3 simulated tenants with isolation tests passing | 
| M6 | Contract YAML processed & enforcement pre-KPI | 
| M7 | At least 2 advanced modules generating artifacts |

## 11. Onboarding Checklist (New Contributor)
1. Read CANONICAL_ARCHITECTURE.md & STATUS.md
2. Run local stack (UDB API + Airbyte)
3. Execute smoke analyze run
4. Review feature flags & toggle matrix
5. Inspect one generator implementation
6. Add or improve a test for a core path

## 12. De-Scope / Kill Switches
| Feature | Disable Mechanism |
|---------|-------------------|
| Quality/Drift | `UDB_ENABLE_QUALITY=0` |
| Charts | `UDB_ENABLE_CHARTS=0` |
| Events | `UDB_ENABLE_EVENTS=0` |
| Tracing | `UDB_ENABLE_TRACING=0` |
| Unstructured | `UDB_ENABLE_UNSTRUCTURED=0` |
| Narrative | `UDB_ENABLE_NARRATIVE=0` |
| Prune Scheduler | `UDB_PRUNE_INTERVAL_SECONDS=0` |

## 13. Future Investigation Backlog
- Query result cache with TTL & invalidation policy
- Adaptive sampling for large table profiling
- Content-addressable artifact store
- Schema evolution timeline visualization
- Embedded vector store for semantic doc search

## 14. Governance Hooks (Planned)
| Hook | Trigger Point | Action |
|------|--------------|--------|
| Contract validation | Pre-KPI execution | Reject or warn mode |
| Drift alert emission | Post-quality run | Emit event `job.drift.alert` |
| Lineage registration | After artifact write | Append lineage JSON node |

## 15. Documentation Maintenance Policy
- Update this roadmap when: new phase begins, milestone closes, or scope changes >15%.
- STATUS.md summarises delta since last revision.
- Changelog entry required for any contract or artifact format change.

---
This canonical roadmap is the authoritative forward plan; operational adjustments must reconcile here within 48h of change approval.
