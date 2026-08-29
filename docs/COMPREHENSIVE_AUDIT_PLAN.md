# Comprehensive Code & Documentation Audit Plan

**Generated:** 2026-07-23
**Scope:** All Python code (`apps/`), all documentation (`docs/`), all infrastructure (`infra/`)
**Rules:** RULES.md is the governing standard. No hype, no stubs, no mocks, no AI slop.

---

## SECTION 1: CRITICAL — Docs That Are Outright Wrong

These docs actively mislead anyone reading them. Fix first.

### 1.1 `docs/api/openapi.json` — 25+ endpoints missing

**Problem:** openapi.json is stale. It doesn't include scrape, analyze, or capsules routers.

| Missing Router | Endpoint Count | Router File |
|---------------|---------------|-------------|
| `scrape_router` | 11 endpoints | `apps/scraper/api.py` |
| `capsules_router` | 14 endpoints | `apps/capsules/api.py` |
| `analyze_router` | 1 endpoint | `apps/analysis/api.py` |
| `search_router` (DELETE, GET by ID) | 2 endpoints | `apps/search/api.py:261,314` |

**Path mismatch:** Governance quota tier endpoint is `/quotas/set-tier` in code but `/quotas/tier` in openapi.json.

**Fix:** Regenerate openapi.json from the running Django Ninja app. Run:
```python
python manage.py export_openapi > docs/api/openapi.json
```

### 1.2 `infra/standalone/README.md` — Service table is wrong

**Problem:** Table claims 18 services. Actual compose has 23. 7 are missing, 2 are phantoms.

| Phantom (in README, not in compose) | Missing (in compose, not in README) |
|--------------------------------------|--------------------------------------|
| `voyant_lago_api` | `voyant_searxng` |
| `voyant_lago_worker` | `voyant_vault` |
| | `voyant_spicedb` |
| | `voyant_etcd` |
| | `voyant_milvus` |
| | `voyant_flaresolverr` |
| | `voyant_browserless` |

Port 45300 attributed to `lago_api` — actually `browserless`.

**Fix:** Rewrite the service table from `docker compose config` output.

### 1.3 `README.md` (root) — Outdated claims

| Line | Claim | Reality |
|------|-------|---------|
| 53 | "15+ tools" | 45 MCP tools |
| 82-88 | Lists 8 REST endpoint categories | 11 categories (scrape + capsules + analyze missing) |
| 92-106 | Lists 12 MCP tool names | 45 exist (33 omitted) |

**Fix:** Rewrite the architecture overview section from actual code.

### 1.4 `docs/specifications/voyant_master_specification.md` — Tool count wrong

**Problem:** Claims "37 tools". Actual count is 45.

8 tools in code but not documented:
- `scrape.deep_archive`
- `scrape.ocr`
- `scrape.parse_pdf`
- `scrape.transcribe`
- `voyant.templates.execute`
- `voyant.discovery.services.list`
- `voyant.discovery.services.get`
- `voyant.discovery.services.register`

**Fix:** Regenerate the tool list from `@mcp_app.tool` decorators.

---

## SECTION 2: HIGH — Stale/Incomplete Documentation

### 2.1 Empty files to delete

| File | Lines | Reason |
|------|-------|--------|
| `docs/management/REFACTORING_PLAN.md` | 0 | Explicitly gutted by ISO audit |
| `docs/specifications/srs/PRESET_SDK_SRS.md` | 0 | Never written |
| `docs/specifications/srs/VOYANT_PRESETS_SRS.md` | 0 | Duplicate of above, never written |

### 2.2 Stub files to flesh out or delete

| File | Lines | Content |
|------|-------|---------|
| `docs/development/TESTING_STRATEGY.md` | 8 | Header only, no strategy |
| `docs/operations/DEPLOYMENT.md` | 26 | Table of contents only, no content |

### 2.3 Broken link

| File | Line | Broken Reference |
|------|------|-----------------|
| `docs/README.md` | ? | References `AGENT_CONTINUITY.md` which does not exist |

### 2.4 Stale percentage

| File | Line | Claim | Reality |
|------|------|-------|---------|
| `docs/management/TASKS.md` | ? | "45% Complete" (Jan 2026) | Needs re-evaluation |

### 2.5 Workflow documentation covers 3 of 17 workflows

| File | Missing |
|------|---------|
| `docs/architecture/modules/doc_workflows_and_execution.md` | 13 workflows undocumented: BenchmarkBrand, DetectAnomalies, AnalyzeSentiment, FixDataQuality, Forecast, SegmentCustomers, LinearRegression, Scrape, DeepResearch, Streaming, Sandbox, Capsule, DeepResearchV2. 46 activities undocumented. |

### 2.6 Historical files marked stale

| File | Status |
|------|--------|
| `docs/specifications/srs/Voyant_SRS.md` (1055 lines) | Self-declared "historical/draft, not canonical" |
| `docs/management/PHASE1_COMPLETION_REPORT.md` | Historical record, completed work |
| `docs/compliance/CODE_SWEEP_2026-02-27.md` | Historical snapshot |
| `docs/compliance/DOCS_TRUTH_AUDIT_2026-02-27.md` | Historical snapshot |
| `docs/compliance/DEPLOYMENT_CLUSTER_CHECK_2026-02-27.md` | Historical snapshot |

**Action:** Either delete these or add a prominent header: "ARCHIVAL DOCUMENT — Last verified 2026-02-27. May contain stale information."

---

## SECTION 3: HIGH — AI Slop in Code Comments & Docstrings

65 violations found. Organized by file.

### 3.1 `apps/core/lib/circuit_breaker.py` — 6 hype violations

| Line | Offending Text | Fix |
|------|---------------|-----|
| 4 | "provides a robust, thread-safe implementation" | "provides a thread-safe implementation" |
| 9-10 | "This is a real, production-ready state machine" | "State machine with OPEN/HALF_OPEN/CLOSED states" |
| 23 | "Ensures minimal overhead (<1ms)" | "Aims for minimal overhead (<1ms)" |
| 25 | "Ensures that error messages do not leak" | "Prevents error message leakage" |
| 26 | "Provides clear documentation for states" | "Documents states" |
| 27 | "Provides a manual reset capability" | "Includes manual reset" |

### 3.2 `apps/core/lib/contracts.py` — 3 hype violations

| Line | Offending Text | Fix |
|------|---------------|-----|
| 4-5 | "comprehensive system for defining, managing, and enforcing" | "System for defining, managing, and enforcing" |
| 6 | "ensuring that data conforms" | "so data conforms" |
| 516 | "# Return latest version by sorting keys semantically (if possible)" | "# Sort by semver" |

### 3.3 `apps/core/lib/retry_config.py` — 1 violation

| Line | Offending Text | Fix |
|------|---------------|-----|
| 7 | "designed to ensure the robustness and reliability of" | "provides defaults for" |

### 3.4 `apps/core/lib/secrets.py` — 1 violation

| Line | Offending Text | Fix |
|------|---------------|-----|
| 12 | "Vault provider (production-ready)" | "Vault provider" |

### 3.5 `apps/core/lib/temporal_client.py` — 2 violations

| Line | Offending Text | Fix |
|------|---------------|-----|
| 4 | "provides a standardized, singleton client" | "provides a singleton client" |
| 6 | "critical for performance and resource management" | "for performance and resource management" |

### 3.6 `apps/core/lib/events.py` — 2 violations

| Line | Offending Text | Fix |
|------|---------------|-----|
| 4 | "provides a standardized interface" | "provides an interface" |
| 7 | "which is critical for performance and resource management" | "for performance" |

### 3.7 `apps/core/lib/plugin_registry.py` — 2 violations

| Line | Offending Text | Fix |
|------|---------------|-----|
| 4 | "implements the 'Platform of Platforms' design pattern" | "implements a plugin registry" |
| 6 | "providing a centralized, singleton registry" | "providing a singleton registry" |

### 3.8 `apps/core/security/auth.py` — 4 over-explained comments

| Line | Offending Text | Fix |
|------|---------------|-----|
| 282 | "# Define a mapping from roles to their associated permissions." | Delete |
| 296 | "# Aggregate permissions from all assigned roles." | Delete |
| 301 | "# Return unique permissions." (after `set()`) | Delete |

### 3.9 `apps/governance/lib/datahub.py` — 3 violations

| Line | Offending Text | Fix |
|------|---------------|-----|
| 10-11 | "crucial for maintaining a comprehensive understanding" | "for maintaining visibility into" |
| 94 | `timeout=30.0, # Set a default timeout` | Delete comment |
| 152 | `"changeType": "UPSERT", # Create or update` | Delete comment |

### 3.10 `apps/discovery/lib/spec_parser.py` — 1 violation

| Line | Offending Text | Fix |
|------|---------------|-----|
| 4 | "provides a robust parser" | "provides a parser" |

### 3.11 `apps/scraper/parsing/pdf_parser.py` — 4 violations

| Line | Offending Text | Fix |
|------|---------------|-----|
| 5 | "intelligently leverages" | "uses" |
| 6 | "comprehensive document analysis" | "document analysis" |
| 21 | "offers a robust approach" | "uses a fallback approach" |
| 42 | "for comprehensive extraction" | "for extraction" |

### 3.12 `apps/scraper/parsing/html_parser.py` — 2 violations

| Line | Offending Text | Fix |
|------|---------------|-----|
| 21 | "A robust HTML parser" | "An HTML parser" |
| 70 | `result[field] = None  # Assign None if extraction for a field fails.` | Delete comment |

### 3.13 `apps/scraper/search_activities.py` — 2 violations

| Line | Offending Text | Fix |
|------|---------------|-----|
| 14 | "Physical Voyager Search Engine Node." | "Search activity that queries the internal SearXNG instance." |
| 43 | "# Vibe Rule 5: Error handling logic implemented robustly" | Delete entirely |

### 3.14 `apps/scraper/api.py` — 1 violation

| Line | Offending Text | Fix |
|------|---------------|-----|
| 5 | "controlled by an external intelligent agent" | "controlled by an external agent" |

### 3.15 `apps/scraper/workflow.py` — 2 over-explained comments

| Line | Offending Text | Fix |
|------|---------------|-----|
| 70 | "# Initialize tracking variables for the workflow's progress and results." | Delete |
| 178 | "# Return a summary of the scraping job for the agent to interpret." | Delete |

### 3.16 `apps/worker/activities/stats_activities.py` — 2 violations

| Line | Offending Text | Fix |
|------|---------------|-----|
| 31 | "R's powerful statistical capabilities" | "R's statistical capabilities" |
| 37-38 | "Initializes the StatsActivities with an R-Engine instance and statistical primitives." | Delete docstring |

### 3.17 `apps/worker/activities/profile_activities.py` — 1 violation

| Line | Offending Text | Fix |
|------|---------------|-----|
| 28 | "generating comprehensive data profiles" | "generating data profiles" |

### 3.18 `apps/worker/activities/kpi_activities.py` — 1 over-explained docstring

| Line | Offending Text | Fix |
|------|---------------|-----|
| 29 | "Initializes the KPIActivities." | Delete docstring |

### 3.19 `apps/worker/activities/capsule_activities.py` — 1 violation

| Line | Offending Text | Fix |
|------|---------------|-----|
| 4 | "Production-grade: all action handlers wire to real Voyant services" | "All action handlers wire to real Voyant services" |

### 3.20 `apps/worker/activities/sandbox_activities.py` — 1 missing docstring

| Line | Issue | Fix |
|------|-------|-----|
| 9 | `class SandboxActivities:` has no docstring | Add: "Activities for running scripts in the Python sandbox." |

### 3.21 `apps/worker/activities/ingest_activities.py` — 1 missing docstring

| Line | Issue | Fix |
|------|-------|-----|
| 26 | `class IngestActivities:` has no docstring | Add: "Activities for data ingestion, contract validation, and lineage recording." |

### 3.22 `apps/worker/workflows/ingest_workflow.py` — 1 violation

| Line | Offending Text | Fix |
|------|---------------|-----|
| 5 | "It ensures that data" | "It validates that data" |

### 3.23 `apps/worker/workflows/profile_workflow.py` — 1 violation

| Line | Offending Text | Fix |
|------|---------------|-----|
| 4 | "generating comprehensive profiles" | "generating profiles" |

### 3.24 `apps/worker/workflows/types.py` — 1 violation

| Line | Offending Text | Fix |
|------|---------------|-----|
| 6 | "ensures consistency, type safety" | "provides consistency, type safety" |

### 3.25 `apps/worker/workflows/analyze_workflow.py` — 2 violations

| Line | Offending Text | Fix |
|------|---------------|-----|
| 9-10 | "designed to be flexible, allowing different stages" | "Stages can be enabled or disabled via input parameters." |
| 141 | "# Return all compiled results." | Delete |

### 3.26 `apps/analysis/lib/anomaly.py` — 4 violations

| Line | Offending Text | Fix |
|------|---------------|-----|
| 9 | "IQR-based detection (robust to outliers)" | "IQR-based detection (resistant to outliers)" |
| 10 | "Modified Z-score (MAD-based, most robust)" | "Modified Z-score (MAD-based)" |
| 178 | "More robust to outliers than z-score" | "Resistant to outliers, unlike z-score" |
| 247 | "Most robust to outliers" | "Uses median instead of mean" |

### 3.27 `apps/analysis/lib/forecasting.py` — 1 over-explained comment

| Line | Offending Text | Fix |
|------|---------------|-----|
| 105 | "# Create X (features) and y (target)" | Delete |

### 3.28 `apps/ingestion/lib/airbyte_client.py` — 3 violations

| Line | Offending Text | Fix |
|------|---------------|-----|
| 1 | "Production-Ready Integration" | Delete subtitle |
| 11 | "Robust error handling" | "Error handling" |
| 122 | "# Initialize circuit breaker for Airbyte API calls." | Delete |

### 3.29 `apps/ingestion/lib/direct_utils.py` — 1 violation

| Line | Offending Text | Fix |
|------|---------------|-----|
| 82 | "use pandas for robust parsing" | "use pandas for parsing" |

### 3.30 `apps/search/lib/embeddings.py` — 2 over-explained comments

| Line | Offending Text | Fix |
|------|---------------|-----|
| 166 | "# Build vocabulary" | Delete |
| 227 | "# Build vector" | Delete |

### 3.31 `apps/core/lib/artifact_store.py` — 1 over-explained comment

| Line | Offending Text | Fix |
|------|---------------|-----|
| 255 | "# Create reference" | Delete |

### 3.32 `apps/core/lib/event_schema.py` — 1 over-explained comment

| Line | Offending Text | Fix |
|------|---------------|-----|
| 572 | "# Initialize all canonical schemas when this module is first imported." | Delete |

### 3.33 `apps/streaming/activities.py` — 1 over-explained docstring

| Line | Offending Text | Fix |
|------|---------------|-----|
| 68 | "Initialize activities with settings-based configuration." | "Load settings." |

### 3.34 `apps/uptp_core/models.py` — 1 Django boilerplate

| Line | Offending Text | Fix |
|------|---------------|-----|
| 1 | "# Create your models here." | Delete |

### 3.35 `apps/uptp_core/tests/test_parser.py` — 2 inaccurate docstrings

| Line | Offending Text | Fix |
|------|---------------|-----|
| 4-5 | "Verification of the core routing protocols ensures..." | "Verifies that malformed URIs raise ValueError before processing." |
| 49 | "The ETL hash pipeline ensures this specific mathematical transformation" | "Asserts SHA-256 hash of SSN matches expected value." |

### 3.36 `apps/analysis/lib/services_forecasting.py` — 1 over-explained comment

| Line | Offending Text | Fix |
|------|---------------|-----|
| 105 | "# Create X (features) and y (target)" | Delete |

---

## SECTION 4: MEDIUM — Code Quality Issues

### 4.1 Exception suppression (silently swallowing errors)

| File | Line | Issue | Fix |
|------|------|-------|-----|
| `apps/core/config.py` | ? | `except Exception: pass` in settings loader | Already fixed to `logger.debug(...)` |
| `apps/mcp/tools_catalog.py` | 173-176 | `except: continue` | Already fixed to `logger.debug(...)` |
| `apps/scraper/api.py` | cancel endpoint | `except Exception: pass` | Already fixed to `logger.warning(...)` |
| `apps/workflows/api.py` | cancel_job | `except Exception: pass` | Already fixed to `logger.warning(...)` |

These are already fixed. Verify no new suppressions were introduced.

### 4.2 `import re` inside function body

| File | Line | Issue |
|------|------|-------|
| `apps/scraper/deep_research/agents/content_extractor.py` | 92, 165 | `import re` inside method body instead of top of file |

### 4.3 Hardcoded 100KB cap without config

| File | Line | Issue |
|------|------|-------|
| `apps/scraper/deep_research_workflow.py` | ? | `combined_text[:100000]` hardcoded cap |

---

## SECTION 5: LOW — Cleanup Tasks

### 5.1 Empty placeholder files

Delete these files:
- `docs/management/REFACTORING_PLAN.md`
- `docs/specifications/srs/PRESET_SDK_SRS.md`
- `docs/specifications/srs/VOYANT_PRESETS_SRS.md`

### 5.2 Historical docs — add archival header

Add to each:
- `docs/management/PHASE1_COMPLETION_REPORT.md`
- `docs/compliance/CODE_SWEEP_2026-02-27.md`
- `docs/compliance/DOCS_TRUTH_AUDIT_2026-02-27.md`
- `docs/compliance/DEPLOYMENT_CLUSTER_CHECK_2026-02-27.md`

Header: `> **ARCHIVAL DOCUMENT** — Last verified 2026-02-27. May contain stale information.`

### 5.3 Stale self-declared SRS

`docs/specifications/srs/Voyant_SRS.md` is self-declared "not canonical" but still 1055 lines. Either delete or move to `docs/archival/`.

---

## SECTION 6: ENVIRONMENT VARIABLES

### 6.1 Settings fields without docker-compose entries

40+ Settings fields have no explicit environment variable in `docker-compose.yml`. Most are optional with defaults. The critical ones that need docker-compose coverage:

| Setting | Env Var | Why Critical |
|---------|---------|-------------|
| `worker_mode` | `VOYANT_WORKER_MODE` | Worker startup mode |
| `searxng_url` | `VOYANT_SEARXNG_URL` | SearXNG connectivity |
| `worker_metrics_port` | `VOYANT_WORKER_METRICS_PORT` | Prometheus scraping |
| `spicedb_tls` | `VOYANT_SPICEDB_TLS` | Security posture |

---

## EXECUTION ORDER

### Phase 1: Fix actively misleading docs (CRITICAL)
1. Regenerate `docs/api/openapi.json`
2. Rewrite `infra/standalone/README.md` service table
3. Rewrite `README.md` architecture overview section
4. Update `docs/specifications/voyant_master_specification.md` tool count

### Phase 2: Delete/flesh out empty stubs (HIGH)
5. Delete 3 empty files
6. Flesh out or delete `TESTING_STRATEGY.md` and `DEPLOYMENT.md`
7. Fix broken link in `docs/README.md`
8. Update `TASKS.md` percentage

### Phase 3: Remove AI slop from code (HIGH)
9. Fix all 65 comment/docstring violations across 35 files (Section 3)

### Phase 4: Update workflow/activity docs (HIGH)
10. Document all 17 workflows in `doc_workflows_and_execution.md`
11. Document all 46 registered activities

### Phase 5: Historical cleanup (LOW)
12. Add archival headers to 5 historical docs
13. Clean up or delete stale SRS
14. Move `import re` to top of file in content_extractor.py
