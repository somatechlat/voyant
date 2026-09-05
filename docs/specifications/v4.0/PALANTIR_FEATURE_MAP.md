# Voyant v4.0 — Complete Palantir Feature Map & Gap Analysis

**Date:** 2026-09-05
**Purpose:** Every Palantir Foundry tool → what Voyant has → what needs building

---

## How to Read This

- **HAS** = Fully implemented in code, tested, working
- **PARTIAL** = Partially implemented, needs enhancement
- **SRS** = Specified in SRS but not yet built
- **MISSING** = Not in code, not in SRS — needs design + build

---

## 1. ONTOLOGY ENGINE (Palantir's Core)

### 1.1 Object & Link Types

| Palantir Feature | Voyant Status | Code Location | Gap |
|-----------------|---------------|---------------|-----|
| Object Types (name, description, properties) | **HAS** | `ontology/models.py:23` ObjectType | — |
| 11 Property Types (string/int/float/bool/date/timestamp/enum/array/map/struct/geopoint) | **HAS** | `ontology/models.py:68` PropertyType enum | — |
| Required Properties | **HAS** | `ontology/models.py:109` required field | — |
| Default Values | **HAS** | `ontology/models.py:113` default_value | — |
| Validation Rules (regex/min/max/enum/custom) | **HAS** | `ontology/models.py:118` validation_rules JSONB | — |
| Schema Versioning | **HAS** | `ontology/models.py:40` version field | — |
| Soft Deletion | **HAS** | `ontology/models.py:44` deleted_at | — |
| Link Types with Cardinality (1:1, 1:N, M:N) | **HAS** | `ontology/models.py:208` LinkType | — |
| Link Instances | **HAS** | `ontology/models.py:285` Link | — |
| Object CRUD | **HAS** | `ontology/services.py` ObjectTypeService | — |
| Object Batch Create (1000+) | **HAS** | `ontology/services.py:297` batch_create | — |
| Object Upsert | **HAS** | `ontology/services.py:323` upsert | — |
| Optimistic Concurrency | **HAS** | `ontology/models.py:168` version field | — |
| Multi-hop Traversal (up to 10 hops) | **HAS** | `ontology/services.py:506` traverse | — |
| **Interfaces (Polymorphic Types)** | **SRS** | — | ONT-F-018 |
| **Struct Types (Nested Composites)** | **SRS** | — | ONT-F-020 |
| **Shared Properties (Reusable)** | **SRS** | — | ONT-F-021 |
| **Value Types (Domain Constraints)** | **SRS** | — | ONT-F-022 |
| **Type Classes (Metadata Classification)** | **MISSING** | — | Needs design |
| **Render Hints (UI Config)** | **MISSING** | — | Needs design |
| **Status Definitions (Lifecycle)** | **MISSING** | — | Needs design |
| **Object Type Groups** | **SRS** | — | ONT-F-036 |

### 1.2 Action Types (Palantir's "Kinetics")

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **Action Types (CRUD operations)** | **SRS** | ONT-F-026 |
| **Action Parameters (types, defaults, validation)** | **SRS** | ONT-F-026 |
| **Action Rules (pre/post conditions)** | **SRS** | ONT-F-026 |
| **Action Side Effects (notifications, webhooks)** | **SRS** | ONT-F-026 |
| **Action Undo/Revert** | **MISSING** | Needs design |
| **Action Permissions (read/write auth)** | **MISSING** | Needs design |
| **Action Logging (audit trail)** | **HAS** | `core/models.py` AuditLog |
| **Batched Action Execution** | **MISSING** | Needs design |
| **Function-Backed Actions** | **SRS** | ONT-F-029 |
| **Action Metrics** | **MISSING** | Needs design |

### 1.3 Functions (Business Logic)

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **Python Functions on Objects** | **SRS** | ONT-F-029 |
| **TypeScript Functions** | **MISSING** | Needs design |
| **Function Versioning** | **MISSING** | Needs design |
| **Function Monitoring** | **MISSING** | Needs design |
| **Function Permissions** | **MISSING** | Needs design |
| **Streaming Functions** | **MISSING** | Needs design |
| **Query Functions (API Gateway)** | **MISSING** | Needs design |
| **Unit Testing for Functions** | **MISSING** | Needs design |

### 1.4 Ontology Services

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **Object Set Service (query/filter/aggregate)** | **PARTIAL** | Basic ORM only — need high-scale |
| **Subscription Service (real-time notifications)** | **SRS** | ONT-F-032 |
| **Indexing Service (full-text + semantic)** | **PARTIAL** | Milvus exists, need full-text |
| **Materialization Service (pre-computed views)** | **MISSING** | Needs design |
| **Scenario Engine (what-if analysis)** | **MISSING** | Needs design |
| **Write Architecture (atomic transactions)** | **HAS** | Django transactions |
| **Ontology Branching (git-like)** | **MISSING** | Needs design |

### 1.5 Ontology UI Tools

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **Object Explorer (search, filter, pivot, compare)** | **PARTIAL** | Admin dashboard has table view only |
| **Object Views (full, panel, configured)** | **MISSING** | Needs React build |
| **Object Monitors (condition-based alerts)** | **MISSING** | Needs design |
| **Vertex (graph visualization)** | **MISSING** | Needs Sigma.js/D3 |
| **Machinery (process mining)** | **MISSING** | Needs design |
| **Map templates** | **MISSING** | Needs design |
| **Dynamic Scheduling (Gantt, calendar)** | **MISSING** | Needs design |
| **Time Series (events, alerts, derived)** | **MISSING** | Needs design |
| **Ontology Manager (browse, edit, branch)** | **PARTIAL** | Admin has basic CRUD |

---

## 2. DATA ENGINEERING (Palantir Pipeline Builder)

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **Visual DAG Pipeline Builder** | **SRS** | DATA-F-012 |
| **Batch Pipelines** | **PARTIAL** | Temporal workflows exist |
| **Streaming Pipelines (Flink)** | **PARTIAL** | `streaming/` stub |
| **Incremental Pipelines** | **MISSING** | Needs design |
| **200+ Data Connectors** | **PARTIAL** | Airbyte client only |
| **Dataset Branching (git-like)** | **MISSING** | Needs design |
| **Data Expectations (quality checks)** | **PARTIAL** | Great Expectations integration |
| **Data Lineage** | **PARTIAL** | DataHub client |
| **SQL Studio** | **HAS** | `sql/api.py` Trino client |
| **Time Travel (dataset snapshots)** | **MISSING** | Needs Iceberg integration |
| **Geospatial Transforms** | **MISSING** | Needs design |
| **LLM Transforms in Pipeline** | **MISSING** | Needs design |
| **Pipeline Parameters** | **MISSING** | Needs design |
| **Subgraphs (reusable blocks)** | **MISSING** | Needs design |
| **Schedules** | **PARTIAL** | Temporal scheduling |

---

## 3. AI/ML PLATFORM (Palantir AIP)

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **Model Connectivity (LLM integration)** | **PARTIAL** | MCP tools connect to models |
| **Agent Bricks (build/evaluate agents)** | **PARTIAL** | Capsule system |
| **Agent Evaluation (AI judge)** | **SRS** | ML-F-007 |
| **Experiment Tracking** | **SRS** | ML-F-001 |
| **Model Registry** | **SRS** | ML-F-003 |
| **Model Serving (real-time + batch)** | **SRS** | ML-F-004 |
| **Feature Store** | **MISSING** | Needs design |
| **AutoML** | **MISSING** | Needs design |
| **LLM Fine-Tuning** | **MISSING** | Needs design |
| **Semantic Search (RAG)** | **PARTIAL** | Milvus + embeddings exist |
| **Document Intelligence** | **PARTIAL** | PDF/OCR/transcription exist |

---

## 4. APPLICATIONS (Palantir Workshop + Quiver)

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **Workshop (low-code app builder)** | **MISSING** | Needs React builder |
| **Quiver (analytical notebooks)** | **MISSING** | Needs design |
| **Object Views (configurable UI)** | **MISSING** | Needs React components |
| **Dashboard Builder** | **PARTIAL** | 13 Lit admin pages exist |
| **Comment on Objects** | **MISSING** | Needs design |
| **Media Rendering (images, PDFs)** | **PARTIAL** | PDF/OCR exist |
| **Marketplace (data sharing)** | **MISSING** | Needs design |

---

## 5. SECURITY & GOVERNANCE

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **RBAC (roles + permissions)** | **HAS** | SpiceDB + Keycloak |
| **Row-Level Security** | **SRS** | GOV-F-003 |
| **Column-Level Masking** | **SRS** | GOV-F-004 |
| **Object Security Policies** | **MISSING** | Needs design |
| **Markings (data classification)** | **MISSING** | Needs design |
| **Audit Logging** | **HAS** | AuditLog model |
| **Data Lineage** | **PARTIAL** | DataHub client |
| **Multi-Tenant Isolation** | **HAS** | TenantModel + RBACManager |
| **SSO/SAML** | **HAS** | Keycloak |
| **Encryption (at-rest, in-transit)** | **PARTIAL** | TLS for connections, Vault for secrets |

---

## 6. DEVELOPER TOOLCHAIN

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **REST API (OpenAPI 3.1)** | **HAS** | 66 endpoints via Django Ninja |
| **MCP Tools** | **HAS** | 46 tools |
| **OSDK (TypeScript + Python)** | **SRS** | API-F-003 |
| **CLI** | **SRS** | API-F-005 |
| **Code Repositories** | **MISSING** | Git integration for notebooks |
| **Unit Testing Framework** | **HAS** | pytest, 2,203 tests |
| **CI/CD (Asset Bundles)** | **MISSING** | Needs design |

---

## 7. WHAT VOYANT HAS THAT PALANTIR DOESN'T

| Feature | Voyant Advantage |
|---------|-----------------|
| **MCP Protocol (46 tools)** | Palantir has zero MCP support |
| **Agent-First Design** | Purpose-built for AI agent orchestration |
| **Web Scraping Engine (8,471 LOC)** | Deep research, browser automation, OCR — Palantir has nothing |
| **Capsule System (2,550 LOC)** | Portable plugin architecture with Ed25519 signing |
| **Self-Hosted (Docker)** | Full control, no vendor lock-in |
| **Open Source (Apache 2.0)** | Community-driven, extensible, auditable |
| **Temporal Workflows (17)** | Durable, replayable orchestration |
| **Lightweight (20 containers)** | vs Palantir's massive infrastructure |

---

## 8. BUILD PRIORITY — What to Build First

### Phase 1 (Weeks 1–6): Ontology Engine Completion
**Why:** This is Palantir's core differentiator. Voyant has the foundation (5 models, CRUD, traversal). Need to add the "kinetics."

Build:
1. `Interface` model + API (polymorphic types)
2. `StructType` model + API (nested composites)
3. `SharedProperty` model + API (reusable properties)
4. `ValueType` model + API (domain constraints)
5. `ActionType` model + API (operations with params, rules, side effects)
6. `Function` model + API (Python business logic on objects)
7. `TypeClass` model (metadata classification)
8. `RenderHint` model (UI rendering config)
9. `StatusDefinition` model (lifecycle statuses)
10. Object Set Service (high-scale query/filter/aggregate)
11. Subscription Service (Redis Pub/Sub for real-time)
12. Ontology Explorer UI (React: table, grid, graph views)

### Phase 2 (Weeks 1–8, parallel): Scraper Octopus
**Why:** Voyant's unique advantage — Palantir/Databricks have nothing.

Build:
1. Template engine + 50 templates
2. Task CRUD + scheduling
3. CAPTCHA solver integration
4. IP rotation + residential proxies
5. Browser fingerprint randomizer
6. Visual workflow builder
7. Export engine (JSON/CSV/XLSX/XML/DB)
8. 13 MCP tools
9. CLI tool

### Phase 3 (Weeks 7–12): ML Platform
**Why:** Databricks' core advantage. Voyant has sklearn primitives only.

Build:
1. Experiment tracking API (MLflow-compatible)
2. Model registry with versioning
3. Model serving endpoints (real-time + batch)
4. Agent definition model
5. Agent evaluation framework
6. Feature Store (basic)

### Phase 4 (Weeks 9–14): Visual Builders
**Why:** Palantir's Workshop/Quiver are their app layer.

Build:
1. Object Explorer (React: search, filter, pivot, compare)
2. Object Views (configurable full/panel views)
3. Action Builder (visual parameter configuration)
4. Function Editor (Monaco code editor)
5. Pipeline Builder (React Flow DAG editor)
6. Graph View (Sigma.js force-directed)
7. Dashboard Builder (chart/table/widget)

### Phase 5 (Weeks 15–20): Governance & Polish
Build:
1. Row-level security filters
2. Column-level masking
3. Object security policies
4. Data markings/classification
5. Scenario Engine (what-if analysis)
6. Ontology branching (git-like)
7. CLI + SDK (auto-generated from OpenAPI)
8. WebSocket API for real-time

### Phase 6 (Weeks 21–24): Enterprise
Build:
1. Kafka event integration
2. GDPR compliance
3. Performance optimization (1M+ objects, 10K users)
4. ISO documentation finalization
5. Load testing
6. Release preparation

---

## 9. EFFORT SUMMARY

| Domain | Requirements | Done | To Build | Weeks |
|--------|-------------|------|----------|-------|
| Ontology Engine | 35 | 15 | 20 | 6 |
| Scraper Octopus | 30 | 6 | 24 | 8 |
| ML Platform | 12 | 0 | 12 | 6 |
| Visual Builders | 15 | 1 | 14 | 6 |
| Governance | 12 | 4 | 8 | 6 |
| Enterprise | 10 | 2 | 8 | 4 |
| **TOTAL** | **114** | **28** | **86** | **24** |

**Team:** 3–4 engineers, 24 weeks, 6 parallel phases.

---

## 10. FILES TO CREATE/MODIFY

### New Django Apps
| App | Purpose | Models | Priority |
|-----|---------|--------|----------|
| `apps/ontology/` (enhance) | Full Palantir-grade ontology | +10 models | P0 |
| `apps/ml_platform/` | MLflow-compatible ML | 6 models | P1 |
| `apps/agent_platform/` | Agent lifecycle | 4 models | P1 |
| `apps/scraper_octopus/` | Octoparse-grade scraping | 9 models | P0 |
| `apps/dashboard_builder/` | Custom dashboards | 3 models | P2 |

### New Frontend (React)
| Component | Purpose | Priority |
|-----------|---------|----------|
| Ontology Explorer | Search, filter, pivot, compare objects | P0 |
| Object Type Builder | Visual schema designer | P0 |
| Action Builder | Visual action configuration | P1 |
| Function Editor | Monaco code editor | P1 |
| Pipeline Builder | React Flow DAG editor | P1 |
| Graph View | Sigma.js force-directed | P1 |
| Dashboard Builder | Chart/table/widget | P2 |
| Scraper Visual Builder | Workflow editor | P0 |

### New API Endpoints (Target: 120+)
| Router | Current | Target | New |
|--------|---------|--------|-----|
| ontology | 5 | 35 | +30 |
| scraper | 11 | 21 | +10 |
| ml_platform | 0 | 12 | +12 |
| agent_platform | 0 | 8 | +8 |
| governance | 7 | 12 | +5 |
| admin_panel | 28 | 28 | 0 |
| **TOTAL** | **66** | **120+** | **+54** |

### New MCP Tools (Target: 80+)
| Category | Current | Target | New |
|----------|---------|--------|-----|
| Ontology | 0 | 15 | +15 |
| Scraper | 7 | 13 | +6 |
| ML | 0 | 8 | +8 |
| Agent | 0 | 5 | +5 |
| Governance | 5 | 8 | +3 |
| Existing | 34 | 34 | 0 |
| **TOTAL** | **46** | **83+** | **+37** |
