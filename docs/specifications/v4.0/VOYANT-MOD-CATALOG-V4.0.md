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

---

# Detailed Design

_Merged from MODULE_ONTOLOGY_ENGINE.md (v4.0.0). Original: 1,971 lines._

# Voyant Ontology Engine — Module Design Document

**Document ID:** VOYANT-ONT-MODULE-4.0.0
**Version:** 4.0.0
**Date:** 2026-09-10
**Standard:** ISO/IEC/IEEE 29148:2018 · ISO/IEC 25010
**Status:** Design Specification

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Current Implementation (What Exists)](#2-current-implementation-what-exists)
3. [Palantir Comparison (Deep)](#3-palantir-comparison-deep)
4. [Improvements Over Palantir](#4-improvements-over-palantir)
5. [Improvements Over Databricks Unity Catalog](#5-improvements-over-databricks-unity-catalog)
6. [Complete API Design (v4.0 Target)](#6-complete-api-design-v40-target)
7. [Complete MCP Tool Design (v4.0 Target)](#7-complete-mcp-tool-design-v40-target)
8. [Test Strategy](#8-test-strategy)
9. [Architecture Diagrams (ASCII)](#9-architecture-diagrams-ascii)

---

## 1. Module Overview

### 1.1 Purpose

The Ontology Engine is the **foundational data modeling layer** of Voyant. It provides a formal, typed, versioned, multi-tenant schema system for defining:

- **What entities exist** (Object Types and their Properties)
- **How entities relate** (Link Types with cardinality)
- **What operations can be performed** (Action Types with rules and side effects)
- **What business logic runs** (Functions with sandboxed execution)
- **How types are organized** (Interfaces, Struct Types, Shared Properties, Value Types)

It is the single source of truth for the domain model that every other module depends on.

### 1.2 Position in Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Consumers                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │  Agents   │  │ Scraper  │  │ ML/Data  │  │ Admin UI     │   │
│  │  (MCP)    │  │ Engine   │  │ Platform │  │ (Dashboard)  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘   │
│       │              │              │               │            │
│  ┌────▼──────────────▼──────────────▼───────────────▼──────┐    │
│  │              ONTOLOGY ENGINE (this module)               │    │
│  │  ┌────────────┐  ┌──────────┐  ┌────────────────────┐  │    │
│  │  │  Models     │  │ Services │  │ Action Executor    │  │    │
│  │  │  (12 ORM)   │  │ (CRUD+   │  │ Function Runner    │  │    │
│  │  │             │  │  Batch)  │  │ Validators         │  │    │
│  │  └──────┬─────┘  └────┬─────┘  └────────┬───────────┘  │    │
│  │         │              │                  │              │    │
│  │  ┌──────▼──────────────▼──────────────────▼──────────┐  │    │
│  │  │              PostgreSQL (ontology_* tables)         │  │    │
│  │  └───────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Cross-Module Dependencies

| Consumer Module | How It Uses Ontology | Integration Point |
|----------------|---------------------|-------------------|
| **Scraper** | Auto-detects entity types from scraped pages; creates objects from extracted data; uses link types to connect entities | `ObjectService.create()`, `LinkService.create()` |
| **ML Platform** | Reads property definitions for feature engineering; uses object type schemas to generate feature vectors | Direct ORM queries on `Property`, `ObjectType` |
| **Agent (MCP)** | Full read/write access via 14 MCP tools; agents create types, objects, links, execute actions, run functions | `tools_ontology.py` → service layer |
| **Governance** | Uses ontology types as securable objects; audits all ontology mutations; applies row-level security to objects | `AuditLog`, SpiceDB bindings |
| **Search** | Indexes object properties for full-text and semantic search; traverses links for graph-based retrieval | Milvus + PostgreSQL full-text |
| **Intent Engine** | Translates natural language to ontology operations ("create a Customer named Alice") | NL→service method mapping |
| **Capsule System** | Packages ontology operations as portable, signed recipes that can be replayed | Serialized service calls |
| **Workflows (Temporal)** | Long-running workflows reference ontology objects; actions can trigger workflow starts | `ActionExecutor` → Temporal client |
| **Admin UI** | Displays ontology types, instances, links in table/grid views; schema designer for types | REST API endpoints |

---

## 2. Current Implementation (What Exists)

### 2.1 Data Models — Complete Reference

The Ontology Engine consists of **12 Django ORM models** across 5 conceptual layers. All models inherit from `TenantModel` (multi-tenancy) and `UUIDModel` (UUID primary keys).

#### 2.1.1 ObjectType

**Table:** `ontology_object_type`
**Purpose:** Schema definition for a class of entities (e.g., Customer, Sensor, Ticket).

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | PK, auto-generated | Primary key |
| `tenant_id` | CharField(128) | NOT NULL, indexed | Multi-tenant isolation |
| `realm` | CharField(64) | DEFAULT 'default', indexed | RBAC realm isolation |
| `name` | CharField(255) | NOT NULL | Unique name within tenant |
| `description` | TextField | DEFAULT '' | Human-readable description |
| `version` | PositiveIntegerField | DEFAULT 1 | Auto-incrementing schema version |
| `deleted_at` | DateTimeField | NULL, indexed | Soft-deletion timestamp |
| `created_at` | DateTimeField | auto_now_add, indexed | Creation timestamp |
| `updated_at` | DateTimeField | auto_now, indexed | Last-update timestamp |

**Constraints:**
- `uq_object_type_name_active`: UNIQUE(`tenant_id`, `name`) WHERE `deleted_at IS NULL` — allows reusing names after soft-delete

**Indexes:**
- `idx_ot_tenant_name`: (`tenant_id`, `name`)

**Relationships:**
- `properties` → Property (reverse FK, CASCADE)
- `instances` → Object (reverse FK, PROTECT)
- `outgoing_link_types` → LinkType (reverse FK, source)
- `incoming_link_types` → LinkType (reverse FK, target)
- `interfaces` → Interface (M2M reverse)
- `shared_properties` → SharedProperty (M2M reverse)
- `action_types` → ActionType (reverse FK)
- `functions` → Function (reverse FK, attached_to_type)

**Soft Deletion:** Sets `deleted_at` to `timezone.now()`. Refuses if active instances exist.

**Version Control:** `version` increments by 1 on every `ObjectTypeService.update()` call.

---

#### 2.1.2 Property

**Table:** `ontology_property`
**Purpose:** A named, typed attribute on an object type.

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | PK | Primary key |
| `tenant_id` | CharField(128) | NOT NULL | Multi-tenant isolation |
| `realm` | CharField(64) | DEFAULT 'default' | RBAC realm isolation |
| `object_type` | FK → ObjectType | CASCADE, NOT NULL | Parent object type |
| `name` | CharField(255) | NOT NULL | Property name (unique per type) |
| `property_type` | CharField(32) | choices=PropertyType | Data type of this property |
| `required` | BooleanField | DEFAULT False | Whether required on instances |
| `default_value` | JSONField | NULL | Default value (JSON-encoded) |
| `validation_rules` | JSONField | NULL | Rules: regex, min, max, enum_values, custom |
| `metadata` | JSONField | DEFAULT {} | Arbitrary metadata (display_name, description) |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last-update timestamp |

**Constraints:**
- `uq_property_name_per_type`: UNIQUE(`object_type_id`, `name`)

**Indexes:**
- `idx_prop_object_type`: (`object_type_id`)

**PropertyType Enum (11 types):**

| Value | Python Type | Validation |
|-------|------------|------------|
| `string` | `str` | `isinstance(v, str)` |
| `integer` | `int` | `isinstance(v, int) and not isinstance(v, bool)` |
| `float` | `int, float` | `isinstance(v, (int, float)) and not isinstance(v, bool)` |
| `boolean` | `bool` | `isinstance(v, bool)` |
| `date` | `str` (ISO) | `datetime.strptime(v, "%Y-%m-%d")` |
| `timestamp` | `str` (ISO) | `datetime.fromisoformat(v)` |
| `enum` | any | `v in validation_rules["enum_values"]` |
| `array` | `list` | `isinstance(v, list)` |
| `map` | `dict` | `isinstance(v, dict)` |
| `struct` | `dict` | `isinstance(v, dict)` |
| `geopoint` | `list` | `isinstance(v, list) and len(v) == 2` |

**Validation Rules (JSONB):**

| Rule | Type | Example | Behavior |
|------|------|---------|----------|
| `regex` | `string` | `r"^[^@]+@[^@]+\.[^@]+$"` | `re.fullmatch(rule, str(value))` |
| `min` | `number` | `0` | `value >= rule` |
| `max` | `number` | `100` | `value <= rule` |
| `min_length` | `int` | `3` | `len(str(value)) >= rule` |
| `max_length` | `int` | `255` | `len(str(value)) <= rule` |
| `enum_values` | `list` | `["active", "inactive"]` | `value in rule` |

---

#### 2.1.3 Object

**Table:** `ontology_object`
**Purpose:** A specific instance of an object type (e.g., Customer #4521).

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | PK | Primary key |
| `tenant_id` | CharField(128) | NOT NULL | Multi-tenant isolation |
| `realm` | CharField(64) | DEFAULT 'default' | RBAC realm isolation |
| `object_type` | FK → ObjectType | PROTECT, NOT NULL | Schema this instance conforms to |
| `properties` | JSONField | DEFAULT {} | Key-value properties conforming to schema |
| `version` | PositiveIntegerField | DEFAULT 1 | Optimistic concurrency version |
| `deleted_at` | DateTimeField | NULL, indexed | Soft-deletion timestamp |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last-update timestamp |

**Indexes:**
- `idx_obj_type`: (`object_type_id`)
- `idx_obj_tenant_type`: (`tenant_id`, `object_type_id`)
- `idx_obj_tenant_created`: (`tenant_id`, `-created_at`)

**Soft Deletion:** Refuses if active links (incoming or outgoing) exist.

**Version Control:** Increments by 1 on every update. Optimistic locking: if caller passes `version` and it doesn't match, a `ValidationError` with code `conflict` is raised.

**Schema Validation:** Every create/update passes through `validate_properties()` which enforces type checks, required fields, default values, validation rules, and rejects unknown fields.

---

#### 2.1.4 LinkType

**Table:** `ontology_link_type`
**Purpose:** Schema for a relationship between two object types.

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | PK | Primary key |
| `tenant_id` | CharField(128) | NOT NULL | Multi-tenant isolation |
| `realm` | CharField(64) | DEFAULT 'default' | RBAC realm isolation |
| `name` | CharField(255) | NOT NULL | Unique link type name |
| `description` | TextField | DEFAULT '' | Human-readable description |
| `source_object_type` | FK → ObjectType | PROTECT, NOT NULL | Source object type |
| `target_object_type` | FK → ObjectType | PROTECT, NOT NULL | Target object type |
| `cardinality` | CharField(20) | DEFAULT 'one_to_many' | Cardinality enum |
| `properties_schema` | JSONField | NULL | JSON schema for link instance properties |
| `inverse_name` | CharField(255) | DEFAULT '' | Name for reverse traversal direction |
| `deleted_at` | DateTimeField | NULL, indexed | Soft-deletion timestamp |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last-update timestamp |

**Cardinality Enum:**

| Value | Meaning | Enforcement |
|-------|---------|-------------|
| `one_to_one` | Each source links to at most one target | Unique check on source_object per link type |
| `one_to_many` | Each source can link to many targets | No uniqueness constraint |
| `many_to_many` | Any source can link to any target | No uniqueness constraint |

**Constraints:**
- `uq_link_type_name_active`: UNIQUE(`tenant_id`, `name`) WHERE `deleted_at IS NULL`

**Indexes:**
- `idx_lt_tenant_name`: (`tenant_id`, `name`)
- `idx_lt_source`: (`source_object_type_id`)
- `idx_lt_target`: (`target_object_type_id`)

---

#### 2.1.5 Link

**Table:** `ontology_link`
**Purpose:** A specific occurrence of a link type connecting two object instances.

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | PK | Primary key |
| `tenant_id` | CharField(128) | NOT NULL | Multi-tenant isolation |
| `realm` | CharField(64) | DEFAULT 'default' | RBAC realm isolation |
| `link_type` | FK → LinkType | PROTECT, NOT NULL | Schema this link conforms to |
| `source_object` | FK → Object | CASCADE, NOT NULL | Source object instance |
| `target_object` | FK → Object | CASCADE, NOT NULL | Target object instance |
| `properties` | JSONField | DEFAULT {} | Optional properties on this link |
| `deleted_at` | DateTimeField | NULL, indexed | Soft-deletion timestamp |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last-update timestamp |

**Constraints:**
- `uq_link_instance_active`: UNIQUE(`link_type_id`, `source_object_id`, `target_object_id`) WHERE `deleted_at IS NULL`

**Indexes:**
- `idx_link_type`: (`link_type_id`)
- `idx_link_source`: (`source_object_id`)
- `idx_link_target`: (`target_object_id`)
- `idx_link_tenant_type`: (`tenant_id`, `link_type_id`)

**Referential Integrity:** On create, the service layer verifies:
1. Source object's type matches `link_type.source_object_type`
2. Target object's type matches `link_type.target_object_type`
3. For `one_to_one` cardinality, no existing active link from the same source

---

#### 2.1.6 Interface

**Table:** `ontology_interface`
**Purpose:** Polymorphic type abstraction. Describes the shape that multiple object types must implement.

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | PK | Primary key |
| `tenant_id` | CharField(128) | NOT NULL | Multi-tenant isolation |
| `realm` | CharField(64) | DEFAULT 'default' | RBAC realm isolation |
| `name` | CharField(255) | NOT NULL | Unique interface name |
| `description` | TextField | DEFAULT '' | Human-readable description |
| `version` | PositiveIntegerField | DEFAULT 1 | Interface version |
| `required_properties` | JSONField | DEFAULT [] | Required property definitions |
| `optional_properties` | JSONField | DEFAULT [] | Optional property definitions |
| `implementing_types` | M2M → ObjectType | blank=True | Object types that implement this interface |
| `deleted_at` | DateTimeField | NULL, indexed | Soft-deletion timestamp |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last-update timestamp |

**Constraints:**
- `uq_interface_name_active`: UNIQUE(`tenant_id`, `name`) WHERE `deleted_at IS NULL`

**Indexes:**
- `idx_iface_tenant_name`: (`tenant_id`, `name`)

**Property Definition Format:**
```json
[
  {"name": "email", "type": "string"},
  {"name": "created_at", "type": "timestamp"}
]
```

---

#### 2.1.7 StructType

**Table:** `ontology_struct_type`
**Purpose:** Nested composite type for complex properties (e.g., an `address` with `street`, `city`, `zip`).

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | PK | Primary key |
| `tenant_id` | CharField(128) | NOT NULL | Multi-tenant isolation |
| `realm` | CharField(64) | DEFAULT 'default' | RBAC realm isolation |
| `name` | CharField(255) | NOT NULL | Unique struct type name |
| `description` | TextField | DEFAULT '' | Human-readable description |
| `version` | PositiveIntegerField | DEFAULT 1 | Struct version |
| `fields` | JSONField | DEFAULT [] | List of field definitions |
| `deleted_at` | DateTimeField | NULL, indexed | Soft-deletion timestamp |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last-update timestamp |

**Constraints:**
- `uq_struct_type_name_active`: UNIQUE(`tenant_id`, `name`) WHERE `deleted_at IS NULL`

**Field Definition Format:**
```json
[
  {"name": "street", "type": "string", "required": true},
  {"name": "city", "type": "string", "required": true},
  {"name": "zip", "type": "string", "required": false}
]
```

---

#### 2.1.8 SharedProperty

**Table:** `ontology_shared_property`
**Purpose:** Reusable property definition that can be applied across multiple object types.

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | PK | Primary key |
| `tenant_id` | CharField(128) | NOT NULL | Multi-tenant isolation |
| `realm` | CharField(64) | DEFAULT 'default' | RBAC realm isolation |
| `name` | CharField(255) | NOT NULL | Unique shared property name |
| `description` | TextField | DEFAULT '' | Human-readable description |
| `property_type` | CharField(32) | choices=PropertyType | Data type |
| `default_value` | JSONField | NULL | Default value |
| `validation_rules` | JSONField | NULL | Validation rules |
| `metadata` | JSONField | DEFAULT {} | Arbitrary metadata |
| `used_by_types` | M2M → ObjectType | blank=True | Object types using this property |
| `deleted_at` | DateTimeField | NULL, indexed | Soft-deletion timestamp |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last-update timestamp |

**Constraints:**
- `uq_shared_prop_name_active`: UNIQUE(`tenant_id`, `name`) WHERE `deleted_at IS NULL`

---

#### 2.1.9 ValueType

**Table:** `ontology_value_type`
**Purpose:** Domain-specific value constraint with versioning (e.g., "email" = string + regex, "percentage" = float + 0–100).

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | PK | Primary key |
| `tenant_id` | CharField(128) | NOT NULL | Multi-tenant isolation |
| `realm` | CharField(64) | DEFAULT 'default' | RBAC realm isolation |
| `name` | CharField(255) | NOT NULL | Unique value type name |
| `description` | TextField | DEFAULT '' | Human-readable description |
| `base_type` | CharField(32) | choices=PropertyType | Underlying property type |
| `version` | PositiveIntegerField | DEFAULT 1 | Value type version |
| `constraints` | JSONField | DEFAULT {} | Constraint definitions |
| `created_by` | CharField(256) | blank | Creator |
| `is_system` | BooleanField | DEFAULT False | System types cannot be deleted |
| `deleted_at` | DateTimeField | NULL, indexed | Soft-deletion timestamp |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last-update timestamp |

**Constraints:**
- `uq_value_type_name_active`: UNIQUE(`tenant_id`, `name`) WHERE `deleted_at IS NULL`

**Constraint Format:**
```json
{
  "regex": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
  "min": 0,
  "max": 100,
  "enum_values": ["active", "inactive", "pending"]
}
```

---

#### 2.1.10 ActionType

**Table:** `ontology_action_type`
**Purpose:** Operation definition with parameters, pre-condition rules, side effects, and undo logic.

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | PK | Primary key |
| `tenant_id` | CharField(128) | NOT NULL | Multi-tenant isolation |
| `realm` | CharField(64) | DEFAULT 'default' | RBAC realm isolation |
| `name` | CharField(255) | NOT NULL | Unique action type name |
| `description` | TextField | DEFAULT '' | Human-readable description |
| `status` | CharField(20) | DEFAULT 'draft', indexed | Lifecycle status |
| `version` | PositiveIntegerField | DEFAULT 1 | Action type version |
| `target_object_type` | FK → ObjectType | PROTECT, NULL | Object type this action operates on |
| `parameters` | JSONField | DEFAULT [] | Parameter definitions |
| `rules` | JSONField | DEFAULT [] | Pre-condition rules |
| `side_effects` | JSONField | DEFAULT [] | Post-execution side effects |
| `undoable` | BooleanField | DEFAULT False | Whether undo is supported |
| `undo_rules` | JSONField | DEFAULT [] | Undo rule definitions |
| `required_permission` | CharField(256) | blank | Permission required to execute |
| `deleted_at` | DateTimeField | NULL, indexed | Soft-deletion timestamp |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last-update timestamp |

**Status Choices:**

| Status | Meaning |
|--------|---------|
| `draft` | Not yet executable |
| `active` | Can be executed |
| `deprecated` | No longer executable |

**Constraints:**
- `uq_action_type_name_active`: UNIQUE(`tenant_id`, `name`) WHERE `deleted_at IS NULL`

**Indexes:**
- `idx_action_tenant_status`: (`tenant_id`, `status`)
- `idx_action_target_type`: (`target_object_type_id`)

---

#### 2.1.11 Function

**Table:** `ontology_function`
**Purpose:** Business logic attached to objects or actions, executed in a sandboxed subprocess.

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | PK | Primary key |
| `tenant_id` | CharField(128) | NOT NULL | Multi-tenant isolation |
| `realm` | CharField(64) | DEFAULT 'default' | RBAC realm isolation |
| `name` | CharField(255) | NOT NULL | Unique function name |
| `description` | TextField | DEFAULT '' | Human-readable description |
| `status` | CharField(20) | DEFAULT 'draft', indexed | Lifecycle status |
| `version` | PositiveIntegerField | DEFAULT 1 | Function version |
| `language` | CharField(20) | DEFAULT 'python' | Runtime language |
| `source_code` | TextField | NOT NULL | Function source code |
| `entry_point` | CharField(255) | DEFAULT 'handler' | Entry point function name |
| `input_schema` | JSONField | DEFAULT {} | Input parameter schema |
| `output_schema` | JSONField | DEFAULT {} | Output schema |
| `attached_to_type` | FK → ObjectType | SET_NULL, NULL | Object type attachment |
| `attached_to_action` | FK → ActionType | SET_NULL, NULL | Action type attachment |
| `timeout_seconds` | IntegerField | DEFAULT 30 | Max execution time |
| `memory_limit_mb` | IntegerField | DEFAULT 128 | Max memory usage |
| `created_by` | CharField(256) | blank | Creator |
| `deleted_at` | DateTimeField | NULL, indexed | Soft-deletion timestamp |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last-update timestamp |

**Language Choices:**

| Value | Runtime |
|-------|---------|
| `python` | `sys.executable` (subprocess) |
| `typescript` | `bun` → `npx tsx` → `ts-node` (detected at runtime) |

**Constraints:**
- `uq_function_name_active`: UNIQUE(`tenant_id`, `name`) WHERE `deleted_at IS NULL`

**Indexes:**
- `idx_func_tenant_status`: (`tenant_id`, `status`)
- `idx_func_attached_type`: (`attached_to_type_id`)
- `idx_func_attached_action`: (`attached_to_action_id`)

---

#### 2.1.12 ActionExecution

**Table:** `ontology_action_execution`
**Purpose:** Records each action execution for undo support and audit trail.

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | PK | Primary key |
| `tenant_id` | CharField(128) | NOT NULL | Multi-tenant isolation |
| `realm` | CharField(64) | DEFAULT 'default' | RBAC realm isolation |
| `action_type` | FK → ActionType | PROTECT, NOT NULL | The action that was executed |
| `target_object` | FK → Object | PROTECT, NOT NULL | The object acted upon |
| `params` | JSONField | DEFAULT {} | Parameters passed to the action |
| `previous_values` | JSONField | DEFAULT {} | Snapshot of object properties before execution |
| `changes` | JSONField | DEFAULT {} | Diff of changes applied |
| `status` | CharField(20) | DEFAULT 'success' | Execution outcome |
| `actor` | CharField(256) | DEFAULT '' | User or service that performed the action |
| `errors` | JSONField | DEFAULT [] | Error details if failed |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last-update timestamp |

**Status Choices:**

| Status | Meaning |
|--------|---------|
| `success` | Action completed successfully |
| `failed` | Action failed during execution |
| `undone` | Action was undone |

**Indexes:**
- `idx_exec_tenant_action`: (`tenant_id`, `action_type_id`)
- `idx_exec_tenant_obj`: (`tenant_id`, `target_object_id`)

---

### 2.2 Service Layer — Complete Method Reference

#### 2.2.1 ObjectTypeService

| Method | Signature | Description | ONT-F Ref |
|--------|-----------|-------------|-----------|
| `list` | `(tenant_id, *, include_deleted=False) → QuerySet[ObjectType]` | Lists all object types, ordered by name. Excludes soft-deleted unless `include_deleted=True`. | ONT-F-001 |
| `get` | `(tenant_id, type_id) → ObjectType` | Gets a single active object type by ID. Raises `ObjectType.DoesNotExist` if not found. | ONT-F-001 |
| `create` | `(tenant_id, *, name, description="", properties=[], created_by="") → ObjectType` | Creates an object type with its properties in a single atomic transaction. Version starts at 1. | ONT-F-001, ONT-F-008 |
| `update` | `(tenant_id, type_id, *, name=None, description=None, properties=None) → ObjectType` | Updates with backward-compatibility checks: (1) cannot change type of required field, (2) new properties always allowed, (3) increments version. | ONT-F-006 |
| `soft_delete` | `(tenant_id, type_id) → None` | Soft-deletes. **Refuses** if active instances exist. | ONT-F-007 |

#### 2.2.2 ObjectService

| Method | Signature | Description | ONT-F Ref |
|--------|-----------|-------------|-----------|
| `list` | `(tenant_id, object_type_id=None) → QuerySet[Object]` | Lists active objects, optionally filtered by type, ordered by `-created_at`. | ONT-F-010 |
| `get` | `(tenant_id, object_id) → Object` | Gets a single active object. | ONT-F-010 |
| `create` | `(tenant_id, object_type_id, properties, *, created_by="") → Object` | Creates an object with full schema validation via `validate_properties()`. | ONT-F-010/011 |
| `update` | `(tenant_id, object_id, properties, *, version=None) → Object` | Updates with validation and optimistic concurrency. Merges with existing properties (partial update). If `version` is provided and doesn't match current, raises `conflict` error. | ONT-F-011/017 |
| `soft_delete` | `(tenant_id, object_id) → None` | Soft-deletes. **Refuses** if active incoming or outgoing links exist. | ONT-F-016 |
| `batch_create` | `(tenant_id, object_type_id, items) → list[Object]` | Creates 1000+ objects using `bulk_create()`. All-or-nothing: if any item fails validation, the entire batch rolls back. | ONT-F-013 |
| `upsert` | `(tenant_id, object_type_id, key_property, items) → list[Object]` | Upserts by a unique key property. Uses `properties__contains={key_property: key_val}` to find existing matches. Creates new or updates existing. | ONT-F-014 |

#### 2.2.3 LinkTypeService

| Method | Signature | Description | ONT-F Ref |
|--------|-----------|-------------|-----------|
| `list` | `(tenant_id) → QuerySet[LinkType]` | Lists all active link types, ordered by name. | ONT-F-020 |
| `get` | `(tenant_id, lt_id) → LinkType` | Gets a single active link type. | ONT-F-020 |
| `create` | `(tenant_id, *, name, source_object_type_id, target_object_type_id, cardinality="one_to_many", description="", properties_schema=None, inverse_name="") → LinkType` | Creates a link type. Validates that source and target object types exist in the same tenant. | ONT-F-020/021 |
| `soft_delete` | `(tenant_id, lt_id) → None` | Soft-deletes. **Refuses** if active link instances exist. | ONT-F-022 |

#### 2.2.4 LinkService

| Method | Signature | Description | ONT-F Ref |
|--------|-----------|-------------|-----------|
| `create` | `(tenant_id, link_type_id, source_object_id, target_object_id, properties=None) → Link` | Creates a link with referential integrity checks: (1) source type matches link type's source, (2) target type matches link type's target, (3) one-to-one uniqueness enforced. | ONT-F-030/023 |
| `delete` | `(tenant_id, link_id) → None` | Soft-deletes a link. | — |
| `traverse` | `(tenant_id, object_id, *, link_type_name=None, direction="outgoing", max_depth=1, filters=None) → list[dict]` | Multi-hop traversal up to 10 hops. Uses recursive DFS with visited set to prevent cycles. Returns list of dicts with `link_id`, `link_type`, `direction`, `object_id`, `object_type`, `properties`, `link_properties`, `depth`. | ONT-F-031/032/033 |

**Traversal Algorithm Detail:**

```python
def _traverse(obj_id, depth):
    if depth > max_depth or obj_id in visited:
        return
    visited.add(obj_id)
    
    # Query outgoing links (source → target)
    qs_out = Link.objects.filter(
        tenant_id=tenant_id,
        source_object_id=obj_id,
        deleted_at__isnull=True,
    )
    # Optionally filter by link_type__name
    if link_type_name:
        qs_out = qs_out.filter(link_type__name=link_type_name)
    
    if direction in ("outgoing", "both"):
        for link in qs_out.select_related("target_object", "link_type"):
            results.append({...})
            _traverse(str(link.target_object_id), depth + 1)
    
    # Same for incoming (target → source)
    if direction in ("incoming", "both"):
        for link in qs_in:
            results.append({...})
            _traverse(str(link.source_object_id), depth + 1)
```

- **Cycle protection:** `visited` set prevents revisiting nodes
- **Max depth:** Clamped to 10 at the API layer (`min(max_depth, 10)`)
- **Lazy loading:** Uses `select_related` to avoid N+1 queries per hop

---

### 2.3 Validation Layer

The `validators.py` module provides the core property validation engine.

#### `validate_properties(properties, property_defs, *, partial=False) → (normalised, errors)`

**Algorithm:**
1. For each property definition in the schema:
   a. If value is `None`:
      - If `required=True` and not `partial`: emit error, continue
      - If `default_value` is set: apply default
      - Else: set to `None`
   b. Type check against `PropertyType`:
      - `ENUM`: check value is in `validation_rules["enum_values"]`
      - `STRUCT`: check value is a `dict`
      - All others: check via `_TYPE_VALIDATORS` lambda map
   c. Rule-based validation: iterate `validation_rules` dict, apply each rule function
2. Reject any properties not in the schema (`unknown_field` error)
3. Return `(normalised_dict, error_list)`

**Key behaviors:**
- `partial=True` skips required checks (used for PATCH/update operations)
- Extra properties not in schema are rejected
- All errors are accumulated (not fail-fast)

---

### 2.4 Action Execution Engine

The `action_executor.py` module provides the `ActionExecutor` class.

#### `ActionExecutor.execute(tenant_id, action_type_id, object_id, params, *, actor="") → ActionResult`

**Pipeline:**
1. **Load** ActionType (must be active) and Object (must exist)
2. **Validate params** against the action's parameter schema (type checking)
3. **Check rules** (pre-condition checks):
   - `status_check`: `obj.properties[field] == expected_value`
   - `field_exists`: `field in obj.properties and obj.properties[field] is not None`
   - `field_value`: `obj.properties[field] == expected_value`
   - `permission_check`: calls `permission_checker(tenant_id, actor, permission)`
4. **Commit** (inside `transaction.atomic()`):
   a. Snapshot `previous_values = dict(obj.properties)`
   b. Apply `_apply_params_to_object()`: merge params into object properties, compute diff
   c. Increment `obj.version += 1`
   d. Execute side effects:
      - `notification`: logs notification event (stub)
      - `webhook`: POST to URL via `httpx`
      - `audit_log`: write to `AuditLog` model
      - `field_update`: update additional object properties
   e. Record `ActionExecution` with status `success`

#### `ActionExecutor.undo(tenant_id, action_id) → UndoResult`

**Pipeline:**
1. Load `ActionExecution` record
2. Verify status is `success` (not `already_undone` or `failed`)
3. Verify ActionType is `undoable`
4. Apply undo rules (inside `transaction.atomic()`):
   - `status_revert`: restore previous status field value
   - `field_revert`: restore specific fields from `previous_values`
   - If no explicit undo rules: full revert of all properties from snapshot
5. Increment `obj.version += 1`
6. Mark execution status as `undone`

---

### 2.5 Function Execution Engine

The `function_runner.py` module provides the `FunctionRunner` class.

#### `FunctionRunner.run(tenant_id, function_id, input_data) → FunctionResult`

**Pipeline:**
1. **Load** Function from cache or DB (cache invalidates on version change)
2. **Guard**: reject deprecated functions
3. **Validate input** against `input_schema` (required fields, type checks)
4. **Execute** in subprocess:
   - **Python**: write wrapper script to temp file, run with `subprocess.Popen`, kill on timeout
   - **TypeScript**: write wrapper script, detect runtime (`bun` → `npx tsx` → `ts-node`), run
   - Wrapper: loads user code via `exec()` (Python) or global eval (TS), calls entry point, prints JSON to stdout
5. **Parse output**: try full stdout as JSON, fallback to last line
6. **Validate output** against `output_schema` (type, required fields, property types)

**Function Cache (`_FunctionCache`):**
- In-memory dict keyed by `(tenant_id, function_id)`
- On every cache hit, checks DB version to detect stale entries
- Public API: `invalidate_function_cache()`, `clear_function_cache()`

---

### 2.6 REST API — Current Endpoints

All endpoints are under `Router(tags=["ontology"])` with default auth `require_permission("read:*")`.

#### Schema/Type Management

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/types` | read:* | List object types with counts |
| `POST` | `/types` | write:ontology | Create object type |
| `GET` | `/types/{type_id}` | read:* | Get type with properties |
| `PUT` | `/types/{type_id}` | write:ontology | Update type |
| `DELETE` | `/types/{type_id}` | write:ontology | Soft-delete type |
| `GET` | `/interfaces` | read:* | List interfaces |
| `POST` | `/interfaces` | write:ontology | Create interface |
| `GET` | `/interfaces/{iface_id}` | read:* | Get interface |
| `PUT` | `/interfaces/{iface_id}` | write:ontology | Update interface |
| `DELETE` | `/interfaces/{iface_id}` | write:ontology | Soft-delete interface |
| `GET` | `/structs` | read:* | List struct types |
| `POST` | `/structs` | write:ontology | Create struct type |
| `GET` | `/structs/{struct_id}` | read:* | Get struct type |
| `PUT` | `/structs/{struct_id}` | write:ontology | Update struct type |
| `DELETE` | `/structs/{struct_id}` | write:ontology | Soft-delete struct type |
| `GET` | `/shared-properties` | read:* | List shared properties |
| `POST` | `/shared-properties` | write:ontology | Create shared property |
| `GET` | `/shared-properties/{prop_id}` | read:* | Get shared property |
| `PUT` | `/shared-properties/{prop_id}` | write:ontology | Update shared property |
| `DELETE` | `/shared-properties/{prop_id}` | write:ontology | Soft-delete shared property |
| `GET` | `/value-types` | read:* | List value types |
| `POST` | `/value-types` | write:ontology | Create value type |
| `GET` | `/value-types/{vt_id}` | read:* | Get value type |
| `PUT` | `/value-types/{vt_id}` | write:ontology | Update value type |
| `DELETE` | `/value-types/{vt_id}` | write:ontology | Soft-delete value type |

#### Object Instance CRUD

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/objects` | read:* | List objects (filter by `object_type_id`, limit) |
| `POST` | `/objects` | write:ontology | Create object |
| `GET` | `/objects/{object_id}` | read:* | Get object |
| `PUT` | `/objects/{object_id}` | write:ontology | Update object (optimistic concurrency) |
| `DELETE` | `/objects/{object_id}` | write:ontology | Soft-delete object |
| `POST` | `/objects/batch` | write:ontology | Batch create objects |
| `POST` | `/objects/upsert` | write:ontology | Upsert by key property |

#### Link Type & Instance

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/link-types` | read:* | List link types |
| `POST` | `/link-types` | write:ontology | Create link type |
| `GET` | `/link-types/{lt_id}` | read:* | Get link type |
| `PUT` | `/link-types/{lt_id}` | write:ontology | Update link type |
| `DELETE` | `/link-types/{lt_id}` | write:ontology | Soft-delete link type |
| `GET` | `/links` | read:* | List links (filter by `link_type_id`, limit) |
| `POST` | `/links` | write:ontology | Create link |
| `DELETE` | `/links/{link_id}` | write:ontology | Soft-delete link |

#### Action Types & Functions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/actions` | read:* | List action types (filter by `status`) |
| `POST` | `/actions` | write:ontology | Create action type |
| `GET` | `/actions/{action_id}` | read:* | Get action type |
| `PUT` | `/actions/{action_id}` | write:ontology | Update action type |
| `DELETE` | `/actions/{action_id}` | write:ontology | Soft-delete action type |
| `GET` | `/functions` | read:* | List functions (filter by `status`) |
| `POST` | `/functions` | write:ontology | Create function |
| `GET` | `/functions/{func_id}` | read:* | Get function |
| `PUT` | `/functions/{func_id}` | write:ontology | Update function |
| `DELETE` | `/functions/{func_id}` | write:ontology | Soft-delete function |

#### Traversal

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/objects/{object_id}/traverse` | read:* | Traverse links (multi-hop up to 10) |

**Total: 44 REST endpoints.**

**Pagination/Filtering/Sorting:**
- Objects: `limit` query param (default 100), `object_type_id` filter
- Links: `limit` query param (default 100), `link_type_id` filter
- Action types: `status` filter
- Functions: `status` filter
- **Missing:** cursor-based pagination, arbitrary property filtering, sort parameters

---

### 2.7 MCP Tools — Current

| Tool Name | Parameters | Internal Call | Description |
|-----------|-----------|---------------|-------------|
| `voyant.ontology.types.list` | `tenant_id?` | `ObjectType.objects.filter(...)` | List all object types with counts |
| `voyant.ontology.types.get` | `type_id`, `tenant_id?` | `ObjectTypeService.get()` | Get type with property definitions |
| `voyant.ontology.types.create` | `name`, `description?`, `properties?`, `tenant_id?` | `ObjectTypeService.create()` | Create new object type |
| `voyant.ontology.objects.list` | `type_id?`, `limit?`, `tenant_id?` | `ObjectService.list()` | List objects filtered by type |
| `voyant.ontology.objects.create` | `type_id`, `properties`, `tenant_id?` | `ObjectService.create()` | Create object with validation |
| `voyant.ontology.objects.get` | `object_id`, `tenant_id?` | `ObjectService.get()` + Link queries | Get object with all links |
| `voyant.ontology.objects.update` | `object_id`, `properties`, `version?`, `tenant_id?` | `ObjectService.update()` | Update with optimistic concurrency |
| `voyant.ontology.objects.batch_create` | `type_id`, `items`, `tenant_id?` | `ObjectService.batch_create()` | Batch create 1000+ objects |
| `voyant.ontology.links.create` | `link_type_id`, `source_object_id`, `target_object_id`, `properties?`, `tenant_id?` | `LinkService.create()` | Create link between objects |
| `voyant.ontology.links.delete` | `link_id`, `tenant_id?` | `LinkService.delete()` | Delete link |
| `voyant.ontology.traverse` | `object_id`, `direction?`, `max_depth?`, `link_type_name?`, `tenant_id?` | `LinkService.traverse()` | Multi-hop traversal |
| `voyant.ontology.interfaces.list` | `tenant_id?` | `Interface.objects.filter(...)` | List interfaces |
| `voyant.ontology.actions.execute` | `action_type_id`, `object_id`, `params?`, `tenant_id?` | `ActionExecutor.execute()` | Execute action on object |
| `voyant.ontology.functions.run` | `function_id`, `input_data?`, `tenant_id?` | `FunctionRunner.run()` | Run sandboxed function |

**Total: 14 MCP tools.**

---

## 3. Palantir Comparison (Deep)

### 3.1 Object Types

| Dimension | Palantir Foundry | Voyant v3.x | Gap | Voyant v4.0 Design |
|-----------|-----------------|-------------|-----|---------------------|
| **Schema Definition** | Rich schema with title, description, icon, color, plural name | Basic name + description | Missing: icon, color, plural, display config | Add `render_config` JSONB field with icon, color, plural_name, primary_display_property |
| **Property Types** | 11 types (string, int, float, boolean, date, decimal, timestamp, media, geopoint, array, object) | 11 types (same set minus decimal/media, plus enum/map/struct) | Parity achieved | Add `decimal` (high-precision) and `media` (file reference) types |
| **Type Inheritance** | Supports abstract types that concrete types extend | No inheritance model | Missing | Use Interfaces as abstract type definitions; concrete types implement interfaces |
| **Display Config** | Per-type render hints (icon, color, which property is primary) | None | Missing | `render_config` JSONB on ObjectType |
| **Type Groups** | Groups for organizing types (e.g., "Customer Types", "Product Types") | None | Missing | New `ObjectTypeGroup` model with M2M to ObjectType |
| **Status Definitions** | Lifecycle states with allowed transitions per type | None | Missing | New `StatusDefinition` model |
| **Schema Evolution** | Automatic versioning with migration scripts | `version` field + backward-compatibility checks in `update()` | Partial — no migration scripts | Add schema migration service with diff detection and migration scripts |

**How Voyant v4.0 Improves:**
- **Render Config** stored as structured JSONB rather than Palantir's opaque UI config — allows programmatic access by agents
- **Interface-based inheritance** is more explicit than Palantir's implicit type extensions
- **Open schema format** (JSON) vs Palantir's proprietary format

### 3.2 Properties

| Dimension | Palantir Foundry | Voyant v3.x | Gap | Voyant v4.0 Design |
|-----------|-----------------|-------------|-----|---------------------|
| **11 Base Types** | Yes | Yes | Parity | Keep all 11 |
| **Decimal Type** | High-precision decimal for financial data | None (use float) | Missing | Add `decimal` PropertyType with configurable precision |
| **Media Type** | File/image references | None | Missing | Add `media` PropertyType with URL/path storage |
| **Required Flag** | Yes | Yes | Parity | Keep |
| **Default Values** | Yes | Yes | Parity | Keep |
| **Validation Rules** | Rich validation (range, regex, custom) | regex/min/max/min_length/max_length/enum_values | Parity | Add: `custom_fn` (reference to a Function ID for validation) |
| **Display Name** | Separate display name from API name | In `metadata` JSONB | Partial | Promote to first-class field `display_name` |
| **Description** | Per-property description | In `metadata` JSONB | Partial | Promote to first-class field `description` |
| **Searchable Flag** | Controls indexing behavior | None | Missing | Add `searchable` boolean, `indexed` boolean |
| **Immutable Flag** | Prevents mutation after creation | None | Missing | Add `immutable` boolean |
| **Hidden Flag** | Hide from UI but store data | None | Missing | Add `hidden` boolean |

**How Voyant v4.0 Improves:**
- **`custom_fn` validation**: Reference a Function by ID for complex validation logic (e.g., "validate this email against the blacklist database"). Palantir has no equivalent — they rely on hardcoded validators.
- **Agent-readable metadata**: `display_name`, `description`, `searchable` are first-class fields, not buried in JSONB, making them discoverable by agents.
- **`immutable` flag**: Critical for audit trails — once a ticket is "closed", its status cannot be changed except through a formal Action Type with undo.

### 3.3 Link Types

| Dimension | Palantir Foundry | Voyant v3.x | Gap | Voyant v4.0 Design |
|-----------|-----------------|-------------|-----|---------------------|
| **Cardinality** | 1:1, 1:N, M:N | 1:1, 1:N, M:N | Parity | Keep |
| **Directional** | Yes (source → target) | Yes | Parity | Keep |
| **Inverse Name** | Yes | Yes (`inverse_name` field) | Parity | Keep |
| **Link Properties** | Yes (properties on edges) | Yes (`properties_schema` + `properties` on instances) | Parity | Keep |
| **Self-Referential Links** | Yes (type links to itself) | Yes (tested in `test_traverse_multi_hop`) | Parity | Keep |
| **Link Validation** | Validates source/target types match | Yes (in `LinkService.create`) | Parity | Keep |
| **Conditional Links** | Links that exist only when conditions met | None | Missing | Add `conditions` JSONB field on LinkType |
| **Temporal Links** | Links with time ranges (valid_from, valid_to) | None | Missing | Add `valid_from`/`valid_to` to Link model |
| **Link Strength/Weight** | Numeric weight on links for graph algorithms | None | Missing | Add `weight` FloatField to Link model |

**How Voyant v4.0 Improves:**
- **Temporal links** with `valid_from`/`valid_to`: "Employee works_at Office from 2024-01-01 to 2025-06-30". Palantir requires separate objects to model this; Voyant puts it on the edge.
- **Link weight**: Enables graph algorithms (PageRank, shortest path, community detection) directly on the ontology graph.
- **Conditional links**: "Link is active only when source.status == 'active'". Palantir has no equivalent — links are unconditional.

### 3.4 Interfaces (Polymorphic Types)

| Dimension | Palantir Foundry | Voyant v3.x | Gap | Voyant v4.0 Design |
|-----------|-----------------|-------------|-----|---------------------|
| **Interface Definition** | Supported — defines shared shape | Model exists, API exists, but no validation enforcement | Partial | Add validation: when ObjectType implements Interface, verify it has all required properties |
| **Multiple Inheritance** | Object type can implement multiple interfaces | Same (M2M relationship) | Parity | Keep |
| **Interface Queries** | Query objects across all types implementing an interface | Not implemented | Missing | Add `/interfaces/{id}/objects` endpoint that queries across implementing types |
| **Interface Validation** | On type update, verify still satisfies all interfaces | Not implemented | Missing | Add `_validate_interface_compliance()` to `ObjectTypeService.update()` |

**How Voyant v4.0 Improves:**
- **Cross-type queries via interfaces**: "Show me all objects that implement `Auditable`" returns results from Customer, Order, Ticket, etc. This is more powerful than Palantir's type-group queries because interfaces carry semantic meaning.
- **Agent discovery**: Agents can discover interfaces to understand what operations are available on unknown types.

### 3.5 Structs

| Dimension | Palantir Foundry | Voyant v3.x | Gap | Voyant v4.0 Design |
|-----------|-----------------|-------------|-----|---------------------|
| **Struct Definition** | Nested composite types | Model exists with `fields` JSONB | Partial | Add validation service for struct fields |
| **Nested Structs** | Struct within struct | Not validated | Missing | Add recursive struct validation |
| **Struct Versioning** | Yes | `version` field exists | Parity | Keep |
| **Struct Validation** | Validates struct values against schema | Not enforced at property level | Missing | When `property_type == "struct"`, look up StructType and validate recursively |

**How Voyant v4.0 Improves:**
- **Recursive validation**: Struct within struct within struct, all validated at write time.
- **Auto-documentation**: StructType's `fields` JSONB is machine-readable, enabling agents to generate API documentation automatically.

### 3.6 Shared Properties

| Dimension | Palantir Foundry | Voyant v3.x | Gap | Voyant v4.0 Design |
|-----------|-----------------|-------------|-----|---------------------|
| **Reusable Definitions** | Supported | Model + M2M exist | Partial | Add "apply" service: copy shared property definition to target types |
| **Sync on Change** | Changing shared property propagates to all types | Not implemented | Missing | Add `_propagate_shared_property_change()` |
| **Override** | Types can override shared property defaults | Not implemented | Missing | Add `overrides` JSONB on the M2M through-table |

### 3.7 Value Types

| Dimension | Palantir Foundry | Voyant v3.x | Gap | Voyant v4.0 Design |
|-----------|-----------------|-------------|-----|---------------------|
| **Domain Constraints** | Reusable value constraints | Model exists with `constraints` JSONB | Partial | Add validation enforcement in `validate_properties()` |
| **System Types** | Pre-defined system types | `is_system` flag exists | Parity | Keep |
| **Versioning** | Yes | `version` field exists | Parity | Keep |
| **Enforcement** | Properties can reference value types | Properties don't reference ValueTypes | Missing | Add `value_type_id` FK on Property model |

**How Voyant v4.0 Improves:**
- **Direct Property→ValueType binding**: `Property.value_type_id` FK allows the validator to automatically look up and enforce domain constraints. No manual rule duplication.
- **Built-in system value types**: `email`, `phone`, `url`, `percentage`, `currency_USD` pre-seeded.

### 3.8 Actions (Palantir's Kinetics)

| Dimension | Palantir Foundry | Voyant v3.x | Gap | Voyant v4.0 Design |
|-----------|-----------------|-------------|-----|---------------------|
| **Action Definition** | Rich actions with params, rules, side effects | ActionType model with all fields | **IMPLEMENTED** | Keep + enhancements |
| **Parameter Types** | String, integer, float, boolean, array, object, enum | Same (6 types in `_PARAM_TYPE_MAP`) | Parity | Add: date, timestamp, geopoint, media |
| **Pre-condition Rules** | Complex rules engine | 4 rule types (status_check, field_exists, field_value, permission_check) | Partial | Add: `linked_object_check`, `date_range_check`, `custom_function` |
| **Side Effects** | Notifications, webhooks, field updates, audit | 4 types (notification, webhook, audit_log, field_update) | Partial | Add: `email`, `sms`, `temporal_workflow`, `agent_prompt` |
| **Undo Support** | Supported with revert logic | Full undo with `previous_values` snapshot and undo rules | **IMPLEMENTED** | Keep |
| **Batch Actions** | Execute action on multiple objects at once | Not implemented | Missing | Add `batch_execute()` to ActionExecutor |
| **Action Metrics** | Execution counts, success rates, latency | Not implemented | Missing | Add `ActionMetrics` model (aggregated from ActionExecution) |
| **Action Workflows** | Chain actions in sequences | Not implemented | Missing | Add `ActionWorkflow` model linking action chains |
| **Conditional Side Effects** | Side effects that fire only when conditions met | Not implemented | Missing | Add `conditions` on side_effect definitions |

**How Voyant v4.0 Improves:**
- **`agent_prompt` side effect**: After an action executes, automatically prompt an agent with context ("The ticket was assigned to Bob. Would you like to notify the customer?"). Palantir has zero agent integration.
- **`temporal_workflow` side effect**: Start a durable workflow after action execution (e.g., "after assigning ticket, start SLA countdown workflow"). Palantir's Kinetics has no workflow engine integration.
- **Batch execute**: Execute the same action on N objects atomically. Palantir requires building a Workshop widget for this.
- **Custom function rules**: Reference a Function ID as a pre-condition rule — arbitrary logic instead of hardcoded rule types.

### 3.9 Functions

| Dimension | Palantir Foundry | Voyant v3.x | Gap | Voyant v4.0 Design |
|-----------|-----------------|-------------|-----|---------------------|
| **Python Functions** | Yes (server-side) | Yes (subprocess sandbox) | **IMPLEMENTED** | Keep |
| **TypeScript Functions** | Yes | Yes (bun/tsx/ts-node) | **IMPLEMENTED** | Keep |
| **Function Versioning** | Yes | `version` field + cache invalidation | **IMPLEMENTED** | Keep |
| **Input/Output Schemas** | Yes | Yes (JSON schema validation) | **IMPLEMENTED** | Keep |
| **Timeout/Memory Limits** | Yes | Yes (timeout_seconds, memory_limit_mb) | **IMPLEMENTED** | Keep |
| **Function Monitoring** | Real-time metrics | Not implemented | Missing | Add `FunctionMetrics` model (calls, avg_duration, error_rate) |
| **Streaming Functions** | Yes (streaming output) | Not implemented | Missing | Add `streaming` flag + SSE/WebSocket support |
| **Function Testing** | Built-in test runner | Not implemented | Missing | Add `/functions/{id}/test` endpoint |
| **Dependency Management** | Python/TS package installation | Not implemented | Missing | Add `dependencies` JSONB + pip/npm install in sandbox |
| **Async Functions** | Yes | Not implemented | Missing | Add `async` flag + async subprocess |

**How Voyant v4.0 Improves:**
- **MCP-callable functions**: Any ontology function can be invoked via MCP tools by agents. Palantir functions are only callable from Workshop widgets.
- **Built-in testing**: `/functions/{id}/test` endpoint runs the function with sample input and returns the result. Palantir has no function test endpoint.
- **Dependency management**: Declare `dependencies: {"requests": ">=2.28", "pandas": ">=2.0"}` and the sandbox installs them before execution.

### 3.10 Object Set Service

| Dimension | Palantir Foundry | Voyant v3.x | Gap | Voyant v4.0 Design |
|-----------|-----------------|-------------|-----|---------------------|
| **Query Language** | Rich query DSL with filters, aggregations, joins | Django ORM only (list with basic filtering) | Major gap | Add structured query endpoint |
| **Filtering** | Property-level filters (equals, contains, range, etc.) | Only `object_type_id` filter | Missing | Add `POST /objects/query` with rich filter DSL |
| **Aggregation** | Count, sum, avg, min, max, group by | Not implemented | Missing | Add aggregation support in query endpoint |
| **Sorting** | Multi-field sorting | Only `-created_at` ordering | Missing | Add `sort_by` parameter |
| **Pagination** | Cursor-based | Limit-only | Missing | Add cursor-based pagination |
| **Full-Text Search** | PostgreSQL-based full-text | Milvus-based semantic only | Partial | Add PostgreSQL full-text index on properties JSONB |
| **Cross-Type Queries** | Query across types via interfaces | Not implemented | Missing | Interface-based cross-type queries |
| **Streaming Results** | Return results as stream for large sets | Not implemented | Missing | Add streaming response for queries returning 10K+ objects |

### 3.11 Subscription Service

| Dimension | Palantir Foundry | Voyant v3.x | Gap | Voyant v4.0 Design |
|-----------|-----------------|-------------|-----|---------------------|
| **Change Notifications** | Real-time notifications on object changes | Not implemented | Missing | Redis Pub/Sub on every create/update/delete |
| **Filtered Subscriptions** | Subscribe to specific types, properties, or conditions | Not implemented | Missing | Channel-per-type + filter conditions |
| **WebSocket API** | Yes | Not implemented | Missing | Django Channels WebSocket consumer |
| **Event Replay** | Replay events from a timestamp | Not implemented | Missing | Event log with replay capability |
| **Fan-Out** | Multiple subscribers per event | Not implemented | Missing | Redis Pub/Sub fan-out (built-in) |

---

## 4. Improvements Over Palantir

### 4.1 MCP Agent Access (Palantir Has ZERO)

**What Palantir does:** All ontology operations are human-only via Workshop UI or OSDK. No programmatic agent access.

**What Voyant does BETTER:**

| Capability | Design | MCP Tool |
|-----------|--------|----------|
| Agent creates object types | Full CRUD via MCP tools | `voyant.ontology.types.create` |
| Agent creates objects | Schema-validated creation | `voyant.ontology.objects.create` |
| Agent traverses graph | Multi-hop with direction control | `voyant.ontology.traverse` |
| Agent executes actions | Full action lifecycle | `voyant.ontology.actions.execute` |
| Agent runs functions | Sandboxed execution | `voyant.ontology.functions.run` |
| Agent queries by NL | Intent Engine integration | `voyant.ontology.query` (proposed) |
| Agent discovers schema | Introspect types, interfaces, links | `voyant.ontology.schema.discover` (proposed) |

**Technical approach:** Every MCP tool calls the service layer directly — no duplicated business logic. The `_tenant()` helper from `tools_core.py` provides tenant isolation.

### 4.2 Intent Engine Integration (NL → Ontology Operations)

**What Palantir does:** Users must manually navigate Workshop UI to perform ontology operations.

**What Voyant does BETTER:** Natural language → ontology operations via the Intent Engine.

**Proposed Design:**

```
User: "Create a Customer named Alice with email alice@example.com"
  → Intent Engine parses intent
  → Calls: ObjectTypeService.get("Customer")
  → Calls: ObjectService.create(tenant_id, "Customer", {"name": "Alice", "email": "alice@example.com"})
  → Returns: "Created Customer #uuid with properties name=Alice, email=alice@example.com"
```

**New MCP Tool Design:**

```json
{
  "name": "voyant.ontology.query",
  "description": "Execute a structured ontology query with filters, sorting, and pagination",
  "parameters": {
    "type_name": {"type": "string", "required": true},
    "filters": {"type": "array", "required": false},
    "sort_by": {"type": "string", "required": false},
    "limit": {"type": "integer", "required": false},
    "cursor": {"type": "string", "required": false}
  }
}
```

### 4.3 Self-Hosted (Palantir Is Cloud-Only)

**What Palantir does:** SaaS-only. Data leaves your infrastructure. $10M+/year contracts.

**What Voyant does BETTER:**
- Docker Compose deployment (20 containers)
- All data stays on-premise
- PostgreSQL as single storage backend
- No vendor lock-in
- Apache 2.0 license

### 4.4 Open Schema (Palantir Is Proprietary)

**What Palantir does:** Proprietary ontology format. Cannot export/import.

**What Voyant does BETTER:**
- All schema definitions are JSON-serializable
- `POST /ontology/export` → complete schema as JSON
- `POST /ontology/import` → import schema from JSON
- Portable across instances
- Version-controllable (git-friendly JSON)

**Proposed endpoint:**

```
POST /api/v1/ontology/export
Response: {
  "object_types": [...],
  "link_types": [...],
  "interfaces": [...],
  "action_types": [...],
  "functions": [...],
  "exported_at": "2026-09-10T00:00:00Z"
}
```

### 4.5 Temporal Durability (Actions Tracked in Workflows)

**What Palantir does:** Actions execute and are logged. No built-in workflow orchestration.

**What Voyant does BETTER:**
- Actions can trigger Temporal workflows
- Workflows are durable and replayable
- Long-running processes (SLA tracking, approval chains) are first-class
- Full execution history with undo

**Proposed `temporal_workflow` side effect:**

```json
{
  "type": "temporal_workflow",
  "workflow_type": "sla_countdown",
  "params": {
    "object_id": "{{object.id}}",
    "sla_hours": 24
  }
}
```

### 4.6 Capsule Integration (Ontology Operations as Portable Recipes)

**What Palantir does:** Operations are tied to Workshop apps. Not portable.

**What Voyant does BETTER:**
- Ontology operations can be packaged as Capsules
- Capsules are signed (Ed25519) and portable
- A Capsule can contain: "Create type X, create objects Y, link them via Z, execute action A"
- Share recipes between tenants or instances

### 4.7 Additional Improvements

| Area | Palantir Limitation | Voyant v4.0 Advantage |
|------|--------------------|-----------------------|
| **Batch Actions** | Requires Workshop widget | `ActionExecutor.batch_execute()` API + MCP tool |
| **Function Testing** | No built-in test runner | `POST /functions/{id}/test` endpoint |
| **Schema Diff** | Manual comparison | `GET /types/{id}/diff?from_version=1&to_version=3` |
| **Graph Algorithms** | Not built-in | `POST /objects/{id}/shortest-path`, `pagerank`, `community-detect` |
| **Temporal Queries** | Not supported | "Show me all objects that changed between date A and date B" |
| **Bulk Import** | Via Pipeline Builder | `POST /objects/import` with CSV/JSON upload |

---

## 5. Improvements Over Databricks Unity Catalog

### 5.1 Architecture Comparison

| Dimension | Databricks Unity Catalog | Voyant Ontology Engine |
|-----------|-------------------------|------------------------|
| **Data Model** | Hierarchical: Catalog → Schema → Table → Column | Graph: ObjectTypes → Properties, Links, Actions, Functions |
| **Relationships** | Foreign key metadata only (no traversal) | Native graph with multi-hop traversal |
| **Operations** | SQL queries via Spark/Photon | REST API + MCP tools + Action Types |
| **Business Logic** | External (notebooks, jobs) | Built-in (Action Types + Functions) |
| **Agent Access** | Via SQL only | Native MCP tools (14 tools, growing) |
| **Validation** | Schema-on-read (Delta Lake) | Schema-on-write (validate_properties) |
| **Multi-Tenancy** | Workspace-level isolation | Row-level tenant isolation |
| **Deployment** | Cloud-only (AWS/Azure/GCP) | Self-hosted Docker |

### 5.2 Why Graph > Hierarchy for Agent-Native Systems

**Databricks Unity Catalog:**
```
catalog.sales_db
  ├── schema.customers
  │   └── table.customer_data (id, name, email, address)
  └── schema.orders
      └── table.order_data (id, customer_id, amount, date)
```

- Relationships are implicit (customer_id → customers.id)
- No native traversal ("show me all orders for this customer" requires SQL JOIN)
- Agents must understand SQL to query

**Voyant Ontology:**
```
ObjectType: Customer (name: string, email: string)
ObjectType: Order (amount: float, date: date)
LinkType: places (Customer → Order, one_to_many)
ActionType: approve_order (target: Order, rules: [status=open])
Function: calculate_discount (attached_to: Order, language: python)
```

- Relationships are explicit and typed
- Native traversal: `POST /objects/{customer_id}/traverse` returns all orders
- Agents use MCP tools (no SQL knowledge required)
- Actions and Functions are part of the domain model

### 5.3 Specific Advantages

| Use Case | Databricks | Voyant |
|----------|-----------|--------|
| "Find all orders for customer X" | SQL JOIN across tables | `traverse(customer_id, direction="outgoing")` |
| "Approve this order" | Write notebook code | `execute(approve_order, order_id, params)` |
| "Calculate discount" | UDF in Spark | `FunctionRunner.run(discount_fn, {order_id})` |
| "What types exist?" | `SHOW TABLES` (flat list) | `voyant.ontology.types.list` (with relationships) |
| "Alert when order approved" | External job scheduler | Side effect: `notification` + `temporal_workflow` |
| "Agent, create a new customer type" | Cannot (requires DDL privileges + SQL) | `voyant.ontology.types.create(name="Customer", ...)` |

---

## 6. Complete API Design (v4.0 Target)

### 6.1 Schema Management

| Method | Path | Request Schema | Response Schema | Auth | MCP Tool |
|--------|------|---------------|-----------------|------|----------|
| `GET` | `/types` | Query: `include_deleted`, `group_id` | `list[ObjectTypeOut]` | read:* | `voyant.ontology.types.list` |
| `POST` | `/types` | `CreateObjectTypeIn` | `ObjectTypeOut` | write:ontology | `voyant.ontology.types.create` |
| `GET` | `/types/{type_id}` | — | `ObjectTypeDetailOut` | read:* | `voyant.ontology.types.get` |
| `PUT` | `/types/{type_id}` | `UpdateObjectTypeIn` | `ObjectTypeOut` | write:ontology | `voyant.ontology.types.update` |
| `DELETE` | `/types/{type_id}` | — | `{"status": "deleted"}` | write:ontology | `voyant.ontology.types.delete` |
| `GET` | `/types/{type_id}/diff` | Query: `from_version`, `to_version` | `SchemaDiffOut` | read:* | `voyant.ontology.types.diff` |
| `GET` | `/types/{type_id}/objects` | Query: `limit`, `cursor`, `filters` | `PaginatedObjectsOut` | read:* | `voyant.ontology.types.objects` |

### 6.2 Interfaces

| Method | Path | Request Schema | Response Schema | Auth | MCP Tool |
|--------|------|---------------|-----------------|------|----------|
| `GET` | `/interfaces` | — | `list[InterfaceOut]` | read:* | `voyant.ontology.interfaces.list` |
| `POST` | `/interfaces` | `CreateInterfaceIn` | `InterfaceOut` | write:ontology | `voyant.ontology.interfaces.create` |
| `GET` | `/interfaces/{id}` | — | `InterfaceDetailOut` | read:* | `voyant.ontology.interfaces.get` |
| `PUT` | `/interfaces/{id}` | `UpdateInterfaceIn` | `InterfaceOut` | write:ontology | `voyant.ontology.interfaces.update` |
| `DELETE` | `/interfaces/{id}` | — | `{"status": "deleted"}` | write:ontology | `voyant.ontology.interfaces.delete` |
| `POST` | `/interfaces/{id}/implement` | `{"object_type_id": "..."}` | `InterfaceOut` | write:ontology | `voyant.ontology.interfaces.implement` |
| `GET` | `/interfaces/{id}/objects` | Query: `limit`, `cursor` | `PaginatedObjectsOut` | read:* | `voyant.ontology.interfaces.objects` |

### 6.3 Struct Types

| Method | Path | Request Schema | Response Schema | Auth | MCP Tool |
|--------|------|---------------|-----------------|------|----------|
| `GET` | `/structs` | — | `list[StructTypeOut]` | read:* | `voyant.ontology.structs.list` |
| `POST` | `/structs` | `CreateStructTypeIn` | `StructTypeOut` | write:ontology | `voyant.ontology.structs.create` |
| `GET` | `/structs/{id}` | — | `StructTypeDetailOut` | read:* | `voyant.ontology.structs.get` |
| `PUT` | `/structs/{id}` | `UpdateStructTypeIn` | `StructTypeOut` | write:ontology | `voyant.ontology.structs.update` |
| `DELETE` | `/structs/{id}` | — | `{"status": "deleted"}` | write:ontology | `voyant.ontology.structs.delete` |

### 6.4 Shared Properties

| Method | Path | Request Schema | Response Schema | Auth | MCP Tool |
|--------|------|---------------|-----------------|------|----------|
| `GET` | `/shared-properties` | — | `list[SharedPropertyOut]` | read:* | `voyant.ontology.shared_properties.list` |
| `POST` | `/shared-properties` | `CreateSharedPropertyIn` | `SharedPropertyOut` | write:ontology | `voyant.ontology.shared_properties.create` |
| `GET` | `/shared-properties/{id}` | — | `SharedPropertyDetailOut` | read:* | `voyant.ontology.shared_properties.get` |
| `PUT` | `/shared-properties/{id}` | `UpdateSharedPropertyIn` | `SharedPropertyOut` | write:ontology | `voyant.ontology.shared_properties.update` |
| `DELETE` | `/shared-properties/{id}` | — | `{"status": "deleted"}` | write:ontology | `voyant.ontology.shared_properties.delete` |
| `POST` | `/shared-properties/{id}/apply` | `{"object_type_id": "..."}` | `{"status": "applied"}` | write:ontology | `voyant.ontology.shared_properties.apply` |

### 6.5 Value Types

| Method | Path | Request Schema | Response Schema | Auth | MCP Tool |
|--------|------|---------------|-----------------|------|----------|
| `GET` | `/value-types` | — | `list[ValueTypeOut]` | read:* | `voyant.ontology.value_types.list` |
| `POST` | `/value-types` | `CreateValueTypeIn` | `ValueTypeOut` | write:ontology | `voyant.ontology.value_types.create` |
| `GET` | `/value-types/{id}` | — | `ValueTypeDetailOut` | read:* | `voyant.ontology.value_types.get` |
| `PUT` | `/value-types/{id}` | `UpdateValueTypeIn` | `ValueTypeOut` | write:ontology | `voyant.ontology.value_types.update` |
| `DELETE` | `/value-types/{id}` | — | `{"status": "deleted"}` | write:ontology | `voyant.ontology.value_types.delete` |

### 6.6 Objects

| Method | Path | Request Schema | Response Schema | Auth | MCP Tool |
|--------|------|---------------|-----------------|------|----------|
| `GET` | `/objects` | Query: `type_id`, `limit`, `cursor` | `PaginatedObjectsOut` | read:* | `voyant.ontology.objects.list` |
| `POST` | `/objects` | `CreateObjectIn` | `ObjectOut` | write:ontology | `voyant.ontology.objects.create` |
| `GET` | `/objects/{id}` | — | `ObjectDetailOut` | read:* | `voyant.ontology.objects.get` |
| `PUT` | `/objects/{id}` | `UpdateObjectIn` | `ObjectOut` | write:ontology | `voyant.ontology.objects.update` |
| `DELETE` | `/objects/{id}` | — | `{"status": "deleted"}` | write:ontology | `voyant.ontology.objects.delete` |
| `POST` | `/objects/batch` | `BatchCreateIn` | `BatchResultOut` | write:ontology | `voyant.ontology.objects.batch_create` |
| `POST` | `/objects/upsert` | `UpsertIn` | `BatchResultOut` | write:ontology | `voyant.ontology.objects.upsert` |
| `POST` | `/objects/query` | `QueryIn` | `QueryResultOut` | read:* | `voyant.ontology.query` |
| `POST` | `/objects/import` | multipart (CSV/JSON) | `BatchResultOut` | write:ontology | `voyant.ontology.objects.import` |
| `POST` | `/objects/{id}/traverse` | `TraverseIn` | `TraverseResultOut` | read:* | `voyant.ontology.traverse` |
| `GET` | `/objects/{id}/history` | — | `list[HistoryEntryOut]` | read:* | `voyant.ontology.objects.history` |
| `POST` | `/objects/{id}/shortest-path` | `{"target_id": "...", "link_types": [...]}` | `PathResultOut` | read:* | `voyant.ontology.objects.shortest_path` |

### 6.7 Link Types & Links

| Method | Path | Request Schema | Response Schema | Auth | MCP Tool |
|--------|------|---------------|-----------------|------|----------|
| `GET` | `/link-types` | — | `list[LinkTypeOut]` | read:* | `voyant.ontology.link_types.list` |
| `POST` | `/link-types` | `CreateLinkTypeIn` | `LinkTypeOut` | write:ontology | `voyant.ontology.link_types.create` |
| `GET` | `/link-types/{id}` | — | `LinkTypeDetailOut` | read:* | `voyant.ontology.link_types.get` |
| `PUT` | `/link-types/{id}` | `UpdateLinkTypeIn` | `LinkTypeOut` | write:ontology | `voyant.ontology.link_types.update` |
| `DELETE` | `/link-types/{id}` | — | `{"status": "deleted"}` | write:ontology | `voyant.ontology.link_types.delete` |
| `GET` | `/links` | Query: `link_type_id`, `limit`, `cursor` | `PaginatedLinksOut` | read:* | `voyant.ontology.links.list` |
| `POST` | `/links` | `CreateLinkIn` | `LinkOut` | write:ontology | `voyant.ontology.links.create` |
| `DELETE` | `/links/{id}` | — | `{"status": "deleted"}` | write:ontology | `voyant.ontology.links.delete` |

### 6.8 Action Types & Execution

| Method | Path | Request Schema | Response Schema | Auth | MCP Tool |
|--------|------|---------------|-----------------|------|----------|
| `GET` | `/actions` | Query: `status` | `list[ActionTypeOut]` | read:* | `voyant.ontology.actions.list` |
| `POST` | `/actions` | `CreateActionTypeIn` | `ActionTypeOut` | write:ontology | `voyant.ontology.actions.create` |
| `GET` | `/actions/{id}` | — | `ActionTypeDetailOut` | read:* | `voyant.ontology.actions.get` |
| `PUT` | `/actions/{id}` | `UpdateActionTypeIn` | `ActionTypeOut` | write:ontology | `voyant.ontology.actions.update` |
| `DELETE` | `/actions/{id}` | — | `{"status": "deleted"}` | write:ontology | `voyant.ontology.actions.delete` |
| `POST` | `/actions/{id}/execute` | `ExecuteActionIn` | `ActionResultOut` | execute:actions | `voyant.ontology.actions.execute` |
| `POST` | `/actions/{id}/batch-execute` | `BatchExecuteIn` | `BatchActionResultOut` | execute:actions | `voyant.ontology.actions.batch_execute` |
| `POST` | `/actions/executions/{id}/undo` | — | `UndoResultOut` | execute:actions | `voyant.ontology.actions.undo` |
| `GET` | `/actions/{id}/metrics` | Query: `from`, `to` | `ActionMetricsOut` | read:* | `voyant.ontology.actions.metrics` |

### 6.9 Functions

| Method | Path | Request Schema | Response Schema | Auth | MCP Tool |
|--------|------|---------------|-----------------|------|----------|
| `GET` | `/functions` | Query: `status` | `list[FunctionOut]` | read:* | `voyant.ontology.functions.list` |
| `POST` | `/functions` | `CreateFunctionIn` | `FunctionOut` | write:ontology | `voyant.ontology.functions.create` |
| `GET` | `/functions/{id}` | — | `FunctionDetailOut` | read:* | `voyant.ontology.functions.get` |
| `PUT` | `/functions/{id}` | `UpdateFunctionIn` | `FunctionOut` | write:ontology | `voyant.ontology.functions.update` |
| `DELETE` | `/functions/{id}` | — | `{"status": "deleted"}` | write:ontology | `voyant.ontology.functions.delete` |
| `POST` | `/functions/{id}/run` | `RunFunctionIn` | `FunctionResultOut` | execute:actions | `voyant.ontology.functions.run` |
| `POST` | `/functions/{id}/test` | `TestFunctionIn` | `FunctionResultOut` | write:ontology | `voyant.ontology.functions.test` |
| `GET` | `/functions/{id}/metrics` | Query: `from`, `to` | `FunctionMetricsOut` | read:* | `voyant.ontology.functions.metrics` |

### 6.10 Schema Export/Import

| Method | Path | Request Schema | Response Schema | Auth | MCP Tool |
|--------|------|---------------|-----------------|------|----------|
| `POST` | `/ontology/export` | `ExportIn` (optional filters) | `OntologyExportOut` | read:* | `voyant.ontology.export` |
| `POST` | `/ontology/import` | `OntologyImportIn` | `ImportResultOut` | write:ontology | `voyant.ontology.import` |
| `GET` | `/ontology/schema` | — | `FullSchemaOut` | read:* | `voyant.ontology.schema.discover` |

**Total v4.0 Target: ~80 REST endpoints, ~35 MCP tools.**

---

## 7. Complete MCP Tool Design (v4.0 Target)

### 7.1 Type Management Tools

| Tool Name | Parameters | Description | Response |
|-----------|-----------|-------------|----------|
| `voyant.ontology.types.list` | `include_deleted?: bool`, `group_id?: str`, `tenant_id?: str` | List all object types with counts | `[{id, name, description, version, property_count, instance_count}]` |
| `voyant.ontology.types.get` | `type_id: str`, `tenant_id?: str` | Get type with full property definitions | `{id, name, description, version, properties: [...]}` |
| `voyant.ontology.types.create` | `name: str`, `description?: str`, `properties?: list`, `render_config?: dict`, `tenant_id?: str` | Create new object type | `{id, name, version}` |
| `voyant.ontology.types.update` | `type_id: str`, `name?: str`, `description?: str`, `properties?: list`, `render_config?: dict`, `tenant_id?: str` | Update existing type | `{id, name, version}` |
| `voyant.ontology.types.delete` | `type_id: str`, `tenant_id?: str` | Soft-delete type | `{status: "deleted"}` |
| `voyant.ontology.types.diff` | `type_id: str`, `from_version: int`, `to_version: int`, `tenant_id?: str` | Schema diff between versions | `{added: [...], removed: [...], changed: [...]}` |

### 7.2 Object Instance Tools

| Tool Name | Parameters | Description | Response |
|-----------|-----------|-------------|----------|
| `voyant.ontology.objects.list` | `type_id?: str`, `limit?: int`, `cursor?: str`, `tenant_id?: str` | List objects with pagination | `{items: [...], next_cursor, total}` |
| `voyant.ontology.objects.get` | `object_id: str`, `include_links?: bool`, `tenant_id?: str` | Get object with optional links | `{id, type, properties, version, links?: {...}}` |
| `voyant.ontology.objects.create` | `type_id: str`, `properties: dict`, `tenant_id?: str` | Create object with validation | `{id, type, properties, version}` |
| `voyant.ontology.objects.update` | `object_id: str`, `properties: dict`, `version?: int`, `tenant_id?: str` | Update with optimistic concurrency | `{id, properties, version}` |
| `voyant.ontology.objects.delete` | `object_id: str`, `tenant_id?: str` | Soft-delete object | `{status: "deleted"}` |
| `voyant.ontology.objects.batch_create` | `type_id: str`, `items: list`, `tenant_id?: str` | Batch create 1000+ objects | `{created: int, ids: [...]}` |
| `voyant.ontology.objects.upsert` | `type_id: str`, `key_property: str`, `items: list`, `tenant_id?: str` | Upsert by key property | `{processed: int, ids: [...]}` |
| `voyant.ontology.objects.import` | `type_id: str`, `format: str`, `data: str`, `tenant_id?: str` | Import from CSV/JSON | `{created: int, errors: [...]}` |
| `voyant.ontology.objects.history` | `object_id: str`, `tenant_id?: str` | Get change history | `{history: [{version, changed_at, changes, actor}]}` |
| `voyant.ontology.objects.shortest_path` | `source_id: str`, `target_id: str`, `link_types?: list`, `tenant_id?: str` | Shortest path between objects | `{path: [{object_id, link_type}], length}` |

### 7.3 Link Tools

| Tool Name | Parameters | Description | Response |
|-----------|-----------|-------------|----------|
| `voyant.ontology.links.create` | `link_type_id: str`, `source_object_id: str`, `target_object_id: str`, `properties?: dict`, `tenant_id?: str` | Create link between objects | `{id, link_type, source, target}` |
| `voyant.ontology.links.delete` | `link_id: str`, `tenant_id?: str` | Delete link | `{status: "deleted"}` |
| `voyant.ontology.links.list` | `link_type_id?: str`, `object_id?: str`, `direction?: str`, `limit?: int`, `tenant_id?: str` | List links with filtering | `[{id, link_type, source, target, properties}]` |
| `voyant.ontology.traverse` | `object_id: str`, `direction?: str`, `max_depth?: int`, `link_type_name?: str`, `tenant_id?: str` | Multi-hop traversal | `{object_id, results: [...], count}` |

### 7.4 Interface Tools

| Tool Name | Parameters | Description | Response |
|-----------|-----------|-------------|----------|
| `voyant.ontology.interfaces.list` | `tenant_id?: str` | List interfaces | `[{id, name, version, implementing_count}]` |
| `voyant.ontology.interfaces.create` | `name: str`, `required_properties?: list`, `optional_properties?: list`, `tenant_id?: str` | Create interface | `{id, name, version}` |
| `voyant.ontology.interfaces.implement` | `interface_id: str`, `object_type_id: str`, `tenant_id?: str` | Make type implement interface | `{status: "implemented"}` |
| `voyant.ontology.interfaces.objects` | `interface_id: str`, `limit?: int`, `tenant_id?: str` | Query objects across implementing types | `{items: [...], total}` |

### 7.5 Action Tools

| Tool Name | Parameters | Description | Response |
|-----------|-----------|-------------|----------|
| `voyant.ontology.actions.list` | `status?: str`, `tenant_id?: str` | List action types | `[{id, name, status, version}]` |
| `voyant.ontology.actions.execute` | `action_type_id: str`, `object_id: str`, `params?: dict`, `tenant_id?: str` | Execute action on object | `{success, action_id, changes, side_effects}` |
| `voyant.ontology.actions.batch_execute` | `action_type_id: str`, `object_ids: list`, `params?: dict`, `tenant_id?: str` | Execute action on multiple objects | `{results: [{object_id, success, errors}]}` |
| `voyant.ontology.actions.undo` | `action_execution_id: str`, `tenant_id?: str` | Undo a previous action | `{success, reverted_fields}` |
| `voyant.ontology.actions.metrics` | `action_type_id: str`, `from?: str`, `to?: str`, `tenant_id?: str` | Get execution metrics | `{total_executions, success_rate, avg_duration_ms}` |

### 7.6 Function Tools

| Tool Name | Parameters | Description | Response |
|-----------|-----------|-------------|----------|
| `voyant.ontology.functions.list` | `status?: str`, `tenant_id?: str` | List functions | `[{id, name, status, language, version}]` |
| `voyant.ontology.functions.run` | `function_id: str`, `input_data?: dict`, `tenant_id?: str` | Run function | `{success, output, duration_ms, error}` |
| `voyant.ontology.functions.test` | `function_id: str`, `test_input: dict`, `expected_output?: dict`, `tenant_id?: str` | Test function with sample input | `{success, output, duration_ms, match_expected}` |
| `voyant.ontology.functions.metrics` | `function_id: str`, `from?: str`, `to?: str`, `tenant_id?: str` | Get execution metrics | `{total_calls, avg_duration_ms, error_rate}` |

### 7.7 Query & Schema Tools

| Tool Name | Parameters | Description | Response |
|-----------|-----------|-------------|----------|
| `voyant.ontology.query` | `type_name: str`, `filters?: list`, `sort_by?: str`, `sort_order?: str`, `limit?: int`, `cursor?: str`, `tenant_id?: str` | Structured query with filtering | `{items: [...], next_cursor, total}` |
| `voyant.ontology.schema.discover` | `tenant_id?: str` | Full schema introspection | `{types: [...], interfaces: [...], links: [...], actions: [...], functions: [...]}` |
| `voyant.ontology.export` | `include?: list`, `tenant_id?: str` | Export full ontology as JSON | Complete ontology JSON |
| `voyant.ontology.import` | `schema: dict`, `dry_run?: bool`, `tenant_id?: str` | Import ontology from JSON | `{created: {}, errors: [...]}` |

**Total v4.0 Target: 35 MCP tools.**

---

## 8. Test Strategy

### 8.1 Existing Test Coverage

| Test File | Tests | Focus | Coverage |
|-----------|-------|-------|----------|
| `test_models.py` | 22 | PropertyType enum completeness, Cardinality enum, model `__str__` | 100% (pure logic) |
| `test_validators.py` | 35 | Type validation (all 11 types), required/default, rules (regex/min/max/enum), unknown fields, partial mode | 100% (pure logic) |
| `test_services.py` | 22 | ObjectType CRUD, Object CRUD+batch+upsert, LinkType CRUD, Link CRUD+traversal (outgoing/incoming/both/multi-hop/cycle), optimistic concurrency, referential integrity | 95% (integration) |
| `test_action_executor.py` | 14 | Param validation, rule checking, full execution, side effects (audit_log, field_update, notification), undo (success, not-undoable, already-undone) | 90% (integration) |
| `test_function_runner.py` | 20 | Python execution (success, timeout, crash, bad output), input/output validation, caching, entry point errors, TS runtime detection | 85% (integration + unit) |

**Total: 113 test functions across 5 test files.**

### 8.2 Missing Tests (v4.0 Target)

| Area | Tests Needed | Priority |
|------|-------------|----------|
| **Interface enforcement** | Verify ObjectType update rejects if interface compliance broken | P1 |
| **StructType validation** | Recursive struct validation for nested structs | P1 |
| **SharedProperty propagation** | Verify changes propagate to all linked types | P1 |
| **ValueType enforcement** | Property with `value_type_id` auto-validates | P1 |
| **Action batch execute** | Batch execution across 100+ objects, partial failure handling | P1 |
| **Action conditional side effects** | Side effect fires only when condition met | P1 |
| **Action metrics aggregation** | Metrics correctly aggregate from ActionExecution records | P2 |
| **Function test endpoint** | Test runner returns correct match/mismatch | P1 |
| **Function dependencies** | Sandbox installs declared dependencies | P2 |
| **Query endpoint** | Filtering, sorting, pagination, aggregation | P1 |
| **Cursor-based pagination** | Correct cursor generation and consumption | P1 |
| **Schema export/import** | Round-trip: export then import produces identical schema | P1 |
| **Schema diff** | Diff between versions shows correct changes | P2 |
| **Temporal links** | Links with valid_from/valid_to filter correctly | P2 |
| **Graph algorithms** | Shortest path returns correct path | P2 |
| **WebSocket subscriptions** | Real-time notifications on object changes | P2 |
| **Cross-type interface queries** | Query via interface returns objects from all implementing types | P1 |
| **API endpoint tests** | Every endpoint returns correct status codes, error shapes | P1 |
| **MCP tool tests** | Every tool returns expected format | P1 |
| **Concurrency tests** | 100 concurrent upserts don't cause data corruption | P2 |
| **Performance tests** | Batch create 10K objects in < 5s, traversal of 10K nodes in < 2s | P2 |

### 8.3 Coverage Targets

| Component | Current | Target | Gap |
|-----------|---------|--------|-----|
| `models.py` | 100% | 100% | — |
| `validators.py` | 100% | 100% | — |
| `services.py` | 95% | 100% | Add edge cases for batch/upsert |
| `action_executor.py` | 90% | 100% | Add batch execute, conditional effects |
| `function_runner.py` | 85% | 95% | Add dependency tests, streaming |
| `api.py` | ~30% (no endpoint tests) | 90% | Add HTTP-level tests for all 80 endpoints |
| `tools_ontology.py` | ~20% (no direct tests) | 85% | Add MCP tool integration tests |

---

## 9. Architecture Diagrams (ASCII)

### 9.1 Data Flow: Agent → MCP → Ontology → PostgreSQL

```
┌─────────────────────────────────────────────────────────────────────┐
│  AI Agent                                                           │
│  "Create a Customer named Alice"                                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ MCP Protocol (JSON-RPC)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  MCP Server (tools_ontology.py)                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ @mcp_app.tool("voyant.ontology.objects.create")             │   │
│  │ def tool(type_id, properties, tenant_id):                   │   │
│  │     tid = _tenant(tenant_id)                                │   │
│  │     obj = ObjectService.create(tid, type_id, properties)    │   │
│  │     return {"id": str(obj.id), "properties": obj.properties}│   │
│  └──────────────────────────────┬──────────────────────────────┘   │
└─────────────────────────────────┼───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Service Layer (services.py)                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ObjectService.create(tenant_id, type_id, properties):       │   │
│  │   1. ot = ObjectTypeService.get(tenant_id, type_id)         │   │
│  │   2. prop_defs = ot.properties.all()                        │   │
│  │   3. normalised, errors = validate_properties(properties,   │   │
│  │        prop_defs)                                           │   │
│  │   4. if errors: raise ValidationError(errors)               │   │
│  │   5. obj = Object.objects.create(                           │   │
│  │        tenant_id=tenant_id, object_type=ot,                 │   │
│  │        properties=normalised, version=1)                    │   │
│  │   6. return obj                                             │   │
│  └──────────────────────────────┬──────────────────────────────┘   │
└─────────────────────────────────┼───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Validators (validators.py)                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ validate_properties(properties, prop_defs):                 │   │
│  │   For each prop_def:                                        │   │
│  │     1. Check required → error if missing                    │   │
│  │     2. Apply default_value if None                          │   │
│  │     3. Type check (11 validators)                           │   │
│  │     4. Rule check (regex, min, max, enum, length)           │   │
│  │   Reject unknown fields                                     │   │
│  │   Return (normalised, errors)                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PostgreSQL                                                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ ontology_object_type | ontology_property | ontology_object   │  │
│  │ ontology_link_type   | ontology_link     | ontology_interface│  │
│  │ ontology_struct_type | ontology_shared_property              │  │
│  │ ontology_value_type  | ontology_action_type                  │  │
│  │ ontology_function    | ontology_action_execution             │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 9.2 Traversal: How Multi-Hop Works

```
Starting Object: Customer #A (depth=0)
    │
    ▼
┌─────────────────────────────────────────────────┐
│ _traverse("A", depth=1)                         │
│   visited = {"A"}                               │
│                                                 │
│   Outgoing Links from A:                        │
│   ┌──────────┐    ┌──────────┐                  │
│   │Link:places│    │Link:cancels│                │
│   │ A → B    │    │ A → D    │                  │
│   └────┬─────┘    └────┬─────┘                  │
│        │               │                        │
│        ▼               ▼                        │
│   Result: B       Result: D                     │
│   depth=1          depth=1                      │
│        │               │                        │
│        ▼               ▼                        │
│   _traverse("B",2)  _traverse("D",2)            │
│   visited={"A","B"} visited={"A","B","D"}        │
│        │               │                        │
│   Links from B:     Links from D:               │
│   ┌──────────┐     (none)                       │
│   │Link:places│                                  │
│   │ B → C    │                                  │
│   └────┬─────┘                                  │
│        │                                        │
│        ▼                                        │
│   Result: C                                     │
│   depth=2                                       │
│        │                                        │
│        ▼                                        │
│   _traverse("C",3)                              │
│   depth=3 > max_depth=2 → RETURN                │
│                                                 │
│   Final Results:                                │
│   [B(depth=1), D(depth=1), C(depth=2)]          │
└─────────────────────────────────────────────────┘

Cycle Protection:
If C → A exists, A is already in `visited`, so it's skipped.
```

### 9.3 Action Execution: How Actions Execute with Side Effects

```
Agent calls: voyant.ontology.actions.execute(
    action_type_id="assign_ticket",
    object_id="ticket-123",
    params={"assignee": "alice"},
    actor="admin"
)
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ ActionExecutor.execute()                            │
│                                                     │
│ Step 1: LOAD                                        │
│   ┌────────────────────────────────────┐            │
│   │ ActionType (status=active) ✓       │            │
│   │ Object (exists, not deleted) ✓     │            │
│   └────────────────────────────────────┘            │
│                                                     │
│ Step 2: VALIDATE PARAMS                             │
│   ┌────────────────────────────────────┐            │
│   │ "assignee" required → "alice" ✓    │            │
│   │ type: string → isinstance ✓        │            │
│   └────────────────────────────────────┘            │
│                                                     │
│ Step 3: CHECK RULES                                 │
│   ┌────────────────────────────────────┐            │
│   │ status_check: status=="open" ✓     │            │
│   │ field_exists: title present ✓      │            │
│   │ permission_check: admin has perm ✓ │            │
│   └────────────────────────────────────┘            │
│                                                     │
│ Step 4: COMMIT (transaction.atomic())               │
│   ┌────────────────────────────────────┐            │
│   │ 4a. Snapshot: prev = {status:open, │            │
│   │     title:Fix, priority:low,       │            │
│   │     assignee:null}                 │            │
│   │ 4b. Apply: obj.assignee = "alice"  │            │
│   │ 4c. Version: 1 → 2                │            │
│   │ 4d. Side Effects:                  │            │
│   │     ┌──────────────────────────┐   │            │
│   │     │ audit_log → AuditLog ✓   │   │            │
│   │     │ webhook → POST url ✓     │   │            │
│   │     │ notification → log ✓     │   │            │
│   │     └──────────────────────────┘   │            │
│   │ 4e. Record ActionExecution         │            │
│   │     {status:success, actor:admin}  │            │
│   └────────────────────────────────────┘            │
│                                                     │
│ Return: ActionResult(                               │
│   success=True,                                     │
│   action_id="exec-456",                             │
│   changes={assignee: {old:null, new:"alice"}}        │
│ )                                                   │
└─────────────────────────────────────────────────────┘
```

### 9.4 Function Execution: How Sandboxed Functions Run

```
Agent calls: voyant.ontology.functions.run(
    function_id="discount-calc",
    input_data={"amount": 100, "tier": "gold"}
)
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ FunctionRunner.run()                                        │
│                                                             │
│ Step 1: LOAD (with cache)                                   │
│   ┌──────────────────────────────────────────┐              │
│   │ Cache.get(tenant_id, function_id)        │              │
│   │   → HIT? Check version in DB             │              │
│   │   → MISS? Load from DB, cache            │              │
│   │ Function(language=python, timeout=30s)   │              │
│   └──────────────────────────────────────────┘              │
│                                                             │
│ Step 2: VALIDATE INPUT                                      │
│   ┌──────────────────────────────────────────┐              │
│   │ Schema: {params: [                       │              │
│   │   {name:"amount", type:"number", req: T},│              │
│   │   {name:"tier", type:"string", req: T}   │              │
│   │ ]}                                       │              │
│   │ Input: {amount:100, tier:"gold"} ✓       │              │
│   └──────────────────────────────────────────┘              │
│                                                             │
│ Step 3: EXECUTE (subprocess)                                │
│   ┌──────────────────────────────────────────┐              │
│   │ Write wrapper to tempfile:               │              │
│   │   import json, sys                       │              │
│   │   __input__ = {"amount":100,"tier":"gold"}│              │
│   │   __code__ = <user source>               │              │
│   │   exec(__code__, __ns__)                 │              │
│   │   result = __ns__["handler"](__input__)   │              │
│   │   print(json.dumps(result))              │              │
│   │                                          │              │
│   │ subprocess.Popen([python, tempfile],     │              │
│   │   stdout=PIPE, stderr=PIPE)              │              │
│   │ proc.communicate(timeout=30)             │              │
│   │ stdout: '{"discounted": 85.0}'           │              │
│   └──────────────────────────────────────────┘              │
│                                                             │
│ Step 4: PARSE + VALIDATE OUTPUT                             │
│   ┌──────────────────────────────────────────┐              │
│   │ json.loads(stdout) → {"discounted": 85.0}│              │
│   │ Output schema check: type=object ✓       │              │
│   └──────────────────────────────────────────┘              │
│                                                             │
│ Return: FunctionResult(                                     │
│   success=True,                                             │
│   output={"discounted": 85.0},                              │
│   duration_ms=142.5                                         │
│ )                                                           │
└─────────────────────────────────────────────────────────────┘
```

### 9.5 Module Relationship Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                          apps/ontology/                               │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────────┐ │
│  │   models.py   │  │ validators.py│  │      services.py           │ │
│  │              │  │              │  │                            │ │
│  │ ObjectType   │◄─┤validate_    │  │ ObjectTypeService          │ │
│  │ Property     │  │properties() │  │ ObjectService              │ │
│  │ Object       │  │              │  │ LinkTypeService            │ │
│  │ LinkType     │  │Type checks  │  │ LinkService                │ │
│  │ Link         │  │Rule checks  │  │                            │ │
│  │ Interface    │  │Default vals │  │ CRUD + Batch + Upsert      │ │
│  │ StructType   │  │Unknown field│  │ Traversal + Versioning     │ │
│  │ SharedProp   │  └──────┬───────┘  └─────┬──────────┬──────────┘ │
│  │ ValueType    │         │                │          │             │
│  │ ActionType   │         │                │          │             │
│  │ Function     │         │                │          │             │
│  │ ActionExec   │         │                │          │             │
│  └──────┬───────┘         │                │          │             │
│         │                 │                │          │             │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌─────▼──────────▼──────────┐ │
│  │   api.py      │  │              │  │                           │ │
│  │              │  │              │  │ action_executor.py         │ │
│  │ 44 REST      │  │              │  │ function_runner.py         │ │
│  │ endpoints    │  │              │  │                           │ │
│  │              │  │              │  │ ActionExecutor.execute()   │ │
│  │ Django Ninja │  │              │  │ ActionExecutor.undo()      │ │
│  │ Router       │  │              │  │ FunctionRunner.run()       │ │
│  └──────────────┘  └──────────────┘  └───────────────────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ apps/mcp/tools_ontology.py                                       ││
│  │ 14 MCP tools calling service layer                               ││
│  └──────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
         │                                       │
         ▼                                       ▼
┌─────────────────┐                    ┌──────────────────────┐
│   PostgreSQL     │                    │  External Services   │
│  12 tables       │                    │  ┌─────────────────┐ │
│  (ontology_*)    │                    │  │ httpx (webhooks) │ │
│                  │                    │  │ AuditLog model   │ │
│  UUID PKs        │                    │  │ Python subprocess│ │
│  JSONB fields    │                    │  │ TS subprocess    │ │
│  Soft-delete     │                    │  └─────────────────┘ │
│  Multi-tenant    │                    └──────────────────────┘
└─────────────────┘
```

---

## Appendix A: Migration History

| Migration | Date | Content |
|-----------|------|---------|
| `0001_add_v4_ontology_models` | 2026-09-05 | Initial creation of all 11 models (ObjectType, Property, Object, LinkType, Link, Interface, StructType, SharedProperty, ValueType, ActionType, Function) with all constraints and indexes |
| `0002_actionexecution` | 2026-09-05 | Adds ActionExecution model for undo support and audit trail |

## Appendix B: SRS Requirements Traceability

| SRS ID | Requirement | Implementation | Status |
|--------|-------------|----------------|--------|
| ONT-F-001 | Object Types with name/description/properties | `ObjectType` + `ObjectTypeService.create()` | ✅ Done |
| ONT-F-002 | 11 property types | `PropertyType` enum + `_TYPE_VALIDATORS` | ✅ Done |
| ONT-F-003 | Required property enforcement | `Property.required` + validator | ✅ Done |
| ONT-F-004 | Default values | `Property.default_value` + validator | ✅ Done |
| ONT-F-005 | Validation rules | `Property.validation_rules` + `_RULE_VALIDATORS` | ✅ Done |
| ONT-F-006 | Backward-compatible schema updates | `ObjectTypeService.update()` with compatibility checks | ✅ Done |
| ONT-F-007 | Soft-deletion with referential integrity | `deleted_at` field + instance/link checks | ✅ Done |
| ONT-F-008 | Schema versioning | `ObjectType.version` auto-increment | ✅ Done |
| ONT-F-009 | Link Types with cardinality | `LinkType` + `Cardinality` enum | ✅ Done |
| ONT-F-013 | Batch create 1000+ objects | `ObjectService.batch_create()` with `bulk_create()` | ✅ Done |
| ONT-F-014 | Upsert by unique key | `ObjectService.upsert()` with `properties__contains` | ✅ Done |
| ONT-F-017 | Optimistic concurrency | `Object.version` + version check in update | ✅ Done |
| ONT-F-018 | Interfaces | `Interface` model + API endpoints | ✅ Done |
| ONT-F-020 | Struct Types | `StructType` model + API endpoints | ✅ Done |
| ONT-F-021 | Shared Properties | `SharedProperty` model + API endpoints | ✅ Done |
| ONT-F-022 | Value Types | `ValueType` model + API endpoints | ✅ Done |
| ONT-F-023 | Referential integrity | LinkService validates source/target types | ✅ Done |
| ONT-F-024 | Cascading operations | CASCADE on Link delete → Object | ✅ Done |
| ONT-F-025 | Inverse link navigation | `inverse_name` field + `direction="incoming"` | ✅ Done |
| ONT-F-026 | Action Types | `ActionType` model + `ActionExecutor` | ✅ Done |
| ONT-F-027 | Action execution | `ActionExecutor.execute()` with full pipeline | ✅ Done |
| ONT-F-028 | Undo support | `ActionExecutor.undo()` + `ActionExecution` | ✅ Done |
| ONT-F-029 | Functions (Python/TS) | `Function` model + `FunctionRunner` | ✅ Done |
| ONT-F-031 | Multi-hop traversal | `LinkService.traverse()` up to 10 hops | ✅ Done |
| ONT-F-032 | Subscription service | Not implemented | ❌ Pending |
| ONT-F-033 | Filtered traversal | `filters` param (reserved) | ⚠️ Partial |
| ONT-F-036 | Object Type Groups | Not implemented | ❌ Pending |

---

## 10. Ontology Query Engine (Deep Specification)

*Sourced from Deep-Dive Module & Function Spec §4.3*

The Ontology Query Engine provides a unified interface for querying objects from the Ontology. It supports five query types, from simple lookups to cross-type interface-based queries and aggregations.

```
┌─────────────────────────────────────────────────────────────────┐
│              ONTOLOGY QUERY ENGINE                                │
│                                                                  │
│  Query Types Supported:                                          │
│                                                                  │
│  1. OBJECT LOOKUP                                                │
│  GET /api/v1/ontology/objects/Customer/1001                      │
│  → Returns: Single object with all properties + linked objects   │
│  → SQL: SELECT * FROM customers_cleaned WHERE customer_id=1001  │
│  → + resolve links: fetch orders, location, reviews              │
│                                                                  │
│  2. OBJECT QUERY (filtered list)                                 │
│  POST /api/v1/ontology/objects/Customer/query                    │
│  Body: {                                                         │
│    "filter": {                                                   │
│      "AND": [                                                    │
│        { "property": "segment", "operator": "eq", "value": "Premium" },│
│        { "property": "lifetime_value", "operator": "gt", "value": 10000 }│
│      ]                                                           │
│    },                                                            │
│    "sort": { "property": "lifetime_value", "order": "desc" },   │
│    "pagination": { "cursor": null, "limit": 50 },               │
│    "includeLinks": ["orders", "location"],                       │
│    "select": ["customer_id", "first_name", "last_name",         │
│               "lifetime_value", "segment"]                       │
│  }                                                               │
│  → Translates to: SELECT ... FROM customers_cleaned              │
│    WHERE segment='Premium' AND lifetime_value > 10000            │
│    ORDER BY lifetime_value DESC LIMIT 50                         │
│  → + resolve links (JOIN or N+1 with batching)                   │
│                                                                  │
│  3. LINK TRAVERSAL                                               │
│  GET /api/v1/ontology/objects/Customer/1001/orders               │
│  → Returns: All Order objects linked to Customer 1001            │
│  → SQL: SELECT * FROM orders WHERE customer_id = 1001            │
│                                                                  │
│  4. INTERFACE-BASED QUERY                                        │
│  POST /api/v1/ontology/interfaces/GeoLocated/query               │
│  Body: {                                                         │
│    "filter": { "near": { "lat": 37.77, "lng": -122.41,         │
│                          "radius_km": 50 }},                    │
│    "limit": 100                                                  │
│  }                                                               │
│  → Returns: Objects from ALL implementing types (Customer,       │
│    Warehouse, Store) that are within 50km of the point           │
│  → SQL: UNION ALL across implementing tables with geospatial     │
│    filter                                                        │
│                                                                  │
│  5. AGGREGATION QUERY                                            │
│  POST /api/v1/ontology/objects/Customer/aggregate                │
│  Body: {                                                         │
│    "groupBy": ["segment"],                                       │
│    "aggregations": [                                             │
│      { "property": "lifetime_value", "function": "AVG" },       │
│      { "property": "customer_id", "function": "COUNT" }         │
│    ],                                                            │
│    "filter": { "property": "country", "operator": "eq",         │
│               "value": "US" }                                   │
│  }                                                               │
│  → SQL: SELECT segment, AVG(lifetime_value), COUNT(*)            │
│    FROM customers_cleaned WHERE country='US' GROUP BY segment    │
│                                                                  │
│  QUERY OPTIMIZATION:                                             │
│  • Predicate pushdown to Iceberg (filter at storage level)       │
│  • Projection pushdown (only read needed columns)                │
│  • Link resolution batching (batch N+1 queries)                  │
│  • Result caching (Redis, configurable TTL per object type)      │
│  • Query plan caching (prepared statements)                      │
│  • Parallel link resolution for fan-out queries                  │
└─────────────────────────────────────────────────────────────────┘
```

### 10.1 Query Type Summary

| # | Query Type | Endpoint | Description |
|---|-----------|----------|-------------|
| 1 | **Object Lookup** | `GET /objects/{Type}/{id}` | Single object with properties + resolved links |
| 2 | **Filtered Object Query** | `POST /objects/{Type}/query` | Filtered, sorted, paginated list with optional link resolution |
| 3 | **Link Traversal** | `GET /objects/{Type}/{id}/{linkName}` | Follow a named link to retrieve related objects |
| 4 | **Interface-Based Query** | `POST /interfaces/{name}/query` | Query across all implementing types (e.g., all `GeoLocated` objects) |
| 5 | **Aggregation Query** | `POST /objects/{Type}/aggregate` | Group-by with aggregations (AVG, COUNT, SUM, MIN, MAX) |

---

## 11. PII Detection Engine (Deep Specification)

*Sourced from Deep-Dive Module & Function Spec §4.4*

The PII Detection Engine automatically identifies columns containing personally identifiable information. It uses three complementary detection strategies to maximize recall and precision.

```
┌─────────────────────────────────────────────────────────────────┐
│              PII DETECTION ENGINE                                 │
│                                                                  │
│  Pattern-Based Detection:                                        │
│  • Email: regex ^[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}$              │
│  • Phone: regex ^\+?[\d\s\-\(\)]{7,15}$                        │
│  • SSN: regex ^\d{3}-\d{2}-\d{4}$                              │
│  • Credit Card: regex ^\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}$│
│  • IP Address: regex ^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$    │
│                                                                  │
│  Name-Based Detection:                                           │
│  Column name contains: email, phone, ssn, name, address,        │
│  birth, dob, passport, license, ip_address, etc.                │
│                                                                  │
│  ML-Based Detection:                                             │
│  NER model scans sample data for person names, addresses,        │
│  organizations, dates of birth                                   │
│                                                                  │
│  Confidence Score: 0.0 to 1.0 per column                       │
│  Auto-classification at confidence > 0.85                        │
│  Manual review queue for confidence 0.5 to 0.85                 │
└─────────────────────────────────────────────────────────────────┘
```

### 11.1 Detection Strategy Details

| Strategy | Method | Example | Precision | Recall |
|----------|--------|---------|-----------|--------|
| **Pattern-Based** | Regex matching against cell values | `user@example.com` matches email regex | High | Medium |
| **Name-Based** | Column name keyword matching | Column named `user_email` detected as PII | Medium | High |
| **ML-Based** | NER (Named Entity Recognition) on sample rows | "John Smith, 123 Main St" detected as PII | Medium | High |

### 11.2 Confidence Scoring and Classification

| Confidence Range | Action | Example |
|-----------------|--------|---------|
| `> 0.85` | **Auto-classify** as PII, apply default masking | Email column with regex + name match |
| `0.50 – 0.85` | **Queue for manual review** | Column with ambiguous values resembling names |
| `< 0.50` | **No classification**, mark as non-PII | Numeric ID column |

### 11.3 PII Categories and Masking Strategies

| PII Category | Detection Signals | Default Masking |
|-------------|-------------------|-----------------|
| Email | Regex + column name | HASH or REDACT |
| Phone Number | Regex + column name | LAST4 |
| SSN / National ID | Regex | LAST4 |
| Credit Card | Regex (Luhn-valid) | LAST4 |
| IP Address | Regex | HASH |
| Person Name | NER + column name | REDACT |
| Physical Address | NER + column name | REDACT |
| Date of Birth | Column name + value range | GENERALIZE (to year only) |

---

## 12. Data Quality Scoring (Deep Specification)

*Sourced from Deep-Dive Module & Function Spec §4.4*

The Data Quality Scoring system evaluates datasets across five dimensions and produces a weighted composite score. Each dimension is scored 0–100.

```
┌─────────────────────────────────────────────────────────────────┐
│              DATA QUALITY SCORING                                 │
│                                                                  │
│  Dimensions (each scored 0-100):                                 │
│                                                                  │
│  COMPLETENESS: % of non-null values across all columns           │
│  Formula: (total_cells - null_cells) / total_cells * 100        │
│                                                                  │
│  UNIQUENESS: % of unique values in key columns                   │
│  Formula: unique_values / total_values * 100                     │
│                                                                  │
│  TIMELINESS: Freshness of data vs. expected update frequency     │
│  Formula: max(0, 100 - (age_hours / expected_hours * 100))      │
│                                                                  │
│  CONSISTENCY: % of values matching expected format/type          │
│  Formula: valid_values / total_values * 100                      │
│                                                                  │
│  ACCURACY: % of values within expected range                     │
│  Formula: in_range_values / total_values * 100                   │
│                                                                  │
│  OVERALL: weighted average of all dimensions                     │
│  Weights: Completeness(0.25) + Uniqueness(0.20) +               │
│           Timeliness(0.20) + Consistency(0.20) +                 │
│           Accuracy(0.15)                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 12.1 Dimension Weights

| Dimension | Weight | What It Measures | Example |
|-----------|--------|-----------------|---------|
| **Completeness** | 0.25 | How much data is present (non-null) | 95% of cells have values → score 95 |
| **Uniqueness** | 0.20 | Deduplication in key columns | 99% of `order_id` values are unique → score 99 |
| **Timeliness** | 0.20 | Data freshness vs. expected cadence | Data is 2 hours old, expected update every 6 hours → score 67 |
| **Consistency** | 0.20 | Format/type conformity | 98% of `age` values are integers in [0,150] → score 98 |
| **Accuracy** | 0.15 | Values within expected range | 97% of prices are positive → score 97 |

### 12.2 Quality Thresholds and Alerts

| Overall Score | Rating | Action |
|--------------|--------|--------|
| `≥ 90` | **Excellent** | No action needed |
| `75 – 89` | **Good** | Monitor trend |
| `60 – 74` | **Fair** | Alert data steward |
| `40 – 59` | **Poor** | Block downstream consumers |
| `< 40` | **Critical** | Quarantine dataset, alert all stakeholders |

---

*End of document.*
