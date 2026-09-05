# Voyant v4.0 — Rapid Development Plan

**Goal:** Ship v4.0 in 24 weeks with 3-4 engineers.
**Strategy:** Parallel workstreams, test-driven, ship weekly.
**Methodology:** Rapid Application Development (RAD) — iterative prototyping, minimal planning overhead, continuous user feedback, weekly deliverables.

---

## Rapid Development Principles

| Principle | Implementation |
|-----------|---------------|
| **Prototype first** | Build working UI/API in days, not weeks. Refine iteratively. |
| **Parallel workstreams** | 2-3 engineers work on different phases simultaneously. |
| **Weekly releases** | Every Friday: working demo of week's deliverable. |
| **Test-driven** | Write test → make it pass → commit. No test = not done. |
| **No big design up front** | SRS defines WHAT. Engineers decide HOW during implementation. |
| **Reuse everything** | Apache projects before custom code. Existing patterns before new ones. |
| **Continuous integration** | Every commit runs full test suite. Broken = blocked. |
| **Feedback loops** | Weekly demo → user feedback → adjust next week's plan. |

---

## Development Rules (Enforced Every Session)

| # | Rule | Enforcement |
|---|------|------------|
| 1 | Test before declare done | `pytest tests/ -q` → 0 failures |
| 2 | No dead code | `ruff check --select F` → 0 errors |
| 3 | No duplicate code | Extract to `core/lib/` if pattern repeats 2+ times |
| 4 | Real interfaces only | Every UI page fully functional — no mocks |
| 5 | ISO compliance | SRS requirement ID traceability, >80% coverage |
| 6 | Lint clean | `ruff check apps/ --select E,F,W,I` → 0 errors |
| 7 | Django check clean | `manage.py check --deploy` → 0 issues |
| 8 | Docs match code | Endpoint/tool/model counts must agree |
| 9 | Functions <100 lines | Split if exceeded |
| 10 | Commit per unit | Don't accumulate 20+ file changes |
| 11 | Security first | Auth + validation on every new endpoint |
| 12 | Performance aware | <200ms p95, indexed queries |

---

## Architecture Decisions for v4.0

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Frontend** | **Lit 3 + Vite + Tailwind** | Already proven (13 views, 96KB). NOT React. |
| **DAG Editor** | **Custom Lit canvas** | Lightweight, no external dependency. |
| **Code Editor** | **Monaco Editor** (Lit wrapper) | Same engine as VS Code, mature. |
| **Graph Viz** | **Sigma.js** (Lit wrapper) | Force-directed ontology graphs. |
| **Charts** | **Apache ECharts** (Lit wrapper) | Rich charting, Apache-backed. |
| **Maps** | **Leaflet** (Lit wrapper) | Geospatial visualization. |
| **BI Dashboards** | **Apache Superset** (Lit iframe embed) | Full BI without building from scratch. |
| **Pipelines** | **Apache NiFi** (Lit iframe + REST API) | Visual DAG builder, 300+ processors. |
| **Ontology Storage** | PostgreSQL + JSONB | Flexible schema, full-text search, proven. |
| **ML Platform** | MLflow-compatible API | Industry standard, open source, no lock-in. |
| **Real-time** | Redis Pub/Sub + WebSocket | Django Channels for subscriptions. |
| **CLI** | Click (Python) | Standard for Python CLIs. |
| **SDK** | Auto-generated from OpenAPI | Single source of truth for all clients. |

---

## Phase 1: Ontology Foundation (Weeks 1–6)

### Week 1–2: Ontology Engine Core
- [ ] `Interface` model (polymorphic type abstractions)
- [ ] `StructType` model (nested composite properties)
- [ ] `SharedProperty` model (reusable across types)
- [ ] `ValueType` model (domain constraints with versioning)
- [ ] `ActionType` model (parameters, rules, side effects, undo)
- [ ] `Function` model (Python/TS business logic attached to objects)
- [ ] Migration + tests for all new models
- [ ] API endpoints for all new models

### Week 3–4: Ontology API + MCP Tools
- [ ] 35 REST endpoints for ontology CRUD + traversal + actions
- [ ] 10 MCP tools for ontology operations
- [ ] Multi-hop traversal (up to 10 hops) optimization
- [ ] Batch operations (1000+ objects) with Django bulk_create
- [ ] Upsert by unique key property
- [ ] Subscription service (Redis Pub/Sub for change notifications)

### Week 5–6: Ontology Explorer UI (Lit 3)
- [ ] Lit 3 Ontology Explorer with table, grid, graph views
- [ ] Lit 3 Object Type Builder (visual schema designer)
- [ ] Lit 3 Filter Builder (visual condition editor)
- [ ] Search Bar (semantic + full-text via Milvus)
- [ ] Graph View (Sigma.js force-directed, Lit wrapper)
- [ ] E2E tests for all UI flows

**Deliverables:** 20+ models, 35 endpoints, 10 MCP tools, Explorer UI

---

## Phase 2: Scraper Octopus (Weeks 1–8, parallel)

### Week 1–4: Template Engine + Task CRUD
- [ ] `ScrapeTemplate` model + API
- [ ] `ScrapeTask` model (replaces ScrapeJob) + full CRUD
- [ ] `ScrapeSchedule` model (cron-based scheduling)
- [ ] `ScrapeRun` model (execution records with trace_id)
- [ ] `ScrapeExport` model (multi-format export config)
- [ ] Template engine: load template, substitute params, execute
- [ ] 50 templates (Amazon, Google Maps, Twitter, YouTube, Reddit, LinkedIn, etc.)
- [ ] Export engine: JSON, JSONL, CSV, XLSX, XML, PostgreSQL, MySQL

### Week 5–6: Anti-Bot Engine
- [ ] CAPTCHA solver integration (2Captcha/AntiCaptcha API)
- [ ] IP rotation with proxy pool management
- [ ] Residential proxy provider integration (BrightData/SmartProxy)
- [ ] Browser fingerprint randomizer (WebGL, Canvas, Audio, Navigator)
- [ ] `ScrapeProxy` and `ScrapeFingerprint` models

### Week 7–8: Browser Automation Enhancements
- [ ] Pagination handler (next button, load more, infinite scroll)
- [ ] Login automation with encrypted credential storage
- [ ] Dropdown/select interaction
- [ ] Form filling and submission
- [ ] iFrame content extraction
- [ ] Screenshot capture
- [ ] 13 MCP tools for scraper operations
- [ ] CLI tool (`voyant scrape`)

**Deliverables:** Template engine, 50 templates, CAPTCHA solving, IP rotation, CLI

---

## Phase 3: ML Platform (Weeks 7–12)

### Week 7–8: Experiment Tracking
- [ ] `Experiment` model (name, description, tags)
- [ ] `Run` model (params, metrics, artifacts, status)
- [ ] `RunArtifact` model (files, images, models)
- [ ] MLflow-compatible REST API (`/api/2.0/mlflow/*`)
- [ ] Experiment CRUD + run logging

### Week 9–10: Model Registry
- [ ] `RegisteredModel` model (name, description, tags)
- [ ] `ModelVersion` model (version, stage, status, metrics)
- [ ] Model stage transitions (None → Staging → Production → Archived)
- [ ] Model artifact storage (MinIO)
- [ ] MLflow model registry API compatibility

### Week 11–12: Model Serving + Agent Platform
- [ ] `ModelEndpoint` model (name, model_version, config)
- [ ] Real-time serving endpoints (REST)
- [ ] Batch prediction endpoints
- [ ] `AgentDefinition` model (prompt, model, tools, guardrails)
- [ ] `AgentEvaluation` model (test cases, scores, AI judge)
- [ ] Agent deployment and monitoring

**Deliverables:** MLflow-compatible experiments, registry, serving, agent lifecycle

---

## Phase 4: Visual Builders (Weeks 9–14)

### Week 9–10: Scraper Visual Builder (Lit 3)
- [ ] Lit 3 DAG canvas component (custom, no React Flow)
- [ ] Step types: navigate, click, scroll, extract, paginate, wait, login
- [ ] Point-and-click element selection (Playwright overlay)
- [ ] Live preview of extraction results
- [ ] Workflow import/export as JSON

### Week 11–12: Ontology Action Builder (Lit 3)
- [ ] Lit 3 visual action configuration (parameters, rules, conditions)
- [ ] Action execution engine (side effects, undo support)
- [ ] Lit 3 Monaco code editor wrapper for functions
- [ ] Function execution sandbox

### Week 13–14: Pipeline Builder (Lit 3 + NiFi)
- [ ] Lit 3 pipeline builder UI (embed NiFi or custom DAG)
- [ ] Pipeline nodes: source, transform, filter, aggregate, export
- [ ] Pipeline execution via Temporal workflows
- [ ] Pipeline monitoring and logs

**Deliverables:** 3 visual builders (scraper, actions, pipelines)

---

## Phase 5: Governance & Polish (Weeks 15–20)

### Week 15–16: Row-Level Security + Column Masking
- [ ] `SecurityPolicy` model (row filters per user/group)
- [ ] `ColumnMask` model (PII masking rules)
- [ ] Ranger integration for row-level checks
- [ ] Query-time column masking in Trino client

### Week 17–18: Unified Catalog + Dashboard Builder (Lit 3)
- [ ] Lit 3 Catalog Explorer (browse databases, tables, columns, lineage)
- [ ] Lit 3 dashboard builder with ECharts charts
- [ ] Dashboard persistence and sharing
- [ ] Data retention policy engine

### Week 19–20: CLI + SDK + Polish
- [ ] CLI tool (`voyant` command) — full platform operations
- [ ] TypeScript SDK (auto-generated from OpenAPI)
- [ ] Python SDK (auto-generated from OpenAPI)
- [ ] WebSocket API for real-time subscriptions
- [ ] Performance optimization (query tuning, caching, connection pooling)

**Deliverables:** RLS, masking, catalog, dashboards, CLI, SDK

---

## Phase 6: Enterprise (Weeks 21–24)

### Week 21–22: Integration + Compliance
- [ ] Kafka event integration for all operations
- [ ] GDPR compliance audit and fixes
- [ ] Data retention enforcement
- [ ] Right-to-deletion implementation
- [ ] SOC 2 preparation checklist

### Week 23–24: Performance + Documentation
- [ ] Load testing (1000 concurrent users, 1M+ objects)
- [ ] ISO documentation finalization
- [ ] API documentation (OpenAPI 3.1)
- [ ] User guide and admin guide
- [ ] Release notes and migration guide

**Deliverables:** Kafka events, GDPR, performance validation, full documentation

---

## Weekly Cadence

| Day | Activity |
|-----|----------|
| Monday | Sprint planning — pick tasks from current phase |
| Tue–Thu | Development — code, test, commit |
| Friday | Integration testing, demo, retro |

## Quality Gates (Every Week)

| Gate | Criteria |
|------|----------|
| Tests | 0 failures, >80% coverage on new code |
| Lint | 0 ruff errors |
| Django check | 0 issues |
| Security | No new auth bypasses, SSRF, injection |
| Docs | SRS requirement IDs traced to code |
| Performance | <200ms p95 on new endpoints |

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| CAPTCHA solver reliability | Multi-provider fallback (2Captcha → AntiCaptcha → CapSolver) |
| Visual builder complexity | Custom Lit canvas, start simple, iterate |
| MLflow API compatibility | Use MLflow's own test suite for validation |
| Performance at scale | Load test weekly, optimize early |
| Scope creep | Strict phase boundaries, no features outside current phase |
