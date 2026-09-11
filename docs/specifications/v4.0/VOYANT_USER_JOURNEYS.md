# Voyant v4.0 — Complete User Journey Map

**Document ID:** VOYANT-UJ-4.0.0
**Version:** 4.0.0-draft
**Date:** 2026-09-05
**Purpose:** Every user journey in Palantir Foundry, Databricks, and how Voyant matches + improves each one
**Status:** Draft for Review

---

## How to Read This Document

Each journey follows this structure:

| Section | Description |
|---------|-------------|
| **Palantir** | Step-by-step in Foundry (screen names, clicks) |
| **Databricks** | Step-by-step in Databricks (screen names, clicks) |
| **Voyant v4.0** | Step-by-step in Voyant (screen names, API calls, MCP tools) |
| **Voyant Improvements** | Where Voyant wins: agent access, MCP, self-hosted, NL |
| **Comparison Table** | Side-by-side feature matrix |

---

## Legend

| Symbol | Meaning |
|--------|---------|
| `→` | Navigate to |
| `[API]` | REST API endpoint |
| `[MCP]` | MCP tool call |
| `[SCREEN]` | UI screen name |
| `[WF]` | Temporal workflow |
| `[AGENT]` | AI agent action |

---

# PART A: DATA ENGINEER JOURNEYS

---

## Journey 1: Register New Data Source (PostgreSQL, S3, API)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Foundry Home** | Click "Connect Data" in left sidebar |
| 2 | **Data Connection Wizard** | Select source type (Database / Cloud Storage / API) |
| 3 | **Connection Config** | Enter: host, port, database, credentials (stored in Foundry Secrets) |
| 4 | **Schema Discovery** | Foundry auto-discovers tables, columns, types |
| 5 | **Preview** | Review discovered schema; select tables to import |
| 6 | **Schedule** | Configure sync frequency (manual / hourly / daily) |
| 7 | **Dataset Created** | Foundry creates backed-up dataset in Foundry Storage |
| 8 | **Pipeline Sync** | Sync pipeline runs via Pipeline Builder |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Data Explorer** | Click "Create" → "External Data" → "Connection" |
| 2 | **Unity Catalog UI** | Select connector (JDBC / S3 / ADLS / GCS) |
| 3 | **Connection Form** | Enter: host, port, database, auth (Databricks Secrets) |
| 4 | **External Location** | Create external location pointing to S3/ADLS |
| 5 | **External Table** | `CREATE TABLE catalog.schema.table USING ...` or UI form |
| 6 | **Credential Storage** | Credentials stored in Databricks Secrets (backed by Key Vault) |
| 7 | **Unity Catalog** | Table registered in Unity Catalog with ownership + tags |
| 8 | **Auto Loader** (optional) | Configure Auto Loader for incremental ingestion from cloud |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Sources** (`view-sources.ts`) | Click "Add Data Source" button |
| 2 | `[SCREEN]` **Source Type Selector** | Select: PostgreSQL / MySQL / S3 / API / File |
| 3 | `[SCREEN]` **Connection Form** | Enter: name, host, port, database, credentials |
| 4 | `[API]` `POST /ingestion/sources` | Validate connection (triggers Airbyte check) |
| 5 | `[API]` `POST /ingestion/sources/{id}/discover` | Schema discovery via Airbyte connector |
| 6 | `[SCREEN]` **Schema Preview** | Review tables, columns, types; select tables to sync |
| 7 | `[API]` `POST /ingestion/sources/{id}/sync` | Trigger first sync |
| 8 | `[WF]` `DataSyncWorkflow` (Temporal) | Orchestrates: Airbyte pull → Kafka → Flink → Iceberg |
| 9 | `[API]` `GET /ingestion/sources/{id}/status` | Monitor sync progress |
| 10 | `[SCREEN]` **Sources** | Source appears with status "Active", last sync time |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_discovery__register_source → register source
[MCP] mcp__voyant_discovery__discover_schema → discover tables
[MCP] mcp__voyant_discovery__profile_table → profile columns
[MCP] mcp__voyant_discovery__run_profiling → run full profile
```

#### ASCII Wireframe: Sources Screen

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Sources                                    [User ▾]   │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─────────────────────────────────────────────────┐   │
│ Dashboard│ │  Data Sources                     [+ Add Source]│   │
│ Ontology │ ├─────────────────────────────────────────────────┤   │
│ SQL      │ │                                                 │   │
│ Sources  │ │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │   │
│ Scraper  │ │  │PostgreSQL│  │   S3     │  │  API     │      │   │
│ ML       │ │  │ ⚡ Active │  │ ⚡ Active │  │ ⏸ Paused │      │   │
│ Search   │ │  │ Last: 2m │  │ Last: 1h │  │ Last: 3d │      │   │
│ Govern   │ │  │ 12 tables│  │ 4 buckets│  │ 1 endpoint│     │   │
│ Audit    │ │  └──────────┘  └──────────┘  └──────────┘      │   │
│ Capsules │ │                                                 │   │
│          │ │  Sync History ──────────────────────────────    │   │
│          │ │  │ 14:32 │ postgres-prod │ ✅ 12 tables │ 2.3s │   │
│          │ │  │ 14:01 │ s3-warehouse  │ ✅ 4 buckets │ 8.1s │   │
│          │ │  │ 13:45 │ api-orders    │ ⚠️  1 timeout │      │   │
│          │ └─────────────────────────────────────────────────┘   │
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| PostgreSQL | ✅ Native | ✅ JDBC | ✅ Airbyte |
| S3/ADLS/GCS | ✅ Native | ✅ Native (Unity) | ✅ Airbyte |
| REST API | ✅ External Dataset | ⚠️ Manual | ✅ Built-in |
| Auto-discovery | ✅ | ✅ | ✅ |
| Secrets Management | ✅ Foundry Secrets | ✅ Databricks Secrets | ✅ HashiCorp Vault |
| Scheduling | ✅ Pipeline Builder | ✅ Jobs/Workflows | ✅ Temporal |
| Incremental Sync | ✅ | ✅ Auto Loader | ✅ Airbyte CDC |
| **Agent-triggered** | ❌ | ❌ | ✅ MCP tools |
| **Self-hosted** | ❌ | ❌ | ✅ Docker |

---

## Journey 2: Create ETL Pipeline (Source → Transform → Validate → Output)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Pipeline Builder** | Click "New Pipeline" → Select type (Batch / Streaming / Incremental) |
| 2 | **DAG Editor** | Drag source dataset onto canvas |
| 3 | **Transform Node** | Add transform: Python, SQL, or visual transform |
| 4 | **Code Editor** | Write transform logic (pandas/PySpark or SQL) |
| 5 | **Quality Node** | Add data expectations (schema checks, null %, range) |
| 6 | **Output Node** | Connect to output dataset |
| 7 | **Schedule** | Set schedule (cron, event-driven, or dependency) |
| 8 | **Run** | Execute pipeline; view DAG execution in real-time |
| 9 | **Monitor** | Pipeline Health dashboard shows success/failure per node |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Workflows** | Click "Create Job" → Add task |
| 2 | **Task Config** | Select type: Notebook / Python / SQL / JAR |
| 3 | **Notebook Editor** | Write transformation in PySpark/SQL notebook |
| 4 | **DLT Pipeline** (alternative) | Create Delta Live Tables pipeline with expectations |
| 5 | **Quality Rules** | Add `@dlt.expect_all()` decorators |
| 6 | **Output** | Write to Delta table in Unity Catalog |
| 7 | **Schedule** | Configure trigger (cron / file arrival / table update) |
| 8 | **Run** | Execute; monitor in "Runs" tab |
| 9 | **Lakeflow Monitor** | View lineage graph, error logs, data quality metrics |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Pipeline Builder** (new React Flow canvas) | Click "New Pipeline" |
| 2 | `[SCREEN]` **DAG Editor** | Drag nodes: Source → Transform → Validate → Output |
| 3 | `[SCREEN]` **Source Node Config** | Select registered data source + tables |
| 4 | `[SCREEN]` **Transform Node** | Choose: Python / SQL / LLM Transform |
| 5 | `[SCREEN]` **Code Editor** (Monaco) | Write transform: `def transform(df): return df[df.amount > 0]` |
| 6 | `[SCREEN]` **Quality Node** | Define expectations: null < 5%, unique keys, range checks |
| 7 | `[SCREEN]` **Output Node** | Select target: Iceberg table / Ontology Object Type / S3 |
| 8 | `[API]` `POST /pipelines` | Save pipeline definition |
| 9 | `[API]` `POST /pipelines/{id}/run` | Execute pipeline |
| 10 | `[WF]` `ETLPipelineWorkflow` (Temporal) | Executes DAG: source pull → transform → validate → write |
| 11 | `[SCREEN]` **Pipeline Monitor** | Real-time DAG view with node status, timings, errors |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_dataintel__create_pipeline → define pipeline
[MCP] mcp__voyant_dataintel__run_pipeline → execute
[MCP] mcp__voyant_dataintel__pipeline_status → check progress
[MCP] mcp__voyant_dataintel__validate_quality → run quality checks
```

#### ASCII Wireframe: Pipeline Builder

```
┌──────────────────────────────────────────────────────────────────┐
│ Pipeline Builder: "Customer ETL"                    [Run] [Save] │
├──────────────────────────────────────────────────────────────────┤
│ ┌────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────┐  │
│ │Postgres│───→│ Transform│───→│ Validate │───→│ Iceberg Table│  │
│ │Source  │    │ Python   │    │ Quality  │    │ customers    │  │
│ │        │    │          │    │ Checks   │    │              │  │
│ │customers│   │ df=filter│    │ null<5%  │    │ ✅ Ready     │  │
│ │ 12,345 │    │ (amount>0)│   │ unique pk│    │              │  │
│ └────────┘    └──────────┘    └──────────┘    └──────────────┘  │
│                                                                   │
│ ┌─ Node Details ─────────────────────────────────────────────┐   │
│ │ Transform: Python                                          │   │
│ │ ┌──────────────────────────────────────────────────────┐   │   │
│ │ │ def transform(df):                                    │   │   │
│ │ │     df = df[df['amount'] > 0]                         │   │   │
│ │ │     df['total'] = df['amount'] * df['quantity']       │   │   │
│ │ │     return df                                          │   │   │
│ │ └──────────────────────────────────────────────────────┘   │   │
│ │ Last run: 2026-09-05 14:32  │  Rows: 11,892  │  Time: 4.2s│   │
│ └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Visual DAG | ✅ Pipeline Builder | ✅ Lakeflow (DLT) | ✅ React Flow |
| Python Transform | ✅ pandas/PySpark | ✅ PySpark | ✅ pandas/PySpark |
| SQL Transform | ✅ | ✅ | ✅ Trino/Spark SQL |
| **LLM Transform** | ❌ | ❌ | ✅ in-pipeline LLM |
| Quality Checks | ✅ Data Expectations | ✅ DLT Expectations | ✅ Great Expectations |
| Streaming | ✅ Flink | ✅ Structured Streaming | ✅ Flink (stub→full) |
| Incremental | ✅ | ✅ Auto Loader | ✅ Airbyte CDC |
| **Agent-built pipeline** | ❌ | ❌ | ✅ MCP tools |
| Subgraphs | ✅ | ❌ | ✅ (planned) |
| Time Travel | ✅ | ✅ Delta | ✅ Iceberg snapshots |

---

## Journey 3: Monitor Pipeline Health and Fix Failures

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Pipeline Health** | View list of all pipelines with status indicators |
| 2 | **Pipeline Detail** | Click failing pipeline → see DAG with red nodes |
| 3 | **Node Log** | Click failed node → view error log, input/output samples |
| 4 | **Edit Transform** | Fix code in code editor |
| 5 | **Re-run** | Re-run from failed node (incremental re-run) |
| 6 | **Alert** | Configure alert rules (failure, latency, data quality) |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Workflows** | View job list with status badges |
| 2 | **Run Detail** | Click failed run → see task graph |
| 3 | **Task Log** | Click failed task → view Spark UI, driver logs, error trace |
| 4 | **Fix Notebook** | Edit notebook, fix transform |
| 5 | **Re-run** | Re-run failed task or full job |
| 6 | **Alerts** | Configure email/webhook alerts on failure |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Pipeline Monitor** | Dashboard shows all pipelines with status badges |
| 2 | `[SCREEN]` **Pipeline Detail** | Click pipeline → DAG view with per-node status |
| 3 | `[SCREEN]` **Node Log Panel** | Click failed node → error log, data samples, timing |
| 4 | `[API]` `GET /pipelines/{id}/runs/{run_id}` | Get run details with per-node metrics |
| 5 | `[SCREEN]` **Code Editor** | Fix transform code inline |
| 6 | `[API]` `POST /pipelines/{id}/runs/{run_id}/retry` | Re-run from failed node |
| 7 | `[WF]` Temporal retry with backoff | Automatic retry with configurable policy |
| 8 | `[SCREEN]` **Alerts Config** | Set alerts: failure, latency > X, quality < Y% |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_dataintel__pipeline_status → check health
[MCP] mcp__voyant_dataintel__pipeline_logs → get failure logs
[MCP] mcp__voyant_dataintel__retry_pipeline → auto-retry
[AGENT] Agent auto-detects failure → retries → escalates if 3 fails
```

#### Voyant Improvement: Self-Healing Pipelines

```
Pipeline fails
    │
    ▼
Agent detects via workflow signal
    │
    ├── Retry #1 (exponential backoff)
    │   ├── Success → log, continue
    │   └── Fail →
    ├── Retry #2 (fix known issues)
    │   ├── Success → log, continue
    │   └── Fail →
    └── Escalate → notify human + create incident
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Visual Status | ✅ | ✅ | ✅ DAG view |
| Error Logs | ✅ | ✅ Spark UI | ✅ Node logs |
| Incremental Re-run | ✅ | ✅ | ✅ |
| Auto-retry | ⚠️ Basic | ⚠️ Basic | ✅ Temporal policies |
| **Self-healing agent** | ❌ | ❌ | ✅ Agent auto-fix |
| Alert Rules | ✅ | ✅ | ✅ |
| Data Quality Metrics | ✅ | ✅ | ✅ |

---

## Journey 4: Set Up Data Quality Rules

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Data Health** | Navigate to Data Health dashboard |
| 2 | **Expectations** | Click "Add Expectation" on dataset |
| 3 | **Rule Builder** | Select rule type: Schema / Null % / Range / Uniqueness / Custom |
| 4 | **Configuration** | Set threshold (e.g., null < 5%, unique column) |
| 5 | **Save** | Attach to pipeline; runs on every sync |
| 6 | **Monitor** | Dashboard shows pass/fail rates over time |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **DLT Pipeline** | Open Delta Live Tables pipeline |
| 2 | **Quality Tab** | View existing expectations |
| 3 | **Add Expectation** | `@dlt.expect("valid_email", "email RLIKE '%@%'")` |
| 4 | **Configure** | Choose: warn / drop / fail on violation |
| 5 | **Save** | Pipeline applies on next run |
| 6 | **Monitor** | Quality metrics in pipeline dashboard |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Data Quality** (new view) | Navigate from sidebar → Data Quality |
| 2 | `[API]` `GET /data/quality/rules` | List all quality rules |
| 3 | `[SCREEN]` **Rule Builder** | Select table → Add rule |
| 4 | `[SCREEN]` **Rule Config** | Type: null_check / range / regex / uniqueness / custom_sql |
| 5 | `[API]` `POST /data/quality/rules` | Save rule definition |
| 6 | `[API]` `POST /data/quality/rules/{id}/run` | Execute quality check |
| 7 | `[SCREEN]` **Quality Dashboard** | View pass/fail rates, trend charts |
| 8 | `[WF]` Quality check runs in pipeline | Integrated with ETL pipeline |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_dataintel__create_quality_rule → define rule
[MCP] mcp__voyant_dataintel__run_quality_check → execute check
[MCP] mcp__voyant_dataintel__quality_report → get results
[AGENT] "Add a quality rule: orders.amount must be > 0"
```

#### ASCII Wireframe: Data Quality Dashboard

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Data Quality                              [User ▾]    │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Quality Overview ────────────────────────────────┐ │
│          │ │  Overall Score: 94.2%  │  Rules: 23  │  Failed: 2 │ │
│          │ └───────────────────────────────────────────────────┘ │
│          │ ┌─ Rules ───────────────────────────────────────────┐ │
│          │ │ Table       │ Rule          │ Status  │ Last Run   │ │
│          │ │ orders      │ null<2%       │ ✅ 0.1% │ 2m ago     │ │
│          │ │ orders      │ amount>0      │ ❌ 3.2% │ 2m ago     │ │
│          │ │ customers   │ unique email  │ ✅ 0.0% │ 1h ago     │ │
│          │ │ products    │ price range   │ ✅ Pass │ 1h ago     │ │
│          │ └──────────────────────────────────────────────────┘ │
│          │ [+ Add Rule]                                          │
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Rule Types | ✅ Schema/Null/Range | ✅ DLT Expectations | ✅ Great Expectations |
| Custom Rules | ✅ Python | ✅ SQL expression | ✅ SQL + Python |
| Auto-fix | ❌ | ❌ Drop mode | ⚠️ (planned) |
| Trend Dashboard | ✅ | ✅ | ✅ |
| **Agent-defined rules** | ❌ | ❌ | ✅ NL → rule |
| In-pipeline | ✅ | ✅ Native | ✅ Temporal |

---

## Journey 5: Configure Data Lineage Tracking

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Lineage Graph** | Navigate to dataset → "Lineage" tab |
| 2 | **Auto-detect** | Foundry auto-tracks: source → pipeline → output |
| 3 | **Visual Graph** | Upstream/downstream graph with dataset nodes |
| 4 | **Impact Analysis** | Click "Impact" to see all downstream consumers |
| 5 | **Column Lineage** | Drill into column-level lineage (which source columns map to output) |
| 6 | **Metadata** | Attach tags, descriptions, owners to lineage nodes |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Lineage Explorer** | Navigate: Data Explorer → table → "Lineage" tab |
| 2 | **Unity Catalog** | Auto-captures lineage from Spark SQL |
| 3 | **Visual Graph** | Upstream/downstream graph |
| 4 | **Column Lineage** | Column-level lineage (Unity Catalog Premium) |
| 5 | **Table Explorer** | Search across all tables with lineage |
| 6 | **Tags** | Apply tags for classification, owner, PII |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Lineage View** (new) | Navigate from sidebar → Lineage |
| 2 | `[API]` `GET /data/lineage/{dataset}` | Fetch lineage graph |
| 3 | `[SCREEN]` **Lineage Graph** | Force-directed graph showing upstream/downstream |
| 4 | `[API]` `POST /data/lineage/track` | Register lineage edge (source → transform → output) |
| 5 | `[WF]` Auto-track in pipeline | Every ETL pipeline auto-registers lineage |
| 6 | `[SCREEN]` **Impact Analysis** | Click node → see all downstream consumers |
| 7 | `[SCREEN]` **Column Lineage** | Drill into column-level mappings |
| 8 | Integration | DataHub + Apache Atlas feed lineage metadata |

#### ASCII Wireframe: Lineage Graph

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Data Lineage                             [User ▾]     │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Lineage: customers_clean ─────────────────────────┐│
│          │ │                                                    ││
│          │ │  [postgres]    [ETL]     [validate]   [iceberg]    ││
│          │ │  ┌────────┐  ┌──────┐  ┌──────────┐ ┌──────────┐ ││
│          │ │  │ raw    │─→│clean │─→│ quality  │─→│customers │ ││
│          │ │  │custs   │  │      │  │ check    │  │_clean    │ ││
│          │ │  │12,345  │  │filter│  │          │  │          │ ││
│          │ │  └────────┘  └──────┘  └──────────┘ └──────────┘ ││
│          │ │                          └──────────┐              ││
│          │ │                          │ Downstream│              ││
│          │ │                          │ Dashboard │              ││
│          │ │                          │ Report    │              ││
│          │ │                          └──────────┘              ││
│          │ └────────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Auto-tracking | ✅ | ✅ Unity Catalog | ✅ Pipeline + Atlas |
| Visual Graph | ✅ | ✅ | ✅ D3/Sigma.js |
| Column Lineage | ✅ | ✅ Premium | ✅ |
| Impact Analysis | ✅ | ✅ | ✅ |
| Metadata Tags | ✅ | ✅ Tags | ✅ Atlas |
| **Agent-explored** | ❌ | ❌ | ✅ MCP traversal |

---

# PART B: BUSINESS ANALYST JOURNEYS

---

## Journey 6: Explore Ontology (Browse Types, Objects, Relationships)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Object Explorer** | Click "Objects" in sidebar |
| 2 | **Type Browser** | Browse all Object Types with counts |
| 3 | **Object List** | Click type → see all objects with properties |
| 4 | **Search/Filter** | Search by property value; filter by conditions |
| 5 | **Object Detail** | Click object → full view with linked objects |
| 6 | **Graph View** | Click "Graph" → see object relationships visually |
| 7 | **Pivot** | Pivot table view: group by property, aggregate |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Data Explorer** | Click "Data Explorer" in sidebar |
| 2 | **Catalog Browser** | Browse catalogs → schemas → tables |
| 3 | **Table Detail** | Click table → columns, sample data, lineage |
| 4 | **SQL Query** | Open SQL Editor to query tables |
| 5 | **No native ontology** | Databricks has no ontology concept — tables only |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Ontology Explorer** (`view-ontology.ts`) | Click "Ontology" in sidebar |
| 2 | `[SCREEN]` **Type Browser** | Browse Object Types with property count + instance count |
| 3 | `[API]` `GET /ontology/object-types` | Fetch all types |
| 4 | `[SCREEN]` **Object List** | Click type → see all instances in sortable table |
| 5 | `[API]` `GET /ontology/object-types/{id}/objects` | Fetch instances with pagination |
| 6 | `[SCREEN]` **Filter Builder** | Add property filters |
| 7 | `[SCREEN]` **Object Detail Panel** | Click object → full detail with linked objects |
| 8 | `[SCREEN]` **Graph View** | Force-directed graph of object relationships |
| 9 | `[API]` `GET /ontology/objects/{id}/traverse` | Multi-hop traversal (up to 10 hops) |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_ontology__list_object_types → browse types
[MCP] mcp__voyant_ontology__search_objects → NL search
[MCP] mcp__voyant_ontology__traverse_links → multi-hop traversal
[MCP] mcp__voyant_ontology__get_object → detail view
```

#### ASCII Wireframe: Ontology Explorer

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Ontology Explorer                         [User ▾]    │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Object Types ──── [Table] [Graph] [Grid] ────────┐│
│          │ │                                                    ││
│          │ │  Type          │ Props │ Instances │ Links          ││
│          │ │  Customer      │  12   │  12,345   │ →Orders        ││
│          │ │  Order         │  8    │  45,678   │ →Products      ││
│          │ │  Product       │  15   │  3,456    │ →Categories    ││
│          │ │  Category      │  4    │  89       │ ←Products      ││
│          │ │  Supplier      │  6    │  234      │ →Products      ││
│          │ │                                                    ││
│          │ │  ┌─ Customer #C-4521 ────────────────────────────┐ ││
│          │ │  │ name: "Acme Corp"                             │ ││
│          │ │  │ email: "info@acme.com"                        │ ││
│          │ │  │ segment: "Enterprise"                         │ ││
│          │ │  │ created: 2024-03-15                           │ ││
│          │ │  │                                               │ ││
│          │ │  │ Linked Objects:                               │ ││
│          │ │  │  ├→ Order #1001 (2026-08-01) $12,500         │ ││
│          │ │  │  ├→ Order #1098 (2026-09-02) $8,300          │ ││
│          │ │  │  └→ Support Ticket #ST-45 (Open)             │ ││
│          │ │  └───────────────────────────────────────────────┘ ││
│          │ └────────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Type Browser | ✅ Object Explorer | ⚠️ Data Explorer (tables) | ✅ Ontology Explorer |
| Object List | ✅ | ⚠️ Table rows | ✅ |
| Relationship Graph | ✅ Vertex | ❌ | ✅ Sigma.js |
| Multi-hop Traversal | ✅ | ❌ | ✅ 10-hop |
| Search/Filter | ✅ Full-text + faceted | ⚠️ SQL only | ✅ Full-text + semantic |
| Pivot | ✅ | ❌ | ✅ (planned) |
| **Agent browsing** | ❌ | ❌ | ✅ MCP tools |
| **NL search** | ❌ | ❌ | ✅ Intent Engine |

---

## Journey 7: Query Data with SQL (Interactive Editor)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **SQL Studio** | Click "SQL" in sidebar |
| 2 | **Editor** | Monaco editor with autocomplete |
| 3 | **Schema Browser** | Browse datasets, columns, types in sidebar |
| 4 | **Run Query** | Execute SQL → results table |
| 5 | **Save as Dataset** | Save result as new backed-up dataset |
| 6 | **Export** | Download as CSV |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **SQL Editor** | Click "SQL Editor" in sidebar |
| 2 | **Editor** | Monaco editor with autocomplete (Unity Catalog aware) |
| 3 | **Catalog Browser** | Browse catalogs, schemas, tables |
| 4 | **Run Query** | Execute on Spark SQL / Photon → results |
| 5 | **Save as View** | Save as view or table |
| 6 | **Visualize** | Built-in chart from results |
| 7 | **Dashboard** | Pin query result to dashboard |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **SQL Studio** (`view-sql.ts`) | Click "SQL" in sidebar |
| 2 | `[SCREEN]` **Monaco Editor** | Write SQL with autocomplete (schema-aware) |
| 3 | `[SCREEN]` **Table Browser** | Left panel: tables, columns, types |
| 4 | `[API]` `POST /sql/query` | Execute SQL (Trino/Spark backend) |
| 5 | `[SCREEN]` **Results Table** | Sortable, paginated results |
| 6 | `[SCREEN]` **Query History** | Last 20 queries with timing |
| 7 | `[API]` `POST /sql/query` (export) | Export as CSV/JSON |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_sql__execute_query → run SQL
[MCP] mcp__voyant_sql__list_tables → browse schema
[MCP] mcp__voyant_sql__describe_table → inspect columns
[AGENT] "Run a query to find all orders over $1000"
```

#### ASCII Wireframe: SQL Studio

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  SQL Studio                                [User ▾]    │
├──────────┬───────────────────────────────────────────────────────┤
│ Tables   │ ┌─ Monaco Editor ───────────────────────────────────┐ │
│  ├ orders│ │ SELECT o.id, c.name, SUM(o.amount) as total       │ │
│  │ ├ id  │ │ FROM orders o                                      │ │
│  │ ├ amt │ │ JOIN customers c ON o.customer_id = c.id           │ │
│  │ └ ... │ │ WHERE o.amount > 1000                              │ │
│  ├ custs │ │ GROUP BY o.id, c.name                              │ │
│  │ ├ id  │ │ ORDER BY total DESC;                               │ │
│  │ ├ name│ └────────────────────────────────────────────────────┘ │
│  │ └ ... │                                            [▶ Run]    │
│  └ prods │ ┌─ Results ─────────────────────────────────────────┐ │
│          │ │ id    │ name       │ total                         │ │
│          │ │ 1001  │ Acme Corp  │ $45,200                       │ │
│          │ │ 1098  │ Globex     │ $32,100                       │ │
│          │ │ 1045  │ Initech    │ $28,750                       │ │
│          │ │ ...   │ ...        │ ...                           │ │
│          │ │ 12 rows │ 0.34s                            [CSV] [JSON]│
│          │ └────────────────────────────────────────────────────┘ │
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| SQL Editor | ✅ Monaco | ✅ Monaco | ✅ Monaco |
| Autocomplete | ✅ Dataset-aware | ✅ Catalog-aware | ✅ Schema-aware |
| Multi-engine | ✅ Foundry SQL | ✅ Photon/Spark | ✅ Trino + Spark |
| Save Results | ✅ As dataset | ✅ As view/table | ✅ As Iceberg table |
| Export | ✅ CSV | ✅ CSV/JSON | ✅ CSV/JSON |
| **Agent SQL** | ❌ | ❌ | ✅ MCP `execute_query` |
| **NL → SQL** | ❌ | ⚠️ Genie | ✅ Intent Engine |

---

## Journey 8: Search Data Semantically (NL Question → Results)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Search Bar** | Type natural language in global search bar |
| 2 | **Results** | Returns matching objects, datasets, pipelines |
| 3 | **Filter** | Filter by type, date, owner |
| 4 | **No NL-to-SQL** | Foundry does not convert NL to queries — search only |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Genie** | Open Genie (Natural Language BI) |
| 2 | **Ask Question** | Type: "What were total sales in June?" |
| 3 | **Genie generates SQL** | AI generates SQL query |
| 4 | **Review & Run** | User reviews SQL, approves, runs |
| 5 | **Chart** | Genie returns table + auto-chart |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Search** (`view-search.ts`) | Type NL question in search bar |
| 2 | `[SCREEN]` **Semantic Search** | Full-text + vector search via Milvus + Elasticsearch |
| 3 | `[API]` `GET /search/query?q=...` | Semantic search across ontology |
| 4 | `[SCREEN]` **Query Intent** (Intent Engine) | System classifies: "This is a data query" |
| 5 | `[SCREEN]` **SQL Preview** | Intent Engine generates SQL from NL |
| 6 | `[API]` `POST /sql/query` | Execute generated SQL |
| 7 | `[SCREEN]` **Results** | Table + auto-generated chart |
| 8 | `[SCREEN]` **Refine** | User can refine NL question or edit SQL directly |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_search__semantic_search → search ontology
[MCP] mcp__voyant_sql__execute_query → run generated SQL
[AGENT] "What are the top 10 customers by order volume?"
  → Intent Engine classifies as query
  → Schema Resolver finds Customer, Order types
  → Plan Generator creates SQL
  → Plan Validator checks permissions
  → Plan Executor runs query
  → Result: table + chart
```

#### ASCII Wireframe: Semantic Search

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Search                                   [User ▾]     │
├──────────┬───────────────────────────────────────────────────────┤
│          │  ┌──────────────────────────────────────────────┐     │
│          │  │ 🔍 What are the top 10 customers by revenue? │     │
│          │  └──────────────────────────────────────────────┘     │
│          │                                                       │
│          │  ┌─ Intent Detected: DATA QUERY ─────────────────┐    │
│          │  │ I found matching types: Customer (12 props),   │    │
│          │  │ Order (8 props). Generating SQL...              │    │
│          │  └────────────────────────────────────────────────┘    │
│          │                                                       │
│          │  ┌─ Generated SQL ───────────────────────────────┐    │
│          │  │ SELECT c.name, SUM(o.amount) as total_revenue │    │
│          │  │ FROM customers c JOIN orders o ON ...          │    │
│          │  │ GROUP BY c.name ORDER BY total_revenue DESC    │    │
│          │  │ LIMIT 10                                 [Edit]│    │
│          │  └────────────────────────────────────────────────┘    │
│          │                                                       │
│          │  ┌─ Results ─────────────────────────────────────┐    │
│          │  │ name         │ total_revenue                   │    │
│          │  │ Acme Corp    │ $452,300                        │    │
│          │  │ Globex Inc   │ $321,800                        │    │
│          │  │ ...          │ ...                             │    │
│          │  │                         [📊 Chart] [📥 Export] │    │
│          │  └────────────────────────────────────────────────┘    │
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| NL Search | ✅ Object search | ✅ Genie | ✅ Intent Engine |
| NL → SQL | ❌ | ✅ Genie | ✅ Intent Engine |
| Semantic (vector) | ❌ | ❌ | ✅ Milvus |
| Full-text | ✅ | ⚠️ | ✅ Elasticsearch |
| Auto-chart | ❌ | ✅ | ✅ ECharts |
| Review before run | N/A | ✅ | ✅ |
| **Agent NL** | ❌ | ❌ | ✅ Full MCP |

---

## Journey 9: Build Dashboard (Charts, Tables, Filters)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Workshop** | Click "New Workshop" → select layout |
| 2 | **Widget Library** | Drag: chart, table, map, metric, filter |
| 3 | **Data Binding** | Bind widget to Object Type or dataset |
| 4 | **Configuration** | Configure axes, aggregations, colors |
| 5 | **Filters** | Add interactive filters (dropdown, date range, search) |
| 6 | **Save & Share** | Save workshop; share with team |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Dashboards** | Click "Create" → "Dashboard" |
| 2 | **Add Widget** | Add: visualization, textbox, filter |
| 3 | **SQL Query** | Each widget backed by SQL query |
| 4 | **Chart Config** | Configure chart type, axes, colors |
| 5 | **Filters** | Add parameter filters |
| 6 | **Publish** | Publish dashboard; share via link |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Dashboard Builder** (new) | Click "New Dashboard" |
| 2 | `[SCREEN]` **Layout Editor** | Choose grid layout (2x2, 3x2, custom) |
| 3 | `[SCREEN]` **Widget Library** | Drag: chart (ECharts), table, metric card, map |
| 4 | `[SCREEN]` **Data Binding** | Bind to Object Type, SQL query, or metric |
| 5 | `[SCREEN]` **Chart Config** | Configure: type (bar/line/pie/scatter), axes, colors |
| 6 | `[SCREEN]` **Filter Bar** | Add filters: dropdown, date range, text search |
| 7 | `[API]` `POST /dashboards` | Save dashboard layout + widget configs |
| 8 | `[SCREEN]` **Dashboard View** | Interactive dashboard with real-time data |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_dataintel__create_dashboard → create dashboard
[MCP] mcp__voyant_dataintel__add_widget → add chart/table
[AGENT] "Create a dashboard showing revenue by month with a customer segment filter"
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Visual Builder | ✅ Workshop | ✅ Dashboards | ✅ Dashboard Builder |
| Chart Types | ✅ Rich | ✅ Rich | ✅ ECharts (50+ types) |
| Interactive Filters | ✅ | ✅ | ✅ |
| Real-time Data | ✅ | ⚠️ Scheduled | ✅ WebSocket (planned) |
| Map Support | ✅ | ⚠️ | ✅ ECharts Geo |
| **Agent-built** | ❌ | ❌ | ✅ MCP tools |
| **NL → Dashboard** | ❌ | ❌ | ✅ Intent Engine |

---

## Journey 10: Export Data for Reporting

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Object Explorer** or **SQL Studio** | Open dataset or query results |
| 2 | **Export Menu** | Click "Export" → CSV / Excel / PDF |
| 3 | **Options** | Select columns, filters, format |
| 4 | **Download** | Download file |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **SQL Editor** or **Notebook** | Run query |
| 2 | **Export** | Click "Download" on results |
| 3 | **Format** | CSV / TSV / JSON / Excel |
| 4 | **Databricks SQL** | `COPY INTO` for bulk export to S3 |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **SQL Studio** or **Ontology Explorer** | Run query or browse objects |
| 2 | `[SCREEN]` **Export Menu** | Click "Export" on results table |
| 3 | `[SCREEN]` **Format Selector** | Choose: CSV / JSON / XLSX / PDF |
| 4 | `[API]` `POST /export` | Generate export file |
| 5 | `[SCREEN]` **Download** | Download file |
| 6 | `[API]` `POST /export/schedule` | Schedule recurring export |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_sql__execute_query → get data
[MCP] mcp__voyant_dataintel__export_data → export to format
[AGENT] "Export all Q3 orders as Excel with customer names"
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| CSV | ✅ | ✅ | ✅ |
| Excel | ✅ | ✅ | ✅ |
| JSON | ✅ | ✅ | ✅ |
| PDF | ✅ | ❌ | ✅ |
| Scheduled Export | ⚠️ | ✅ COPY INTO | ✅ Temporal |
| **Agent export** | ❌ | ❌ | ✅ MCP tools |

---

# PART C: DATA SCIENTIST JOURNEYS

---

## Journey 11: Explore Data in Notebook

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Quiver** | Click "Notebooks" → "New Notebook" |
| 2 | **Cell Editor** | Write Python/SQL/R cells |
| 3 | **Import Data** | `import foundry; ds = foundry.dataset("customers")` |
| 4 | **Explore** | pandas/PySpark analysis with inline charts |
| 5 | **Save** | Save notebook; share with team |
| 6 | **Version** | Notebooks versioned in Foundry Repos |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Workspace** | Click "Create" → "Notebook" |
| 2 | **Language** | Select: Python / SQL / R / Scala |
| 3 | **Cluster** | Attach to compute cluster |
| 4 | **Import Data** | `df = spark.table("catalog.schema.table")` |
| 5 | **Explore** | PySpark/pandas with `%sql` magic, inline charts |
| 6 | **Save** | Auto-saves; version in Repos |
| 7 | **Share** | Share link; collaborate in real-time |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Notebooks** (new) | Click "New Notebook" |
| 2 | `[SCREEN]` **Cell Editor** (Monaco) | Write Python / SQL cells |
| 3 | `[API]` `POST /notebooks/{id}/execute` | Execute cell |
| 4 | `[SCREEN]` **Import Panel** | Browse ontology types or run SQL to load data |
| 5 | `[API]` `GET /ontology/object-types/{id}/objects` | Load objects as DataFrame |
| 6 | `[SCREEN]` **Inline Output** | Tables, charts (ECharts), text output |
| 7 | `[API]` `PUT /notebooks/{id}` | Save notebook |
| 8 | `[SCREEN]` **Version History** | View/restore previous versions |

#### ASCII Wireframe: Notebook

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Notebook: "Customer Analysis"        [Run All] [Save] │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Cell 1 [Python] ─────────────────────────────────┐ │
│ Ontology │ │ import pandas as pd                                │ │
│  ├ Custs │ │ from voyant import ontology                        │ │
│  ├ Orders│ │                                                    │ │
│  └ Prods │ │ df = ontology.objects("Customer").to_dataframe()   │ │
│          │ │ df.head()                                    [▶ Run]│ │
│          │ └────────────────────────────────────────────────────┘ │
│          │ ┌─ Output ──────────────────────────────────────────┐ │
│          │ │    name        segment    revenue   created        │ │
│          │ │ 0  Acme Corp   Enterprise  452300   2024-03-15    │ │
│          │ │ 1  Globex Inc  Mid-Market  321800   2023-11-20    │ │
│          │ │ ...                                                  │ │
│          │ └────────────────────────────────────────────────────┘ │
│          │ ┌─ Cell 2 [Python] ─────────────────────────────────┐ │
│          │ │ df.groupby('segment')['revenue'].sum().plot.bar()  │ │
│          │ └────────────────────────────────────────────────────┘ │
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Notebook UI | ✅ Quiver | ✅ Native | ✅ Monaco cells |
| Multi-language | ✅ Py/SQL/R | ✅ Py/SQL/R/Scala | ✅ Py/SQL |
| Collaboration | ⚠️ | ✅ Real-time | ⚠️ (planned) |
| Inline Charts | ✅ | ✅ | ✅ ECharts |
| **Ontology-aware** | ✅ Foundry SDK | ❌ | ✅ Ontology API |
| **Agent-created** | ❌ | ❌ | ✅ MCP tools |
| Version Control | ✅ Repos | ✅ Repos | ✅ Git |

---

## Journey 12: Train ML Model with Experiment Tracking

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **ML Workspace** | Open ML workspace → "New Experiment" |
| 2 | **Configure** | Set: framework (sklearn/PyTorch/TF), compute, dataset |
| 3 | **Training Code** | Write training script in notebook |
| 4 | **Logging** | `foundry.log_metric("accuracy", 0.95)` |
| 5 | **Artifacts** | Upload model artifacts to Foundry Storage |
| 6 | **Compare** | Experiment tracker shows all runs with metrics |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Experiments** | Click "Experiments" → "Create Experiment" |
| 2 | **Notebook** | Write training code with `mlflow.start_run()` |
| 3 | **Autolog** | `mlflow.autolog()` captures params/metrics automatically |
| 4 | **Manual Logging** | `mlflow.log_metric("f1", 0.92)` |
| 5 | **Artifacts** | `mlflow.log_artifact("model.pkl")` |
| 6 | **Compare** | MLflow UI: compare runs, parallel coordinates |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **ML Platform** (new) | Click "Experiments" → "New Experiment" |
| 2 | `[API]` `POST /ml/experiments` | Create experiment (MLflow-compatible) |
| 3 | `[SCREEN]` **Training Config** | Select: framework, compute, dataset |
| 4 | `[API]` `POST /ml/experiments/{id}/runs` | Start run |
| 5 | `[API]` `POST /ml/runs/{id}/log` | Log params, metrics, artifacts |
| 6 | `[WF]` `MLTrainingWorkflow` (Temporal) | Orchestrates: data prep → train → evaluate → log |
| 7 | `[SCREEN]` **Run Comparison** | Table + charts comparing all runs |
| 8 | `[API]` `GET /ml/experiments/{id}/runs` | List all runs |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_ml__create_experiment → create experiment
[MCP] mcp__voyant_ml__start_run → start training run
[MCP] mcp__voyant_ml__log_metric → log metric
[MCP] mcp__voyant_ml__log_artifact → log model
[AGENT] "Train a customer churn model on the orders dataset"
```

#### ASCII Wireframe: Experiment Tracking

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  ML Experiments                           [User ▾]     │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Experiment: "Customer Churn Prediction" ──────────┐│
│          │ │ Runs: 12  │  Best F1: 0.92  │  Framework: sklearn  ││
│          │ ├────────────────────────────────────────────────────┤│
│          │ │ Run      │ Accuracy │ F1     │ AUC   │ Status       ││
│          │ │ run-12   │ 0.94     │ 0.92   │ 0.96  │ ✅ Finished  ││
│          │ │ run-11   │ 0.91     │ 0.89   │ 0.93  │ ✅ Finished  ││
│          │ │ run-10   │ 0.88     │ 0.85   │ 0.90  │ ✅ Finished  ││
│          │ │ run-09   │ 0.93     │ 0.91   │ 0.95  │ ✅ Finished  ││
│          │ │ run-08   │ —        │ —      │ —     │ 🔄 Running   ││
│          │ ├────────────────────────────────────────────────────┤│
│          │ │ [Compare Selected]  [Register Best Model]           ││
│          │ └────────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Experiment Tracking | ✅ ML Workspace | ✅ MLflow | ✅ MLflow-compatible |
| Autologging | ⚠️ | ✅ `mlflow.autolog()` | ⚠️ (manual logging) |
| Run Comparison | ✅ | ✅ MLflow UI | ✅ Comparison view |
| Artifact Storage | ✅ Foundry Storage | ✅ MLflow artifacts | ✅ MinIO |
| **Agent training** | ❌ | ❌ | ✅ MCP tools |
| **Self-hosted** | ❌ | ❌ | ✅ Docker |

---

## Journey 13: Compare Model Runs

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Experiment Tracker** | Select multiple runs |
| 2 | **Comparison View** | Parallel coordinates, scatter plots |
| 3 | **Metric Table** | Side-by-side metrics |
| 4 | **Best Run** | System highlights best run per metric |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **MLflow Experiments** | Click experiment → select runs |
| 2 | **Compare** | Click "Compare" button |
| 3 | **Parallel Coordinates** | Visual comparison of hyperparams vs metrics |
| 4 | **Metric Table** | Side-by-side run metrics |
| 5 | **Artifact Diff** | Compare model artifacts |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Run Comparison** | Select runs from experiment detail |
| 2 | `[API]` `GET /ml/runs/compare?ids=run1,run2,...` | Fetch comparison data |
| 3 | `[SCREEN]` **Comparison Table** | Side-by-side params + metrics |
| 4 | `[SCREEN]` **Parallel Coordinates Chart** | ECharts parallel coordinate visualization |
| 5 | `[SCREEN]` **Metric Trend** | Line chart showing metric across runs |
| 6 | `[SCREEN]` **Best Run Highlight** | Auto-highlight best run per metric |

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Run Selection | ✅ | ✅ | ✅ |
| Parallel Coordinates | ✅ | ✅ | ✅ ECharts |
| Metric Table | ✅ | ✅ | ✅ |
| Auto-highlight | ⚠️ | ✅ | ✅ |
| **Agent comparison** | ❌ | ❌ | ✅ MCP |

---

## Journey 14: Register and Version Model

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **ML Workspace** | Click best run → "Register Model" |
| 2 | **Model Name** | Enter model name |
| 3 | **Version** | First version is v1 |
| 4 | **Metadata** | Add description, tags |
| 5 | **Model Registry** | Model appears in registry |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **MLflow Run** | Click run → "Register Model" |
| 2 | **Model Registry** | Select/create registered model |
| 3 | **Version Created** | New version auto-created |
| 4 | **Stage** | Set stage: None → Staging → Production → Archived |
| 5 | **Tags** | Add tags, description |
| 6 | **Approval** | Request approval for stage transitions |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Run Detail** | Click run → "Register Model" |
| 2 | `[API]` `POST /ml/models` | Create registered model |
| 3 | `[API]` `POST /ml/models/{id}/versions` | Create version from run |
| 4 | `[SCREEN]` **Model Registry** | Browse all registered models with versions |
| 5 | `[API]` `PATCH /ml/models/{id}/versions/{v}` | Set stage (none → staging → production → archived) |
| 6 | `[SCREEN]` **Version Detail** | View: metrics, artifacts, lineage to run |

#### ASCII Wireframe: Model Registry

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Model Registry                            [User ▾]    │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Registered Models ───────────────────────────────┐ │
│          │ │ [+ Register Model]                                 │ │
│          │ │                                                     │ │
│          │ │  Model              │ Versions │ Stage      │ F1    │ │
│          │ │  churn-predictor    │ 5        │ Production │ 0.92  │ │
│          │ │  fraud-detector     │ 3        │ Staging    │ 0.95  │ │
│          │ │  price-optimizer    │ 1        │ None       │ 0.87  │ │
│          │ ├────────────────────────────────────────────────────┤ │
│          │ │ ┌─ churn-predictor Versions ──────────────────────┐│ │
│          │ │ │ v5 │ Production │ F1: 0.92 │ 2026-09-04 [Deploy]││ │
│          │ │ │ v4 │ Staging    │ F1: 0.89 │ 2026-09-02        ││ │
│          │ │ │ v3 │ Archived   │ F1: 0.87 │ 2026-08-28        ││ │
│          │ │ └─────────────────────────────────────────────────┘│ │
│          │ └─────────────────────────────────────────────────────┘ │
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Model Registry | ✅ | ✅ MLflow | ✅ MLflow-compatible |
| Versioning | ✅ | ✅ | ✅ |
| Stage Management | ✅ | ✅ (4 stages) | ✅ (4 stages) |
| Approval Workflow | ⚠️ | ✅ | ⚠️ (planned) |
| **Agent register** | ❌ | ❌ | ✅ MCP tools |

---

## Journey 15: Deploy Model to Serving Endpoint

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Model Registry** | Click model → "Deploy" |
| 2 | **Endpoint Config** | Set: compute, scaling, timeout |
| 3 | **Deploy** | Foundry provisions endpoint |
| 4 | **Test** | Send test request via API or UI |
| 5 | **Monitor** | Latency, throughput, error rate |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Model Registry** | Click model version → "Deploy" → "Serving Endpoint" |
| 2 | **Endpoint Config** | Set: compute size, scale-to-zero, timeout |
| 3 | **Deploy** | Databricks provisions GPU/CPU endpoint |
| 4 | **Test** | "Query Endpoint" tab → send test payload |
| 5 | **Traffic** | Configure traffic splitting between versions |
| 6 | **Monitor** | Inference tables, latency, error rate |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Model Detail** | Click model version → "Deploy Endpoint" |
| 2 | `[API]` `POST /ml/endpoints` | Create serving endpoint |
| 3 | `[SCREEN]` **Endpoint Config** | Set: timeout, max batch, replicas |
| 4 | `[API]` `POST /ml/endpoints/{id}/activate` | Activate endpoint |
| 5 | `[SCREEN]` **Test Panel** | Send test payload, view response |
| 6 | `[API]` `POST /ml/endpoints/{id}/predict` | Real-time prediction |
| 7 | `[SCREEN]` **Endpoint Monitor** | Latency, throughput, error rate |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_ml__create_endpoint → deploy model
[MCP] mcp__voyant_ml__predict → call endpoint
[AGENT] "Deploy churn-predictor v5 to production"
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| One-click Deploy | ✅ | ✅ | ✅ |
| Auto-scaling | ✅ | ✅ | ⚠️ (planned) |
| Traffic Splitting | ⚠️ | ✅ | ⚠️ (planned) |
| Scale-to-zero | ❌ | ✅ | ⚠️ (planned) |
| **Agent deploy** | ❌ | ❌ | ✅ MCP tools |

---

## Journey 16: Monitor Model Drift

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **ML Monitor** | Navigate to model monitoring dashboard |
| 2 | **Drift Detection** | System compares production vs training distributions |
| 3 | **Alerts** | Configure drift thresholds |
| 4 | **Retrain** | Trigger retrain pipeline when drift detected |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Model Serving** | Click endpoint → "Monitoring" tab |
| 2 | **Inference Tables** | Logs every prediction to Delta table |
| 3 | **Quality Metrics** | Auto-computes: drift, skew, missing values |
| 4 | **Alerts** | Configure alerts on quality metrics |
| 5 | **Retrain** | Databricks can auto-trigger retrain jobs |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Endpoint Monitor** | Navigate to endpoint → "Monitoring" tab |
| 2 | `[API]` `GET /ml/endpoints/{id}/metrics` | Fetch inference metrics |
| 3 | `[SCREEN]` **Drift Dashboard** | Feature distribution comparison (training vs production) |
| 4 | `[API]` `POST /ml/endpoints/{id}/drift-check` | Run drift detection |
| 5 | `[SCREEN]` **Alert Config** | Set drift thresholds (PSI, KS statistic) |
| 6 | `[WF]` Automatic retrain trigger | When drift > threshold → start retrain pipeline |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_ml__endpoint_metrics → check drift
[MCP] mcp__voyant_ml__trigger_retrain → auto-retrain
[AGENT] "Check if churn model is drifting and retrain if needed"
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Drift Detection | ✅ | ✅ | ✅ |
| Inference Logging | ✅ | ✅ Inference Tables | ✅ |
| Auto-alerts | ✅ | ✅ | ✅ |
| Auto-retrain | ⚠️ | ✅ | ✅ Temporal |
| **Agent monitoring** | ❌ | ❌ | ✅ MCP tools |

---

# PART D: AI/AGENT ENGINEER JOURNEYS

---

## Journey 17: Define AI Agent (Prompt, Model, Tools, Guardrails)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **AIP Console** | Click "Create Agent" |
| 2 | **Model Selection** | Select LLM (GPT-4, Claude, Llama) |
| 3 | **System Prompt** | Define agent behavior and instructions |
| 4 | **Tools** | Attach tools: ontology read, action, web search |
| 5 | **Guardrails** | Set safety rules: max calls, blocked actions |
| 6 | **Test** | Test in chat interface |
| 7 | **Deploy** | Publish to AIP production |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Agent Bricks** | Click "Create Agent" |
| 2 | **Model** | Select model from Model Serving |
| 3 | **Instructions** | Define agent instructions |
| 4 | **Tools** | Attach: SQL, vector search, web, custom |
| 5 | **Guardrails** | Set safety constraints |
| 6 | **Evaluate** | Run evaluation suite |
| 7 | **Deploy** | Deploy to Model Serving endpoint |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Agent Builder** (new) | Click "Create Agent" |
| 2 | `[API]` `POST /ml/agents` | Create agent definition |
| 3 | `[SCREEN]` **Agent Config** | Set: name, description, system prompt |
| 4 | `[SCREEN]` **Model Selector** | Choose provider (Groq/OpenAI/local) + model |
| 5 | `[SCREEN]` **Tool Selector** | Select MCP tools: voyant.sql, voyant.ontology.*, etc. |
| 6 | `[SCREEN]` **Guardrails Config** | Set: max queries, blocked tables, require approval |
| 7 | `[API]` `PUT /ml/agents/{id}` | Save agent definition |
| 8 | `[SCREEN]` **Test Chat** | Test agent in built-in chat interface |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_ml__create_agent → define agent
[MCP] mcp__voyant_ml__list_agents → browse agents
[MCP] mcp__voyant_ml__update_agent → modify config
[AGENT] "Create an agent that answers sales questions using SQL and ontology"
```

#### ASCII Wireframe: Agent Builder

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Agent Builder                             [User ▾]    │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Define Agent ────────────────────────────────────┐ │
│          │ │ Name: [Sales Assistant                        ]    │ │
│          │ │ Model: [Groq ▾] [openai/gpt-oss-120b ▾]           │ │
│          │ │ Temp: [0.1]  Max Tokens: [4096]                    │ │
│          │ │                                                     │ │
│          │ │ System Prompt:                                      │ │
│          │ │ ┌──────────────────────────────────────────────┐   │ │
│          │ │ │ You are a sales data assistant. Answer       │   │ │
│          │ │ │ questions about customers and orders using    │   │ │
│          │ │ │ the available MCP tools. Always explain       │   │ │
│          │ │ │ your reasoning.                               │   │ │
│          │ │ └──────────────────────────────────────────────┘   │ │
│          │ │                                                     │ │
│          │ │ Tools:                                              │ │
│          │ │ ☑ voyant.sql.execute_query                          │ │
│          │ │ ☑ voyant.ontology.list_object_types                 │ │
│          │ │ ☑ voyant.ontology.search_objects                    │ │
│          │ │ ☑ voyant.ontology.traverse_links                    │ │
│          │ │ ☐ voyant.ontology.create_object                     │ │
│          │ │                                                     │ │
│          │ │ Guardrails:                                         │ │
│          │ │ Max queries/session: [50]                            │ │
│          │ │ Blocked tables: [audit_log, credentials]            │ │
│          │ │ Require approval: [No ▾]                            │ │
│          │ │                                           [Save]    │ │
│          │ └─────────────────────────────────────────────────────┘ │
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Agent Definition | ✅ AIP | ✅ Agent Bricks | ✅ Agent Builder |
| Multi-model | ✅ | ✅ | ✅ Groq/OpenAI/local |
| Tool Selection | ✅ Ontology tools | ✅ SQL/Vector/Web | ✅ 80+ MCP tools |
| Guardrails | ✅ | ✅ | ✅ |
| Test Chat | ✅ | ✅ | ✅ |
| **Self-hosted** | ❌ | ❌ | ✅ Docker |
| **Open-source** | ❌ | ❌ | ✅ Apache 2.0 |

---

## Journey 18: Evaluate Agent with Test Cases

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **AIP Evaluation** | Click "Evaluate" on agent |
| 2 | **Test Cases** | Define test cases: input + expected output |
| 3 | **AI Judge** | Select judge model for scoring |
| 4 | **Run** | Execute evaluation suite |
| 5 | **Results** | Per-test scores + overall pass rate |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Agent Evaluation** | Click "Evaluate" on agent |
| 2 | **Test Suite** | Define test cases with expected answers |
| 3 | **AI Judge** | LLM-as-judge scoring |
| 4 | **Run** | Execute evaluation |
| 5 | **Results** | Scores, explanations, failure analysis |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Evaluation** | Click "Evaluate" on agent |
| 2 | `[API]` `POST /ml/agents/{id}/evaluations` | Create evaluation |
| 3 | `[SCREEN]` **Test Case Editor** | Define: input, expected output, expected tools |
| 4 | `[API]` `POST /ml/evaluations/{id}/run` | Run evaluation |
| 5 | `[WF]` `AgentEvaluationWorkflow` (Temporal) | Runs each test case, collects results |
| 6 | `[SCREEN]` **Results Dashboard** | Per-test: score, tool calls, judge notes |
| 7 | `[API]` `GET /ml/evaluations/{id}/results` | Fetch detailed results |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_ml__create_evaluation → define eval
[MCP] mcp__voyant_ml__run_evaluation → execute
[MCP] mcp__voyant_ml__evaluation_results → get scores
[AGENT] "Evaluate the sales agent with these 20 test questions"
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Test Cases | ✅ | ✅ | ✅ |
| AI Judge | ✅ | ✅ | ✅ |
| Tool Verification | ⚠️ | ⚠️ | ✅ (check MCP tools used) |
| Detailed Results | ✅ | ✅ | ✅ |
| **Agent self-eval** | ❌ | ❌ | ✅ MCP tools |

---

## Journey 19: Deploy Agent to Production

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **AIP Console** | Click "Deploy" on evaluated agent |
| 2 | **Endpoint** | Agent gets API endpoint |
| 3 | **Monitoring** | Enable monitoring and logging |
| 4 | **Access** | Share endpoint with users/apps |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Model Serving** | Click "Deploy" on agent |
| 2 | **Endpoint** | Agent gets serving endpoint |
| 3 | **Scale** | Configure scaling policy |
| 4 | **Access** | API access via token |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Agent Detail** | Click "Deploy" on agent |
| 2 | `[API]` `POST /ml/agents/{id}/deploy` | Deploy agent |
| 3 | `[WF]` `AgentDeployWorkflow` (Temporal) | Provisions endpoint, registers MCP server |
| 4 | `[SCREEN]` **Agent Endpoint** | Agent accessible via API + MCP |
| 5 | `[API]` `POST /ml/agents/{id}/chat` | Send message to agent |
| 6 | `[SCREEN]` **Production Monitor** | Real-time: messages, latency, tool calls |

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| One-click Deploy | ✅ | ✅ | ✅ |
| API Endpoint | ✅ | ✅ | ✅ |
| **MCP Endpoint** | ❌ | ❌ | ✅ Agent-as-MCP |
| Monitoring | ✅ | ✅ | ✅ |
| Scaling | ✅ | ✅ | ⚠️ (planned) |

---

## Journey 20: Monitor Agent Performance

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **AIP Monitor** | Navigate to agent monitoring |
| 2 | **Metrics** | View: calls/hour, latency, error rate |
| 3 | **Conversation Log** | Browse past conversations |
| 4 | **Tool Usage** | Which tools used, frequency |
| 5 | **Cost** | Token usage and cost estimation |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Serving Endpoint** | Click endpoint → "Monitoring" |
| 2 | **Metrics** | Latency, throughput, errors |
| 3 | **Inference Log** | Every request logged |
| 4 | **Cost** | DBU consumption |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Agent Monitor** | Navigate to agent → "Monitoring" tab |
| 2 | `[API]` `GET /ml/agents/{id}/metrics` | Fetch performance metrics |
| 3 | `[SCREEN]` **Metrics Dashboard** | Messages/hour, latency, error rate, cost |
| 4 | `[SCREEN]` **Conversation Browser** | Browse past conversations with tool call details |
| 5 | `[SCREEN]` **Tool Analytics** | Most used tools, avg response time per tool |
| 6 | `[SCREEN]` **Cost Tracker** | Token usage by model, daily/weekly/monthly |
| 7 | `[SCREEN]` **Anomaly Alerts** | Alert on unusual patterns |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_ml__agent_metrics → check performance
[MCP] mcp__voyant_ml__agent_conversations → browse logs
[AGENT] "How is the sales agent performing this week?"
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Latency Monitoring | ✅ | ✅ | ✅ |
| Error Tracking | ✅ | ✅ | ✅ |
| Conversation Log | ✅ | ⚠️ Inference tables | ✅ |
| Tool Analytics | ✅ | ❌ | ✅ |
| Cost Tracking | ✅ | ✅ DBU | ✅ Token-based |
| **Agent self-monitor** | ❌ | ❌ | ✅ MCP |

---

## Journey 21: Build and Deploy MCP Tools

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Palantir has zero MCP support |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Databricks has zero MCP support |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **MCP Tools** (new) | Navigate to MCP Tools management |
| 2 | `[SCREEN]` **Tool Builder** | Define tool: name, description, input schema |
| 3 | `[SCREEN]` **Function Editor** (Monaco) | Write handler function (Python) |
| 4 | `[API]` `POST /mcp/tools` | Register tool |
| 5 | `[SCREEN]` **Test Panel** | Test tool with sample input |
| 6 | `[API]` `POST /mcp/tools/{id}/deploy` | Deploy to MCP server |
| 7 | `[SCREEN]` **Tool Registry** | Browse all 80+ MCP tools |
| 8 | `[SCREEN]` **Tool Analytics** | Usage stats, latency, error rate |

#### ASCII Wireframe: MCP Tool Builder

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  MCP Tools                                [User ▾]     │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ MCP Tool Registry ─── [+ Create Tool] ───────────┐│
│          │ │                                                    ││
│          │ │  Category    │ Tools │ Usage/hr │ Avg Latency      ││
│          │ │  Ontology    │ 15    │ 342      │ 23ms             ││
│          │ │  SQL         │ 3     │ 189      │ 45ms             ││
│          │ │  Scraper     │ 13    │ 67       │ 1.2s             ││
│          │ │  ML          │ 8     │ 23       │ 120ms            ││
│          │ │  Governance  │ 8     │ 56       │ 12ms             ││
│          │ │  Search      │ 3     │ 234      │ 35ms             ││
│          │ │                                                    ││
│          │ │ ┌─ Create Tool ─────────────────────────────────┐  ││
│          │ │ │ Name: [voyant.custom.my_tool             ]     │  ││
│          │ │ │ Description: [Custom analysis tool       ]     │  ││
│          │ │ │ Input Schema:                                  │  ││
│          │ │ │ ┌────────────────────────────────────────┐    │  ││
│          │ │ │ │ {"type": "object", "properties": {     │    │  ││
│          │ │ │ │   "query": {"type": "string"},         │    │  ││
│          │ │ │ │   "limit": {"type": "integer"}         │    │  ││
│          │ │ │ │ }, "required": ["query"]}              │    │  ││
│          │ │ │ └────────────────────────────────────────┘    │  ││
│          │ │ │ Handler:                                      │  ││
│          │ │ │ ┌────────────────────────────────────────┐    │  ││
│          │ │ │ │ def handler(query: str, limit: int=10): │    │  ││
│          │ │ │ │     results = search(query)             │    │  ││
│          │ │ │ │     return results[:limit]               │    │  ││
│          │ │ │ └────────────────────────────────────────┘    │  ││
│          │ │ │                                    [Test] [Deploy]││
│          │ │ └────────────────────────────────────────────────┘  ││
│          │ └────────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| MCP Protocol | ❌ | ❌ | ✅ 80+ tools |
| Visual Tool Builder | ❌ | ❌ | ✅ |
| Function Editor | ❌ | ❌ | ✅ Monaco |
| Tool Analytics | ❌ | ❌ | ✅ |
| Tool Registry | ❌ | ❌ | ✅ |
| **Voyant-unique** | ❌ | ❌ | ✅ Exclusive |

---

## Journey 22: Create Capsule (Portable Intelligence Recipe)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Palantir has no capsule concept |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Databricks has no capsule concept |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Capsules** (`view-capsules.ts`) | Click "Create Capsule" |
| 2 | `[SCREEN]` **Capsule Builder** | Define: name, description, version |
| 3 | `[SCREEN]` **Recipe Editor** | Configure steps: agents, tools, workflows, prompts |
| 4 | `[SCREEN]` **Signing** | Ed25519 signature for integrity |
| 5 | `[API]` `POST /capsules` | Create capsule |
| 6 | `[SCREEN]` **Capsule Registry** | Browse, install, share capsules |
| 7 | `[API]` `POST /capsules/{id}/execute` | Run capsule |
| 8 | `[SCREEN]` **Execution Log** | View step-by-step execution |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_capsules__create_capsule → create capsule
[MCP] mcp__voyant_capsules__list_capsules → browse registry
[MCP] mcp__voyant_capsules__execute_capsule → run
[AGENT] "Create a capsule that scrapes competitor prices and generates a report"
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Portable Recipes | ❌ | ❌ | ✅ Capsules |
| Signing | ❌ | ❌ | ✅ Ed25519 |
| Agent Composition | ❌ | ❌ | ✅ Multi-agent |
| **Voyant-unique** | ❌ | ❌ | ✅ Exclusive |

---

# PART E: GOVERNANCE OFFICER JOURNEYS

---

## Journey 23: Configure RBAC Policies

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Admin Console** | Navigate to "Access Control" |
| 2 | **Roles** | Create/edit roles (Viewer, Editor, Admin) |
| 3 | **Permissions** | Assign permissions per role (read/write/admin on types) |
| 4 | **Users** | Assign roles to users |
| 5 | **Markings** | Add security markings (classification levels) |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Admin Console** | Navigate to "Access Control" |
| 2 | **Workspace ACLs** | Set permissions on workspace objects |
| 3 | **Unity Catalog** | GRANT/REVOKE on catalogs, schemas, tables |
| 4 | **Service Principals** | Manage service principal access |
| 5 | **Groups** | Create groups, assign to roles |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Governance** (`view-governance.ts`) | Navigate to Governance |
| 2 | `[API]` `GET /governance/roles` | List all roles |
| 3 | `[SCREEN]` **Role Editor** | Create role: name, description, permissions |
| 4 | `[API]` `POST /governance/roles` | Save role (synced to SpiceDB + Keycloak) |
| 5 | `[SCREEN]` **Permission Matrix** | Grid: roles × resources × actions |
| 6 | `[API]` `POST /governance/assignments` | Assign role to user/group |
| 7 | `[SCREEN]` **User List** | View all users with roles |
| 8 | Keycloak | SSO/SAML/LDAP integration |

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Roles | ✅ | ✅ | ✅ |
| Permissions | ✅ Fine-grained | ✅ GRANT/REVOKE | ✅ SpiceDB |
| SSO/SAML | ✅ | ✅ | ✅ Keycloak |
| Markings | ✅ | ❌ | ⚠️ (planned) |
| **Agent RBAC** | ❌ | ❌ | ✅ Per-agent perms |

---

## Journey 24: Set Up Row-Level Security

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Object Security** | Navigate to object type security |
| 2 | **Policy** | Create row-level policy: "Users see only their region's data" |
| 3 | **Conditions** | Define: `user.region == object.region` |
| 4 | **Apply** | Policy enforced on all queries |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Unity Catalog** | `CREATE ROW FILTER` |
| 2 | **Filter Function** | Write SQL function returning boolean |
| 3 | **Apply** | `ALTER TABLE ... SET ROW FILTER` |
| 4 | **Test** | Verify users see only their rows |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Governance → Row Security** | Navigate to row-level security |
| 2 | `[API]` `GET /governance/row-filters` | List existing filters |
| 3 | `[SCREEN]` **Filter Builder** | Create filter: table, condition, roles |
| 4 | `[API]` `POST /governance/row-filters` | Save filter (registered in Ranger) |
| 5 | `[SCREEN]` **Test Panel** | Test filter as different users |
| 6 | Ranger | Apache Ranger enforces on all queries |

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Row Filters | ✅ | ✅ Unity Catalog | ✅ Ranger |
| Visual Builder | ⚠️ | ❌ SQL only | ✅ Filter Builder |
| Test as User | ⚠️ | ❌ | ✅ |
| **Agent filtering** | ❌ | ❌ | ✅ Automatic |

---

## Journey 25: Configure Column-Level Masking

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Data Security** | Navigate to column masking |
| 2 | **Masking Policy** | Create: "Mask SSN for non-HR roles" |
| 3 | **Rules** | Define masking: hash, partial, null, regex |
| 4 | **Apply** | Policy enforced automatically |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Unity Catalog** | `CREATE COLUMN MASK` |
| 2 | **Mask Function** | Write masking function |
| 3 | **Apply** | `ALTER TABLE ... ALTER COLUMN ... SET MASK` |
| 4 | **Test** | Verify masking works for different roles |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Governance → Column Masking** | Navigate to column masking |
| 2 | `[API]` `GET /governance/masking-rules` | List existing rules |
| 3 | `[SCREEN]` **Masking Builder** | Create: table, column, mask type, roles exempted |
| 4 | `[API]` `POST /governance/masking-rules` | Save rule (registered in Ranger) |
| 5 | `[SCREEN]` **Preview** | Preview masked vs unmasked data |
| 6 | Ranger | Apache Ranger enforces on all queries |

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Column Masking | ✅ | ✅ | ✅ Ranger |
| Mask Types | ✅ Hash/Partial/Null | ✅ Custom functions | ✅ Hash/Partial/Null/Regex |
| Visual Builder | ⚠️ | ❌ | ✅ Masking Builder |
| Preview | ❌ | ❌ | ✅ |

---

## Journey 26: Review Audit Logs

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Admin Console** | Navigate to "Audit Logs" |
| 2 | **Log Viewer** | Search/filter audit entries |
| 3 | **Details** | Click entry: who, what, when, where, result |
| 4 | **Export** | Export logs for compliance |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **System Tables** | Query `system.access.audit` |
| 2 | **Dashboard** | Pre-built audit dashboard |
| 3 | **Search** | SQL queries on audit data |
| 4 | **Export** | Export to Delta table |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Audit** (`view-audit.ts`) | Navigate to Audit in sidebar |
| 2 | `[API]` `GET /governance/audit` | Fetch audit logs |
| 3 | `[SCREEN]` **Audit Log Viewer** | Table: timestamp, user, action, resource, result |
| 4 | `[SCREEN]` **Filters** | Filter by: user, action, resource, date range |
| 5 | `[SCREEN]` **Detail Panel** | Click entry → full details (IP, user agent, changes) |
| 6 | `[API]` `GET /governance/audit/export` | Export as CSV/JSON |

#### ASCII Wireframe: Audit Log

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Audit Log                                 [User ▾]    │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Audit Log ──── [Filter] [Export] ─────────────────┐│
│          │ │                                                    ││
│          │ │  Time       │ User      │ Action      │ Resource   ││
│          │ │  14:32:01   │ john@acme │ CREATE      │ ObjectType ││
│          │ │  14:31:45   │ agent-1   │ QUERY       │ SQL        ││
│          │ │  14:30:12   │ jane@acme │ UPDATE      │ Object     ││
│          │ │  14:29:55   │ agent-2   │ SCRAPE      │ ScrapeJob  ││
│          │ │  14:28:30   │ admin     │ RBAC_CHANGE │ Role       ││
│          │ │                                                    ││
│          │ │ ┌─ Detail: CREATE ObjectType ─────────────────────┐││
│          │ │ │ User: john@acme (IP: 10.0.1.45)                 │││
│          │ │ │ Resource: ObjectType "Supplier"                  │││
│          │ │ │ Changes: {name: "Supplier", properties: [...]}   │││
│          │ │ │ Result: SUCCESS                                  │││
│          │ │ └─────────────────────────────────────────────────┘││
│          │ └────────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Log Viewer | ✅ | ✅ System Tables | ✅ |
| Search/Filter | ✅ | ✅ SQL | ✅ Visual |
| Detail View | ✅ | ✅ | ✅ |
| Export | ✅ | ✅ | ✅ |
| **Agent audit** | ❌ | ❌ | ✅ Agent actions logged |

---

## Journey 27: Set Up Data Retention Policies

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Admin Console** | Navigate to "Data Retention" |
| 2 | **Policy** | Create: "Delete records older than 7 years" |
| 3 | **Apply** | Apply to datasets |
| 4 | **Monitor** | Track deletions |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Unity Catalog** | Set table properties: `TTL`, `delta.logRetentionDuration` |
| 2 | **VACUUM** | Periodic vacuum of old data |
| 3 | **Policies** | Configure via workspace admin |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Governance → Retention** | Navigate to retention policies |
| 2 | `[API]` `GET /governance/retention` | List policies |
| 3 | `[SCREEN]` **Policy Builder** | Create: scope (table/object type), duration, action |
| 4 | `[API]` `POST /governance/retention` | Save policy |
| 5 | `[WF]` Retention workflow (Temporal) | Periodic cleanup |
| 6 | `[SCREEN]` **Monitor** | Track deletions, storage reclaimed |

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Retention Policies | ✅ | ✅ TTL/VACUUM | ✅ Temporal |
| Visual Builder | ⚠️ | ❌ | ✅ |
| Auto-cleanup | ✅ | ✅ | ✅ Temporal |
| Audit Trail | ✅ | ⚠️ | ✅ |

---

## Journey 28: GDPR Right-to-Deletion

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Data Request** | Receive GDPR deletion request |
| 2 | **Search** | Find all records for the individual across datasets |
| 3 | **Delete** | Execute deletion across all datasets |
| 4 | **Verify** | Verify deletion complete |
| 5 | **Document** | Generate deletion certificate |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Manual Process** | No native GDPR workflow |
| 2 | **SQL** | `DELETE FROM ... WHERE person_id = ...` |
| 3 | **Delta VACUUM** | Vacuum deleted data |
| 4 | **Audit** | Log deletion in audit log |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Governance → GDPR** | Navigate to GDPR compliance |
| 2 | `[API]` `POST /governance/gdpr/deletion-request` | Create deletion request |
| 3 | `[SCREEN]` **Request Form** | Enter: subject identifier, data scope |
| 4 | `[WF]` `GDPRDeletionWorkflow` (Temporal) | Finds all records across ontology + data |
| 5 | `[SCREEN]` **Progress Tracker** | Track: tables scanned, records found, deleted |
| 6 | `[API]` `GET /governance/gdpr/{id}/status` | Check request status |
| 7 | `[SCREEN]` **Completion Certificate** | Generate deletion certificate |
| 8 | `[SCREEN]` **Audit Log** | Full audit trail of deletion |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_governance__gdpr_deletion → initiate deletion
[MCP] mcp__voyant_governance__gdpr_status → check progress
[AGENT] "Process GDPR deletion for user john@example.com"
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| GDPR Workflow | ⚠️ Manual | ❌ Manual SQL | ✅ Automated |
| Cross-table Scan | ✅ | ❌ | ✅ Ontology-aware |
| Progress Tracking | ❌ | ❌ | ✅ Temporal |
| Certificate | ❌ | ❌ | ✅ |
| **Agent-driven** | ❌ | ❌ | ✅ MCP |

---

# PART F: SCRAPER OPERATOR JOURNEYS

---

## Journey 29: Create Scraping Task (URL + Selectors)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Palantir has zero scraping capability |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Databricks has zero scraping capability |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Scraper** (`view-scraper.ts`) | Navigate to Scraper → "Create Task" |
| 2 | `[SCREEN]` **Task Form** | Enter: URLs, CSS/XPath selectors, options |
| 3 | `[API]` `POST /scraper/jobs` | Create scrape job |
| 4 | `[WF]` `ScrapeJobWorkflow` (Temporal) | Executes: fetch → extract → store |
| 5 | `[SCREEN]` **Job Monitor** | Real-time: pages fetched, bytes processed |
| 6 | `[API]` `GET /scraper/jobs/{id}` | Check job status |
| 7 | `[SCREEN]` **Results** | View extracted data |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_scraper__create_task → create scrape job
[MCP] mcp__voyant_scraper__get_status → check status
[MCP] mcp__voyant_scraper__get_results → fetch results
[AGENT] "Scrape product prices from https://example.com/products"
```

---

## Journey 30: Use Template Library (Amazon, Google Maps, etc.)

### Palantir Foundry

N/A — No scraping capability.

### Databricks

N/A — No scraping capability.

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Scraper → Templates** | Browse template library by category |
| 2 | `[SCREEN]` **Category Filter** | Select: E-Commerce / Maps / News / Finance / Jobs |
| 3 | `[SCREEN]` **Template Detail** | View: name, site pattern, selectors, parameters |
| 4 | `[API]` `GET /scraper/templates` | Fetch templates |
| 5 | `[SCREEN]` **Run Template** | Fill in parameters (URL, search term, page count) |
| 6 | `[API]` `POST /scraper/templates/{id}/run` | Execute with parameters |
| 7 | `[SCREEN]` **Results** | View extracted data |

#### ASCII Wireframe: Template Library

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Scraper → Templates                      [User ▾]     │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Template Library ─── [All] [E-Commerce] [Maps] ──┐│
│          │ │                [News] [Finance] [Jobs]              ││
│          │ │                                                     ││
│          │ │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐  ││
│          │ │  │ Amazon       │ │ Google Maps  │ │ LinkedIn   │  ││
│          │ │  │ Products     │ │ Places       │ │ Jobs       │  ││
│          │ │  │ 🛒 ecommerce │ │ 🗺 maps      │ │ 💼 jobs    │  ││
│          │ │  │ Used: 1,234  │ │ Used: 890    │ │ Used: 567  │  ││
│          │ │  │ Rate: 94.2%  │ │ Rate: 97.1%  │ │ Rate: 88.5%│  ││
│          │ │  │ [Use]        │ │ [Use]        │ │ [Use]      │  ││
│          │ │  └──────────────┘ └──────────────┘ └────────────┘  ││
│          │ │                                                     ││
│          │ │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐  ││
│          │ │  │ Zillow       │ │ Indeed       │ │ Twitter/X  │  ││
│          │ │  │ Listings     │ │ Jobs         │ │ Posts      │  ││
│          │ │  │ 🏠 realestate│ │ 💼 jobs      │ │ 📱 social  │  ││
│          │ │  │ [Use]        │ │ [Use]        │ │ [Use]      │  ││
│          │ │  └──────────────┘ └──────────────┘ └────────────┘  ││
│          │ └────────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Scraping Engine | ❌ | ❌ | ✅ Playwright + Scrapy |
| Template Library | ❌ | ❌ | ✅ 50+ templates |
| Parameterization | ❌ | ❌ | ✅ |
| Success Tracking | ❌ | ❌ | ✅ |
| **Voyant-unique** | ❌ | ❌ | ✅ Exclusive |

---

## Journey 31: Build Visual Scraping Workflow

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Palantir has zero scraping capability. No visual web automation builder. |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Databricks has zero scraping capability. Users must build custom notebooks with requests/BeautifulSoup. |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Scraper → Builder** | Click "Visual Workflow Builder" |
| 2 | `[SCREEN]` **Workflow Canvas** | Drag nodes from palette: Navigate → Wait → Extract → Click → Loop |
| 3 | `[SCREEN]` **Node Config** | Configure each node: URL, selector, action, wait time |
| 4 | `[SCREEN]` **Preview** | Run step-by-step with live browser preview (Browserless) |
| 5 | `[API]` `POST /scraper/workflows` | Save workflow definition |
| 6 | `[API]` `POST /scraper/workflows/{id}/run` | Execute full workflow |
| 7 | `[WF]` `ScrapeWorkflowExecution` (Temporal) | Orchestrates: navigate → wait → extract → loop |
| 8 | `[SCREEN]` **Execution Log** | Step-by-step execution with timing and screenshots |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_scraper__create_workflow → define workflow steps
[MCP] mcp__voyant_scraper__run_workflow → execute
[MCP] mcp__voyant_scraper__get_workflow_status → monitor
[AGENT] "Build a workflow to crawl all product pages on site X, scroll to load more, extract titles and prices"
```

#### ASCII Wireframe: Visual Scraper Builder

```
┌──────────────────────────────────────────────────────────────────┐
│ Scraper Workflow Builder: "Product Crawler"          [Run] [Save] │
├──────────────────────────────────────────────────────────────────┤
│ ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────────┐ │
│ │Navigate│─→│ Wait   │─→│Extract │─→│Click   │─→│Loop/Next   │ │
│ │URL     │  │2s      │  │CSS     │  │Next    │  │Page        │ │
│ │        │  │        │  │.product│  │Page    │  │Max: 10     │ │
│ │        │  │        │  │-title  │  │Button  │  │            │ │
│ └────────┘  └────────┘  └────────┘  └────────┘  └────────────┘ │
│                                                                   │
│ ┌─ Node Details ─────────────────────────────────────────────┐   │
│ │ Extract: CSS Selector                                      │   │
│ │ Selector: [.product-title]                                 │   │
│ │ Attribute: [text]                                          │   │
│ │ Output: [product_names[]]                                  │   │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                   │
│ ┌─ Live Preview ─────────────────────────────────────────────┐   │
│ │ [Browserless screenshot showing extracted elements          │   │
│ │  highlighted on the page]                                   │   │
│ └────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Visual Workflow | ❌ | ❌ | ✅ React Flow canvas |
| Live Preview | ❌ | ❌ | ✅ Browserless |
| Node Types | ❌ | ❌ | 8 types (Navigate/Wait/Extract/Click/Scroll/Loop/Condition/Export) |
| Reusable Workflows | ❌ | ❌ | ✅ Save & share |
| Agent-built | ❌ | ❌ | ✅ MCP tools |
| **Voyant-unique** | ❌ | ❌ | ✅ Exclusive |

---

## Journey 32: Configure Anti-Bot (CAPTCHA, Proxy, Fingerprint)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Palantir has zero web scraping or anti-bot capability. Foundry connects only to authorized data sources. |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Databricks has no built-in scraping. Users building scrapers in notebooks have no anti-bot support. |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Scraper → Anti-Bot** | Navigate to anti-bot configuration panel |
| 2 | `[SCREEN]` **CAPTCHA Solver** | Enable CAPTCHA solving (2Captcha / AntiCaptcha integration) |
| 3 | `[SCREEN]` **Proxy Config** | Configure proxy pool: residential/datacenter, rotation strategy, geo-targeting |
| 4 | `[API]` `PUT /scraper/config/anti-bot` | Save anti-bot configuration |
| 5 | `[SCREEN]` **Fingerprint** | Enable browser fingerprint randomization (canvas, WebGL, fonts, screen) |
| 6 | `[SCREEN]` **Rate Limiting** | Set: requests/second, concurrent sessions, delay between requests |
| 7 | `[SCREEN]` **User-Agent Pool** | Manage rotating user agent strings (100+ pre-loaded) |
| 8 | `[SCREEN]` **Test Panel** | Test anti-bot config against target site |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_scraper__configure_anti_bot → set anti-bot config
[MCP] mcp__voyant_scraper__test_anti_bot → verify config works
[AGENT] "Enable residential proxy rotation and CAPTCHA solving for the Amazon scraper"
```

#### ASCII Wireframe: Anti-Bot Configuration

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Scraper → Anti-Bot                       [User ▾]     │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Anti-Bot Configuration ───────────────────────────┐│
│          │ │                                                     ││
│          │ │ CAPTCHA Solving:  [☑ Enabled]                       ││
│          │ │   Provider: [2Captcha ▾]  API Key: [••••••••]       ││
│          │ │   Types: ☑ reCAPTCHA ☑ hCaptcha ☑ Cloudflare       ││
│          │ │                                                     ││
│          │ │ Proxy Pool:  [☑ Enabled]                            ││
│          │ │   Type: [Residential ▾]  Rotation: [Per-request ▾]  ││
│          │ │   Providers: [Bright Data ▾] [Oxylabs ▾]            ││
│          │ │   Geo: [US ▾] [EU ▾]  Pool size: [500 IPs]         ││
│          │ │                                                     ││
│          │ │ Fingerprint:  [☑ Enabled]                           ││
│          │ │   Canvas: ☑  WebGL: ☑  Fonts: ☑  Screen: ☑         ││
│          │ │                                                     ││
│          │ │ Rate Limiting:                                      ││
│          │ │   Max req/s: [5]  Delay: [1-3s random]              ││
│          │ │   Concurrent: [3]  Max pages/session: [100]         ││
│          │ │                                                     ││
│          │ │ User-Agent Pool: [127 agents loaded]                ││
│          │ │   Chrome: 45  Firefox: 38  Safari: 22  Edge: 22     ││
│          │ │                                            [Save]   ││
│          │ └─────────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| CAPTCHA Solving | ❌ | ❌ | ✅ 2Captcha/AntiCaptcha |
| Proxy Rotation | ❌ | ❌ | ✅ Residential + Datacenter |
| Browser Fingerprint | ❌ | ❌ | ✅ Canvas/WebGL/Fonts/Screen |
| Rate Limiting | ❌ | ❌ | ✅ Per-task configurable |
| User-Agent Rotation | ❌ | ❌ | ✅ 127+ agents |
| Geo-targeting | ❌ | ❌ | ✅ Country-level proxy selection |
| **Voyant-unique** | ❌ | ❌ | ✅ Exclusive |

---

## Journey 33: Schedule Recurring Scrape

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Palantir has zero scraping capability. Data pipelines can be scheduled, but not web scraping. |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Databricks Jobs can schedule notebooks, but there is no scraping infrastructure. Users would need to build custom solutions. |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Scraper → Schedule** | Click "Schedule" on task or template |
| 2 | `[SCREEN]` **Schedule Config** | Set: cron expression, timezone, start/end dates |
| 3 | `[SCREEN]` **Advanced Options** | Configure: retry on failure, max retries, notify on completion |
| 4 | `[API]` `POST /scraper/schedules` | Create schedule |
| 5 | `[WF]` Temporal cron schedule | Automatic recurring execution via Temporal |
| 6 | `[SCREEN]` **Schedule List** | View all scheduled scrapes with next run time, status |
| 7 | `[SCREEN]` **Run History** | View past runs with success/failure, duration, artifacts |
| 8 | `[API]` `GET /scraper/schedules/{id}/runs` | Fetch run history |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_scraper__schedule_task → create schedule
[MCP] mcp__voyant_scraper__list_schedules → browse schedules
[MCP] mcp__voyant_scraper__schedule_history → view past runs
[AGENT] "Schedule the competitor price scrape to run every 6 hours"
```

#### ASCII Wireframe: Schedule Manager

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Scraper → Schedules                      [User ▾]     │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Scheduled Scrapes ──── [+ New Schedule] ─────────┐│
│          │ │                                                     ││
│          │ │  Task               │ Cron      │ Next Run │ Status ││
│          │ │  Amazon Products    │ */6 * * * │ 18:00    │ ✅ Active││
│          │ │  Google Maps NYC    │ 0 9 * * 1 │ Mon 9am  │ ✅ Active││
│          │ │  Competitor Prices  │ 0 */2 * * │ 16:00    │ ✅ Active││
│          │ │  Job Listings       │ 0 0 * * * │ Midnight │ ⏸ Paused ││
│          │ │                                                     ││
│          │ ├─ Run History: Amazon Products ──────────────────────┤│
│          │ │  Time      │ Status │ Duration │ Pages │ Artifacts  ││
│          │ │  14:00     │ ✅ OK  │ 2m 34s   │ 45    │ 2,340 rows ││
│          │ │  08:00     │ ✅ OK  │ 2m 12s   │ 45    │ 2,338 rows ││
│          │ │  02:00     │ ⚠️ 3 err│ 3m 01s  │ 42    │ 2,190 rows ││
│          │ └────────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Cron Scheduling | ❌ | ❌ | ✅ Temporal cron |
| Visual Scheduler | ❌ | ❌ | ✅ UI + cron expression |
| Retry on Failure | ❌ | ❌ | ✅ Configurable retries |
| Run History | ❌ | ❌ | ✅ Full audit trail |
| Per-task Schedule | ❌ | ❌ | ✅ Independent schedules |
| **Voyant-unique** | ❌ | ❌ | ✅ Exclusive |

---

## Journey 34: Export Results (JSON, CSV, XLSX, DB)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Palantir has zero scraping capability. Data exports from Foundry are via dataset download, not scraping-specific. |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Databricks exports via `COPY INTO` or notebook output, but has no scraping data export pipeline. |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Scraper → Results** | View scrape job results with artifact list |
| 2 | `[SCREEN]` **Export Menu** | Click "Export" on job or artifact |
| 3 | `[SCREEN]` **Format Selector** | Choose: JSON / CSV / XLSX / XML / Database (PostgreSQL/Iceberg) |
| 4 | `[API]` `POST /scraper/jobs/{id}/export` | Generate export in selected format |
| 5 | `[SCREEN]` **Download** | Download file or confirm DB write |
| 6 | `[API]` `POST /scraper/jobs/{id}/export/auto` | Configure auto-export on job completion |
| 7 | `[SCREEN]` **Export History** | View past exports with format, size, destination |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_scraper__export_results → export data
[MCP] mcp__voyant_scraper__configure_auto_export → set auto-export
[AGENT] "Export the latest Amazon scrape as XLSX and write to the products Iceberg table"
```

#### ASCII Wireframe: Export Dialog

```
┌──────────────────────────────────────────────────────────────────┐
│ Export Results: Job #scrape-a1b2c3d4                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│ Format:     (●) JSON  ( ) CSV  ( ) XLSX  ( ) XML                │
│                                                                   │
│ Destination: (●) Download  ( ) Database  ( ) S3/MinIO            │
│                                                                   │
│ Options:                                                          │
│   ☑ Include metadata  ☑ Flatten nested JSON  ☐ Compress (gzip)  │
│                                                                   │
│ Preview:                                                          │
│ ┌────────────────────────────────────────────────────────────┐   │
│ │ [{"title": "Widget A", "price": 29.99, "rating": 4.5},    │   │
│ │  {"title": "Widget B", "price": 49.99, "rating": 4.8},    │   │
│ │  ... (2,340 rows total)]                                   │   │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                   │
│ Size estimate: 1.2 MB                            [Export] [Cancel]│
└──────────────────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| JSON | ❌ (no scraping) | ❌ | ✅ |
| CSV | ❌ | ❌ | ✅ |
| XLSX | ❌ | ❌ | ✅ |
| XML | ❌ | ❌ | ✅ |
| Direct DB Write | ❌ | ❌ | ✅ PostgreSQL + Iceberg |
| Auto-export | ❌ | ❌ | ✅ On job completion |
| **Voyant-unique** | ❌ | ❌ | ✅ Exclusive |

---

# PART G: AGENT JOURNEYS (VOYANT-UNIQUE)

These journeys exist **only** in Voyant. Neither Palantir nor Databricks can do them.

---

## Journey 35: Agent Discovers New Data Source → Auto-Creates Ontology Types

### Voyant v4.0

| Step | Actor | Action |
|------|-------|--------|
| 1 | `[AGENT]` | Agent receives instruction: "Onboard the PostgreSQL sales database" |
| 2 | `[MCP]` `mcp__voyant_discovery__register_source` | Register data source |
| 3 | `[MCP]` `mcp__voyant_discovery__discover_schema` | Discover tables, columns, types |
| 4 | `[MCP]` `mcp__voyant_discovery__profile_table` | Profile each table (types, distributions, nulls) |
| 5 | `[AGENT]` | Agent analyzes schema → infers Object Types |
| 6 | `[MCP]` `mcp__voyant_ontology__create_object_type` | Create ObjectType for each table |
| 7 | `[MCP]` `mcp__voyant_ontology__create_property` | Create Properties for each column |
| 8 | `[AGENT]` | Agent infers relationships from FK columns |
| 9 | `[MCP]` `mcp__voyant_ontology__create_link_type` | Create LinkTypes for FK relationships |
| 10 | `[MCP]` `mcp__voyant_ontology__batch_create_objects` | Ingest data as Object instances |
| 11 | `[SCREEN]` **Ontology Explorer** | New types appear automatically |

#### Flow Diagram

```
Agent: "Onboard the sales database"
    │
    ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Register Source │────→│ Discover Schema │────→│ Profile Tables  │
│ (PostgreSQL)    │     │ (12 tables)     │     │ (types, nulls)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
    ┌───────────────────────────────────────────────────┘
    ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Create Object   │────→│ Create          │────→│ Create Link     │
│ Types (12)      │     │ Properties (89) │     │ Types (15)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │ Batch Ingest    │
                                                │ Objects (45,678)│
                                                └─────────────────┘
```

### Comparison

| Step | Palantir | Databricks | Voyant |
|------|----------|------------|--------|
| Auto-discovery | ⚠️ Manual wizard | ⚠️ Manual | ✅ Agent-driven |
| Auto-ontology | ❌ | ❌ | ✅ Agent creates types |
| Auto-linking | ❌ | ❌ | ✅ Agent infers FK → LinkType |
| **Voyant-unique** | ❌ | ❌ | ✅ Exclusive |

---

## Journey 36: Agent Answers NL Question Using Ontology + SQL

### Voyant v4.0

| Step | Actor | Action |
|------|-------|--------|
| 1 | `[AGENT]` | Receives: "What's the average order value by customer segment?" |
| 2 | `[AGENT]` | Intent Engine classifies: DATA_QUERY |
| 3 | `[MCP]` `mcp__voyant_ontology__list_object_types` | Load schema: Customer (segment), Order (amount) |
| 4 | `[MCP]` `mcp__voyant_ontology__search_objects` | Find relevant types |
| 5 | `[AGENT]` | Generate SQL: `SELECT c.segment, AVG(o.amount) FROM ...` |
| 6 | `[MCP]` `mcp__voyant_sql__execute_query` | Execute SQL |
| 7 | `[AGENT]` | Format results with explanation |
| 8 | `[MCP]` `mcp__voyant_sql__list_tables` | (verify table exists) |

#### Full Agent Trace

```
User: "What's the average order value by customer segment?"

Agent Trace:
  1. classify_intent() → DATA_QUERY
  2. list_object_types() → [Customer (12 props), Order (8 props)]
  3. search_objects("segment") → Customer.segment found
  4. search_objects("amount") → Order.amount found
  5. Plan: SQL query with JOIN
  6. validate_plan() → permissions OK
  7. execute_query("SELECT c.segment, AVG(o.amount) ...") →
     ┌──────────────┬────────────┐
     │ segment      │ avg_amount │
     ├──────────────┼────────────┤
     │ Enterprise   │ $12,450    │
     │ Mid-Market   │ $5,230     │
     │ SMB          │ $1,890     │
     └──────────────┴────────────┘
  8. Format response with explanation
```

---

## Journey 37: Agent Traverses Relationships (Multi-Hop)

### Voyant v4.0

| Step | Actor | Action |
|------|-------|--------|
| 1 | `[AGENT]` | Receives: "Find all products ordered by Acme Corp's top sales rep" |
| 2 | `[MCP]` `mcp__voyant_ontology__search_objects` | Find Customer "Acme Corp" |
| 3 | `[MCP]` `mcp__voyant_ontology__traverse_links` | Customer → SalesRep (1 hop) |
| 4 | `[MCP]` `mcp__voyant_ontology__traverse_links` | SalesRep → Orders (2 hops) |
| 5 | `[MCP]` `mcp__voyant_ontology__traverse_links` | Orders → Products (3 hops) |
| 6 | `[AGENT]` | Aggregate and format results |

#### Traversal Visualization

```
Customer "Acme Corp"
    │
    ├──[assigned_to]──→ SalesRep "Jane Smith" (top performer)
    │                      │
    │                      ├──[placed]──→ Order #1001
    │                      │                 │
    │                      │                 ├──[contains]──→ Product "Widget A"
    │                      │                 ├──[contains]──→ Product "Widget B"
    │                      │
    │                      ├──[placed]──→ Order #1098
    │                                        │
    │                                        └──[contains]──→ Product "Service Plan"
```

### Comparison

| Capability | Palantir | Databricks | Voyant |
|------------|----------|------------|--------|
| Graph Traversal | ✅ 10-hop | ❌ | ✅ 10-hop |
| Agent-driven | ❌ | ❌ | ✅ MCP traverse |
| NL query | ❌ | ❌ | ✅ |

---

## Journey 38: Agent Executes Action on Ontology Object

### Voyant v4.0

| Step | Actor | Action |
|------|-------|--------|
| 1 | `[AGENT]` | Receives: "Approve order #1001 and notify the customer" |
| 2 | `[MCP]` `mcp__voyant_ontology__get_object` | Fetch Order #1001 |
| 3 | `[AGENT]` | Check: order status is "pending" (pre-condition met) |
| 4 | `[MCP]` `mcp__voyant_ontology__execute_action` | Execute "Approve Order" action |
| 5 | `[AGENT]` | Action side effect: send notification to customer |
| 6 | `[MCP]` `mcp__voyant_ontology__get_object` | Verify order status → "approved" |
| 7 | `[SCREEN]` **Audit Log** | Action logged with full context |

### Comparison

| Capability | Palantir | Databricks | Voyant |
|------------|----------|------------|--------|
| Action Types | ✅ Kinetics | ❌ | ✅ ActionType |
| Agent-executed | ❌ | ❌ | ✅ MCP |
| Side effects | ✅ | ❌ | ✅ Notifications + webhooks |
| Undo | ✅ | ❌ | ✅ (planned) |

---

## Journey 39: Agent Runs Scraping Task via MCP

### Voyant v4.0

| Step | Actor | Action |
|------|-------|--------|
| 1 | `[AGENT]` | Receives: "Scrape the latest product prices from competitor.com" |
| 2 | `[MCP]` `mcp__voyant_scraper__create_task` | Create scrape job with URL + selectors |
| 3 | `[MCP]` `mcp__voyant_scraper__get_status` | Monitor job progress |
| 4 | `[MCP]` `mcp__voyant_scraper__get_results` | Fetch extracted data |
| 5 | `[AGENT]` | Analyze data: "Competitor X has 15 products cheaper than ours" |
| 6 | `[MCP]` `mcp__voyant_scraper__export_results` | Export to Iceberg table |
| 7 | `[MCP]` `mcp__voyant_ontology__batch_create_objects` | Create PriceAlert objects |

### Comparison

| Capability | Palantir | Databricks | Voyant |
|------------|----------|------------|--------|
| Scraping | ❌ | ❌ | ✅ |
| Agent-triggered | ❌ | ❌ | ✅ MCP |
| Auto-analysis | ❌ | ❌ | ✅ |
| Auto-ontology | ❌ | ❌ | ✅ |

---

## Journey 40: Agent Triggers ML Training Pipeline

### Voyant v4.0

| Step | Actor | Action |
|------|-------|--------|
| 1 | `[AGENT]` | Receives: "Retrain the churn model with the latest data" |
| 2 | `[MCP]` `mcp__voyant_ml__create_experiment` | Create or reuse experiment |
| 3 | `[MCP]` `mcp__voyant_ml__start_run` | Start training run |
| 4 | `[MCP]` `mcp__voyant_sql__execute_query` | Fetch latest training data |
| 5 | `[WF]` `MLTrainingWorkflow` (Temporal) | Execute: data prep → train → evaluate |
| 6 | `[MCP]` `mcp__voyant_ml__log_metric` | Log metrics (accuracy, F1, AUC) |
| 7 | `[AGENT]` | Compare with previous: "New model: F1 0.93 vs old 0.91" |
| 8 | `[MCP]` `mcp__voyant_ml__register_model` | Register new model version |
| 9 | `[MCP]` `mcp__voyant_ml__create_endpoint` | Deploy to production endpoint |
| 10 | `[AGENT]` | "Churn model retrained and deployed. F1 improved 2.2%" |

#### Agent Pipeline Flow

```
Agent: "Retrain churn model"
    │
    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Create       │────→│ Fetch Latest │────→│ Start        │
│ Experiment   │     │ Training Data│     │ Training Run │
└──────────────┘     └──────────────┘     └──────────────┘
                                                │
                                                ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Deploy to    │←────│ Compare      │←────│ Log          │
│ Endpoint     │     │ vs Previous  │     │ Metrics      │
└──────────────┘     └──────────────┘     └──────────────┘
        │
        ▼
"Churn model deployed. F1: 0.93 (+2.2%)"
```

### Comparison

| Capability | Palantir | Databricks | Voyant |
|------------|----------|------------|--------|
| ML Training | ✅ | ✅ | ✅ MLflow-compatible |
| Agent-triggered | ❌ | ❌ | ✅ MCP |
| Auto-deploy | ❌ | ⚠️ Manual | ✅ Agent-driven |
| Auto-compare | ❌ | ❌ | ✅ |

---

# CROSS-CUTTING ANALYSIS

---

## Journey Coverage Matrix

| # | Journey | Palantir | Databricks | Voyant |
|---|---------|----------|------------|--------|
| 1 | Register Data Source | ✅ | ✅ | ✅ + Agent |
| 2 | Create ETL Pipeline | ✅ | ✅ | ✅ + LLM Transform |
| 3 | Monitor Pipeline | ✅ | ✅ | ✅ + Self-healing |
| 4 | Data Quality | ✅ | ✅ | ✅ + Agent rules |
| 5 | Data Lineage | ✅ | ✅ | ✅ + Agent explored |
| 6 | Explore Ontology | ✅ | ⚠️ Tables only | ✅ + Agent |
| 7 | SQL Editor | ✅ | ✅ | ✅ + Agent SQL |
| 8 | Semantic Search | ⚠️ Objects only | ✅ Genie | ✅ Intent Engine |
| 9 | Build Dashboard | ✅ Workshop | ✅ | ✅ + Agent-built |
| 10 | Export Data | ✅ | ✅ | ✅ + Agent export |
| 11 | Notebook | ✅ Quiver | ✅ | ✅ Ontology-aware |
| 12 | Train ML | ✅ | ✅ MLflow | ✅ + Agent train |
| 13 | Compare Runs | ✅ | ✅ MLflow | ✅ |
| 14 | Register Model | ✅ | ✅ | ✅ + Agent |
| 15 | Deploy Model | ✅ | ✅ | ✅ + Agent deploy |
| 16 | Monitor Drift | ✅ | ✅ | ✅ + Agent monitor |
| 17 | Define Agent | ✅ AIP | ✅ Agent Bricks | ✅ + Open-source |
| 18 | Evaluate Agent | ✅ | ✅ | ✅ |
| 19 | Deploy Agent | ✅ | ✅ | ✅ + MCP endpoint |
| 20 | Monitor Agent | ✅ | ✅ | ✅ |
| 21 | Build MCP Tools | ❌ | ❌ | ✅ **Unique** |
| 22 | Create Capsule | ❌ | ❌ | ✅ **Unique** |
| 23 | Configure RBAC | ✅ | ✅ | ✅ + Agent RBAC |
| 24 | Row-level Security | ✅ | ✅ | ✅ |
| 25 | Column Masking | ✅ | ✅ | ✅ |
| 26 | Audit Logs | ✅ | ✅ | ✅ + Agent audit |
| 27 | Data Retention | ✅ | ✅ | ✅ |
| 28 | GDPR Deletion | ⚠️ | ❌ | ✅ Automated |
| 29 | Create Scrape Task | ❌ | ❌ | ✅ **Unique** |
| 30 | Template Library | ❌ | ❌ | ✅ **Unique** |
| 31 | Visual Scraper | ❌ | ❌ | ✅ **Unique** |
| 32 | Anti-Bot | ❌ | ❌ | ✅ **Unique** |
| 33 | Schedule Scrape | ❌ | ❌ | ✅ **Unique** |
| 34 | Export Scrape | ❌ | ❌ | ✅ **Unique** |
| 35 | Agent Auto-ontology | ❌ | ❌ | ✅ **Unique** |
| 36 | Agent NL Query | ❌ | ❌ | ✅ **Unique** |
| 37 | Agent Multi-hop | ❌ | ❌ | ✅ **Unique** |
| 38 | Agent Actions | ❌ | ❌ | ✅ **Unique** |
| 39 | Agent Scraping | ❌ | ❌ | ✅ **Unique** |
| 40 | Agent ML Pipeline | ❌ | ❌ | ✅ **Unique** |

---

## Voyant Unique Advantages Summary

| Advantage | Journeys | Description |
|-----------|----------|-------------|
| **MCP Protocol (80+ tools)** | All agent journeys | Neither Palantir nor Databricks has MCP support |
| **Agent-First Design** | 35–40 | Every feature callable by AI agents |
| **Web Scraping Engine** | 29–34, 39 | 8,471 LOC — competitors have nothing |
| **Capsule System** | 22 | Portable intelligence recipes with Ed25519 signing |
| **Self-Hosted** | All | Full Docker deployment, no vendor lock-in |
| **Open Source** | All | Apache 2.0, community-driven |
| **Temporal Workflows** | All pipelines | Durable, self-healing orchestration |
| **Intent Engine** | 8, 36 | NL → structured execution plan |
| **GDPR Automation** | 28 | Automated deletion workflow with certificates |
| **4 Access Modes** | All | UI + API + MCP + CLI (planned) |

---

## Per-Role Feature Availability

| Feature | Data Eng | Analyst | Data Sci | Agent Eng | Gov Officer | Scraper Op |
|---------|----------|---------|----------|-----------|-------------|------------|
| Journey 1-5 | ✅ Core | 👁 Read | 👁 Read | 🔧 MCP | 🔒 Audit | — |
| Journey 6-10 | 👁 Read | ✅ Core | 👁 Read | 🔧 MCP | 🔒 Audit | — |
| Journey 11-16 | — | — | ✅ Core | 🔧 MCP | 🔒 Audit | — |
| Journey 17-22 | — | — | — | ✅ Core | 🔒 Audit | — |
| Journey 23-28 | 🔒 Apply | — | — | 🔒 Apply | ✅ Core | — |
| Journey 29-34 | — | — | — | 🔧 MCP | — | ✅ Core |
| Journey 35-40 | — | — | — | ✅ Core | — | — |

---

## API Endpoint Summary by Journey

| Journey Group | Key Endpoints | Count |
|--------------|---------------|-------|
| Data Source (1) | `POST /ingestion/sources`, `POST /ingestion/sources/{id}/discover`, `POST /ingestion/sources/{id}/sync` | 5 |
| Pipeline (2-3) | `POST /pipelines`, `POST /pipelines/{id}/run`, `GET /pipelines/{id}/runs/{run_id}` | 6 |
| Quality (4) | `POST /data/quality/rules`, `POST /data/quality/rules/{id}/run` | 4 |
| Lineage (5) | `GET /data/lineage/{dataset}`, `POST /data/lineage/track` | 3 |
| Ontology (6) | `GET /ontology/object-types`, `GET /ontology/object-types/{id}/objects`, `GET /ontology/objects/{id}/traverse` | 15 |
| SQL (7) | `POST /sql/query`, `GET /sql/tables`, `GET /sql/tables/{id}/describe` | 3 |
| Search (8) | `GET /search/query`, `POST /search/index` | 4 |
| Dashboard (9) | `POST /dashboards`, `PUT /dashboards/{id}` | 4 |
| Export (10) | `POST /export`, `POST /export/schedule` | 3 |
| ML (11-16) | `POST /ml/experiments`, `POST /ml/runs`, `POST /ml/models`, `POST /ml/endpoints` | 12 |
| Agent (17-22) | `POST /ml/agents`, `POST /ml/evaluations`, `POST /mcp/tools`, `POST /capsules` | 12 |
| Governance (23-28) | `GET /governance/roles`, `POST /governance/row-filters`, `GET /governance/audit` | 12 |
| Scraper (29-34) | `POST /scraper/jobs`, `GET /scraper/templates`, `POST /scraper/schedules` | 10 |

---

## MCP Tool Summary by Journey

| Journey Group | Key MCP Tools | Count |
|--------------|---------------|-------|
| Data Source | `mcp__voyant_discovery__register_source`, `discover_schema`, `profile_table`, `run_profiling` | 4 |
| Pipeline | `mcp__voyant_dataintel__create_pipeline`, `run_pipeline`, `pipeline_status`, `validate_quality` | 6 |
| Ontology | `mcp__voyant_ontology__create_object_type`, `search_objects`, `traverse_links`, `execute_action`, `batch_create_objects` | 15 |
| SQL | `mcp__voyant_sql__execute_query`, `list_tables`, `describe_table` | 3 |
| Search | `mcp__voyant_search__semantic_search` | 1 |
| ML | `mcp__voyant_ml__create_experiment`, `start_run`, `log_metric`, `register_model`, `create_endpoint`, `predict` | 8 |
| Agent | `mcp__voyant_ml__create_agent`, `create_evaluation`, `run_evaluation` | 5 |
| Scraper | `mcp__voyant_scraper__create_task`, `get_status`, `get_results`, `export_results`, `use_template` | 7 |
| Governance | `mcp__voyant_governance__audit_logs`, `gdpr_deletion`, `check_permissions` | 5 |

---

## VOYANT-ONLY SCREEN INDEX

All screens unique to Voyant that do not exist in Palantir or Databricks:

| Screen Name | View File | Journeys | Description |
|-------------|-----------|----------|-------------|
| Ontology Explorer | `view-ontology.ts` | 6, 35–38 | Browse types, objects, relationships with graph view |
| SQL Studio | `view-sql.ts` | 7 | Monaco editor with Trino/Spark backend |
| Semantic Search | `view-search.ts` | 8 | NL question → intent → SQL → results |
| Sources | `view-sources.ts` | 1 | Data source registration and monitoring |
| Scraper Templates | `view-scraper.ts` | 29–30 | Template library with 50+ categories |
| Scraper Builder | (new) | 31 | Visual workflow canvas (React Flow) |
| Scraper Anti-Bot | (new) | 32 | CAPTCHA, proxy, fingerprint config |
| Scraper Schedules | (new) | 33 | Recurring scrape management |
| Capsules | `view-capsules.ts` | 22 | Portable intelligence recipes |
| Audit Log | `view-audit.ts` | 26 | Full audit trail with agent actions |
| Governance | `view-governance.ts` | 23–28 | RBAC, RLS, masking, GDPR |
| Pipeline Builder | (new) | 2–3 | Visual DAG editor (React Flow) |
| Pipeline Monitor | (new) | 3 | Real-time DAG execution view |
| Data Quality | (new) | 4 | Quality rules and pass/fail dashboard |
| Data Lineage | (new) | 5 | Force-directed lineage graph |
| Dashboard Builder | (new) | 9 | Chart/table/widget builder (ECharts) |
| ML Experiments | (new) | 12–13 | Experiment tracking with run comparison |
| Model Registry | (new) | 14 | Versioned model management |
| Model Endpoints | (new) | 15–16 | Serving endpoints with monitoring |
| Agent Builder | (new) | 17 | Agent definition with MCP tool selection |
| Agent Evaluation | (new) | 18 | Test cases with AI judge scoring |
| Agent Monitor | (new) | 20 | Performance metrics, conversation browser |
| MCP Tool Builder | (new) | 21 | Visual tool definition + function editor |
| Notebook | (new) | 11 | Python/SQL cells with ontology integration |
| GDPR Compliance | (new) | 28 | Automated deletion workflow |

**Total screens:** 25 (13 existing `view-*.ts` + 12 new)

---

## KEY ARCHITECTURAL DIFFERENTIATORS

### Why Voyant Wins Where Others Can't Compete

#### 1. Agent-Native (Not Agent-Added)

| Aspect | Palantir | Databricks | Voyant |
|--------|----------|------------|--------|
| Design Philosophy | Human-first, agent bolted on | Human-first, agent bolted on | **Agent-first, human overlaid** |
| API for Agents | REST (no MCP) | REST (no MCP) | **REST + MCP (80+ tools)** |
| Agent Can Create Types | ❌ | ❌ | ✅ Via MCP tools |
| Agent Can Traverse Graph | ❌ | ❌ | ✅ 10-hop traversal |
| Agent Can Run Scraping | ❌ | ❌ | ✅ Full scraper access |
| Agent Can Train Models | ❌ | ❌ | ✅ ML pipeline access |

#### 2. Intent Engine (NL → Deterministic Execution)

```
Palantir:  NL → Object Search (limited)
Databricks: NL → Genie SQL (single table focus)
Voyant:    NL → Intent Classification → Schema Resolution → Plan Generation
           → Plan Validation → Deterministic Execution → Formatted Result
```

The Intent Engine is the key differentiator. It:
- Classifies intent (query / pipeline / scrape / analyze)
- Resolves against the full ontology schema
- Generates structured JSON execution plans (not raw SQL)
- Validates against permissions and governance rules
- Executes deterministically (no LLM in execution path)

#### 3. Scraping as a First-Class Platform

Neither Palantir nor Databricks has any scraping capability. Voyant provides:
- Playwright + Scrapy engines
- 50+ pre-built templates
- Visual workflow builder
- Anti-bot suite (CAPTCHA, proxy, fingerprint)
- Temporal-scheduled recurring scrapes
- 7 dedicated MCP tools for agent-driven scraping

#### 4. Capsule System (Portable Intelligence)

Voyant's Capsule system has no equivalent in any competitor:
- Portable recipes combining agents, tools, workflows, and prompts
- Ed25519 cryptographic signing for integrity
- Shareable across teams and deployments
- Agent-composable (agents can create and execute capsules)

#### 5. Self-Hosted + Open Source

| Aspect | Palantir | Databricks | Voyant |
|--------|----------|------------|--------|
| Deployment | Cloud-only (Palantir-managed) | Cloud-only (AWS/Azure/GCP) | **Docker (any infra)** |
| Source Code | Proprietary | Proprietary | **Apache 2.0** |
| Vendor Lock-in | High | High | **Zero** |
| Data Sovereignty | Palantir cloud | Cloud provider | **Your infrastructure** |
| Cost Model | Per-user + compute | Per-DBU | **Self-hosted (fixed infra cost)** |

---

## JOURNEY COMPLETION STATUS

| Phase | Journeys | Status | Notes |
|-------|----------|--------|-------|
| A: Data Engineer | 1–5 | ✅ Complete | All journeys fully documented |
| B: Business Analyst | 6–10 | ✅ Complete | All journeys fully documented |
| C: Data Scientist | 11–16 | ✅ Complete | All journeys fully documented |
| D: AI/Agent Engineer | 17–22 | ✅ Complete | All journeys fully documented |
| E: Governance Officer | 23–28 | ✅ Complete | All journeys fully documented |
| F: Scraper Operator | 29–34 | ✅ Complete | All journeys fully documented |
| G: Agent Journeys | 35–40 | ✅ Complete | All journeys fully documented |

**All 40 journeys documented with:**
- ✅ Step-by-step Palantir walkthrough
- ✅ Step-by-step Databricks walkthrough
- ✅ Step-by-step Voyant v4.0 walkthrough
- ✅ API endpoints (where applicable)
- ✅ MCP tools (where applicable)
- ✅ Comparison tables
- ✅ ASCII wireframes (16 screens)
- ✅ Cross-cutting analysis

---

**Created:** 2026-09-05
**Author:** Voyant Engineering
**Next review:** 2026-09-19
**Total journeys documented:** 40
**Total screens wireframed:** 16
**Total comparison tables:** 45
**Document standard:** ISO/IEC/IEEE 29148:2018 aligned
