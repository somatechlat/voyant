# Pipeline Builder — Functional Specification

**Document ID:** VOYANT-ISO-CONNECT-4.0.0
**Standard:** ISO/IEC/IEEE 29148:2018
**Version:** 1.0.0
**Last Updated:** 2026-01-15
**Status:** Draft
**Owner:** Voyant Platform Team

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Actors & Roles](#2-actors--roles)
3. [Screens / UI Views](#3-screens--ui-views)
4. [Functional Requirements](#4-functional-requirements)
5. [Data Model](#5-data-model)
6. [API Endpoints](#6-api-endpoints)
7. [Integration Points](#7-integration-points)
8. [Quality Attributes](#8-quality-attributes)
9. [Implementation Details](#9-implementation-details)

---

## 1. Module Overview

### 1.1 Purpose

The Pipeline Builder module provides a visual DAG (Directed Acyclic Graph) editor for designing, validating, scheduling, and executing multi-step data pipelines. It offers a palette of composable transform operations (Filter, Map, Join, Aggregate, Sort, Dedup, Flatten, etc.) that can be connected into execution graphs, validated for correctness, and run on-demand or via cron schedules.

### 1.2 Scope

| Capability | Source File |
|---|---|
| Pipeline / Step / Run models | `apps/pipelines/models.py` (321 lines) |
| Transform registry | `apps/pipelines/transforms.py` (589 lines) |
| DAG validation | `apps/pipelines/validator.py` (308 lines) |
| Pipeline API | `apps/pipelines/api.py` |
| Pipeline UI | `dashboard/src/views/view-pipelines.ts` (1126 lines) |

### 1.3 Position in Voyant Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                       Dashboard (Lit)                                │
│  view-pipelines.ts                                                   │
│  ├─ List View: pipeline cards + create form                          │
│  └─ Editor View: SVG canvas + palette + inspector panel              │
│     ├─ Drag-drop node creation                                       │
│     ├─ Edge connection (click source → click target)                 │
│     ├─ Canvas pan/zoom (mouse + wheel)                               │
│     └─ Validation, save, run, import/export                          │
└───────────────┬──────────────────────────────────────────────────────┘
                │ HTTP REST
┌───────────────▼──────────────────────────────────────────────────────┐
│            Pipeline API (Django Ninja)                                │
│  /v1/pipelines/* endpoints                                           │
│  ├─ Pipeline CRUD                                                    │
│  ├─ Step CRUD                                                        │
│  ├─ DAG validation                                                   │
│  ├─ Run trigger + history                                            │
│  ├─ Transform catalog                                                │
│  └─ Import/export                                                    │
├──────────────────────────────────────────────────────────────────────┤
│  Services Layer                                                      │
│  ├─ PipelineExecutor: step-by-step DAG execution                     │
│  ├─ TransformRegistry: composable transform operations               │
│  └─ DAG Validator: cycle detection, schema checks, topo-sort        │
├──────────────────────────────────────────────────────────────────────┤
│  Django ORM (PostgreSQL)              │  External Systems             │
│  voyant_pipeline                      │  Trino (SQL queries)          │
│  voyant_pipeline_step                 │  Temporal (workflow mgmt)     │
│  voyant_pipeline_run                  │  S3 (file sources)            │
│  voyant_pipeline_step_run             │  Iceberg (lakehouse)          │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.4 Key Differentiators

| Feature | Voyant Pipeline Builder | Databricks Workflows | Palantir Pipeline Builder |
|---|---|---|---|
| Visual DAG editor | Browser-based SVG canvas | Notebook-centric | Code-first |
| Transform palette | 12 built-in transforms with drag-drop | Task-based (Notebook/Python) | Template-based |
| Client-side validation | Real-time cycle detection + schema checks | Pre-submit validation | Server-side |
| Transform composability | `TransformBase.execute()` interface | Custom code | Template functions |
| Import/Export JSON | Full pipeline export with layout | Notebook export | Not native |
| Cron scheduling | Built-in with timezone support | Job clusters | Cadence-based |
| Run history | Pipeline-level + step-level tracking | Run history | Audit trail |

---

## 2. Actors & Roles

| Actor | Role | Permissions | Description |
|---|---|---|---|
| Data Engineer | `write:pipelines` | Full CRUD on pipelines, steps; trigger runs | Primary user — designs and maintains data pipelines |
| Data Analyst | `read:*` | View pipelines and run history | Monitors pipeline status and results |
| Platform Admin | `write:pipelines` | Full access + scheduling management | Manages production pipelines and schedules |
| MCP Agent | `read:*` / `write:pipelines` | Programmatic pipeline management | AI agents that trigger or monitor pipelines |

---

## 3. Screens / UI Views

### 3.1 Pipeline List View

**Route:** `/admin/pipelines`
**Component:** `<view-pipelines>` — `dashboard/src/views/view-pipelines.ts`
**Mode:** `editorMode === 'list'`

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ▓▓ Sidebar ▓▓│  Pipelines                                                │
│              │                                                           │
│              │  [Import JSON] [Refresh] [+ New Pipeline]                  │
│              │                                                           │
│              │  ┌──────────────────────────────────────────────────────┐  │
│              │  │ Create New Pipeline                                  │  │
│              │  │ Name: [Customer ETL    ] Desc: [Daily refresh  ]     │  │
│              │  │ Schedule (cron): [0 */6 * * *]                       │  │
│              │  │                              [Cancel] [Create]       │  │
│              │  └──────────────────────────────────────────────────────┘  │
│              │                                                           │
│              │  ┌──────────────────────────────────────────────────────┐  │
│              │  │ Customer ETL                    [active]             │  │
│              │  │ Daily customer data refresh                           │  │
│              │  │ 4 steps · Last run: 2h ago                           │  │
│              │  │                                                       │  │
│              │  │ [▶ Run] [✏️ Editor] [📋 History] [📥 Export] [🗑️]    │  │
│              │  └──────────────────────────────────────────────────────┘  │
│              │                                                           │
│              │  ┌──────────────────────────────────────────────────────┐  │
│              │  │ Product Sync                    [draft]              │  │
│              │  │ Sync product catalog from warehouse                   │  │
│              │  │ 2 steps · No runs yet                                │  │
│              │  │                                                       │  │
│              │  │ [▶ Run] [✏️ Editor] [📋 History] [📥 Export] [🗑️]    │  │
│              │  └──────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

**API Endpoints Called:**

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/v1/pipelines` | Load all pipelines |
| `GET` | `/v1/pipelines/transforms/catalog` | Load available transform types |
| `POST` | `/v1/pipelines` | Create new pipeline |
| `POST` | `/v1/pipelines/{id}/run` | Trigger pipeline run |
| `DELETE` | `/v1/pipelines/{id}` | Delete pipeline |
| `POST` | `/v1/pipelines/import` | Import pipeline from JSON |

**User Interactions:**

| Action | Trigger | Handler | Code Reference |
|---|---|---|---|
| Create pipeline | "+ New Pipeline" button | `createPipeline()` | `view-pipelines.ts:240` |
| Open editor | "✏️ Editor" button | `openEditor(pipeline)` | `view-pipelines.ts:271` |
| Run pipeline | "▶ Run" button | `runPipeline(id)` | `view-pipelines.ts:532` |
| Export pipeline | "📥 Export" button | `exportPipeline()` | `view-pipelines.ts:556` |
| Import pipeline | "Import JSON" button | `importPipeline()` | `view-pipelines.ts:580` |
| Delete pipeline | "🗑️" button | `deletePipeline(id)` | `view-pipelines.ts:258` |

**Loading State:** Standard loading indicator when `this.loading === true`
**Empty State:** Implicit — no pipelines shows empty list

---

### 3.2 Pipeline Editor — DAG Canvas

**Trigger:** Click "✏️ Editor" on a pipeline card
**Mode:** `editorMode === 'editor'`

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ▓▓ Sidebar ▓▓│  Customer ETL — Editor                                        │
│              │  [← Back] [💾 Save] [✓ Validate] [▶ Run] [📋 Runs] [📥 Exp]  │
│              │                                                               │
│              │  ┌──────────────┐                                             │
│              │  │ 📥 Source    │  ┌──────────────┐  ┌──────────────┐         │
│              │  │              │──│⚙️ Transform  │──│🔍 Filter     │         │
│              │  └──────────────┘  │              │  │              │         │
│              │                    └──────┬───────┘  └──────┬───────┘         │
│              │                           │                 │                 │
│              │                           ▼                 ▼                 │
│              │                    ┌──────────────┐  ┌──────────────┐         │
│              │                    │📊 Aggregate  │  │📤 Export     │         │
│              │                    │              │──│              │         │
│              │                    └──────────────┘  └──────────────┘         │
│              │                                                               │
│              │  ┌───────────────────────────────────────┐ ┌────────────────┐ │
│              │  │ PALETTE                               │ │ INSPECTOR      │ │
│              │  │ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐  │ │ Name: Filter   │ │
│              │  │ │📥  │ │⚙️  │ │🔍  │ │📊  │ │🔗  │  │ │ Type: filter   │ │
│              │  │ │Src │ │Trn │ │Flt │ │Agg │ │Join│  │ │                │ │
│              │  │ └────┘ └────┘ └────┘ └────┘ └────┘  │ │ Config:        │ │
│              │  │ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐  │ │ Field: [status]│ │
│              │  │ │↕️  │ │🧹  │ │📐  │ │🗺️  │ │📤  │  │ │ Op:    [==   ] │ │
│              │  │ │Sort│ │Dup │ │Flt │ │Map │ │Exp │  │ │ Value: [active]│ │
│              │  │ └────┘ └────┘ └────┘ └────┘ └────┘  │ │                │ │
│              │  │ ┌────┐ ┌────┐                       │ │ [🗑️ Delete]    │ │
│              │  │ │✅  │ │🔧  │                       │ │                │ │
│              │  │ │QC  │ │Cust│                       │ │ CONNECT        │ │
│              │  │ └────┘ └────┘                       │ │ [🔗 Connect]   │ │
│              │  └───────────────────────────────────────┘ └────────────────┘ │
│              │                                                               │
│              │  Validation: ✓ DAG is valid · Execution order: Ingest → ...   │
│              │  Runs: succeeded (2h ago, 45s) · failed (1d ago, timeout)     │
└──────────────────────────────────────────────────────────────────────────────┘
```

**API Endpoints Called:**

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/v1/pipelines/{id}/steps` | Load pipeline steps |
| `GET` | `/v1/pipelines/{id}/runs` | Load run history |
| `POST` | `/v1/pipelines/{id}/validate` | Validate DAG |
| `POST` | `/v1/pipelines/{id}/steps` | Create step |
| `DELETE` | `/v1/pipelines/steps/{id}` | Delete step |
| `POST` | `/v1/pipelines/{id}/run` | Trigger run |

**User Interactions:**

| Action | Trigger | Handler | Code Reference |
|---|---|---|---|
| Add node from palette | Drag-drop from palette | `addNodeFromPalette(type, e)` | `view-pipelines.ts:323` |
| Add node at center | Click palette item | `addNodeAtCenter(type)` | `view-pipelines.ts:342` |
| Select node | Click node on canvas | `selectNode(node)` | `view-pipelines.ts:363` |
| Move node | Mouse drag on node | `onNodeMouseDown(node, e)` | `view-pipelines.ts:403` |
| Connect nodes | Click source → click target | `startConnect(id)` + `selectNode(target)` | `view-pipelines.ts:380` |
| Delete node | Inspector "🗑️ Delete" button | `removeNode(id)` | `view-pipelines.ts:357` |
| Update node name | Inspector name input | `updateNodeName(name)` | `view-pipelines.ts:388` |
| Update node config | Inspector config inputs | `updateNodeConfig(key, value)` | `view-pipelines.ts:394` |
| Pan canvas | Mouse drag on canvas background | `onCanvasMouseDown(e)` | `view-pipelines.ts:430` |
| Zoom canvas | Mouse wheel | `onCanvasWheel(e)` | `view-pipelines.ts:454` |
| Validate DAG | "✓ Validate" button | `validateDag()` | `view-pipelines.ts:462` |
| Save DAG | "💾 Save" button | `saveDag()` | `view-pipelines.ts:483` |
| Run pipeline | "▶ Run" button | `runPipeline(id)` | `view-pipelines.ts:532` |
| Remove edge | Edge context action | `removeEdge(src, tgt)` | `view-pipelines.ts:384` |

---

### 3.3 Transform Palette

**Location:** Left side of DAG editor canvas
**Code Reference:** `view-pipelines.ts:111–124`

| Icon | Type | Label | Config Fields |
|---|---|---|---|
| 📥 | `ingest` | Source | (source connection config) |
| ⚙️ | `transform` | Transform | (custom transform config) |
| 🔍 | `filter` | Filter | field, operator, value |
| 📊 | `aggregate` | Aggregate | group_by (comma-sep) |
| 🔗 | `join` | Join | left_key, right_key, join_type, right_data_field |
| ↕️ | `sort` | Sort | sort_by, sort_direction |
| 🧹 | `dedup` | Dedup | fields (comma-sep), keep (first/last) |
| 📐 | `flatten` | Flatten | field, flatten_type |
| 🗺️ | `map` | Map | expression, output_field |
| 📤 | `export` | Export | (destination config) |
| ✅ | `quality_check` | Quality | (quality rules) |
| 🔧 | `custom` | Custom | (arbitrary config) |

**Node Colors:** Each step type has a distinct color (line 92–109):
- Source/Ingest: `#3B82F6` (blue)
- Transform: `#8B5CF6` (purple)
- Filter: `#F59E0B` (amber)
- Aggregate: `#EC4899` (pink)
- Export: `#22C55E` (green)
- Quality Check: `#EF4444` (red)

---

### 3.4 Node Inspector Panel

**Trigger:** Click a node on canvas → right panel shows inspector
**Code Reference:** `view-pipelines.ts:388–399`

```
┌────────────────────────┐
│ INSPECTOR              │
│                        │
│ Name: [Filter Orders]  │
│ Type: filter           │
│                        │
│ Config:                │
│ ┌────────────────────┐ │
│ │ Field:    [status] │ │
│ │ Operator: [==    ] │ │
│ │ Value:    [active] │ │
│ └────────────────────┘ │
│                        │
│ [🗑️ Delete Node]       │
│                        │
│ CONNECT                │
│ [🔗 Start Connect]     │
└────────────────────────┘
```

**Config Fields per Transform Type** (`view-pipelines.ts:130–161`):

| Transform | Fields |
|---|---|
| `filter` | field (text), operator (select: ==/!=/>/</>=/<=/in/not_in/contains), value (text) |
| `map` | expression (text), output_field (text) |
| `join` | left_key (text), right_key (text), join_type (select: inner/left/right/full), right_data_field (text) |
| `aggregate` | group_by (text, comma-sep) |
| `sort` | sort_by (text), sort_direction (select: asc/desc) |
| `dedup` | fields (text, comma-sep), keep (select: first/last) |
| `flatten` | field (text), flatten_type (select: list/object) |

---

### 3.5 Run History Panel

**Trigger:** Click "📋 Runs" button in editor toolbar

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    Run History                              [✕ Close]    │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ #run-4821  │ succeeded │ Started 2h ago  │ Duration: 45s            │ │
│ │ Steps: 4/4 completed   │ Triggered: manual                           │ │
│ ├──────────────────────────────────────────────────────────────────────┤ │
│ │ #run-4819  │ failed    │ Started 1d ago  │ Duration: 5m 0s (timeout)│ │
│ │ Steps: 2/4 completed   │ Error: Transform step timed out            │ │
│ ├──────────────────────────────────────────────────────────────────────┤ │
│ │ #run-4815  │ succeeded │ Started 2d ago  │ Duration: 38s            │ │
│ │ Steps: 4/4 completed   │ Triggered: schedule                         │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

**Status Badges:** `active` (green), `draft` (gray), `running` (blue), `succeeded` (green), `failed` (red), `queued` (blue), `cancelled` (gray), `timeout` (gray)

---

### 3.6 Loading / Error / Empty States

| State | Condition | UI |
|---|---|---|
| **Loading pipelines** | `this.loading === true` | Standard loading indicator |
| **No pipelines** | `pipelines.length === 0` | Empty list (no special message) |
| **Validation errors** | `dagValidation.valid === false` | Red error list with cycle path messages |
| **Validation warnings** | `dagValidation.warnings.length > 0` | Yellow warning list (disconnected steps) |
| **Validation success** | `dagValidation.valid === true` | Green "✓ DAG is valid" + execution order |
| **Saving** | `this.saving === true` | "Saving..." on save button |
| **Run history loading** | `this.runsLoading === true` | Loading indicator in run panel |

---

## 4. Functional Requirements

### 4.1 Pipeline Lifecycle

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| PIPE-F-001 | Create pipeline with name, description, schedule | Unique name per tenant; returns UUID | ✅ Impl | `view-pipelines.ts:240` |
| PIPE-F-002 | Pipeline status lifecycle | draft → active → paused → archived | ✅ Impl | `apps/pipelines/models.py:22–27` |
| PIPE-F-003 | Cron schedule with timezone | `schedule` field (cron expression) + `schedule_timezone` | ✅ Impl | `apps/pipelines/models.py:44–54` |
| PIPE-F-004 | Version tracking | Auto-incrementing `version` field | ✅ Impl | `apps/pipelines/models.py:60–63` |
| PIPE-F-005 | Soft-delete pipelines | `deleted_at` with unique constraint partial index | ✅ Impl | `apps/pipelines/models.py:64–69` |
| PIPE-F-006 | Delete pipeline with confirmation | `confirm()` dialog before deletion | ✅ Impl | `view-pipelines.ts:259` |

### 4.2 DAG Editor

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| PIPE-F-010 | Visual DAG canvas with SVG nodes/edges | Nodes render as colored rects; edges as paths with arrows | ✅ Impl | `view-pipelines.ts:645+` |
| PIPE-F-011 | Drag-drop node creation from palette | Drop creates node at cursor position | ✅ Impl | `view-pipelines.ts:323` |
| PIPE-F-012 | Canvas pan (mouse drag) | Background drag pans all nodes | ✅ Impl | `view-pipelines.ts:430` |
| PIPE-F-013 | Canvas zoom (mouse wheel) | 0.2x – 3.0x zoom range | ✅ Impl | `view-pipelines.ts:454–458` |
| PIPE-F-014 | Node selection | Click node highlights it; shows inspector | ✅ Impl | `view-pipelines.ts:363` |
| PIPE-F-015 | Node drag-to-move | Drag selected node to reposition | ✅ Impl | `view-pipelines.ts:403` |
| PIPE-F-016 | Edge connection mode | Click source → enter connect mode → click target | ✅ Impl | `view-pipelines.ts:380–377` |
| PIPE-F-017 | Edge removal | Remove edge via UI action | ✅ Impl | `view-pipelines.ts:384` |
| PIPE-F-018 | Node deletion | Removes node + all connected edges | ✅ Impl | `view-pipelines.ts:357` |
| PIPE-F-019 | Node config editing | Type-specific config fields in inspector panel | ✅ Impl | `view-pipelines.ts:394` |
| PIPE-F-020 | Node name editing | Custom name per step | ✅ Impl | `view-pipelines.ts:388` |

### 4.3 DAG Validation

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| PIPE-F-030 | Cycle detection | Kahn's algorithm; reports cycle path | ✅ Impl | `apps/pipelines/validator.py:120–128` |
| PIPE-F-031 | Edge reference validation | Source/target must exist in steps | ✅ Impl | `apps/pipelines/validator.py:105–118` |
| PIPE-F-032 | Self-loop detection | `src == tgt` check | ✅ Impl | `apps/pipelines/validator.py:114` |
| PIPE-F-033 | Disconnected component warnings | Steps with no connections flagged | ✅ Impl | `apps/pipelines/validator.py:132–143` |
| PIPE-F-034 | Source node check | At least one node with no incoming edges | ✅ Impl | `apps/pipelines/validator.py:146` |
| PIPE-F-035 | Sink node check | At least one node with no outgoing edges (warning) | ✅ Impl | `apps/pipelines/validator.py:150–153` |
| PIPE-F-036 | Schema compatibility checks | Connected transforms' input/output schemas validated | ✅ Impl | `apps/pipelines/validator.py:156` |
| PIPE-F-037 | Transform config validation | Each transform's config checked via `validate_config()` | ✅ Impl | `apps/pipelines/validator.py:159` |
| PIPE-F-038 | Topological sort (execution order) | Returns valid execution order when DAG is valid | ✅ Impl | `apps/pipelines/validator.py:167–186` |

### 4.4 Pipeline Execution

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| PIPE-F-040 | Trigger manual run | `POST /v1/pipelines/{id}/run` creates PipelineRun | ✅ Impl | `view-pipelines.ts:532` |
| PIPE-F-041 | Track run status | queued → running → succeeded/failed/cancelled/timeout | ✅ Impl | `apps/pipelines/models.py:173–179` |
| PIPE-F-042 | Track step-level results | PipelineStepRun per step: status, timing, output, logs | ✅ Impl | `apps/pipelines/models.py:268–321` |
| PIPE-F-043 | Step retry on failure | `retry_count` on PipelineStep | ✅ Impl | `apps/pipelines/models.py:135–138` |
| PIPE-F-044 | Step timeout | `timeout_seconds` on PipelineStep (default 300s) | ✅ Impl | `apps/pipelines/models.py:139–142` |
| PIPE-F-045 | Step dependencies (M2M) | `depends_on` M2M field for DAG ordering | ✅ Impl | `apps/pipelines/models.py:143–149` |
| PIPE-F-046 | Run history per pipeline | `GET /v1/pipelines/{id}/runs` | ✅ Impl | `view-pipelines.ts:542` |
| PIPE-F-047 | Temporal workflow tracking | `temporal_workflow_id` field for external orchestration | ✅ Impl | `apps/pipelines/models.py:248–253` |

### 4.5 Transform Engine

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| PIPE-F-050 | Filter transform | Supports ==, !=, >, <, >=, <=, in, not_in, contains, starts_with, ends_with | ✅ Impl | `apps/pipelines/transforms.py:80–143` |
| PIPE-F-051 | Map transform | Expression mode (`eval` with sandboxed builtins) + field rename mode | ✅ Impl | `apps/pipelines/transforms.py:145–200` |
| PIPE-F-052 | Join transform | Inner/left/right/full join on key columns | ✅ Impl | `apps/pipelines/transforms.py:202+` |
| PIPE-F-053 | Aggregate transform | Group-by with count/sum/avg/min/max | ✅ Impl | `apps/pipelines/transforms.py` |
| PIPE-F-054 | Sort transform | Single-column sort ascending/descending | ✅ Impl | `apps/pipelines/transforms.py` |
| PIPE-F-055 | Dedup transform | Deduplicate by specified fields (keep first/last) | ✅ Impl | `apps/pipelines/transforms.py` |
| PIPE-F-056 | Flatten transform | Flatten nested lists or objects in a field | ✅ Impl | `apps/pipelines/transforms.py` |
| PIPE-F-057 | Transform registry | Auto-discovery via `TransformBase` subclasses | ✅ Impl | `apps/pipelines/transforms.py:25–74` |
| PIPE-F-058 | Sandboxed expression eval | `eval()` with `{"__builtins__": {}}` for Map expressions | ✅ Impl | `apps/pipelines/transforms.py:195–196` |

### 4.6 Import / Export

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| PIPE-F-060 | Export pipeline to JSON | Includes name, description, schedule, steps (with layout), edges | ✅ Impl | `view-pipelines.ts:556–578` |
| PIPE-F-061 | Import pipeline from JSON | Creates pipeline + steps + edges from file | ✅ Impl | `view-pipelines.ts:580–611` |
| PIPE-F-062 | Save DAG (full replace) | Delete existing steps, recreate from canvas state | ✅ Impl | `view-pipelines.ts:483–530` |

---

## 5. Data Model

### 5.1 Pipeline

**Table:** `voyant_pipeline`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Primary key |
| `tenant_id` | VARCHAR(255) | NOT NULL | Multi-tenancy isolation |
| `name` | VARCHAR(255) | NOT NULL | Pipeline name |
| `description` | TEXT | DEFAULT "" | Human-readable description |
| `status` | VARCHAR(20) | CHOICES, INDEX | draft / active / paused / archived |
| `schedule` | VARCHAR(128) | DEFAULT "" | Cron expression (empty = manual) |
| `schedule_timezone` | VARCHAR(64) | DEFAULT "UTC" | Timezone for schedule |
| `config` | JSONField | DEFAULT {} | Global config (default params, retry policy) |
| `version` | PositiveIntegerField | DEFAULT 1 | Auto-incrementing version |
| `deleted_at` | DateTimeField | NULL, INDEX | Soft-deletion timestamp |
| `created_at` / `updated_at` | DateTimeField | AUTO | Timestamps |

**Constraints:**
- `uq_pipeline_name_active`: UNIQUE(`tenant_id`, `name`) WHERE `deleted_at IS NULL`

**Indexes:**
- `idx_pipe_tenant_status`: (`tenant_id`, `status`)
- `idx_pipe_tenant_created`: (`tenant_id`, `-created_at`)

### 5.2 PipelineStep

**Table:** `voyant_pipeline_step`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Primary key |
| `pipeline_id` | FK → Pipeline | CASCADE | Parent pipeline |
| `step_type` | VARCHAR(32) | CHOICES | ingest / transform / quality_check / profile / export / scrape / sql_query / custom |
| `name` | VARCHAR(255) | DEFAULT "" | Human-readable step name |
| `order` | PositiveIntegerField | DEFAULT 0 | Execution order (lower runs first) |
| `config` | JSONField | DEFAULT {} | Step-specific configuration |
| `retry_count` | PositiveIntegerField | DEFAULT 0 | Retries on failure |
| `timeout_seconds` | PositiveIntegerField | DEFAULT 300 | Max execution time |
| `depends_on` | M2M → self | — | Steps that must complete first |

**Indexes:**
- `idx_step_pipeline_order`: (`pipeline_id`, `order`)

**Ordering:** `["order"]` (ascending)

### 5.3 PipelineRun

**Table:** `voyant_pipeline_run`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Primary key |
| `tenant_id` | VARCHAR(255) | NOT NULL | Multi-tenancy |
| `pipeline_id` | FK → Pipeline | CASCADE | Pipeline being executed |
| `status` | VARCHAR(20) | CHOICES, INDEX | queued / running / succeeded / failed / cancelled / timeout |
| `triggered_by` | VARCHAR(256) | DEFAULT "" | User or system that triggered |
| `trigger_type` | VARCHAR(32) | DEFAULT "manual" | manual / schedule / api |
| `parameters` | JSONField | DEFAULT {} | Runtime parameters |
| `started_at` | DateTimeField | NULL | Execution start time |
| `completed_at` | DateTimeField | NULL | Execution end time |
| `logs` | TEXT | DEFAULT "" | Aggregated execution logs |
| `result_summary` | JSONField | DEFAULT {} | Rows processed, errors, etc. |
| `error_message` | TEXT | DEFAULT "" | Error message on failure |
| `steps_completed` | PositiveIntegerField | DEFAULT 0 | Steps completed count |
| `steps_total` | PositiveIntegerField | DEFAULT 0 | Total steps count |
| `temporal_workflow_id` | VARCHAR(256) | DEFAULT "" | Temporal workflow tracking ID |
| `created_at` / `updated_at` | DateTimeField | AUTO | Timestamps |

**Indexes:**
- `idx_run_pipeline_created`: (`pipeline_id`, `-created_at`)
- `idx_run_tenant_status`: (`tenant_id`, `status`)

### 5.4 PipelineStepRun

**Table:** `voyant_pipeline_step_run`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Primary key |
| `pipeline_run_id` | FK → PipelineRun | CASCADE | Parent run |
| `step_id` | FK → PipelineStep | CASCADE | Step being executed |
| `status` | VARCHAR(20) | CHOICES, INDEX | pending / running / succeeded / failed / skipped |
| `started_at` | DateTimeField | NULL | Step start time |
| `completed_at` | DateTimeField | NULL | Step end time |
| `output_data` | JSONField | DEFAULT {} | Step output / artifact references |
| `logs` | TEXT | DEFAULT "" | Step-level logs |
| `error_message` | TEXT | DEFAULT "" | Error on failure |
| `attempt` | PositiveIntegerField | DEFAULT 1 | Execution attempt number |

**Indexes:**
- `idx_steprun_run_step`: (`pipeline_run_id`, `step_id`)

### 5.5 Entity Relationship Diagram

```
Pipeline ──1:N──► PipelineStep
    │                  │
    │                  │ M:M (depends_on)
    │                  │
    └──1:N──► PipelineRun ──1:N──► PipelineStepRun
                                    │
                                    └──FK──► PipelineStep
```

---

## 6. API Endpoints

### 6.1 Pipeline CRUD

| Method | Path | Auth | Summary |
|---|---|---|---|
| `GET` | `/v1/pipelines` | `read:*` | List all pipelines |
| `POST` | `/v1/pipelines` | `write:pipelines` | Create pipeline |
| `GET` | `/v1/pipelines/{id}` | `read:*` | Get pipeline details |
| `PUT` | `/v1/pipelines/{id}` | `write:pipelines` | Update pipeline |
| `DELETE` | `/v1/pipelines/{id}` | `write:pipelines` | Delete pipeline |

### 6.2 Steps

| Method | Path | Auth | Summary |
|---|---|---|---|
| `GET` | `/v1/pipelines/{id}/steps` | `read:*` | List steps for a pipeline |
| `POST` | `/v1/pipelines/{id}/steps` | `write:pipelines` | Create step |
| `DELETE` | `/v1/pipelines/steps/{id}` | `write:pipelines` | Delete step |

### 6.3 Validation & Execution

| Method | Path | Auth | Summary |
|---|---|---|---|
| `POST` | `/v1/pipelines/{id}/validate` | `write:pipelines` | Validate DAG (steps + edges) |
| `POST` | `/v1/pipelines/{id}/run` | `write:pipelines` | Trigger pipeline run |
| `GET` | `/v1/pipelines/{id}/runs` | `read:*` | List run history |

### 6.4 Catalog & Import

| Method | Path | Auth | Summary |
|---|---|---|---|
| `GET` | `/v1/pipelines/transforms/catalog` | `read:*` | List available transform types |
| `POST` | `/v1/pipelines/import` | `write:pipelines` | Import pipeline from JSON |

### 6.5 Validation Request/Response

**Request (`POST /v1/pipelines/{id}/validate`):**
```json
{
  "steps": [
    {"id": "node-1", "step_type": "ingest", "name": "Source", "config": {}},
    {"id": "node-2", "step_type": "filter", "name": "Filter", "config": {"field": "status", "operator": "==", "value": "active"}}
  ],
  "edges": [
    {"source": "node-1", "target": "node-2"}
  ]
}
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "execution_order": ["node-1", "node-2"]
}
```

---

## 7. Integration Points

### 7.1 Internal Module Connections

| From | To | Integration | Description |
|---|---|---|---|
| Pipelines | SQL Console | `sql_query` step type | Pipeline steps can execute SQL queries via Trino |
| Pipelines | Ontology | `ingest` step reads ontology objects | Source steps can read from ontology-backed datasets |
| Pipelines | Feature Store | Scheduled feature computation | Pipelines can be used for feature materialization |
| Pipelines | Sources | `ingest` connects to data sources | Source steps reference configured data sources |
| Pipelines | Dashboard | Run status metrics | Dashboard shows pipeline job distribution chart |

### 7.2 External Systems

| System | Protocol | Purpose |
|---|---|---|
| Trino | SQL over HTTP | SQL Query pipeline steps |
| Temporal | Workflow API | External orchestration and tracking (`temporal_workflow_id`) |
| PostgreSQL | Django ORM | Pipeline metadata persistence |
| S3 / Iceberg | Via Trino connector | Data sources for ingest/export steps |

---

## 8. Quality Attributes

### 8.1 Performance Targets

| Metric | Target | Notes |
|---|---|---|
| Pipeline list load | < 200ms | `GET /v1/pipelines` |
| Step list load | < 100ms | `GET /v1/pipelines/{id}/steps` |
| DAG validation | < 50ms | Client-side + server validation |
| Save DAG (10 steps) | < 1s | Delete + recreate steps |
| Canvas render (50 nodes) | < 500ms | SVG rendering |
| Canvas zoom | 60fps | Hardware-accelerated transform |

### 8.2 Security Considerations

| Concern | Mitigation |
|---|---|
| Pipeline permissions | `write:pipelines` required for mutations; `read:*` for view |
| Tenant isolation | `tenant_id` on Pipeline and PipelineRun; steps inherit via Pipeline |
| Sandboxed expressions | Map transform `eval()` with `{"__builtins__": {}}` |
| Step timeout | `timeout_seconds` (default 300s) prevents runaway executions |
| Soft-delete | `deleted_at` prevents accidental permanent deletion |

### 8.3 Accessibility

| Feature | Implementation |
|---|---|
| ARIA roles | `role="main"` on editor; `aria-label` on buttons and controls |
| Keyboard navigation | Tab-based navigation; Enter to confirm |
| Screen reader | Status badge text readable; action buttons labeled |
| Focus management | Back button returns to list view |

---

## 9. Implementation Details

### 9.1 Key Algorithms

#### Topological Sort (Kahn's Algorithm) — `validator.py:189–220`

```python
def _topological_sort(node_ids, adj, in_degree):
    queue = deque()
    for nid in node_ids:
        if in_degree.get(nid, 0) == 0:
            queue.append(nid)
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in adj.get(node, set()):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    if len(order) != len(node_ids):
        return None  # Cycle detected
    return order
```

#### Cycle Detection — `validator.py:120–128`

When topological sort fails (returns `None`), the validator attempts to identify the specific cycle path using `_find_cycle()` for a useful error message like: `Cycle path: A → B → C → A`.

#### Sandboxed Expression Evaluation — `transforms.py:195–196`

```python
new_row[output_field] = eval(
    expression,
    {"__builtins__": {}},  # No builtins (no import, exec, etc.)
    {"row": row, **row}    # Row data accessible as 'row' or individual fields
)
```

#### Canvas Pan/Zoom — `view-pipelines.ts:430–458`

- **Pan:** Mouse drag on canvas background updates `canvasPanX`/`canvasPanY`
- **Zoom:** Mouse wheel multiplies `canvasZoom` by 0.92 (out) or 1.08 (in), clamped to [0.2, 3.0]
- **Node position:** Calculated as `(mouseX - panX) / zoom - nodeW/2`

#### DAG Save Strategy — `view-pipelines.ts:483–530`

1. Fetch all existing steps
2. Delete each existing step
3. Create new steps in order, building an `idMap` (local → server ID)
4. Each step's `config.depends_on` references server IDs from upstream edges
5. Update local node IDs to server-assigned IDs

### 9.2 Design Patterns

| Pattern | Usage | Location |
|---|---|---|
| Abstract Base Class | `TransformBase` defines transform interface | `transforms.py:25` |
| Registry Pattern | Transform subclasses auto-discovered | `transforms.py` |
| Builder Pattern | DAG built incrementally via UI interactions | `view-pipelines.ts` |
| Command Pattern | Canvas operations (add/remove/connect) are discrete actions | `view-pipelines.ts` |
| State Machine | Pipeline status (draft→active→paused→archived) | `models.py:22–27` |
| Observer Pattern | Canvas re-renders on state mutation via Lit `@state()` | `view-pipelines.ts` |
| Memento Pattern | Export/Import preserves full pipeline state as JSON | `view-pipelines.ts:556–611` |

### 9.3 Transform Config Schema

Each transform type defines its config schema in the `CONFIG_FIELDS` constant (`view-pipelines.ts:130–161`):

```
filter:
  - field: { type: text, placeholder: "column name" }
  - operator: { type: select, options: ["==", "!=", ">", "<", ">=", "<=", "in", "not_in", "contains"] }
  - value: { type: text, placeholder: "value to match" }

map:
  - expression: { type: text, placeholder: "row['price'] * 1.1" }
  - output_field: { type: text, placeholder: "result_column" }

join:
  - left_key: { type: text }
  - right_key: { type: text }
  - join_type: { type: select, options: ["inner", "left", "right", "full"] }
  - right_data_field: { type: text }

aggregate:
  - group_by: { type: text, placeholder: "category, region" }

sort:
  - sort_by: { type: text }
  - sort_direction: { type: select, options: ["asc", "desc"] }

dedup:
  - fields: { type: text, placeholder: "email, name (empty = all)" }
  - keep: { type: select, options: ["first", "last"] }

flatten:
  - field: { type: text }
  - flatten_type: { type: select, options: ["list", "object"] }
```

### 9.4 File Locations

| Layer | File | Lines | Description |
|---|---|---|---|
| Models | `apps/pipelines/models.py` | 321 | Pipeline, PipelineStep, PipelineRun, PipelineStepRun |
| Transforms | `apps/pipelines/transforms.py` | 589 | TransformBase + 7 concrete transforms |
| Validator | `apps/pipelines/validator.py` | 308 | DAG validation + topological sort |
| API | `apps/pipelines/api.py` | — | REST endpoints |
| UI View | `dashboard/src/views/view-pipelines.ts` | 1126 | Full pipeline editor with DAG canvas |
| Sidebar | `dashboard/src/components/saas-sidebar.ts` | — | Navigation sidebar |

### 9.5 Canvas Rendering Architecture

```
<view-pipelines render()>
├── <saas-sidebar>
├── <main>
│   ├── renderList()                    -- Pipeline cards list
│   └── renderEditor()                  -- DAG editor mode
│       ├── Toolbar                     -- Back, Save, Validate, Run, Runs, Export
│       ├── SVG Canvas                  -- Nodes + Edges
│       │   ├── <g transform="translate(panX, panY) scale(zoom)">
│       │   │   ├── Edges              -- <path> with arrow markers
│       │   │   └── Nodes              -- <g class="dag-node">
│       │   │       ├── Colored header rect (step_type color)
│       │   │       ├── White body rect
│       │   │       ├── Step type icon + label
│       │   │       └── Input/Output ports (<circle>)
│       │   └── (mouse event handlers for pan/drag/connect)
│       ├── Palette (left overlay)      -- Draggable transform cards
│       ├── Inspector (right overlay)   -- Config panel for selected node
│       ├── Validation results bar      -- Errors/warnings/success
│       └── Run history panel           -- Toggle-able run list
```

**Node Dimensions:** `NODE_W=180`, `NODE_H=64`, `PORT_R=7`
