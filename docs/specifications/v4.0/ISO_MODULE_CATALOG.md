# Ontology Catalog — Functional Specification

**Document ID:** VOYANT-ISO-CATALOG-4.0.0
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

The Ontology Catalog module is Voyant's central knowledge-graph layer. It provides a Palantir-class ontology engine that lets organizations define **Object Types** (entity schemas), **Link Types** (relationships), **Instances** (data), and attach **Actions** and **Functions** for business logic. It includes a semantic **Query Engine** that translates ontology-aware queries into Trino SQL against Iceberg-backed datasets, a **Time Travel** service for historical queries, a **PII Detection** engine, and a **Data Quality Scorer**.

### 1.2 Scope

| Capability | Sub-system | Source File |
|---|---|---|
| Object Type CRUD | Schema layer | `apps/ontology/models.py:23–84` |
| Property definitions | Schema layer | `apps/ontology/models.py:103–161` |
| Object Instance CRUD | Data layer | `apps/ontology/models.py:169–218` |
| Link Type / Link Instance | Graph layer | `apps/ontology/models.py:233–368` |
| Interface polymorphism | Abstraction | `apps/ontology/models.py:376–427` |
| Struct types | Abstraction | `apps/ontology/models.py:435–468` |
| Shared properties | Reusability | `apps/ontology/models.py:476–516` |
| Value types | Domain constraints | `apps/ontology/models.py:524–565` |
| Action types | Operations | `apps/ontology/models.py:573–678` |
| Functions | Business logic | `apps/ontology/models.py:686–792` |
| PII Detection | Governance | `apps/ontology/pii_detector.py` |
| Quality Scoring | Governance | `apps/ontology/quality_scorer.py` |
| Query Engine | Analytics | `apps/ontology/query_engine.py` |
| Time Travel | Historical | `apps/ontology/time_travel.py` |
| REST API | Transport | `apps/ontology/api.py` |
| Admin UI | Presentation | `dashboard/src/views/view-ontology.ts` |

### 1.3 Position in Voyant Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Dashboard (Lit)                          │
│  view-ontology.ts ─── voyant-graph-view                      │
│                     ─── voyant-data-table                     │
│                     ─── voyant-detail-panel                   │
│                     ─── voyant-monaco-editor                  │
└───────────────┬──────────────────────────────────────────────┘
                │ HTTP REST
┌───────────────▼──────────────────────────────────────────────┐
│                Ontology API (Django Ninja)                     │
│  ontology_router — 40+ endpoints                             │
├──────────────────────────────────────────────────────────────┤
│  Services Layer                                              │
│  ├─ ObjectTypeService    ├─ ObjectService                    │
│  ├─ LinkTypeService      ├─ ActionExecutor                   │
│  ├─ OntologyQueryEngine  ├─ TimeTravelService                │
│  ├─ PIIDetector          └─ DataQualityScorer                │
├──────────────────────────────────────────────────────────────┤
│  Django ORM (PostgreSQL)          │  Trino (Iceberg Lakehouse)│
│  ontology_object_type             │  backing_dataset queries  │
│  ontology_property                │  aggregate/interface SQL  │
│  ontology_object                  │  time-travel snapshots    │
│  ontology_link_type / ontology_link                           │
│  ontology_interface / ontology_struct_type                    │
│  ontology_shared_property / ontology_value_type              │
│  ontology_action_type / ontology_function                    │
│  ontology_pii_detection / ontology_quality_score             │
└──────────────────────────────────────────────────────────────┘
```

### 1.4 Key Differentiators

| Feature | Voyant Catalog | Palantir AIP | Databricks Unity |
|---|---|---|---|
| Ontology modeling | Built-in UI + API | Ontology Manager | External (Hive Metastore) |
| Action types with rules/side-effects/undo | Native (§5.9) | Workshop actions | Not native |
| Functions (Python/TS) | In-browser Monaco editor | Code repository | Notebooks |
| Query engine → Trino SQL | Automatic translation | Foundry SQL | Spark SQL |
| Time-travel queries | Iceberg snapshots via Trino | Dataset versioning | Delta time-travel |
| PII auto-detection | Regex + column-name + ML | Manual classification | Manual tags |
| Quality scoring (5-dimension) | Built-in scorer | Not native | Expectations-based |
| Multi-tenancy | Row-level (tenant_id) | Organization-based | Workspace-based |

---

## 2. Actors & Roles

| Actor | Role | Permissions | Description |
|---|---|---|---|
| Data Architect | `write:ontology` | Full CRUD on types, links, interfaces, structs | Designs the ontology schema — creates object types, defines properties, establishes link types |
| Data Engineer | `write:ontology` | Create/edit objects, batch operations, upserts | Manages instance data — imports, updates, batch-loads object instances |
| Data Analyst | `read:*` | Read types, query instances, run aggregates | Queries the ontology using the filter builder, exports data |
| Application Developer | `write:ontology` | Create actions, functions | Authors business logic (actions with rules, Python/TS functions) |
| Data Steward | `read:*` | Review PII detections, quality scores | Reviews governance outputs — PII flags, quality reports |
| MCP Agent | `read:*` / `write:ontology` | Programmatic access via tool calls | AI agents that read ontology structure, query instances, execute actions |

---

## 3. Screens / UI Views

### 3.1 Main Ontology View — Table Mode

**Route:** `/admin/ontology` (view-mode=table)
**Component:** `<view-ontology>` — `dashboard/src/views/view-ontology.ts`
**Sub-tabs:** Object Types | Object Instances | Link Types | Link Instances

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ▓▓ Sidebar ▓▓│  Ontology                                                │
│              │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│ • Dashboard  │  │📐 Obj    │ │📦 Obj    │ │🔗 Link   │ │⛓️ Link   │    │
│ • Ontology ◄─│  │  Types(4)│ │  Inst(0) │ │  Types(2)│ │  Inst(0) │    │
│ • SQL        │  └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
│ • Sources    │                                                          │
│ • Pipelines  │  ┌─────────────────────────────────────────────────────┐ │
│              │  │ 🔍 Search object types...                           │ │
│              │  └─────────────────────────────────────────────────────┘ │
│              │  ┌─────────────────────────────────────────────────────┐ │
│              │  │ Name     │ Description │ Props │ Insts │ Ver │ ...  │ │
│              │  │──────────┼─────────────┼───────┼───────┼─────┼──────│ │
│              │  │ Customer │ Core CRM..  │   8   │ 1,247 │ v3  │ ✏️🗑 │ │
│              │  │ Order    │ Transaction │  12   │   893 │ v5  │ ✏️🗑 │ │
│              │  │ Product  │ Catalog it..│   6   │   342 │ v2  │ ✏️🗑 │ │
│              │  │ Driver   │ Fleet mgmt  │  10   │    56 │ v1  │ ✏️🗑 │ │
│              │  └─────────────────────────────────────────────────────┘ │
│              │  📥 JSON  📥 CSV                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**API Endpoints Called:**

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/admin/ontology/types` | Load object types |
| `GET` | `/admin/ontology/links` | Load link types |
| `GET` | `/ontology/objects?object_type_id={id}&limit=500` | Load instances (lazy) |
| `GET` | `/ontology/links?limit=500` | Load link instances (lazy) |

**User Interactions:**

| Action | Trigger | Handler | Code Reference |
|---|---|---|---|
| Click row | `@click` on table row | `_openTypeDetail(t)` | `view-ontology.ts:313` |
| Search | Text input `@input` | `_filterSearch(rows)` | `view-ontology.ts:305` |
| Switch tab | Tab button `@click` | `_switchTableTab(tab)` | `view-ontology.ts:292` |
| Export JSON | Button `@click` | `_exportJSON(data, name)` | `view-ontology.ts:422` |
| Delete type | Action button | `_deleteType(id, name)` | `view-ontology.ts:355` |

**Loading State:** Shows centered "Loading..." text when `this.loading === true`
**Empty State:** Shows "No object types defined. Create your first type..."
**Error State:** Silent — API errors caught via `.catch(() => [])`

---

### 3.2 Main Ontology View — Grid Mode

**Route:** `/admin/ontology` (view-mode=grid)
**Component:** Same `<view-ontology>`, `_renderGridView()` method

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ▓▓ Sidebar ▓▓│  Ontology                                                │
│              │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│              │  │ [Table]  │ │ [Grid] ◄─│ │ [Graph]  │ │[Builders]│    │
│              │  └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
│              │                                                          │
│              │  ┌─────────────────────┐ ┌─────────────────────┐         │
│              │  │ 📐 Customer         │ │ 📐 Order            │         │
│              │  │ v3 · tenant-acme    │ │ v5 · tenant-acme    │         │
│              │  │ Core CRM entity for │ │ Transaction record  │         │
│              │  │ managing customers  │ │ linking customers   │         │
│              │  │                     │ │ to products         │         │
│              │  │ 8 properties        │ │ 12 properties       │         │
│              │  │ 1,247 instances     │ │ 893 instances       │         │
│              │  │                     │ │                     │         │
│              │  │ orders → items →    │ │ customer → product  │         │
│              │  │ +2 more             │ │ +1 more             │         │
│              │  │                     │ │                     │         │
│              │  │ Created 1/10/2026   │ │ Created 1/12/2026   │         │
│              │  └─────────────────────┘ └─────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Components:** Card grid with `minmax(300px, 1fr)` auto-fill columns
**Interactions:** Click card → `_openTypeDetail(t)`; Hover → border color animation

---

### 3.3 Main Ontology View — Graph Mode

**Route:** `/admin/ontology` (view-mode=graph)
**Component:** `<voyant-graph-view>` inside `<view-ontology>`

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ▓▓ Sidebar ▓▓│  Ontology                                                │
│              │  [Table] [Grid] [Graph◄] [Builders]                      │
│              │                                                          │
│              │  ┌─────────────────────────────────────────────────────┐ │
│              │  │                                                     │ │
│              │  │         ┌──────────┐         ┌──────────┐          │ │
│              │  │         │ Customer │─orders──│  Order   │          │ │
│              │  │         └────┬─────┘         └────┬─────┘          │ │
│              │  │              │                     │                │ │
│              │  │              │has_address          │contains        │ │
│              │  │              ▼                     ▼                │ │
│              │  │         ┌──────────┐         ┌──────────┐          │ │
│              │  │         │ Address  │         │ Product  │          │ │
│              │  │         └──────────┘         └──────────┘          │ │
│              │  │                                                     │ │
│              │  └─────────────────────────────────────────────────────┘ │
│              │  🔍 Search graph nodes...                                │
└─────────────────────────────────────────────────────────────────────────┘
```

**API Endpoints:** Same as Table mode (`/admin/ontology/types`, `/admin/ontology/links`)
**Node sizing:** `Math.max(8, Math.min(24, instance_count/100 + 8))` — `view-ontology.ts:771`
**Interactions:** Click node → `_openTypeDetail(node.data)` — `view-ontology.ts:785`

---

### 3.4 Detail Panel — Object Type Overview

**Trigger:** Click type row/card/node → slides open `<voyant-detail-panel>` (width=560px)
**Tabs:** Overview | Actions | Functions

```
┌──────────────────────────────────────────────────────────────┐
│                                        │ ┌──────────────────┐│
│ ▓▓ Sidebar ▓▓│  Ontology               │ │ ✕ Close          ││
│              │                          │ │                  ││
│              │  ... (main view)         │ │ Customer v3      ││
│              │                          │ │                  ││
│              │                          │ │ [Overview][⚡Act] ││
│              │                          │ │ [💻 Functions]    ││
│              │                          │ │                  ││
│              │                          │ │ Core CRM entity  ││
│              │                          │ │ for managing...  ││
│              │                          │ │                  ││
│              │                          │ │ ┌────┐ ┌────┐   ││
│              │                          │ │ │  8 │ │1247│   ││
│              │                          │ │ │props│ │inst│   ││
│              │                          │ │ └────┘ └────┘   ││
│              │                          │ │ ┌────┐ ┌────┐   ││
│              │                          │ │ │  3 │ │ v3 │   ││
│              │                          │ │ │links│ │ver │   ││
│              │                          │ │ └────┘ └────┘   ││
│              │                          │ │                  ││
│              │                          │ │ PROPERTIES       ││
│              │                          │ │ name   │string│✓ ││
│              │                          │ │ email  │string│✓ ││
│              │                          │ │ age    │int   │  ││
│              │                          │ │                  ││
│              │                          │ │ CONNECTED LINKS  ││
│              │                          │ │ 🔗 orders →      ││
│              │                          │ │   Order (1:N) 24 ││
│              │                          │ │                  ││
│              │                          │ │ [📦 View Objects] ││
│              │                          │ │ [✏️ Edit Type]    ││
│              │                          │ │ [⚡ Create Action]││
│              │                          │ │ [💻 Create Func]  ││
│              │                          │ │ [🗑️ Delete Type]  ││
│              │                          │ └──────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

**API Endpoints Called:**

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/ontology/types/{type_id}` | Load properties |
| `GET` | `/ontology/actions?object_type_id={id}` | Load actions |
| `GET` | `/ontology/functions?object_type_id={id}` | Load functions |

**Code References:**
- `_openTypeDetail()`: `view-ontology.ts:313`
- `_renderTypeDetail()`: `view-ontology.ts:1172`
- `_renderTypeActionsTab()`: `view-ontology.ts:1289`
- `_renderTypeFunctionsTab()`: `view-ontology.ts:1317`

---

### 3.5 Filter Builder

**Trigger:** View-mode = "builders" → `_renderFilterBuilder()` at `view-ontology.ts:1429`

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ▓▓ Sidebar ▓▓│  Ontology                                                │
│              │  [Table] [Grid] [Graph] [Builders◄]                      │
│              │                                                          │
│              │  ┌─────────────────────────────────────────────────────┐ │
│              │  │ Filter Builder            [🔍 Apply] [✕ Clear]     │ │
│              │  │                                                     │ │
│              │  │ Target Type: [All Types ▾]                          │ │
│              │  │ Logic: [AND] [OR]                                   │ │
│              │  │                                                     │ │
│              │  │ ┌───────────────────────────────────────────────┐  │ │
│              │  │ │ [status  ▾] [ =      ▾] [active          ] 🗑│  │ │
│              │  │ ├───────────────────────────────────────────────┤  │ │
│              │  │ │ [age     ▾] [ >      ▾] [25              ] 🗑│  │ │
│              │  │ └───────────────────────────────────────────────┘  │ │
│              │  │ [+ Add Condition]                                   │ │
│              │  │                                                     │ │
│              │  │ ┌───────────────────────────────────────────────┐  │ │
│              │  │ │ ID       │ Type     │ name    │ status │ ...  │  │ │
│              │  │ │ a1b2..   │ Customer │ John    │ active │      │  │ │
│              │  │ │ c3d4..   │ Customer │ Jane    │ active │      │  │ │
│              │  │ └───────────────────────────────────────────────┘  │ │
│              │  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

**Operators:** `=`, `!=`, `>`, `<`, `>=`, `<=`, `contains`, `starts_with`, `ends_with`
**Logic:** AND (all conditions must match) / OR (any condition matches)
**API:** `GET /ontology/objects?object_type_id={id}&limit=500` → client-side filtering

---

### 3.6 Type Builder

**Trigger:** `_openTypeBuilder()` — `view-ontology.ts:512`
**Modal overlay** with name, description, property list, validation rules, JSON preview

```
┌──────────────────────────────────────────────────────────┐
│                        (overlay)                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │ Type Builder                              [✕]    │    │
│  │                                                  │    │
│  │ Name: [Customer Type                    ]        │    │
│  │ Description: [Customer entity schema    ]        │    │
│  │                                                  │    │
│  │ Properties:                           [+ Add]    │    │
│  │ ┌────────────────────────────────────────────┐   │    │
│  │ │ name    │ string │ Req │ regex: [  ] 🗑    │   │    │
│  │ │ email   │ string │ Req │ regex: [@] 🗑    │   │    │
│  │ │ age     │integer │     │ min:[0]max:[150]🗑│   │    │
│  │ └────────────────────────────────────────────┘   │    │
│  │                                                  │    │
│  │ [📋 Preview JSON]                                │    │
│  │ { "name": "Customer Type", "properties": [...] } │    │
│  │                                                  │    │
│  │        [Cancel]  [Create Type]                   │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

**API Endpoint:** `POST /ontology/types` with `{ name, description, properties[] }`
**Code Reference:** `_submitTypeBuilder()` — `view-ontology.ts:560`

---

### 3.7 Action Builder

**Trigger:** `_openActionBuilder()` — `view-ontology.ts:588`

```
┌──────────────────────────────────────────────────────────┐
│                        (overlay)                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │ Action Builder                             [✕]    │    │
│  │                                                  │    │
│  │ Name: [Approve Order                    ]        │    │
│  │ Description: [Transition order status   ]        │    │
│  │ Target Type: [Order ▾]                           │    │
│  │                                                  │    │
│  │ Parameters:                           [+ Add]    │    │
│  │ │ reason │ string │ Req │                       │    │
│  │                                                  │    │
│  │ Rules (Pre-conditions):               [+ Add]    │    │
│  │ │ status_check │ status │ = "pending" │         │    │
│  │                                                  │    │
│  │ Side Effects:                         [+ Add]    │    │
│  │ │ webhook │ url: https://hooks...     │         │    │
│  │ │ notification │ channel: email       │         │    │
│  │                                                  │    │
│  │ ☑ Undoable                                       │    │
│  │ Undo Rules:                            [+ Add]   │    │
│  │ │ status_revert │ status              │         │    │
│  │                                                  │    │
│  │        [Cancel]  [Create Action]                 │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

**API Endpoint:** `POST /ontology/actions` with full payload
**Code Reference:** `_submitActionBuilder()` — `view-ontology.ts:650`

---

### 3.8 Function Editor

**Trigger:** `_openFunctionEditor()` — `view-ontology.ts:691`
**Components:** `<voyant-monaco-editor>` for source code editing

```
┌──────────────────────────────────────────────────────────┐
│                        (overlay)                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │ Function Editor                            [✕]    │    │
│  │                                                  │    │
│  │ Name: [calculate_risk_score    ] Language:[▾ Py] │    │
│  │                                                  │    │
│  │ ┌────────────────────────────────────────────┐   │    │
│  │ │ 1│ def handler(input_data):                │   │    │
│  │ │ 2│     """Process input and return result."""│  │    │
│  │ │ 3│     return {"status": "ok"}              │   │    │
│  │ │  │                                         │   │    │
│  │ └────────────────────────────────────────────┘   │    │
│  │                                                  │    │
│  │ Input Schema:  { }           Output: { }         │    │
│  │                                                  │    │
│  │ ┌────────────────────────────────────────────┐   │    │
│  │ │ {"status": "ok"}                           │   │    │
│  │ └────────────────────────────────────────────┘   │    │
│  │                                                  │    │
│  │ [▶ Run]  [💾 Save Function]                      │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

**API Endpoints:**
- `POST /ontology/functions/run` — Execute code snippet
- `POST /ontology/functions` — Persist function

---

## 4. Functional Requirements

### 4.1 Schema Management

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| ONT-F-001 | Create object type with name and description | Name unique per tenant; returns UUID | ✅ Impl | `apps/ontology/api.py:233` |
| ONT-F-002 | Define typed properties on object types | 11 types: string, integer, float, boolean, date, timestamp, enum, array, map, struct, geopoint | ✅ Impl | `apps/ontology/models.py:87–101` |
| ONT-F-003 | Mark properties as required | Boolean flag on Property model | ✅ Impl | `apps/ontology/models.py:128` |
| ONT-F-004 | Set default values on properties | JSONField on Property model | ✅ Impl | `apps/ontology/models.py:132` |
| ONT-F-005 | Define validation rules on properties | JSONField: regex, min, max, enum_values, custom | ✅ Impl | `apps/ontology/models.py:137` |
| ONT-F-006 | Update object type (name, description, properties) | Increments version; returns updated entity | ✅ Impl | `apps/ontology/api.py:618` |
| ONT-F-007 | Delete object type (soft-delete) | Sets `deleted_at`; confirm dialog required | ✅ Impl | `apps/ontology/api.py:643` |
| ONT-F-008 | Automatic schema versioning | `version` field auto-increments on update | ✅ Impl | `apps/ontology/models.py:40–43` |
| ONT-F-009 | Search/filter types by name | Client-side case-insensitive filter | ✅ Impl | `view-ontology.ts:305` |

### 4.2 Instance Management

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| ONT-F-010 | Create object instance | Validates type exists; returns UUID | ✅ Impl | `apps/ontology/api.py:1259` |
| ONT-F-011 | Get single object by ID | Returns object with properties and type name | ✅ Impl | `apps/ontology/api.py:1238` |
| ONT-F-012 | List objects with type filter | `?object_type_id=` optional filter, limit param | ✅ Impl | `apps/ontology/api.py:1217` |
| ONT-F-013 | Update object properties | Optimistic concurrency via `version` field | ✅ Impl | `apps/ontology/api.py:1280` |
| ONT-F-014 | Delete object (soft-delete) | Sets `deleted_at` timestamp | ✅ Impl | `apps/ontology/api.py:1301` |
| ONT-F-015 | Batch create 1000+ objects | Single request with `items[]` array | ✅ Impl | `apps/ontology/api.py:1316` |
| ONT-F-016 | Upsert by unique key property | Creates or updates based on `key_property` | ✅ Impl | `apps/ontology/api.py:1334` |
| ONT-F-017 | Edit instance via UI modal | PUT `/ontology/objects/{id}` with properties | ✅ Impl | `view-ontology.ts:398` |

### 4.3 Link Management

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| ONT-F-020 | Define link type between two object types | Source + target type FKs; cardinality enum | ✅ Impl | `apps/ontology/models.py:233` |
| ONT-F-021 | Cardinality: one-to-one, one-to-many, many-to-many | TextChoices enum on LinkType | ✅ Impl | `apps/ontology/models.py:225–231` |
| ONT-F-022 | Properties on link instances | JSONField on Link model | ✅ Impl | `apps/ontology/models.py:336` |
| ONT-F-023 | Create link instance | Source + target object FKs; unique constraint | ✅ Impl | `apps/ontology/api.py:1400+` |
| ONT-F-024 | Traverse links (outgoing/incoming) | Filter link instances by source or target object | ✅ Impl | `view-ontology.ts:1355–1356` |

### 4.4 Advanced Schema

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| ONT-F-018 | Interface polymorphism | M2M to ObjectType; required/optional properties | ✅ Impl | `apps/ontology/models.py:376` |
| ONT-F-019 | Struct types for nested properties | JSONField `fields[]` with name/type/required | ✅ Impl | `apps/ontology/models.py:435` |
| ONT-F-020b | Shared properties across types | M2M to ObjectType; reuse definitions | ✅ Impl | `apps/ontology/models.py:476` |
| ONT-F-022b | Value types with domain constraints | base_type + constraints (regex, min, max) | ✅ Impl | `apps/ontology/models.py:524` |

### 4.5 Actions & Functions

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| ONT-F-026 | Action type with parameters, rules, side effects | Full lifecycle: draft → active → deprecated | ✅ Impl | `apps/ontology/models.py:573` |
| ONT-F-027 | Undo support on actions | `undoable` flag + `undo_rules[]` | ✅ Impl | `apps/ontology/models.py:634–641` |
| ONT-F-028 | Approval gate on actions | `requires_approval` flag creates approval request | ✅ Impl | `apps/ontology/models.py:651` |
| ONT-F-029 | Functions in Python/TypeScript | Monaco editor, execute via API, persist source code | ✅ Impl | `apps/ontology/models.py:686` |
| ONT-F-030 | Function sandboxing | `timeout_seconds` (default 30), `memory_limit_mb` (default 128) | ✅ Impl | `apps/ontology/models.py:766–767` |

### 4.6 Query Engine

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| ONT-F-031 | Aggregate queries (GROUP BY + SUM/AVG/COUNT/MIN/MAX/P95/P99) | Translates to Trino SQL with parameterized placeholders | ✅ Impl | `apps/ontology/query_engine.py:311` |
| ONT-F-032 | Interface-based queries (UNION across types) | Queries each implementing type, merge-sorts results | ✅ Impl | `apps/ontology/query_engine.py:411` |
| ONT-F-033 | Count queries | `SELECT COUNT(*)` with optional filter | ✅ Impl | `apps/ontology/query_engine.py:383` |
| ONT-F-034 | Cursor-based (keyset) pagination | Uses PK column for efficient paging | ✅ Impl | `apps/ontology/query_engine.py:522` |
| ONT-F-035 | Geospatial near() filter | Haversine approximation bounding box | ✅ Impl | `apps/ontology/query_engine.py:186–201` |
| ONT-F-036 | Filter DSL (AND/OR/eq/neq/gt/gte/lt/lte/in/not_in/like/is_null/is_not_null) | Recursive tree → SQL WHERE clause | ✅ Impl | `apps/ontology/query_engine.py:150–239` |

### 4.7 Time Travel

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| ONT-F-037 | Query by Iceberg snapshot version | `FOR SYSTEM_VERSION AS OF <id>` | ✅ Impl | `apps/ontology/time_travel.py:161` |
| ONT-F-038 | Query by timestamp | `FOR SYSTEM_TIME AS OF <timestamp>` | ✅ Impl | `apps/ontology/time_travel.py:202+` |
| ONT-F-039 | Diff between two versions | `CHANGES BETWEEN` syntax; added/removed/modified | ✅ Impl | `apps/ontology/time_travel.py` |
| ONT-F-040 | List available versions | Iceberg REST catalog snapshot metadata | ✅ Impl | `apps/ontology/time_travel.py` |

### 4.8 Governance

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| ONT-F-041 | PII detection (regex, column-name, ML) | Confidence 0.0–1.0; auto-classify > 0.85 | ✅ Impl | `apps/ontology/pii_detector.py:132` |
| ONT-F-042 | Quality scoring (5 dimensions) | Completeness, uniqueness, timeliness, consistency, accuracy | ✅ Impl | `apps/ontology/quality_scorer.py:163` |
| ONT-F-043 | Export data (JSON/CSV) | Client-side Blob generation and download | ✅ Impl | `view-ontology.ts:422–429, 1032–1049` |

---

## 5. Data Model

### 5.1 ObjectType

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Primary key (UUIDModel) |
| `tenant_id` | VARCHAR(255) | NOT NULL, INDEX | Multi-tenancy isolation |
| `name` | VARCHAR(255) | NOT NULL | Unique per tenant (active) |
| `description` | TEXT | DEFAULT "" | Human-readable description |
| `version` | PositiveIntegerField | DEFAULT 1 | Auto-incrementing schema version |
| `backing_dataset` | VARCHAR(512) | DEFAULT "" | Fully-qualified Iceberg table name |
| `primary_key_column` | VARCHAR(255) | DEFAULT "id" | PK column for keyset pagination |
| `deleted_at` | DateTimeField | NULL, INDEX | Soft-deletion timestamp |
| `created_at` | DateTimeField | AUTO | Creation timestamp |
| `updated_at` | DateTimeField | AUTO | Last update timestamp |

**Constraints:**
- `uq_object_type_name_active`: UNIQUE(`tenant_id`, `name`) WHERE `deleted_at IS NULL`

**Indexes:**
- `idx_ot_tenant_name`: (`tenant_id`, `name`)

### 5.2 Property

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Primary key |
| `tenant_id` | VARCHAR(255) | NOT NULL | Multi-tenancy |
| `object_type_id` | FK → ObjectType | CASCADE | Parent object type |
| `name` | VARCHAR(255) | NOT NULL | Property name |
| `property_type` | VARCHAR(32) | CHOICES | One of 11 types |
| `required` | BooleanField | DEFAULT false | Required on instances |
| `default_value` | JSONField | NULL | Default value |
| `validation_rules` | JSONField | NULL | regex, min, max, enum_values |
| `metadata` | JSONField | DEFAULT {} | Display name, description, etc. |

**Constraints:**
- `uq_property_name_per_type`: UNIQUE(`object_type_id`, `name`)

### 5.3 Object (Instance)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Primary key |
| `tenant_id` | VARCHAR(255) | NOT NULL | Multi-tenancy |
| `object_type_id` | FK → ObjectType | PROTECT | Schema reference |
| `properties` | JSONField | DEFAULT {} | Key-value data |
| `version` | PositiveIntegerField | DEFAULT 1 | Optimistic concurrency |
| `deleted_at` | DateTimeField | NULL, INDEX | Soft-deletion |
| `created_at` / `updated_at` | DateTimeField | AUTO | Timestamps |

**Indexes:**
- `idx_obj_type`: (`object_type_id`)
- `idx_obj_tenant_type`: (`tenant_id`, `object_type_id`)
- `idx_obj_tenant_created`: (`tenant_id`, `-created_at`)

### 5.4 LinkType

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Primary key |
| `tenant_id` | VARCHAR(255) | NOT NULL | Multi-tenancy |
| `name` | VARCHAR(255) | NOT NULL | Link type name |
| `description` | TEXT | DEFAULT "" | Description |
| `source_object_type_id` | FK → ObjectType | PROTECT | Source type |
| `target_object_type_id` | FK → ObjectType | PROTECT | Target type |
| `cardinality` | VARCHAR(20) | CHOICES | one_to_one / one_to_many / many_to_many |
| `properties_schema` | JSONField | NULL | JSON schema for link props |
| `inverse_name` | VARCHAR(255) | DEFAULT "" | Reverse traversal name |
| `deleted_at` | DateTimeField | NULL, INDEX | Soft-delete |

**Constraints:**
- `uq_link_type_name_active`: UNIQUE(`tenant_id`, `name`) WHERE `deleted_at IS NULL`

### 5.5 Link (Instance)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Primary key |
| `tenant_id` | VARCHAR(255) | NOT NULL | Multi-tenancy |
| `link_type_id` | FK → LinkType | PROTECT | Link schema |
| `source_object_id` | FK → Object | CASCADE | Source instance |
| `target_object_id` | FK → Object | CASCADE | Target instance |
| `properties` | JSONField | DEFAULT {} | Link properties |
| `deleted_at` | DateTimeField | NULL, INDEX | Soft-delete |

**Constraints:**
- `uq_link_instance_active`: UNIQUE(`link_type_id`, `source_object_id`, `target_object_id`) WHERE `deleted_at IS NULL`

### 5.6 Additional Models

| Model | Table | Key Fields | Relationships |
|---|---|---|---|
| `Interface` | `ontology_interface` | name, version, required_properties (JSON), optional_properties (JSON) | M2M → ObjectType |
| `StructType` | `ontology_struct_type` | name, version, fields (JSON) | — |
| `SharedProperty` | `ontology_shared_property` | name, property_type, default_value, validation_rules | M2M → ObjectType |
| `ValueType` | `ontology_value_type` | name, base_type, version, constraints (JSON), is_system | — |
| `ActionType` | `ontology_action_type` | name, status, parameters, rules, side_effects, undoable, undo_rules, requires_approval | FK → ObjectType |
| `Function` | `ontology_function` | name, status, language, source_code, entry_point, input_schema, output_schema, timeout_seconds, memory_limit_mb | FK → ObjectType, FK → ActionType |
| `PIIDetection` | `ontology_pii_detection` | column_name, dataset_urn, pii_type, confidence, method, auto_classified | — |
| `QualityScore` | `ontology_quality_score` | dataset_id, overall, completeness, uniqueness, timeliness, consistency, accuracy, report (JSON) | — |

---

## 6. API Endpoints

### 6.1 Object Types

| Method | Path | Auth | Request Body | Response | MCP Tool |
|---|---|---|---|---|---|
| `GET` | `/ontology/types` | `read:*` | — | `ObjectTypeOut[]` | `list_object_types` |
| `POST` | `/ontology/types` | `write:ontology` | `CreateObjectTypeIn` | `ObjectTypeOut` | `create_object_type` |
| `GET` | `/ontology/types/{id}` | `read:*` | — | `{...type, properties[]}` | `get_object_type` |
| `PUT` | `/ontology/types/{id}` | `write:ontology` | `UpdateObjectTypeIn` | Updated type | `update_object_type` |
| `DELETE` | `/ontology/types/{id}` | `write:ontology` | — | `{status: "deleted"}` | `delete_object_type` |

### 6.2 Objects (Instances)

| Method | Path | Auth | Request Body | Response | MCP Tool |
|---|---|---|---|---|---|
| `GET` | `/ontology/objects` | `read:*` | `?object_type_id=&limit=` | `ObjectOut[]` | `list_objects` |
| `POST` | `/ontology/objects` | `write:ontology` | `CreateObjectIn` | `ObjectOut` | `create_object` |
| `GET` | `/ontology/objects/{id}` | `read:*` | — | `ObjectOut` | `get_object` |
| `PUT` | `/ontology/objects/{id}` | `write:ontology` | `UpdateObjectIn` | `ObjectOut` | `update_object` |
| `DELETE` | `/ontology/objects/{id}` | `write:ontology` | — | `{status: "deleted"}` | `delete_object` |
| `POST` | `/ontology/objects/batch` | `write:ontology` | `BatchCreateIn` | `{created, ids[]}` | `batch_create_objects` |
| `POST` | `/ontology/objects/upsert` | `write:ontology` | `UpsertIn` | `{processed, ids[]}` | `upsert_objects` |

### 6.3 Interfaces, Structs, Shared Properties, Value Types

Each follows the same pattern: `GET /list`, `POST /create`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}`.

### 6.4 Actions & Functions

| Method | Path | Auth | Summary |
|---|---|---|---|
| `GET` | `/ontology/actions` | `read:*` | List action types (filterable by `?status=`) |
| `POST` | `/ontology/actions` | `write:ontology` | Create action type |
| `GET/PUT/DELETE` | `/ontology/actions/{id}` | varies | CRUD on action type |
| `GET` | `/ontology/functions` | `read:*` | List functions |
| `POST` | `/ontology/functions` | `write:ontology` | Create function |
| `POST` | `/ontology/functions/run` | `write:ontology` | Execute function code |
| `GET/PUT/DELETE` | `/ontology/functions/{id}` | varies | CRUD on function |

### 6.5 Link Types & Links

| Method | Path | Auth | Summary |
|---|---|---|---|
| `GET` | `/ontology/link-types` | `read:*` | List link types |
| `POST` | `/ontology/link-types` | `write:ontology` | Create link type |
| `GET` | `/ontology/links` | `read:*` | List link instances |
| `POST` | `/ontology/links` | `write:ontology` | Create link instance |

---

## 7. Integration Points

### 7.1 Internal Module Connections

| From | To | Integration | Description |
|---|---|---|---|
| Catalog | SQL Console | Query Engine → Trino | Backing datasets queried via Trino; SQL Console can query same tables |
| Catalog | Pipelines | ObjectType as pipeline source | Pipeline `ingest` steps can read from ontology object types |
| Catalog | Feature Store | Shared entity model | Feature groups may reference ontology object types as entity sources |
| Catalog | Dashboard | Metric cards | Dashboard shows ontology metrics (type count, instance count) |
| Catalog | Admin API | `/admin/ontology/*` routes | Admin panel lists types, links for management |

### 7.2 External System Connections

| System | Protocol | Purpose |
|---|---|---|
| Trino | SQL over HTTP | Query execution for backing datasets |
| Iceberg REST Catalog | HTTP REST | Snapshot metadata for time-travel |
| PostgreSQL | Django ORM | Ontology metadata storage |
| Redis | Django Cache | Feature serving cache (shared with Feature Store) |

---

## 8. Quality Attributes

### 8.1 Performance Targets

| Metric | Target | Measurement |
|---|---|---|
| Type list load | < 200ms | API response time for `GET /ontology/types` |
| Instance list (500) | < 500ms | Including property expansion |
| Aggregate query | < 2s | Trino query execution |
| Filter builder | < 300ms | Client-side filtering of 500 instances |
| Graph render | < 1s | Up to 50 nodes with edges |
| Batch create (1000) | < 5s | Single API call |

### 8.2 Security Considerations

| Concern | Mitigation |
|---|---|
| SQL injection | `_validate_identifier()` regex guard (`^[A-Za-z_][A-Za-z0-9_]*$`) in `query_engine.py:126` |
| Cross-tenant access | Row-level `tenant_id` on every model; `get_tenant_id(request)` middleware |
| Permission enforcement | `require_permission("read:*")` / `require_permission("write:ontology")` on all endpoints |
| Function sandboxing | `timeout_seconds=30`, `memory_limit_mb=128`; builtins disabled in eval |
| Soft-deletion | `deleted_at` prevents permanent data loss; unique constraints use partial indexes |

### 8.3 Accessibility

| Feature | Implementation |
|---|---|
| ARIA labels | All interactive elements have `aria-label` attributes |
| Keyboard navigation | Tab-based navigation on cards, tables, detail panels |
| Screen reader | `role="tablist"`, `role="tab"`, `role="table"`, `aria-selected`, `aria-live="polite"` |
| Focus management | `tabindex="0"` on clickable cards; `@keydown` handlers for Enter/Space |

---

## 9. Implementation Details

### 9.1 Key Algorithms

#### Filter DSL → SQL Translation (`query_engine.py:150–239`)

The `_build_filter_sql()` function recursively translates a `QueryFilter` tree into parameterized SQL:

1. **Branch nodes** (AND/OR): Recurse into children, join with ` AND ` / ` OR `
2. **Geospatial near()**: Haversine bounding-box approximation (±lat/±lng deltas)
3. **Leaf nodes**: Map operator to SQL (`eq` → `= ?`, `in` → `IN (?, ?)`, etc.)
4. **Identifier validation**: Every column/table name passes through `_validate_identifier()` regex

#### DAG Validation (`validator.py:74–161`)

The `validate_dag()` function checks pipeline DAGs:

1. Edge reference validation (source/target exist in steps)
2. Self-loop detection
3. Cycle detection via Kahn's algorithm (topological sort)
4. Disconnected component warnings
5. Source/sink node presence
6. Schema compatibility checks
7. Transform config validation

#### PII Detection (`pii_detector.py:132–200`)

Three-strategy detection with confidence merging:

1. **Regex** (confidence 0.95): Pattern match sample values
2. **Column-name** (confidence 0.70): Keyword lookup in column name
3. **ML** (confidence 0.80): Placeholder for NER models
4. **Merge**: `max(existing.confidence, new.confidence)` when strategies agree

### 9.2 Design Patterns

| Pattern | Usage | Location |
|---|---|---|
| Repository (Service Layer) | `ObjectTypeService`, `ObjectService`, `LinkTypeService` | `apps/ontology/services.py` |
| Schema/DTO | Django Ninja `Schema` classes for input/output validation | `apps/ontology/api.py:39–199` |
| Soft-Delete | `deleted_at` field + partial unique constraints | All models |
| Optimistic Concurrency | `version` field on Object instances | `apps/ontology/models.py:187` |
| Multi-tenancy | `TenantModel` base class with `tenant_id` | All models inherit |
| UUID PK | `UUIDModel` base class | All models inherit |
| State Machine | `status` field (draft → active → deprecated) | ActionType, Function |
| Composable Transforms | `TransformBase` ABC → concrete transforms | `apps/pipelines/transforms.py` |
| Event Bus | Cross-component filter communication | `dashboard/src/lib/event-bus.ts` |

### 9.3 File Locations

| Layer | File | Lines | Description |
|---|---|---|---|
| Models | `apps/ontology/models.py` | 947 | 12 Django ORM models |
| API | `apps/ontology/api.py` | 2003 | 40+ REST endpoints |
| Services | `apps/ontology/services.py` | — | Business logic layer |
| Query Engine | `apps/ontology/query_engine.py` | 613 | Trino SQL translation |
| Time Travel | `apps/ontology/time_travel.py` | 418 | Iceberg time-travel |
| PII Detector | `apps/ontology/pii_detector.py` | 301 | PII detection engine |
| Quality Scorer | `apps/ontology/quality_scorer.py` | 538 | 5-dimension quality scoring |
| Action Executor | `apps/ontology/action_executor.py` | — | Action execution engine |
| UI View | `dashboard/src/views/view-ontology.ts` | 2072 | Main ontology admin view |
| Graph Component | `dashboard/src/components/voyant-graph-view.ts` | — | Force-directed graph |
| Detail Panel | `dashboard/src/components/voyant-detail-panel.ts` | — | Slide-out detail panel |
| Data Table | `dashboard/src/components/voyant-data-table.ts` | — | Sortable data table |
| Monaco Editor | `dashboard/src/components/voyant-monaco-editor.ts` | — | Code editor for functions |
