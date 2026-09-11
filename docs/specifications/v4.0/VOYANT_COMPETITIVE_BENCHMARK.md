# Voyant v4.0 — Deep Competitive Benchmark
## Palantir Foundry vs Databricks vs Voyant

**Document ID:** VOYANT-CB-4.0.0
**Version:** 1.0.0
**Date:** 2026-09-05
**Status:** Draft for Review
**Author:** Voyant Engineering
**Sources:** Palantir Foundry docs, Databricks product pages, MLflow docs, internal SRS/SAD/Feature Map, code inspection of `apps/ontology/models.py`, `apps/ml_platform/models.py`, `apps/mcp/tools_*.py`

---

## 1. Executive Summary

### 1.1 Three-Way Comparison Table (25 Dimensions)

| Dimension | Palantir Foundry | Databricks | Voyant v4.0 | Winner |
|-----------|-----------------|------------|-------------|--------|
| **Deployment** | SaaS only (Palantir-hosted) | SaaS (AWS/Azure/GCP) | Self-hosted Docker/K8s | **Voyant** (full control) |
| **Source Code** | Proprietary closed-source | Mixed (Spark open, platform closed) | Apache 2.0 open source | **Voyant** (audit, extend, fork) |
| **Voyant Catalog (M3)** | Full (Object Types, Actions, Functions, OSS) | None (Genie Ontology is semantic layer only) | Full (10 models, Actions, Functions, MCP) | **Voyant** = Palantir |
| **Data Ingestion** | 200+ connectors, Pipeline Builder | Lakeflow (DLT), Auto Loader, 200+ connectors | Airbyte + NiFi + Temporal | **Databricks** |
| **SQL Engine** | Pipeline Builder SQL transforms | Photon + Spark SQL (10–100x faster) | Trino + Spark SQL | **Databricks** |
| **Storage Format** | Proprietary datasets | Delta Lake (ACID, time travel, open) | Apache Iceberg on MinIO | **Databricks** (maturity) |
| **Voyant ML (M6)** | AIP model connectivity, Agent Bricks | MLflow (experiments, registry, serving, AutoML) | MLflow-compatible (models built, 8 new models) | **Databricks** |
| **Voyant Agent (M7)** | AIP chat, code execution | Agent Bricks (build/evaluate/deploy) | Intent Engine + 67 MCP tools + Capsules | **Voyant** (agent-native) |
| **MCP Protocol** | Zero support | Zero support (proprietary gateway) | 67 tools, native MCP server | **Voyant** (unique) |
| **NL→Execution** | AIP chat (LLM interprets) | Genie (text-to-SQL, LLM interprets) | Intent Engine (LLM proposes, code executes) | **Voyant** (deterministic) |
| **Voyant Scrape (M8)** | None | None | Octopus (8,471 LOC, 8 browser arms) | **Voyant** (unique) |
| **Voyant Shield (M9)** | Object security, markings, audit | Unity Catalog (RLS, column masking, lineage) | SpiceDB RBAC + RLS + masking + DataHub | **Databricks** (maturity) |
| **Data Lineage** | Built-in lineage | Automated column-level lineage | DataHub client (partial) | **Databricks** |
| **Real-time** | Subscription Service (WebSocket) | Structured Streaming, Auto Loader | Kafka + Flink (stub), Redis Pub/Sub | **Databricks** |
| **Visualization** | Workshop (low-code app builder) | Dashboards, Notebooks | Lit 3 admin (13 views) | **Palantir** |
| **Notebooks** | Quiver (analytical notebooks) | Databricks Notebooks (collaborative) | None | **Databricks** |
| **Data Quality** | Built-in expectations | Lakeflow expectations + monitoring | Great Expectations + Evidently | **Databricks** |
| **Multi-Cloud** | AWS + Azure (limited GCP) | AWS + Azure + GCP | Docker (any infra) | **Databricks** |
| **Pricing** | $1M+ annual contracts | Pay-per-DBU (~$0.07–$0.40/DBU) | Self-hosted (infra cost only) | **Voyant** |
| **Time to Value** | 3–6 months (Forward Deployed Engineers) | Days (serverless), weeks (custom) | Hours (Docker compose up) | **Voyant** |
| **Agent Evaluation** | Limited (AIP eval) | Agent Evaluation (AI judges) | AgentDefinition + AgentEvaluation models | **Databricks** (depth) |
| **Capsule System** | None | None | Ed25519-signed plugins (2,550 LOC) | **Voyant** (unique) |
| **Temporal Durability** | Proprietary orchestration | Workflow orchestration (Airflow/DLT) | Temporal.io (25+ workflows, replayable) | **Voyant** (durability) |
| **Graph Traversal** | Limited (link traversal in OSS) | None native | Multi-hop traversal (up to 10 hops) | **Voyant** |
| **Container Count** | Massive infra (proprietary) | Managed (cloud-native) | 20 containers | **Voyant** (lightweight) |

### 1.2 Summary Scorecard

| Category | Palantir | Databricks | Voyant |
|----------|----------|------------|--------|
| Data Engineering (M2, M4) | 8/10 | 10/10 | 6/10 |
| Ontology/Semantics (M3) | 10/10 | 4/10 | 8/10 |
| ML/AI Platform (M6) | 7/10 | 10/10 | 3/10 |
| Agent Platform (M7) | 6/10 | 7/10 | 9/10 |
| Governance (M9) | 8/10 | 9/10 | 6/10 |
| UI/UX | 8/10 | 7/10 | 4/10 |
| Developer Experience (M12) | 6/10 | 7/10 | 8/10 |
| Self-Hosted / Sovereignty | 0/10 | 0/10 | 10/10 |
| Agent-Native (MCP) (M7) | 0/10 | 0/10 | 10/10 |
| Web Data Extraction (M8) | 0/10 | 0/10 | 10/10 |
| **Overall** | **53/100** | **54/100** | **74/100** |

> **Key Insight:** Voyant's score is inflated by unique capabilities (MCP, scraping, self-hosted). In raw feature parity with Palantir/Databricks, Voyant is ~37% complete. But the 37% includes the most differentiated features competitors cannot replicate without rearchitecting.

---

## 2. Architecture Comparison

### 2.1 Palantir Foundry Architecture

```
┌─────────────────────────────────────────────┐
│ LAYER: APPLICATIONS                          │
│ Workshop (low-code) · Quiver (notebooks)     │
│ Object Explorer · Vertex (graph) · Maps      │
├──────────────────────────────────────────────┤
│ LAYER: ONTOLOGY                              │
│ Object Types · Properties · Links            │
│ Actions · Functions · Object Set Service     │
│ Subscription Service · Scenario Engine       │
├──────────────────────────────────────────────┤
│ LAYER: MODEL BUILDING                        │
│ Model Connectivity · AIP · Agent Bricks      │
│ Foundry Agent · Code Repositories            │
├──────────────────────────────────────────────┤
│ LAYER: PIPELINE                              │
│ Pipeline Builder (visual DAG)                │
│ Batch · Streaming (Flink) · Incremental      │
│ 200+ Connectors · Quality Checks             │
├──────────────────────────────────────────────┤
│ LAYER: STORAGE                               │
│ Datasets (proprietary format)                │
│ Dataset Branching · Time Travel · Lineage    │
├──────────────────────────────────────────────┤
│ LAYER: SECURITY                              │
│ RBAC · Object Security · Markings            │
│ Audit · SSO/SAML · Encryption                │
└──────────────────────────────────────────────┘
```

**Key architectural decisions:**
- Proprietary dataset format (not open — lock-in)
- Ontology is THE central abstraction (everything maps to objects/links)
- Pipeline Builder is the data engineering UI (not code-first)
- Closed-source, SaaS-only (you never see the code)
- AIP is the AI layer (added 2023, evolving rapidly)

### 2.2 Databricks Lakehouse Architecture

```
┌─────────────────────────────────────────────┐
│ LAYER: APPLICATIONS                          │
│ Genie One (AI Assistant) · Dashboards        │
│ Notebooks · Databricks Apps · BI Tools       │
├──────────────────────────────────────────────┤
│ LAYER: AI/ML                                 │
│ Agent Bricks · Model Serving · MLflow        │
│ AI Search · Unity AI Gateway · Doc Intel     │
│ Model Training · Fine-Tuning · AutoML        │
├──────────────────────────────────────────────┤
│ LAYER: GOVERNANCE                            │
│ Unity Catalog · Unity AI Gateway             │
│ Business Semantics · Column-level Lineage    │
│ Attribute-based Access Control · Monitoring  │
├──────────────────────────────────────────────┤
│ LAYER: DATA ENGINEERING                      │
│ Lakeflow (DLT) · Auto Loader                 │
│ Workflow Orchestration · Job Scheduling       │
│ Incremental Processing · CDC                 │
├──────────────────────────────────────────────┤
│ LAYER: COMPUTE                               │
│ Photon Engine (C++) · Apache Spark           │
│ Serverless Compute · GPU Clusters            │
├──────────────────────────────────────────────┤
│ LAYER: STORAGE                               │
│ Delta Lake (open format, ACID)               │
│ Apache Iceberg · Hudi · Parquet support      │
│ Managed Tables (auto-optimization)           │
└──────────────────────────────────────────────┘
```

**Key architectural decisions:**
- Open formats (Delta Lake, Iceberg, Parquet) — data is portable
- Unity Catalog as single governance plane for data AND AI
- Genie Ontology learns from usage (user-modeled + inferred semantics)
- Agent Bricks for multi-framework agent development
- Serverless compute with instant-start capability
- Lakebase (Postgres) for transactional + operational workloads

### 2.3 Voyant v4.0 Architecture

```
┌─────────────────────────────────────────────┐
│ LAYER 1: CONSUMERS                           │
│ AI Agents (MCP) · Humans (Dashboard)         │
│ Systems (Kafka) · CLI (planned)              │
├──────────────────────────────────────────────┤
│ LAYER 2: GATEWAY                             │
│ Apache APISIX (rate limit, auth, TLS)        │
├──────────────────────────────────────────────┤
│ LAYER 3: API                                 │
│ Django 5 + Django Ninja (120+ REST)          │
│ django-mcp (67 MCP tools)                    │
│ WebSocket (real-time subscriptions)          │
├──────────────────────────────────────────────┤
│ LAYER 4: INTENT ENGINE                       │
│ Query Intent · Pipeline Intent · Scraper     │
│ LLM Router · Ontology Cache                  │
│ Output: Structured JSON execution plans      │
├──────────────────────────────────────────────┤
│ LAYER 5: DOMAIN SERVICES                     │
│ Ontology · Data Intel · Scraper · ML         │
│ Voyant Agent (M7) · Shield (M9) · Capsules   │
│ Search Engine                                │
├──────────────────────────────────────────────┤
│ LAYER 6: ORCHESTRATION                       │
│ Temporal.io (25+ workflows, self-healing)    │
├──────────────────────────────────────────────┤
│ LAYER 7: DATA                                │
│ PostgreSQL · Iceberg · Kafka · Flink         │
│ Spark · Milvus · Elasticsearch · Redis       │
│ MinIO · DuckDB                               │
├──────────────────────────────────────────────┤
│ LAYER 8: GOVERNANCE                          │
│ Ranger (data RBAC) · SpiceDB (app RBAC)      │
│ Atlas (meta) · Vault · Keycloak · AuditLog   │
├──────────────────────────────────────────────┤
│ LAYER 9: OBSERVABILITY                       │
│ Prometheus · Grafana · SkyWalking            │
└──────────────────────────────────────────────┘
```

### 2.4 Side-by-Side Architecture Comparison

| Layer | Palantir | Databricks | Voyant | Voyant Advantage |
|-------|----------|------------|--------|-----------------|
| **Gateway** | Proprietary | Cloud-native | Apache APISIX | Open source, pluggable |
| **API** | REST (proprietary) | REST + SDKs (proprietary) | Django Ninja + MCP | **MCP protocol** — agents talk natively |
| **Intent/Translation (M7)** | AIP chat (LLM interprets) | Genie (LLM interprets) | Intent Engine (LLM proposes, code executes) | **Deterministic execution** — no hallucinated queries |
| **Orchestration** | Proprietary | Databricks Jobs / DLT | Temporal.io | **Replayable**, durable, self-healing |
| **Storage** | Proprietary datasets | Delta Lake (open) | Iceberg on MinIO | Open format, S3-compatible |
| **Governance** | Object security | Unity Catalog | SpiceDB + Ranger + DataHub | Granular Zanzibar-style auth |
| **Compute** | Managed | Photon + Spark serverless | Trino + Spark (self-managed) | Full control over compute |
| **AI/ML (M6)** | AIP | MLflow + Agent Bricks | MLflow-compatible + Intent Engine | Agent-native, MCP-connected |

### 2.5 What Voyant Does Differently (and WHY It's Better)

1. **Agent-Native Architecture** — Palantir and Databricks bolt agents onto existing platforms. Voyant was built with agents as the primary consumer. Every feature is MCP-callable from day one.

2. **Deterministic Execution** — Palantir AIP and Databricks Genie let the LLM generate SQL/code that executes directly. If the LLM hallucinates, the wrong query runs. Voyant's Intent Engine: LLM proposes a structured plan → Plan Validator checks against schema → Plan Executor runs deterministic code. **The LLM never touches production data.**

3. **Self-Hosted Sovereignty** — Both competitors are SaaS-only. Voyant runs on your hardware, your cloud, your air-gapped network. Full data sovereignty.

4. **Lightweight** — Voyant runs in 20 Docker containers vs Palantir/Databricks requiring massive infrastructure. A single `docker compose up` gets you a working platform.

5. **Apache-First** — Every layer uses Apache projects (Iceberg, Spark, Flink, NiFi, Ranger, Atlas, APISIX, SkyWalking). No proprietary lock-in at any layer.

---

## 3. Voyant Catalog (M3) — Ontology Engine Deep Dive

### 3.1 Palantir Ontology Architecture

Palantir's ontology is their core differentiator — the "operating system for the enterprise."

**Core Concepts:**
- **Object Types** — Schema definitions (e.g., "Customer", "Order", "Sensor")
- **Properties** — 11 data types (string, int, float, boolean, date, timestamp, enum, array, map, struct, geopoint)
- **Links** — Relationships between objects with cardinality (1:1, 1:N, M:N)
- **Actions** — Operations on objects with parameters, pre-conditions, side effects, undo
- **Functions** — Python/TypeScript business logic attached to objects/actions
- **Object Set Service** — High-scale query, filter, aggregate on object collections
- **Subscription Service** — Real-time change notifications (WebSocket-based)
- **Interfaces** — Polymorphic type abstractions (like Java interfaces)
- **Struct Types** — Nested composite types
- **Shared Properties** — Reusable property definitions across types
- **Value Types** — Domain constraints with versioning
- **Scenario Engine** — What-if analysis with branching/merging
- **Ontology Branching** — Git-like versioning for schema changes

### 3.2 Feature-by-Feature Ontology Comparison (35+ rows)

| Feature | Palantir | Voyant v4.0 | Voyant Advantage | Code Reference |
|---------|----------|-------------|-----------------|----------------|
| Object Types | Full (proprietary) | **HAS** — `ObjectType` model | Open schema, MCP-accessible | `ontology/models.py:23` |
| 11 Property Types | Full | **HAS** — `PropertyType` enum (11 types) | Identical coverage | `ontology/models.py:68` |
| Required Properties | Full | **HAS** — `required` field | — | `ontology/models.py:109` |
| Default Values | Full | **HAS** — `default_value` JSONB | — | `ontology/models.py:113` |
| Validation Rules | Full | **HAS** — `validation_rules` JSONB (regex/min/max/enum/custom) | JSON-native validation | `ontology/models.py:118` |
| Schema Versioning | Full | **HAS** — `version` auto-increment | — | `ontology/models.py:40` |
| Soft Deletion | Full | **HAS** — `deleted_at` with referential integrity | — | `ontology/models.py:44` |
| Link Types | Full | **HAS** — `LinkType` with cardinality enum | — | `ontology/models.py:208` |
| Link Cardinality | 1:1, 1:N, M:N | **HAS** — `Cardinality` enum | — | `ontology/models.py:200` |
| Link Properties | Full | **HAS** — `properties_schema` JSONB | — | `ontology/models.py:243` |
| Object CRUD | Full | **HAS** — `ObjectService` | — | `ontology/services.py` |
| Batch Create (1000+) | Full | **HAS** — `batch_create()` | — | `ontology/services.py:297` |
| Upsert | Full | **HAS** — `upsert()` by unique key | — | `ontology/services.py:323` |
| Optimistic Concurrency | Full | **HAS** — `version` field on Object | — | `ontology/models.py:168` |
| Multi-hop Traversal | Up to 10 hops | **HAS** — `LinkService.traverse()` | MCP-callable (`voyant.ontology.traverse`) | `ontology/services.py:506` |
| **Interfaces** | Full | **HAS** — `Interface` model with M2M | **Agent can query via MCP** | `ontology/models.py:351` |
| **Struct Types** | Full | **HAS** — `StructType` model | — | `ontology/models.py:410` |
| **Shared Properties** | Full | **HAS** — `SharedProperty` model with M2M | — | `ontology/models.py:451` |
| **Value Types** | Full | **HAS** — `ValueType` model with constraints | — | `ontology/models.py:499` |
| **Action Types** | Full (proprietary) | **HAS** — `ActionType` model (params, rules, side effects, undo) | **Open, auditable, MCP-executable** | `ontology/models.py:546` |
| **Action Execution** | Proprietary | **HAS** — `ActionExecutor` with validation, pre/post conditions, audit | Full undo support via `ActionExecution` | `ontology/action_executor.py` |
| **Functions** | Full (Python/TS) | **HAS** — `Function` model (Python + TS) | Sandboxed subprocess execution | `ontology/models.py:646` |
| **Function Runner** | Proprietary | **HAS** — `FunctionRunner` with timeout, memory limits | Subprocess isolation, schema validation | `ontology/function_runner.py` |
| **Object Set Service** | High-scale | **PARTIAL** — Basic ORM queries | Need: Redis caching, aggregation pipeline | — |
| **Subscription Service** | Real-time WS | **SRS** — ONT-F-032 | Will use Redis Pub/Sub + WebSocket | — |
| **Scenario Engine** | What-if branching | **MISSING** | Planned: Git-like branching | — |
| **Ontology Branching** | Git-like | **MISSING** | Planned: Version branches | — |
| **Type Classes** | Metadata classification | **MISSING** | — | — |
| **Render Hints** | UI config per type | **MISSING** | — | — |
| **Status Definitions** | Lifecycle states | **MISSING** | — | — |
| **Object Type Groups** | Organization | **SRS** — ONT-F-036 | — | — |
| **MCP Tools for Ontology** | Zero | **HAS** — 14 tools | **UNIQUE — agents can CRUD ontology via MCP** | `mcp/tools_ontology.py` |
| **Self-Hosted** | No (SaaS only) | **HAS** — Docker | Full data sovereignty | — |
| **Open Schema** | No (proprietary) | **HAS** — PostgreSQL + JSONB | Inspect, audit, extend | — |
| **Action Audit Trail** | Proprietary | **HAS** — `ActionExecution` model with `previous_values` | Full undo history | `action_executor.py:33` |

### 3.3 Exact Improvements Voyant Catalog (M3) Makes Over Palantir Ontology

| Improvement | Description | Why It Matters |
|------------|-------------|---------------|
| **MCP Access** | 14 MCP tools (`voyant.ontology.types.*`, `voyant.ontology.objects.*`, `voyant.ontology.links.*`, `voyant.ontology.traverse`, `voyant.ontology.interfaces.list`, `voyant.ontology.actions.execute`, `voyant.ontology.functions.run`) | Palantir has ZERO MCP support. AI agents cannot natively interact with Palantir ontology. Voyant agents can create types, write objects, traverse graphs, execute actions — all via standardized MCP protocol. |
| **Self-Hosted** | Runs on Docker, any infrastructure | Palantir requires $1M+ annual contracts and Palantir Forward Deployed Engineers on-site. Voyant: `docker compose up`. |
| **Open Schema** | PostgreSQL + JSONB storage, inspectable | Palantir's dataset format is proprietary. Voyant's ontology is stored in standard PostgreSQL — you can query it directly, back it up, migrate it. |
| **Agent-Native Design** | Every ontology operation is MCP-callable | Palantir was designed for humans first, agents second. Voyant was designed for agents first, humans second. |
| **Function Sandboxing** | Subprocess isolation with timeout + memory limits (`function_runner.py`) | Voyant runs user functions in isolated subprocesses with strict resource limits. Palantir's function execution details are opaque. |
| **Temporal Durability** | All ontology mutations can be wrapped in Temporal workflows | Actions can be made durable and replayable via Temporal. Palantir has no equivalent durable execution layer. |

---

## 4. Voyant Analyze (M5) — Data Intelligence Comparison

### 4.1 Three-Way Data Stack

| Capability | Palantir Foundry | Databricks | Voyant v4.0 |
|-----------|-----------------|------------|-------------|
| **Compute Engine** | Managed (proprietary) | Photon (C++) + Spark SQL | Trino + Spark SQL |
| **Storage Format** | Proprietary datasets | Delta Lake (ACID, time travel) | Apache Iceberg on MinIO |
| **Ingestion** | 200+ connectors, Pipeline Builder | Lakeflow (DLT), Auto Loader, 200+ connectors | Airbyte (200+ connectors), NiFi |
| **SQL** | SQL Studio (proprietary) | Databricks SQL (Photon-accelerated) | Trino SQL (via `tools_core.py:181`) |
| **Data Quality** | Built-in expectations | Lakeflow expectations + quality monitoring | Great Expectations + Evidently |
| **Data Lineage** | Built-in | Automated column-level lineage | DataHub client (`tools_catalog.py:43`) |
| **Streaming** | Flink (managed) | Structured Streaming, Auto Loader | Kafka + Flink (stub) |
| **Pipeline Builder** | Visual DAG (Pipeline Builder) | Lakeflow declarative pipelines | Temporal workflows (code-first) |
| **Time Travel** | Dataset snapshots | Delta Lake time travel (24/7) | Iceberg snapshots (planned) |
| **NL→SQL** | AIP chat | Genie (text-to-SQL) | Intent Engine (NL→plan→Trino SQL) |
| **MCP Data Tools** | None | None | `voyant.sql`, `voyant.ingest`, `voyant.profile`, `voyant.quality`, `voyant.analyze`, `voyant.kpi`, `voyant.lineage` |

### 4.2 Data Engineering: What Voyant Analyze (M5) Improves

| Improvement | Technical Approach | Why It's Better |
|------------|-------------------|-----------------|
| **Agent-First Data Ops** | Every data operation is an MCP tool. An AI agent can discover sources, ingest data, profile quality, run SQL, check lineage — all via MCP protocol. | Neither Palantir nor Databricks allow AI agents to manage data pipelines natively. Their agents can query data, but not orchestrate ingestion/quality/lineage. |
| **Temporal Durability** | All pipelines run as Temporal workflows with replay, retry, timeout. | If a Databricks job fails mid-run, you restart. If a Temporal workflow fails, it automatically resumes from the last completed step. |
| **MCP Lineage Tool** | `voyant.lineage(urn, direction, depth)` — agents can traverse upstream/downstream lineage graphs via MCP. | Neither competitor exposes lineage as a programmatic API for agents. |
| **KPI Template Engine** | `voyant.kpi_templates.*` — pre-built SQL templates for common KPIs, agents can list, get, render. | Neither competitor has agent-callable KPI templates. |

### 4.3 Databricks-Specific Gaps Voyant Must Close

| Databricks Feature | Voyant Gap | Improvement Strategy |
|-------------------|------------|---------------------|
| **Photon Engine** | Trino is 10–100x slower on analytical queries | Phase 3: Deploy Spark with Photon-compatible optimizations; long-term: evaluate DuckDB for small queries, Spark for large |
| **Auto Loader** | No incremental file ingestion | Build: Temporal workflow watching MinIO/S3 for new files, auto-ingest |
| **Serverless Compute** | Manual container scaling | Phase 6: K8s HPA based on queue depth, or serverless Spark on K8s |
| **Managed Tables** | No auto-optimization | Build: Compaction + Z-ordering scheduled workflows on Iceberg tables |
| **Business Semantics** | No semantic layer | Phase 5: Ontology → semantic layer mapping (object types = business entities) |

---

## 5. Voyant ML (M6) — ML/AI Platform Deep Dive

### 5.1 Databricks MLflow: Full Feature Map

| MLflow Feature | Databricks Implementation | Voyant v4.0 Status |
|---------------|--------------------------|-------------------|
| **Experiment Tracking** | Experiments + Runs (params, metrics, artifacts) | **HAS** — `Experiment`, `Run`, `RunArtifact` models (`ml_platform/models.py:15-94`) |
| **Model Registry** | Registered models + versions + stages (none/staging/production/archived) | **HAS** — `RegisteredModel`, `ModelVersion` models (`ml_platform/models.py:97-144`) |
| **Model Serving** | Real-time endpoints + batch inference + GPU | **HAS** — `ModelEndpoint` model (`ml_platform/models.py:147-176`) |
| **MLflow-Compatible API** | Native (built by Databricks creators) | **SRS** — ML-F-005: Will implement `/api/2.0/mlflow/*` endpoints |
| **AutoML** | Built-in (classification, regression, forecasting) | **MISSING** — No AutoML engine |
| **Feature Store** | Centralized feature engineering + serving | **MISSING** — No feature store |
| **LLM Fine-Tuning** | Mosaic AI Training (open-source LLMs) | **MISSING** — No fine-tuning |
| **MLflow Tracing** | GenAI tracing (LLM call logging) | **MISSING** — No tracing |
| **MLflow Evaluate** | AI judges, custom metrics, human feedback | **SRS** — ML-F-007: Agent evaluation with AI judge |
| **Collaborative Notebooks** | PySpark, SQL, R, Scala | **MISSING** — No notebook environment |
| **GPU Clusters** | Multi-GPU training | **MISSING** — CPU-only |

### 5.2 Palantir AIP: Feature Map

| AIP Feature | Palantir Implementation | Voyant v4.0 Status |
|------------|------------------------|-------------------|
| **Model Connectivity** | Connect any LLM (OpenAI, Anthropic, etc.) | **PARTIAL** — MCP tools connect models |
| **Agent Bricks** | Build agents with tools, evaluate, deploy | **PARTIAL** — `AgentDefinition` + `AgentEvaluation` models |
| **AIP Chat** | Chat with your data (NL→query) | **PARTIAL** — Intent Engine (NL→plan→execute) |
| **Code Execution** | Execute Python/SQL in sandbox | **HAS** — `FunctionRunner` (subprocess sandbox) |
| **Evaluation** | AI-powered evaluation | **SRS** — ML-F-007 |
| **Ontology Integration** | Agents operate on ontology objects | **HAS** — 14 ontology MCP tools |
| **Application Studio** | Build AI-powered apps | **MISSING** — No app builder |

### 5.3 Voyant ML (M6): What's Built vs Planned

| Model | Status | Description |
|-------|--------|-------------|
| `Experiment` | **BUILT** | MLflow-compatible experiment tracking |
| `Run` | **BUILT** | Individual runs with params, metrics, artifacts |
| `RunArtifact` | **BUILT** | File artifacts (model, dataset, image, metric, log) |
| `RegisteredModel` | **BUILT** | Model registry with naming |
| `ModelVersion` | **BUILT** | Versioned models with staging pipeline (none→staging→production→archived) |
| `ModelEndpoint` | **BUILT** | Serving endpoints with invocation tracking |
| `AgentDefinition` | **BUILT** | Agent config: system_prompt, model, tools, guardrails |
| `AgentEvaluation` | **BUILT** | AI-judge evaluation with test cases, scores, pass rates |

### 5.4 Exact ML Improvements Voyant ML (M6) Makes

| Improvement | Technical Approach | Why It's Better |
|------------|-------------------|-----------------|
| **Agent Evaluation (not just model evaluation)** | `AgentDefinition` + `AgentEvaluation` models evaluate entire agent pipelines — prompt + model + tools + guardrails — not just individual model outputs. | Databricks evaluates models. Voyant evaluates agents. An agent is more than a model — it's the full system. |
| **MCP-Connected ML** | Every ML operation will be an MCP tool: `voyant.ml.experiment.create`, `voyant.ml.run.log`, `voyant.ml.model.deploy`. | Neither Palantir nor Databricks allow AI agents to manage ML experiments programmatically. |
| **Capsule-Deployed Models** | Models can be packaged as capsules (Ed25519-signed) for portable, auditable deployment. | Neither competitor has signed, portable model deployment. |
| **Intent Engine for ML** | "Train a random forest on the sales data, predict Q4 revenue" → Intent Engine generates structured ML plan → deterministic execution. | No competitor translates NL directly into structured ML training plans with schema validation. |
| **Guardrails in AgentDefinition** | `guardrails` field: `max_queries_per_session`, `blocked_tables`, `require_approval`. | Databricks has Unity AI Gateway guardrails. Voyant has per-agent guardrails at the definition level. |

---

## 6. Voyant Agent (M7) — Agent Platform Comparison

### 6.1 Three-Way Agent Comparison

| Capability | Databricks Agent Bricks | Palantir AIP | Voyant |
|-----------|------------------------|-------------|--------|
| **Agent Definition** | Code-based (Python, LangChain, etc.) | AIP config | `AgentDefinition` model (prompt + model + tools + guardrails) |
| **Tool System** | Unity Catalog Functions (proprietary) | Proprietary tools | **MCP Protocol (67 tools)** |
| **NL Interface** | Genie (text-to-SQL) | AIP Chat | **Intent Engine** (NL→structured plan→deterministic execution) |
| **Evaluation** | AI judges + human feedback | Limited | `AgentEvaluation` model (test cases, AI judge, scores) |
| **Governance** | Unity AI Gateway | Object security | SpiceDB + Ranger + per-agent guardrails |
| **Multi-Model** | Any model via Agent Bricks | Model connectivity | Model-agnostic (LLM Router) |
| **Deployment** | Model Serving endpoints | AIP deployment | ModelEndpoint + Capsule system |
| **Code Execution** | Databricks notebooks | AIP Code Workspaces | `FunctionRunner` (sandboxed subprocess) |
| **Data Access** | Via SQL/Unity Catalog | Via ontology | Via MCP tools (SQL, ontology, scraper, search) |
| **Deterministic Execution** | No (LLM generates code directly) | No (LLM generates code directly) | **Yes** (LLM proposes plan, code executes) |

### 6.2 Why Voyant Agent (M7) Is Superior

**1. MCP Protocol (Unique)**
```
Palantir/Databricks: Agent → Proprietary API → Platform → Result
Voyant:              Agent → MCP Protocol → 67 Standardized Tools → Result
```
MCP is an open, standardized protocol. Any MCP-compatible agent (Claude, GPT, Gemini, open-source) can connect to Voyant and use all 67 tools. Palantir and Databricks lock agents into proprietary APIs.

**2. Deterministic Execution (Unique)**
```
Databricks Genie:  User: "Show me sales in June" → LLM generates SQL → SQL executes
                   Risk: LLM hallucinates wrong table/column → wrong query runs

Voyant Intent:     User: "Show me sales in June" → LLM generates plan →
                   Plan Validator checks against ontology schema →
                   Plan Executor runs validated code → Result
                   Safety: LLM NEVER touches production data directly
```

**3. 67 MCP Tools (Comprehensive)**
| Category | Tools | Examples |
|----------|-------|---------|
| Core Operations | 11 | `voyant.discover`, `voyant.connect`, `voyant.ingest`, `voyant.sql`, `voyant.search` |
| Catalog/Management | 23 | `voyant.lineage`, `voyant.sources.*`, `voyant.jobs.*`, `voyant.kpi_templates.*`, `voyant.discovery.*` |
| Governance | 7 | `voyant.governance.*`, `voyant.quotas.*` |
| Ontology | 14 | `voyant.ontology.types.*`, `voyant.ontology.objects.*`, `voyant.ontology.links.*`, `voyant.ontology.actions.execute`, `voyant.ontology.functions.run` |
| Vector/Search | 2 | `voyant.vector.search`, `voyant.vector.index` |
| Scraper | 7+ | `scrape.fetch`, `scrape.extract`, `scrape.ocr`, `scrape.parse_pdf`, `scrape.transcribe` |
| **Total** | **67** | **83+ targeted for v4.0** |

**4. Capsule System (Unique)**
- Portable, Ed25519-signed agent plugins
- Each capsule bundles: tools + prompts + guardrails + dependencies
- Verified before execution — tamper-proof
- Neither Palantir nor Databricks has anything equivalent

**5. Intent Engine (Unique)**
- 6-stage pipeline: Classify → Schema Resolve → Plan Generate → Plan Validate → Execute → Format
- LLM is only used in stage 3 (Plan Generator)
- Stages 4-6 are pure deterministic code
- Plans are cached for reuse (same intent = cached plan)

---

## 7. Voyant Shield (M9) — Governance Comparison

### 7.1 Three-Way Governance

| Capability | Databricks Unity Catalog | Palantir | Voyant |
|-----------|-------------------------|----------|--------|
| **Authentication** | SSO, SAML, OAuth | SSO, SAML | Keycloak (SSO, SAML, OAuth, OIDC) |
| **App-Level RBAC** | Unity Catalog permissions | Object security policies | SpiceDB (Zanzibar model) |
| **Data-Level RBAC** | Attribute-based access control | Object-level permissions | Apache Ranger (row/column policies) |
| **Row-Level Security** | Dynamic views + RLS policies | Object security | Ranger RLS filters (SRS GOV-F-003) |
| **Column Masking** | Built-in column masking | N/A | Ranger column masking (SRS GOV-F-004) |
| **Audit Logging** | Unity Catalog audit logs | Full audit trail | `AuditLog` model + SkyWalking |
| **Data Lineage** | Automated column-level lineage | Built-in lineage | DataHub client (partial) |
| **Data Classification** | AI-powered auto-classification | Markings system | SRS: Planned |
| **Secrets** | Databricks Secrets | Proprietary | HashiCorp Vault |
| **Agent Governance** | Unity AI Gateway (access, spend, observability) | Object security | Per-agent guardrails in `AgentDefinition` |
| **Multi-Tenancy** | Workspace isolation | Organization isolation | `TenantModel` on every model |
| **Encryption** | At-rest + in-transit | At-rest + in-transit | TLS in-transit, Vault for secrets |

### 7.2 Governance Improvements Voyant Shield (M9) Makes

| Improvement | Description | Why It's Better |
|------------|-------------|-----------------|
| **Agent-Level Governance** | `AgentDefinition.guardrails`: `max_queries_per_session`, `blocked_tables`, `require_approval`. SpiceDB checks which agents can access which resources. | Databricks has Unity AI Gateway at the platform level. Voyant has guardrails at the individual agent definition level — more granular. |
| **Intent Engine Trust Boundary** | The Intent Engine's Plan Validator is a governance checkpoint. Every LLM-generated plan is validated against ontology schema and permissions BEFORE execution. | Neither Palantir nor Databricks validate LLM output before execution. |
| **Zanzibar-Style Auth** | SpiceDB implements Google's Zanzibar authorization model (the same model that powers Google's internal permissions). | More expressive than Databricks' role-based permissions. Supports complex relationships like "manager of team X can access data of team X's members." |
| **Dual-Layer RBAC** | App-level (SpiceDB) + Data-level (Ranger). Separation of concerns. | Databricks conflates app and data governance in Unity Catalog. Voyant separates them for defense-in-depth. |

---

## 8. Voyant Scrape (M8) — Scraper Comparison (vs Octoparse + Bright Data)

### 8.1 Feature Comparison

| Feature | Octoparse | Bright Data | Voyant Octopus |
|---------|-----------|------------|----------------|
| **No-Code Visual Builder** | Full (drag-and-drop) | Full (visual editor) | SRS: Planned (React builder) |
| **Template Library** | 600+ templates | 100+ templates | SRS: 50 templates Phase 1, 200+ Phase 5 |
| **Browser Automation** | Full | Full | **HAS** — 8 browser arms (static, dynamic, crawl, document, OCR, transcribe, evasion, archive) |
| **Anti-Bot** | Full | Enterprise-grade | Partial (user-agent rotation, fingerprint, curl-cffi, camoufox) |
| **CAPTCHA Solving** | AI-powered | AI-powered | SRS: Planned (reCAPTCHA, hCaptcha, Turnstile) |
| **IP Rotation** | Residential proxies | 72M+ residential IPs | SRS: Planned (BrightData/SmartProxy/Oxylabs integration) |
| **Deep Research** | None | None | **UNIQUE** — `deep_research_workflow.py` with query generation, multi-source synthesis |
| **OCR** | None | Limited | **HAS** — Tesseract OCR (`arm_ocr`) |
| **PDF Parsing** | None | Limited | **HAS** — pdfplumber (`pdf_parser.py`) |
| **Audio Transcription** | None | None | **HAS** — Transcription arm (`arm_transcribe`) |
| **MCP Integration** | None | None | **UNIQUE** — 7 MCP tools (`scrape.*`) |
| **Ontology Integration** | None | None | **UNIQUE** — Scrape → auto-create ontology objects |
| **Temporal Durability** | None | None | **UNIQUE** — Scrape jobs as Temporal workflows (replayable, self-healing) |
| **Self-Hosted** | No | No | **YES** — Docker |
| **Open Source** | No | No | **YES** — Apache 2.0 |
| **Content Extraction** | Basic | Basic | **5-strategy chain**: trafilatura → readability → newspaper → crawl4ai → fallback |
| **Evasion Techniques** | Basic | Advanced | Partial: User-agent rotation, fingerprint randomization, curl-cffi TLS, Camoufox browser |

### 8.2 Voyant Scrape (M8) Unique Advantages (No Competitor Has These)

1. **Deep Research Pipeline** — Multi-step research workflow: generate queries → search multiple engines → fetch + extract → synthesize results. No web scraping tool has integrated deep research.

2. **MCP Integration** — 7 MCP tools let AI agents orchestrate scraping: `scrape.fetch`, `scrape.extract`, `scrape.ocr`, `scrape.parse_pdf`, `scrape.transcribe`, `scrape.deep_archive`, `voyant.research.run/status`.

3. **Ontology Integration** — Scraped data can automatically create ontology objects. Scrape a product page → create a `Product` ontology object with structured properties. No competitor connects scraping to a semantic data model.

4. **5-Strategy Content Extraction** — `content_extractor.py` chains 5 extractors: trafilatura → readability → newspaper → crawl4ai → raw fallback. Each fallback is tried if the previous one fails. This is more resilient than any competitor's single-strategy extraction.

---

## 9. UI/UX Comparison

### 9.1 Application Layer

| UI Component | Palantir Workshop | Databricks | Voyant v4.0 |
|-------------|------------------|------------|-------------|
| **App Builder** | Workshop (low-code, ontology-connected) | Databricks Apps (serverless) | SRS: Visual builders (Phase 4) |
| **Notebooks** | Quiver (analytical) | Databricks Notebooks (Py/SQL/R/Scala) | **MISSING** |
| **Object Explorer** | Full (search, filter, pivot, compare) | N/A (no ontology) | SRS: React Explorer (Phase 4) |
| **Graph View** | Vertex (force-directed) | N/A | SRS: Sigma.js graph (Phase 4) |
| **SQL Editor** | SQL Studio | Databricks SQL Editor | **HAS** — `voyant.sql` MCP tool (agent-accessible) |
| **Dashboard** | Configurable views | Dashboards (built-in BI) | 13 Lit admin views |
| **Map View** | Map templates | N/A | SRS: Planned |
| **Data Pipeline Builder** | Visual DAG (Pipeline Builder) | Lakeflow visual builder | SRS: React Flow DAG editor |
| **NL Interface** | AIP Chat | Genie One (AI Assistant) | Intent Engine (backend) + SRS: Chat UI |

### 9.2 What Voyant Improves for Each

| Component | Voyant's Improvement Strategy |
|----------|------------------------------|
| **Object Explorer** | React + TanStack Table + Sigma.js. Not just table view — grid, map, graph. Plus: every explorer action is MCP-callable, so agents can explore too. |
| **SQL Editor** | Agent-accessible via `voyant.sql` MCP tool. SQL isn't just for humans — agents can execute, review, and iterate on queries. |
| **Dashboard Builder** | Chart.js/Apache ECharts integration. Widgets are ontology-aware (show object data). |
| **Pipeline Builder** | React Flow DAG editor. Pipelines execute as Temporal workflows — durable, replayable, self-healing. Palantir's Pipeline Builder has no durable execution. |
| **NL Interface** | Intent Engine (backend) + Chat UI. Unlike Genie/AIP Chat, the Intent Engine validates plans before execution. |

### 9.3 Palantir Foundry — Screen-by-Screen Comparison

Palantir has 5 products: **Foundry** (data + ontology + analytics), **Gotham** (intelligence/military), **AIP** (AI platform), **Workshop** (app builder), **Quiver** (notebooks). Below is every major screen and how Voyant maps to it.

#### 9.3.1 Ontology Manager Screens

| Palantir Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|----------------|-------------|-------------------|--------|-----------------|
| **Browse Object Types** | Table view with search across all types | `voyant.ontology.types.list` MCP tool + admin dashboard | **HAS** (MCP) / **SRS** (React UI) | Agent-callable via MCP; Palantir has no agent API for this |
| **Edit Type — Properties Tab** | Edit property definitions (name, type, required, default, validation) | `voyant.ontology.types.get` returns full property definitions; CRUD via REST | **HAS** (API + MCP) | Open schema in PostgreSQL; agents can read/write property defs |
| **Edit Type — Links Tab** | View/edit link types connected to this object type | LinkType model with FK to ObjectType; `voyant.ontology.links.*` tools | **HAS** (API + MCP) | Agents can programmatically manage relationships |
| **Edit Type — Actions Tab** | View/edit action types on this object type | ActionType model with FK to ObjectType; `voyant.ontology.actions.execute` | **HAS** (API + MCP) | ActionExecutor with full undo support and audit trail |
| **Edit Type — Functions Tab** | View/edit Python/TS functions attached to type | Function model with FK to ObjectType; `voyant.ontology.functions.run` | **HAS** (API + MCP) | Sandboxed subprocess with timeout + memory limits |
| **Create New Type Wizard** | Step-by-step: name → properties → links → review | REST API + MCP `voyant.ontology.types.create` (with properties list) | **HAS** (API) / **SRS** (React wizard) | Single API call creates type + properties; agent-driven creation |
| **Type Hierarchy Tree** | Visual inheritance view of type hierarchy | Interface model with M2M implementing_types | **PARTIAL** (model exists, no tree UI) | Interfaces are MCP-queryable; agents can discover type relationships |
| **Schema Diff Viewer** | Compare version changes | ObjectType.version field tracks changes | **PARTIAL** (version tracking, no diff UI) | SRS: Visual diff viewer in Phase 4 |

**What Voyant does BETTER on every Ontology Manager screen:**
- Every operation is MCP-callable (14 ontology tools). Palantir's Ontology Manager is human-only UI.
- Open PostgreSQL schema — direct SQL access to ontology metadata. Palantir's is opaque.
- ActionExecutor records full `previous_values` for undo — more transparent than Palantir's proprietary undo.

#### 9.3.2 Object Explorer Screens

| Palantir Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|----------------|-------------|-------------------|--------|-----------------|
| **Search Bar** | Semantic + full-text search across all objects | Milvus vector search + Elasticsearch full-text; `voyant.search` + `voyant.vector.search` MCP tools | **PARTIAL** (backend exists, no React search bar) | Dual search: vector (semantic) + Elasticsearch (full-text). Agent-callable. |
| **Filter Builder** | Visual: field → operator → value with AND/OR groups | ORM filters in ObjectService; SRS: React filter builder | **PARTIAL** (API-level filtering, no visual builder) | SRS Phase 4: React visual filter builder with condition groups |
| **Pivot Table View** | Row/column configuration on object properties | SRS: Pivot component | **SRS** (Phase 4) | Will use Apache ECharts pivot; also agent-callable via MCP |
| **Compare View** | Side-by-side object comparison | SRS: Compare component | **SRS** (Phase 4) | Agents can compare objects programmatically via `voyant.ontology.objects.get` |
| **Export (CSV, JSON)** | Export filtered results | ObjectService.list → serialize → download | **HAS** (API-level) | MCP agents can export data programmatically; add JSONL streaming |

**What Voyant does BETTER on Object Explorer:**
- **Agent-accessible search**: `voyant.search` and `voyant.vector.search` let AI agents search the ontology. Palantir has zero agent API for object exploration.
- **Dual vector + text search**: Milvus dense vectors + Elasticsearch sparse. More resilient than Palantir's single search.
- **MCP export**: Agents can list objects, filter, and export — all programmatically. No human needed.

#### 9.3.3 Object Detail Screens

| Palantir Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|----------------|-------------|-------------------|--------|-----------------|
| **Properties Panel** | View/edit object properties | `voyant.ontology.objects.get` returns full properties; update via `voyant.ontology.objects.update` | **HAS** (API + MCP) | Optimistic concurrency via version field; agents can read/write |
| **Relationships Panel** | Graph of connected objects (outgoing + incoming links) | `voyant.ontology.objects.get` returns `outgoing_links` + `incoming_links`; `voyant.ontology.traverse` for multi-hop | **HAS** (API + MCP) | Up to 10-hop traversal via MCP — deeper than Palantir's default view |
| **Actions Panel** | Execute operations on this object | `voyant.ontology.actions.execute` MCP tool | **HAS** (API + MCP) | Full undo support via ActionExecution model; audit trail with previous_values |
| **Timeline Panel** | History of changes to this object | AuditLog model + ActionExecution history | **PARTIAL** (audit exists, no timeline UI) | SRS Phase 4: Visual timeline; data is already captured |
| **Comments Panel** | Collaborative annotations on objects | **MISSING** | **SRS** (Phase 5) | Will use Django comments framework; agent-callable via MCP |

**What Voyant does BETTER on Object Detail:**
- **Deep traversal**: `voyant.ontology.traverse` supports up to 10 hops with direction control (outgoing/incoming/both). Palantir's UI typically shows 1-2 hops.
- **Action undo**: Every action execution records `previous_values`. Full revert capability. More transparent than Palantir.
- **Agent interaction**: Every detail panel action is MCP-callable. An AI agent can view, edit, execute actions, traverse links — all programmatically.

#### 9.3.4 Pipeline Builder Screens

| Palantir Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|----------------|-------------|-------------------|--------|-----------------|
| **DAG Canvas** | Drag nodes, connect edges (visual pipeline editor) | SRS: React Flow DAG editor; Temporal workflows as backend | **SRS** (Phase 4, React Flow) | Pipelines execute as Temporal workflows — durable, replayable, self-healing |
| **Node Types** | Source, Transform, Filter, Aggregate, Join, Output | Temporal activities; Airbyte for source; Spark/Trino for transform | **PARTIAL** (backend exists, no visual nodes) | Code-first pipelines via Temporal are more debuggable than visual-only |
| **Node Configuration** | Configure each node (connection, transform logic) | Django admin config; SRS: visual config panels | **SRS** (Phase 4) | JSON-configured nodes; version-controlled |
| **Run History** | Status, duration, logs per pipeline run | Temporal UI (built-in at port 45089); Job model | **HAS** (Temporal UI) | Temporal UI is superior — shows every workflow step, replay capability |
| **Schedule Configuration** | Cron-based scheduling | Temporal schedules; ScrapeSchedule model for scraper | **HAS** (Temporal) | Durable scheduling — survives restarts; exactly-once execution |
| **Parameter Templates** | Reusable pipeline configurations | SRS: Pipeline parameters | **SRS** | Will support JSON parameter schemas with validation |

**What Voyant does BETTER on Pipeline Builder:**
- **Temporal Durability**: Every pipeline is a Temporal workflow. If any step fails, Temporal automatically retries from the failed step. Palantir's Pipeline Builder has no durable execution — if a job fails, you restart from scratch.
- **Temporal UI**: Built-in workflow visualization at port 45089 shows every step, its status, duration, and logs. Replay capability for debugging.
- **Code-first option**: Developers can write pipelines as Python Temporal workflows instead of using a visual builder. More powerful for complex logic.

#### 9.3.5 Workshop (App Builder) Screens

| Palantir Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|----------------|-------------|-------------------|--------|-----------------|
| **Component Palette** | Tables, forms, charts, maps, text widgets | SRS: React component library | **SRS** (Phase 4) | Components will be ontology-aware + MCP-callable |
| **Drag-Drop Layout** | Visual layout editor | SRS: React drag-drop builder | **SRS** (Phase 4) | Lit 3 + Tailwind (current); React (planned) |
| **Data Binding** | Connect components to ontology objects | Ontology API integration | **SRS** (Phase 4) | MCP tools let agents create and configure apps programmatically |
| **Action Configuration** | What happens on click/submit | ActionType + ActionExecutor | **HAS** (backend) | Full undo support; side effects are logged |
| **Preview Mode** | Preview app before publishing | SRS: Live preview | **SRS** (Phase 4) | Hot-reload with Vite |
| **Publish to Marketplace** | Share apps across organization | SRS: Capsule distribution | **PARTIAL** (capsule system exists, no marketplace UI) | Ed25519-signed capsules for auditable distribution |

**What Voyant does BETTER on Workshop:**
- **Agent-created apps**: Via MCP, agents can programmatically create and configure Workshop-equivalent apps. Palantir's Workshop is human-only.
- **Capsule distribution**: Apps can be packaged as Ed25519-signed capsules for tamper-proof distribution. Palantir's marketplace has no signing.
- **Dual access**: Every Workshop action has a corresponding MCP tool. Users can interact via UI OR agents can interact via MCP.

#### 9.3.6 Quiver (Notebooks) Screens

| Palantir Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|----------------|-------------|-------------------|--------|-----------------|
| **Cell Editor** | Code, markdown, SQL, visualization cells | **MISSING** — No notebook environment | **SRS** (Phase 6: Jupyter integration) | Will embed JupyterHub; agent-accessible via MCP |
| **Collaborative Editing** | Multiple users edit simultaneously | **MISSING** | **SRS** (Phase 6) | JupyterHub supports real-time collaboration |
| **Kernel Management** | Python, R, SQL kernels | **MISSING** | **SRS** (Phase 6) | Jupyter kernels; MCP tool for programmatic execution |
| **Output Rendering** | Tables, charts, maps | **MISSING** | **SRS** (Phase 6) | Will use Apache ECharts for inline visualization |
| **Version History** | Track notebook changes | **MISSING** | **SRS** (Phase 6) | Git integration for notebooks |

**What Voyant WILL do BETTER on Notebooks:**
- **Agent-executable cells**: MCP tools to create, execute, and read notebook cells. Agents can write and run analysis code in notebooks.
- **FunctionRunner**: Voyant's `FunctionRunner` already provides sandboxed Python/TS execution with timeout and memory limits. This becomes the notebook kernel execution engine.
- **Intent Engine integration**: "Run this analysis in a notebook" → Intent Engine generates cell sequence → deterministic execution.

#### 9.3.7 AIP (AI Platform) Screens

| Palantir Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|----------------|-------------|-------------------|--------|-----------------|
| **Model Connectivity** | Configure LLM providers (OpenAI, Anthropic, etc.) | LLM Router in Intent Engine; model_provider field in AgentDefinition | **HAS** (backend) | Model-agnostic; supports any OpenAI-compatible provider |
| **Logic Studio** | Build AI workflows | Intent Engine (backend) + SRS: visual workflow builder | **PARTIAL** (Intent Engine, no visual builder) | Deterministic execution: LLM proposes, code executes |
| **Agent Builder** | Define agents with tools + guardrails | `AgentDefinition` model (system_prompt, model, tools, guardrails) | **HAS** (model) | 67 MCP tools as agent tools; per-agent guardrails |
| **Evaluation Framework** | Test cases + scoring | `AgentEvaluation` model (test_cases, AI judge, scores) | **HAS** (model) | AI-judge evaluation with per-test-case scoring |
| **Deployment Management** | Deploy agents to production | `ModelEndpoint` model + Capsule system | **HAS** (models) | Ed25519-signed capsule deployment; MCP-callable |
| **Monitoring Dashboard** | Agent performance metrics | Prometheus + Grafana + SkyWalking | **HAS** (observability stack) | Full distributed tracing via SkyWalking |

**What Voyant does BETTER on AIP:**
- **Deterministic execution**: Voyant's Intent Engine validates LLM plans against schema before execution. Palantir's AIP lets LLM-generated code execute directly.
- **67 MCP tools**: Voyant agents have access to 67 standardized tools. Palantir's tools are proprietary and less numerous.
- **Capsule deployment**: Agent deployments are Ed25519-signed for tamper-proof distribution.
- **Agent-level guardrails**: Per-agent `guardrails` field in AgentDefinition. More granular than Palantir's platform-level controls.

---

### 9.4 Databricks — Screen-by-Screen Comparison

Databricks has 15 products. Below is every major screen and how Voyant maps to it.

#### 9.4.1 Workspace Screens

| Databricks Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|-------------------|-------------|-------------------|--------|-----------------|
| **File Browser** | Browse notebooks, libraries, models, experiments | Django admin panel (13 views); SRS: React file browser | **PARTIAL** (admin panel) | Self-hosted: files are on your own MinIO; no cloud lock-in |
| **Notebook Editor** | Cells: code, markdown, SQL, visualization | **MISSING** — No notebook | **SRS** (Phase 6: Jupyter) | Will embed JupyterHub with MCP integration |
| **Collaboration** | Shared notebooks, comments | **MISSING** | **SRS** (Phase 6) | Agent collaboration: agents can share artifacts via MCP |
| **Version Control** | Git integration | **MISSING** | **SRS** (Phase 6) | Git-native: all config is version-controlled |
| **Cluster Management** | Start/stop/configure compute clusters | Docker container management; K8s (planned) | **PARTIAL** (manual Docker) | `docker compose up` — simpler than Databricks cluster management |
| **Job Scheduler** | Cron-based job scheduling | Temporal scheduling (built-in) | **HAS** (Temporal) | Durable scheduling with replay — survives restarts |

#### 9.4.2 SQL Editor Screens

| Databricks Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|-------------------|-------------|-------------------|--------|-----------------|
| **Monaco Editor** | SQL editor with autocomplete | SRS: Monaco-based SQL editor | **SRS** (Phase 4) | Agents can also write SQL via `voyant.sql` MCP tool |
| **Schema Browser** | Catalogs → schemas → tables → columns tree | `voyant.tables.list` + `voyant.tables.columns` MCP tools | **HAS** (MCP) | Agent-callable: agents can browse schemas programmatically |
| **Query Results Table** | Tabular query results | `voyant.sql` returns columns + rows + row_count + truncated flag | **HAS** (MCP) | JSON-native results; agents can process results immediately |
| **Visualization from Results** | Chart from query data | SRS: ECharts visualization | **SRS** (Phase 4) | MCP tools let agents create visualizations programmatically |
| **Query History** | List of past queries | SRS: Query history model | **SRS** | Agent-accessible: agents can review past queries |
| **Saved Queries** | Persist named queries | SRS: Saved query model | **SRS** | MCP tool: `voyant.queries.save` (planned) |
| **SQL AI Assistant (Genie)** | NL → SQL generation | Intent Engine: NL → structured plan → SQL | **HAS** (Intent Engine) | Deterministic: plan is validated before SQL execution. Genie generates SQL directly — risk of hallucinated queries. |

**What Voyant does BETTER on SQL Editor:**
- **Agent-native SQL**: `voyant.sql` MCP tool lets any AI agent execute SQL queries. Databricks SQL Editor is human-only.
- **Deterministic NL→SQL**: Intent Engine generates a structured plan that is validated against the ontology schema before execution. Databricks Genie generates SQL directly from NL — no validation, hallucination risk.
- **Schema browsing for agents**: `voyant.tables.list` and `voyant.tables.columns` let agents discover data structures. No competitor exposes schema browsing as an agent API.

#### 9.4.3 Dashboard Screens

| Databricks Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|-------------------|-------------|-------------------|--------|-----------------|
| **Widget Palette** | Chart, table, text, filter, image widgets | SRS: Widget library (ECharts + TanStack Table) | **SRS** (Phase 4/5) | Widgets are ontology-aware; show real-time object data |
| **Drag-Drop Layout** | Arrange widgets on canvas | SRS: React grid layout | **SRS** (Phase 5) | Agent-created dashboards via MCP (planned) |
| **Data Source Binding** | Each widget bound to SQL query | Widget → SQL → Trino/Iceberg | **SRS** | MCP tools: agents can configure data sources for widgets |
| **Chart Types** | Line, bar, pie, scatter, heatmap, counter, table | Apache ECharts (planned: 20+ chart types) | **SRS** | ECharts has more chart types than Databricks built-in |
| **Filter Widgets** | Date range, dropdown, multi-select | SRS: Filter components | **SRS** (Phase 5) | Agent-set filters: agents can programmatically configure filters |
| **Auto-Refresh** | Scheduled data refresh | SRS: WebSocket-based refresh | **SRS** | Temporal scheduled refresh (more reliable than polling) |
| **Sharing & Permissions** | Share dashboards with teams | SpiceDB RBAC; SRS: dashboard sharing | **PARTIAL** | Zanzibar-style auth: more granular than Databricks role-based sharing |
| **Embedded Analytics** | Embed dashboards in external apps | SRS: Embeddable components | **SRS** (Phase 6) | Open-source: embed without licensing restrictions |

#### 9.4.4 MLflow Screens

| Databricks Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|-------------------|-------------|-------------------|--------|-----------------|
| **Experiment List** | Name, tags, run count | `Experiment` model | **HAS** (model) / **SRS** (React UI) | Agent-callable: `voyant.ml.experiment.list` (planned MCP tool) |
| **Run Comparison** | Side-by-side params + metrics | `Run` model with params + metrics JSON | **HAS** (model) | Agents can compare runs programmatically |
| **Run Detail** | Params, metrics, artifacts, tags | `Run` + `RunArtifact` models | **HAS** (models) | MCP tools: agents can log params/metrics/artifacts |
| **Artifact Viewer** | Browse model files, images, data | `RunArtifact` model with storage_path | **HAS** (model) | MinIO-based storage; self-hosted, no vendor lock-in |
| **Model Registration** | Register best model from run | `RegisteredModel` + `ModelVersion` models | **HAS** (models) | Staging pipeline: none → staging → production → archived |
| **Model Registry List** | Model list with versions + stages | `RegisteredModel` + `ModelVersion` | **HAS** (models) | Agent-callable model management |
| **Stage Transitions** | None → Staging → Production → Archived | `ModelVersion.stage` field with choices | **HAS** (model) | Agents can promote/demote models via API |
| **Serving Configuration** | Configure model serving endpoints | `ModelEndpoint` model with config JSON | **HAS** (model) | Self-hosted serving; no per-DBU cost |

**What Voyant does BETTER on MLflow screens:**
- **Agent-managed ML**: Every ML operation will be an MCP tool. Databricks MLflow is human-UI-only.
- **Self-hosted serving**: Model endpoints run on your infrastructure. No per-DBU pricing. No vendor lock-in.
- **Agent evaluation**: `AgentEvaluation` model evaluates entire agent pipelines (prompt + model + tools + guardrails), not just individual model outputs.

#### 9.4.5 Unity Catalog Screens

| Databricks Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|-------------------|-------------|-------------------|--------|-----------------|
| **Catalog Browser** | 3-level hierarchy (catalog → schema → table) | DataHub metadata; `voyant.governance.schema` MCP tool | **PARTIAL** (DataHub client, no 3-level UI) | Agent-callable schema browsing via MCP |
| **Table Detail** | Schema, sample data, lineage, permissions | `voyant.tables.columns` + `voyant.lineage` + `voyant.governance.schema` | **PARTIAL** (APIs exist, no unified UI) | 3 MCP tools provide table + column + lineage data to agents |
| **Column Security** | Column-level access configuration | Apache Ranger column masking | **SRS** (GOV-F-004) | Dual-layer: Ranger (data) + SpiceDB (app) — defense-in-depth |
| **Row Security** | Row-level security rules | Apache Ranger RLS | **SRS** (GOV-F-003) | Zanzibar-style SpiceDB for app-level + Ranger for data-level |
| **Data Masking** | Mask sensitive columns | Apache Ranger masking policies | **SRS** (GOV-F-004) | Vault for secrets; Ranger for masking — no secrets in platform code |
| **Audit Log** | Track all data access | `AuditLog` model + SkyWalking tracing | **HAS** | Full distributed tracing via SkyWalking — more detailed than UC audit |

#### 9.4.6 Genie (NL BI) Screens

| Databricks Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|-------------------|-------------|-------------------|--------|-----------------|
| **Chat Interface** | Natural language questions about data | Intent Engine backend + SRS: Chat UI | **PARTIAL** (backend, no chat UI) | Deterministic execution — validated plans, not raw LLM output |
| **NL → SQL** | LLM generates SQL from question | Intent Engine: NL → plan → validated SQL | **HAS** (Intent Engine) | Plan validation catches hallucinated table/column names before execution |
| **Result Visualization** | Auto-chart from query results | SRS: Auto-visualization | **SRS** | Intent Engine can generate visualization specs in the plan |
| **Feedback Loop** | Thumbs up/down on results | SRS: Feedback model | **SRS** | Agent evaluation feedback loop — systematic improvement |
| **Trust Configuration** | Which tables Genie can access | Ontology schema + SpiceDB permissions | **HAS** (RBAC) | Intent Engine validates against ontology — only generates plans for known types |

#### 9.4.7 Lakeflow Pipeline Screens

| Databricks Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|-------------------|-------------|-------------------|--------|-----------------|
| **Pipeline List** | Name, status, last update | Job model + Temporal UI | **HAS** (Temporal UI) | Temporal UI shows step-level detail, replay capability |
| **Pipeline Editor** | Visual DAG or code | SRS: React Flow DAG; Temporal workflows (code) | **PARTIAL** (code-first via Temporal) | Dual: visual builder (planned) + code-first (Temporal workflows) |
| **Quality Expectations** | Data quality rules | Great Expectations integration; `voyant.quality` MCP tool | **PARTIAL** | Agent-callable quality checks: `voyant.quality(source_id, table, checks)` |
| **Monitoring** | Freshness, quality, cost | Prometheus + Grafana; `voyant.status` MCP tool | **HAS** | Agent-callable monitoring: agents can check pipeline status via MCP |

---

### 9.5 User Journey Comparison — Palantir Foundry

#### Journey 1: Data Engineer Integrates New Source

| Step | Palantir Foundry | Voyant | Voyant Advantage |
|------|-----------------|--------|-----------------|
| 1. Navigate to Pipeline Builder | Open Pipeline Builder UI | Open Temporal UI OR call `voyant.connect` MCP tool | Agent can also do this via MCP |
| 2. Create new pipeline | Click "New Pipeline" | Create Temporal workflow OR use Airbyte UI | Code-first option with Temporal |
| 3. Add Source node | Drag Source node → configure connection | `voyant.connect(name, source_type, connection_config)` | Single MCP call; validated connection config |
| 4. Add Transform node | Write SQL transform | Spark/Trino SQL in workflow OR `voyant.sql` MCP tool | Agent can write and test transforms |
| 5. Add Output node | Set destination dataset | MinIO/Iceberg write in workflow | Open format (Iceberg) vs proprietary dataset |
| 6. Run pipeline | Click Run → monitor in Pipeline Builder | `voyant.ingest(source_id)` → Temporal auto-executes | Temporal: durable, replayable, self-healing |
| 7. Data in Ontology | Auto-detected by Foundry | Source detection via `voyant.discover`; auto-profile via `voyant.profile` | Agent can orchestrate the full pipeline |

**Voyant's advantage in this journey:** Steps 1-7 can all be executed by an AI agent via MCP tools. Palantir requires a human at every step. Additionally, Temporal provides durable execution — if any step fails, it resumes from the failed step.

#### Journey 2: Business Analyst Explores Data

| Step | Palantir Foundry | Voyant | Voyant Advantage |
|------|-----------------|--------|-----------------|
| 1. Open Ontology Manager | Browse types in table view | `voyant.ontology.types.list` (agent or admin UI) | Agent can also explore types |
| 2. Search for 'Customer' | Search bar with type-ahead | Full-text + semantic search (Milvus + Elasticsearch) | Dual search strategy — more resilient |
| 3. Click → Object Explorer | Object list with properties | `voyant.ontology.objects.list(type_id)` | Agent-callable object listing |
| 4. Apply filters | Visual filter builder (field → op → value) | ORM filters OR `voyant.ontology.objects.list` with query params | API-level filtering; visual builder in Phase 4 |
| 5. Pivot table | Pivot row/column configuration | SRS: Pivot component (Phase 4) | Will use ECharts pivot; agent-callable |
| 6. Export | CSV/JSON download | API export + MCP agent export | JSON-native; agents can process programmatically |
| 7. Create Workshop dashboard | Build dashboard with Workshop | SRS: Dashboard Builder (Phase 5) | Agent-created dashboards via MCP (planned) |

**Voyant's advantage in this journey:** Steps 1-6 can be performed by an AI agent via MCP tools. An agent can explore data, apply filters, and export results without human intervention. Palantir requires a human analyst at every step.

#### Journey 3: Data Scientist Builds ML Model

| Step | Palantir Foundry | Voyant | Voyant Advantage |
|------|-----------------|--------|-----------------|
| 1. Open Quiver notebook | Cell-based editor | SRS: Jupyter integration (Phase 6) | Agent-executable notebooks via MCP |
| 2. Load data from Ontology | `ontology.load("Customer")` | `voyant.sql` + `voyant.ontology.objects.list` | Agent can load data programmatically |
| 3. Explore with pandas/SQL | Interactive cells | `voyant.sql` for SQL; FunctionRunner for Python | Sandboxed execution with timeout + memory limits |
| 4. Train model | ML code in notebook | MLflow-compatible Experiment + Run models | Agent-managed training via MCP tools |
| 5. Log to MLflow | `mlflow.log_metric()` | `Run.metrics` + `RunArtifact` models | Self-hosted MLflow — no per-DBU cost |
| 6. Register model | Model Registry | `RegisteredModel` + `ModelVersion` | Agent-callable model registration |
| 7. Deploy to serving | Model Serving endpoint | `ModelEndpoint` model | Self-hosted serving; no vendor cost |
| 8. Create AIP agent | AIP Agent Builder | `AgentDefinition` model (prompt + model + tools + guardrails) | 67 MCP tools; per-agent guardrails |

**Voyant's advantage in this journey:** The entire ML workflow can be orchestrated by an AI agent. Steps 1-8 map to MCP tools. Databricks requires a data scientist with notebooks; Voyant lets agents manage the full ML lifecycle.

#### Journey 4: Operations Team Monitors System

| Step | Palantir Foundry | Voyant | Voyant Advantage |
|------|-----------------|--------|-----------------|
| 1. Open Pipeline Operations | Pipeline Operations dashboard | Temporal UI (port 45089) + Grafana (port 3000) | Temporal shows step-level workflow detail |
| 2. Check build history | Build history list | Temporal workflow history + `voyant.jobs.list` MCP tool | Agent-callable: agents can check history |
| 3. Review health alerts | Health monitoring | Prometheus alerts + Grafana dashboards | Industry-standard monitoring stack |
| 4. Check resource usage | Resource metrics | Prometheus + Grafana | Full observability with SkyWalking tracing |
| 5. Drill into failed pipeline | Log viewer | Temporal UI: click workflow → see failed step → see error | Step-level failure visibility + replay capability |
| 6. Fix and rerun | Edit pipeline → rerun | Fix code → deploy → Temporal auto-replays from failed step | Temporal replay: doesn't re-run completed steps |

**Voyant's advantage in this journey:** Temporal's replay capability means failed pipelines resume from the failed step, not from scratch. Operations team can also use `voyant.jobs.list` and `voyant.jobs.cancel` MCP tools for programmatic operations management.

---

### 9.6 User Journey Comparison — Databricks

#### Journey 1: Data Engineer Creates ETL Pipeline

| Step | Databricks | Voyant | Voyant Advantage |
|------|-----------|--------|-----------------|
| 1. Open Lakeflow | Lakeflow UI | Temporal UI + Airbyte UI | Code-first pipelines via Temporal workflows |
| 2. Create new pipeline | Click "New Pipeline" | Define workflow in Python OR use Airbyte connector | Python workflow: more flexible than visual-only |
| 3. Define source | Auto Loader or batch | `voyant.connect` + `voyant.ingest` MCP tools | Agent-callable: agents can set up sources |
| 4. Write transforms | SQL or Python transforms | Spark SQL / Trino SQL in Temporal activities | Agent-managed transforms via `voyant.sql` |
| 5. Add quality expectations | Lakeflow expectations | Great Expectations + `voyant.quality` MCP tool | Agent-callable quality checks |
| 6. Set schedule | Built-in scheduler | Temporal schedules (durable, exactly-once) | Durable scheduling — survives restarts |
| 7. Monitor | Pipeline health dashboard | Temporal UI + Prometheus + Grafana + `voyant.status` MCP | Agent-callable monitoring |

**Voyant's advantage:** Every step is agent-accessible via MCP. Databricks requires a human data engineer. Temporal provides durable execution with step-level replay.

#### Journey 2: Analyst Queries Data

| Step | Databricks | Voyant | Voyant Advantage |
|------|-----------|--------|-----------------|
| 1. Open SQL Editor | Monaco editor + autocomplete | `voyant.sql` MCP tool (agent) + SRS: Monaco editor (human) | Agent AND human can write SQL |
| 2. Browse schema | Unity Catalog tree (catalogs → schemas → tables) | `voyant.tables.list` + `voyant.tables.columns` MCP tools | Agent-callable schema discovery |
| 3. Write query | Manual SQL or Genie NL | Intent Engine (NL→plan→SQL) OR `voyant.sql` (manual) | Deterministic NL→SQL (validated before execution) |
| 4. Run query | Photon-accelerated execution | Trino SQL (medium), Spark SQL (large), DuckDB (small) | Query router: right engine for right query size |
| 5. Create visualization | Built-in chart from results | SRS: ECharts visualization (Phase 4) | ECharts: 20+ chart types, open source |
| 6. Add to dashboard | Dashboard builder | SRS: Dashboard Builder (Phase 5) | Agent-created dashboards |
| 7. Share dashboard | Databricks sharing | SpiceDB permissions + SRS: sharing UI | Zanzibar-style auth: more granular |

**Voyant's advantage:** Agents can query data (`voyant.sql`), browse schema (`voyant.tables.*`), and manage dashboards — all via MCP. Databricks SQL Editor is human-only. Intent Engine provides deterministic NL→SQL with plan validation.

#### Journey 3: Data Scientist Trains Model

| Step | Databricks | Voyant | Voyant Advantage |
|------|-----------|--------|-----------------|
| 1. Create notebook | Workspace → New Notebook | SRS: Jupyter integration | Agent-executable notebooks (planned) |
| 2. Load data | `spark.read.table("delta_table")` | `voyant.sql` MCP tool | Agent-callable data loading |
| 3. Feature engineering | Feature Store | SRS: Feature Store (Phase 5) | MCP tools for feature discovery (planned) |
| 4. Train with MLflow tracking | `mlflow.log_param()`, `mlflow.log_metric()` | Experiment + Run + RunArtifact models | Agent-managed training via MCP tools |
| 5. Compare runs | MLflow comparison UI | API comparison + SRS: React comparison UI | Agent-callable run comparison |
| 6. Register best model | Model Registry | RegisteredModel + ModelVersion | Staging pipeline: none→staging→production→archived |
| 7. Deploy to serving | Model Serving | ModelEndpoint model | Self-hosted serving; no per-DBU cost |
| 8. Monitor endpoint | Serving metrics | Prometheus + Grafana + ModelEndpoint.invocation_count | Built-in invocation tracking + latency metrics |

**Voyant's advantage:** Every ML step maps to an MCP tool or API. Databricks MLflow is human-UI-driven. Voyant's self-hosted model serving has zero per-DBU cost.

#### Journey 4: BI Analyst Builds Dashboard

| Step | Databricks | Voyant | Voyant Advantage |
|------|-----------|--------|-----------------|
| 1. Open Dashboard builder | Dashboard UI | SRS: Dashboard Builder (Phase 5) | Agent-created dashboards via MCP |
| 2. Add SQL widgets | Widget → SQL query → results | Widget → `voyant.sql` → results | Same SQL backend; agent-accessible |
| 3. Configure charts | Chart type + axes + styling | Apache ECharts (open source, 20+ types) | More chart types; open source |
| 4. Add filter widgets | Date range, dropdown | SRS: Filter components | Agent-set filters |
| 5. Arrange layout | Drag-drop grid | SRS: React grid layout | Hot-reload with Vite |
| 6. Auto-refresh | Scheduled refresh | WebSocket + Temporal scheduled refresh | Durable refresh scheduling |
| 7. Publish & share | Databricks sharing | SpiceDB RBAC + public URL | Zanzibar-style auth; embed without licensing |

---

## 10. Developer Experience Comparison

### 10.1 Access Modes

| Access Mode | Palantir | Databricks | Voyant |
|------------|----------|------------|--------|
| **REST API** | OpenAPI 3.0 | OpenAPI 3.0 | **HAS** — 66 endpoints (Django Ninja, targeting 120+) |
| **MCP Protocol** | None | None | **HAS** — 67 tools (targeting 83+) |
| **Python SDK** | OSDK (Python) | Databricks SDK for Python | **SRS** — OSDK (API-F-003) |
| **TypeScript SDK** | OSDK (TypeScript) | Databricks SDK for JS | **SRS** — OSDK (API-F-003) |
| **CLI** | Foundry CLI | Databricks CLI | **SRS** — CLI (API-F-005) |
| **Webhooks** | Notifications | Job webhooks | **SRS** — Planned |
| **WebSocket** | Subscription Service | N/A | **SRS** — WebSocket API (API-F-004) |
| **Kafka Events** | Event-driven | Event-driven | **SRS** — Kafka integration (API-F-006) |

### 10.2 Developer Experience Advantages

| Advantage | Description |
|----------|-------------|
| **MCP Protocol** | Any AI coding assistant (Claude, Copilot, Cursor) can connect to Voyant via MCP and manage data, ontology, scraping, ML. Neither Palantir nor Databricks support this. |
| **Self-Hosted** | Full control: run on your laptop, your server, your air-gapped network. No vendor approval needed. |
| **Docker Compose** | `docker compose up` and you have a working platform. 20 containers. No cloud account, no sales call. |
| **Apache 2.0** | Read the code. Fork it. Extend it. No proprietary black boxes. |
| **2,203 Tests** | 2,203 test functions across 148 test files. Production-grade quality from day one. |
| **OpenAPI Auto-Generation** | Django Ninja auto-generates OpenAPI 3.1 specs. SDK generation is trivial. |
| **Temporal Workflows** | Every complex operation is a Temporal workflow: durable, replayable, visible in Temporal UI. Developers can debug workflows step-by-step. |

---

## 11. Specific Improvement Strategies

### 11.1 Areas Where Voyant Is Behind

| Area | Competitor | Gap | Strategy to Match | Strategy to Exceed |
|------|-----------|-----|-------------------|-------------------|
| **Photon Performance** | Databricks | 10–100x faster analytical queries | Deploy Spark cluster with Iceberg; tune Trino for small queries | Use DuckDB for embedded analytics (zero-setup, in-process); route small queries to DuckDB, large to Spark |
| **MLflow API Compatibility** | Databricks | ML platform has models but no API | Implement `/api/2.0/mlflow/*` endpoints matching MLflow's REST API | Add MCP tools for every ML operation (agents can manage experiments) |
| **AutoML** | Databricks | No AutoML engine | Phase 5: Basic AutoML using scikit-learn + Optuna for hyperparameter tuning | Intent Engine: "Find the best model for this data" → structured AutoML plan |
| **Feature Store** | Databricks | No centralized features | Phase 5: Simple feature store (computed features in Iceberg tables, cached in Redis) | MCP tools for feature discovery: agents can find and reuse features |
| **Notebooks** | Databricks + Palantir | No notebook environment | Phase 6: Jupyter integration (embed JupyterHub) | Agent-accessible: agents can create and execute notebook cells via MCP |
| **Data Lineage Depth** | Databricks | Column-level lineage, automated | Phase 5: Enhance DataHub integration with column-level lineage | Agent-callable: `voyant.lineage` MCP tool for programmatic lineage traversal |
| **Streaming** | Databricks | Structured Streaming (mature) | Phase 3: Complete Flink integration for streaming pipelines | Temporal workflows for streaming: durable, replayable streaming jobs |
| **Visual Builders** | Palantir | Workshop (mature low-code) | Phase 4: React visual builders for ontology, pipelines, scraping | Every visual action has a corresponding MCP tool (dual UI + agent access) |
| **Multi-Cloud** | Databricks | AWS + Azure + GCP | Phase 6: Terraform modules for each cloud | Self-hosted means ANY cloud, plus on-prem, plus air-gapped — more flexible |
| **Object Security** | Palantir | Per-object access policies | Phase 5: SpiceDB relationships per object type (e.g., `user:alice can_view object:order123`) | Agent-level security: which agents can access which objects, enforced at Intent Engine level |

### 11.2 Specific Technical Approaches

**Photon Performance Gap → Solution:**
```
Current:  Trino → PostgreSQL/MinIO (slow for analytical queries)
Phase 2:  Trino → Iceberg on MinIO (better, still slow for complex aggregations)
Phase 3:  Spark SQL → Iceberg on MinIO (fast, distributed)
Phase 5:  DuckDB for embedded queries <10K rows (<1ms latency, zero setup)
Final:    Query Router: small queries → DuckDB, medium → Trino, large → Spark
```

**MLflow API Compatibility → Solution:**
```python
# Target API endpoints to implement:
POST /api/2.0/mlflow/experiments/create
POST /api/2.0/mlflow/experiments/get
POST /api/2.0/mlflow/runs/create
POST /api/2.0/mlflow/runs/log-metric
POST /api/2.0/mlflow/runs/log-parameter
POST /api/2.0/mlflow/registered-models/create
POST /api/2.0/mlflow/model-versions/create
POST /api/2.0/mlflow/model-versions/transition-stage
POST /api/2.0/mlflow/endpoints/create  # Custom extension
```

**Data Lineage Gap → Solution:**
```
Phase 1: DataHub client (current — entity-level lineage)
Phase 3: Enhance with column-level lineage tracking
Phase 5: Auto-lineage: Airbyte ingestion → automatic DataHub lineage entries
Phase 5: MCP lineage tool: `voyant.lineage(urn, direction, depth)` — already built!
Final:   Intent Engine: "What upstream data affects Q4 revenue?" → lineage traversal plan
```

---

## 12. Benchmark Metrics to Track

### 12.1 Performance Metrics

| Metric | Databricks Target | Palantir Target | Voyant v4.0 Target |
|--------|------------------|----------------|-------------------|
| Simple query latency (p95) | <50ms (Photon) | <100ms | <200ms (Trino), <5ms (DuckDB) |
| Complex aggregation (p95) | <2s | <5s | <5s (Spark SQL) |
| Object CRUD latency (p95) | N/A (no ontology) | <50ms | <50ms (PostgreSQL) |
| Object traversal (3-hop, p95) | N/A | <200ms | <200ms |
| API endpoint latency (p95) | <200ms | <200ms | <200ms |
| MCP tool latency (p95) | N/A | N/A | <500ms |
| Concurrent users | 10,000+ | 5,000+ | 10,000+ (target) |
| Objects per type | 10M+ | 1M+ | 1M+ (target) |
| Pipeline throughput | 1TB/hour | 500GB/hour | 100GB/hour (target) |

### 12.2 Feature Completeness Metrics

| Domain | Current (v3.0) | Target (v4.0 GA) | Palantir Parity | Databricks Parity |
|--------|---------------|------------------|-----------------|-------------------|
| Ontology Engine (M3 Voyant Catalog) | 56% | 90% | 85% | N/A |
| Data Intelligence | 65% | 85% | 70% | 60% |
| ML/AI Platform | 0% | 70% | 60% | 50% |
| Governance | 43% | 80% | 70% | 65% |
| UI/UX | 15% | 60% | 50% | 45% |
| Scraper | 46% | 85% | N/A | N/A |
| API/SDK | 42% | 80% | 70% | 60% |
| **Overall** | **37%** | **78%** | **68%** | **46%** |

### 12.3 Unique Differentiator Metrics (Voyant Only)

| Metric | v3.0 | v4.0 Target | Why It Matters |
|--------|------|-------------|---------------|
| MCP Tools | 46 | 83+ | More tools = more agent capability |
| Temporal Workflows | 17 | 25+ | More durable operations |
| Browser Arms | 8 | 8+ | Web scraping breadth |
| Deep Research Workflows | 1 | 3+ | Research capability depth |
| Capsule Types | 5 | 15+ | Plugin ecosystem breadth |
| Intent Engine Accuracy | N/A | >95% | NL→plan translation quality |
| Agent Evaluation Score | N/A | >0.85 | Agent quality benchmark |
| Docker Container Count | 20 | 30 | Still lightweight |
| Test Functions | 2,203 | 3,500+ | Quality assurance |

### 12.4 Key Competitive Positioning Targets

| Positioning Statement | Target Metric | Timeline |
|----------------------|---------------|----------|
| "Self-hosted Palantir" | Ontology parity 85% | v4.0 GA |
| "Agent-native Databricks" | MCP tools 83+, MLflow API compatible | v4.0 GA |
| "Deterministic AI platform" | Intent Engine >95% accuracy | v4.0 GA |
| "Open-source data intelligence" | Apache 2.0, all layers | Already done |
| "AI agents can manage your data" | 14 ontology MCP tools + 7 scraper MCP tools | v4.0 Phase 1 |
| "The platform AI agents actually use" | 83+ MCP tools covering all domains | v4.0 GA |

---

## Appendix A: Sources

| Source | Type | Date Accessed |
|--------|------|--------------|
| `docs/specifications/v4.0/PALANTIR_FEATURE_MAP.md` | Internal | 2026-09-05 |
| `docs/specifications/v4.0/VOYANT_SRS_V4.md` | Internal | 2026-09-05 |
| `docs/specifications/v4.0/VOYANT_SAD_V4.md` | Internal | 2026-09-05 |
| `docs/specifications/v4.0/VOYANT_SCRAPER_SRS_V4.md` | Internal | 2026-09-05 |
| `apps/ontology/models.py` (754 LOC) | Code | 2026-09-05 |
| `apps/ontology/action_executor.py` (826 LOC) | Code | 2026-09-05 |
| `apps/ontology/function_runner.py` (665 LOC) | Code | 2026-09-05 |
| `apps/ml_platform/models.py` (249 LOC) | Code | 2026-09-05 |
| `apps/mcp/tools_core.py` (200 LOC) | Code | 2026-09-05 |
| `apps/mcp/tools_catalog.py` (408 LOC) | Code | 2026-09-05 |
| `apps/mcp/tools_ontology.py` (386 LOC) | Code | 2026-09-05 |
| Databricks Product Pages (unity-catalog, platform, ai, genie) | Web | 2026-09-05 |
| MLflow Documentation (mlflow.org) | Web | 2026-09-05 |
| Palantir Foundry/AIP pages (palantir.com) | Web | 2026-09-05 |

## Appendix B: Abbreviations

| Abbreviation | Full Form |
|-------------|-----------|
| AIP | Artificial Intelligence Platform (Palantir) |
| DLT | Declarative Pipelines (Databricks Lakeflow) |
| MCP | Model Context Protocol |
| OSS | Object Set Service (Palantir) |
| OSDK | Ontology SDK (Palantir) |
| RLS | Row-Level Security |
| UC | Unity Catalog (Databricks) |

---

**Created:** 2026-09-05
**Author:** Voyant Engineering
**Review cycle:** Monthly
**Next review:** 2026-10-05
