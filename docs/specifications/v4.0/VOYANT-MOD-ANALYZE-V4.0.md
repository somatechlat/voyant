# SQL Console — Functional Specification

**Document ID:** VOYANT-ISO-ANALYZE-4.0.0
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

The SQL Console module provides a browser-based, read-only SQL query environment powered by **Trino** against the Voyant Iceberg lakehouse. It enables data analysts, engineers, and AI agents to explore datasets, run analytical queries, save and share queries, and inspect table schemas — all from within the Voyant dashboard.

### 1.2 Scope

| Capability | Source File |
|---|---|
| SQL query execution | `apps/sql/api.py:311–341` |
| Table listing | `apps/sql/api.py:344–360` |
| Column inspection | `apps/sql/api.py:363–381` |
| Saved query CRUD | `apps/sql/api.py:60–264` |
| Saved query model | `apps/sql/models.py:10–63` |
| Admin SQL execution | `apps/sql/api.py` (admin routes) |
| Console UI | `dashboard/src/views/view-sql.ts` (325 lines) |

### 1.3 Position in Voyant Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       Dashboard (Lit)                            │
│  view-sql.ts                                                    │
│  ├─ <saas-sidebar>          (navigation)                        │
│  ├─ <voyant-monaco-editor>  (SQL editor with Ctrl+Enter)        │
│  └─ <voyant-data-table>     (results with sort/export/filter)   │
└───────────────┬──────────────────────────────────────────────────┘
                │ HTTP REST
┌───────────────▼──────────────────────────────────────────────────┐
│               SQL API (Django Ninja)                              │
│  sql_router — /sql/* endpoints                                   │
│  ├─ POST /sql/query         → TrinoClient.execute()             │
│  ├─ GET  /sql/tables        → TrinoClient.get_tables()          │
│  ├─ GET  /sql/tables/{t}/columns → TrinoClient.get_columns()   │
│  ├─ CRUD /sql/saved/*       → SavedQuery model                  │
│  └─ POST /sql/saved/{id}/share → (stub)                        │
├──────────────────────────────────────────────────────────────────┤
│  TrinoClient (apps/core/lib/trino.py)                            │
│  ├─ Read-only enforcement (SELECT only)                          │
│  ├─ Tenant-scoped schema                                        │
│  └─ QueryResult: columns, rows, row_count, execution_time_ms    │
├──────────────────────────────────────────────────────────────────┤
│  Trino Cluster → Iceberg Lakehouse                               │
│  └─ Tables: customers, orders, products, pipeline_runs, etc.    │
└──────────────────────────────────────────────────────────────────┘
```

### 1.4 Key Differentiators

| Feature | Voyant SQL Console | Databricks SQL Editor | Palantir Workshop |
|---|---|---|---|
| Engine | Trino (federated) | Spark SQL | Foundry SQL |
| Read-only enforcement | Built-in client-side | Cluster config | Policy-based |
| Saved queries with sharing | User + public visibility | Workspace-level | Not native |
| Table browser sidebar | Inline with schema preview | Separate Data Explorer | Ontology-aware |
| Query history | In-memory (20 recent) | Persistent | Persistent |
| Cross-module integration | Ontology query engine shares Trino | Unity Catalog | Ontology-first |
| Monaco editor | Full-featured with SQL syntax | Monaco-based | Code repositories |

---

## 2. Actors & Roles

| Actor | Role | Permissions | Description |
|---|---|---|---|
| Data Analyst | `execute:sql` | Run SELECT queries, save/share queries | Primary user — explores data, creates saved queries, exports results |
| Data Engineer | `execute:sql` | Run SELECT queries, inspect schemas | Verifies pipeline outputs, checks table schemas |
| Admin User | `execute:sql` + admin routes | Full access including admin SQL endpoint | Manages sources, runs admin queries |
| MCP Agent | `execute:sql` | Programmatic SQL via tool calls | AI agents running automated queries |

---

## 3. Screens / UI Views

### 3.1 SQL Console — Main View

**Route:** `/admin/sql`
**Component:** `<view-sql>` — `dashboard/src/views/view-sql.ts`
**Layout:** 2-column grid (editor+results | sidebar)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ▓▓ Sidebar ▓▓│  SQL Console                                                 │
│              │  Execute read-only queries via Trino · Ctrl+Enter to run      │
│              │                                                               │
│              │  ┌──────────────────────────────────┐ ┌──────────────────────┐│
│              │  │ ┌──────────────────────────────┐ │ │ TABLES              ││
│              │  │ │ 1│ SELECT * FROM customers   │ │ │ 📋 customers        ││
│              │  │ │ 2│ WHERE age > 25             │ │ │ 📋 orders           ││
│              │  │ │ 3│ LIMIT 100                  │ │ │ 📋 products         ││
│              │  │ │  │                             │ │ │ 📋 pipeline_runs   ││
│              │  │ └──────────────────────────────┘ │ │ 📋 feature_values   ││
│              │  │ (Monaco Editor — SQL syntax)      │ │                     ││
│              │  └──────────────────────────────────┘ │ SAVED QUERIES       ││
│              │  ┌──────────────────────────────────┐ │ ┌──────────────────┐││
│              │  │ [▶ Run Query] [💾 Save]          │ │ │ Active Customers │││
│              │  │ 100 rows · 245ms                  │ │ │ SELECT c.name... │││
│              │  └──────────────────────────────────┘ │ │ 🔗 🗑             │││
│              │  ┌──────────────────────────────────┐ │ │ High-Value Ord.. │││
│              │  │ name  │ email        │ age │ ... │ │ │ SELECT o.total.. │││
│              │  │───────┼──────────────┼─────┼─────│ │ └──────────────────┘││
│              │  │ John  │ j@mail.com   │  32 │     │ │                     ││
│              │  │ Jane  │ j@corp.com   │  28 │     │ │ HISTORY             ││
│              │  │ Bob   │ bob@ex.com   │  45 │     │ │ ┌──────────────────┐││
│              │  │ ...   │ ...          │ ... │     │ │ │ SELECT * FROM... │││
│              │  │       │              │     │     │ │ │ 100 rows · 245ms │││
│              │  └──────────────────────────────────┘ │ │ SELECT c.name... │││
│              │  [📥 Export] [🔍 Filter]              │ │ 50 rows · 120ms  │││
│              │                                       │ └──────────────────┘││
│              │                                       └──────────────────────┘│
└──────────────────────────────────────────────────────────────────────────────┘
```

**API Endpoints Called:**

| Method | Path | Purpose | Code Reference |
|---|---|---|---|
| `GET` | `/admin/sql/tables` | Load table list | `view-sql.ts:42` |
| `POST` | `/sql/query` | Execute SQL | `view-sql.ts:67` |
| `GET` | `/sql/saved` | Load saved queries | `view-sql.ts:56` |
| `POST` | `/sql/saved` | Create saved query | `view-sql.ts:121` |
| `PUT` | `/sql/saved/{id}` | Update saved query | `view-sql.ts:119` |
| `DELETE` | `/sql/saved/{id}` | Delete saved query | `view-sql.ts:134` |
| `POST` | `/sql/saved/{id}/share` | Share query (stub) | `view-sql.ts:147` |

**User Interactions:**

| Action | Trigger | Handler | Code Reference |
|---|---|---|---|
| Run query | `Ctrl+Enter` or button click | `_runQuery()` | `view-sql.ts:61` |
| Edit SQL | Monaco `@change` | `_onEditorChange(e)` | `view-sql.ts:82` |
| Click table | Table name click | Sets `this.sql = 'SELECT * FROM ...'` | `view-sql.ts:225` |
| Save query | Save button click | `_openSaveDialog()` | `view-sql.ts:86` |
| Load saved query | Saved query click | `_loadSavedQuery(q)` | `view-sql.ts:140` |
| Delete saved query | Trash icon click | `_deleteSavedQuery(id)` | `view-sql.ts:132` |
| Share query | Link icon click | `_shareQuery(q)` (stub) | `view-sql.ts:145` |
| Load history item | History click | Sets `this.sql` | `view-sql.ts:273` |

### 3.2 Save Query Dialog

**Trigger:** Click "💾 Save" or "💾 Update" button
**Type:** Modal overlay (420px wide)

```
┌─────────────────────────────────────────────────┐
│                  (overlay)                        │
│  ┌─────────────────────────────────────────────┐ │
│  │ Save Query                           (or    │ │
│  │                                  Update)    │ │
│  │                                             │ │
│  │ Name *                                      │ │
│  │ ┌─────────────────────────────────────────┐ │ │
│  │ │ Active Customer Report                  │ │ │
│  │ └─────────────────────────────────────────┘ │ │
│  │                                             │ │
│  │ Description                                 │ │
│  │ ┌─────────────────────────────────────────┐ │ │
│  │ │ Customers with age > 25 and status...   │ │ │
│  │ └─────────────────────────────────────────┘ │ │
│  │                                             │ │
│  │ ☐ Public (visible to all team members)     │ │
│  │                                             │ │
│  │              [Cancel]  [Save]               │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**Code Reference:** `view-sql.ts:286–322`

### 3.3 Loading / Error / Empty States

| State | Condition | UI |
|---|---|---|
| **Loading tables** | `tables.length === 0` on init | "Loading tables..." text — `view-sql.ts:229` |
| **Running query** | `this.running === true` | "⏳ Running..." button with spinner — `view-sql.ts:182` |
| **Query error** | `this.error !== ''` | Red error text below run bar — `view-sql.ts:192` |
| **No results** | `this.results === null` | Empty state with 📊 icon: "Write a query and press Ctrl+Enter" — `view-sql.ts:206` |
| **No saved queries** | `savedQueries.length === 0` | "No saved queries" text — `view-sql.ts:258` |
| **No history** | `history.length === 0` | "No queries yet" text — `view-sql.ts:278` |

---

## 4. Functional Requirements

### 4.1 Query Execution

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| SQL-F-001 | Execute read-only SQL query | Only SELECT statements allowed; enforced by TrinoClient | ✅ Impl | `apps/sql/api.py:311` |
| SQL-F-002 | Return structured results | `{columns[], rows[][], row_count, execution_time_ms, query_id, truncated}` | ✅ Impl | `apps/sql/api.py:288–309` |
| SQL-F-003 | Configurable row limit | `limit` param 1–10000, default 1000 | ✅ Impl | `apps/sql/api.py:274–279` |
| SQL-F-004 | Parameterized queries | Optional `parameters` dict in request | ✅ Impl | `apps/sql/api.py:280–285` |
| SQL-F-005 | Ctrl+Enter keyboard shortcut | Monaco editor `@run` event fires `_runQuery()` | ✅ Impl | `view-sql.ts:77–80` |
| SQL-F-006 | Execution timing | Client-side `performance.now()` measurement | ✅ Impl | `view-sql.ts:65–68` |
| SQL-F-007 | Query history (session-only) | Last 20 queries stored in `@state() history[]` | ✅ Impl | `view-sql.ts:28, 70` |
| SQL-F-008 | Results display via sortable table | `<voyant-data-table>` with sortable columns | ✅ Impl | `view-sql.ts:198–204` |

### 4.2 Schema Exploration

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| SQL-F-010 | List available tables | Returns table names from Trino `SHOW TABLES` | ✅ Impl | `apps/sql/api.py:344` |
| SQL-F-011 | Get table columns | Returns column metadata for a specific table | ✅ Impl | `apps/sql/api.py:363` |
| SQL-F-012 | Click-to-insert table query | Clicking table name sets editor to `SELECT * FROM table LIMIT 100` | ✅ Impl | `view-sql.ts:225–226` |
| SQL-F-013 | Table list in sidebar | Sidebar card with scrollable table list, max-height 200px | ✅ Impl | `view-sql.ts:215–231` |

### 4.3 Saved Queries

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| SQL-F-020 | Save query with name/description | `POST /sql/saved` creates SavedQuery record | ✅ Impl | `apps/sql/api.py:98` |
| SQL-F-021 | Update existing saved query | `PUT /sql/saved/{id}` updates by owner only | ✅ Impl | `apps/sql/api.py:175` |
| SQL-F-022 | Delete saved query | `DELETE /sql/saved/{id}` by owner only; returns 204 | ✅ Impl | `apps/sql/api.py:214` |
| SQL-F-023 | List user's + public queries | `GET /sql/saved` returns `Q(created_by=uid) OR Q(is_public=True)` | ✅ Impl | `apps/sql/api.py:67` |
| SQL-F-024 | Public/private visibility | `is_public` boolean flag on SavedQuery | ✅ Impl | `apps/sql/models.py:41–45` |
| SQL-F-025 | Load saved query into editor | Click saved query → sets `this.sql` + `activeSavedId` | ✅ Impl | `view-sql.ts:140` |
| SQL-F-026 | Share query (stub) | `POST /sql/saved/{id}/share` — not yet implemented | 🔲 Stub | `apps/sql/api.py:239` |
| SQL-F-027 | Visual indicator for active query | Border highlight on active saved query card | ✅ Impl | `view-sql.ts:238` |

### 4.4 Results & Export

| FR-ID | Description | Acceptance Criteria | Status | Code Reference |
|---|---|---|---|---|
| SQL-F-030 | Sortable result columns | `<voyant-data-table>` with `.sortable=true` | ✅ Impl | `view-sql.ts:152` |
| SQL-F-031 | Filterable results | `<voyant-data-table>` with `.filterable=true` | ✅ Impl | `view-sql.ts:202` |
| SQL-F-032 | Export results | `<voyant-data-table>` with `.exportable=true` | ✅ Impl | `view-sql.ts:201` |

---

## 5. Data Model

### 5.1 SavedQuery

**Table:** `voyant_saved_query`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Primary key (UUIDModel) |
| `tenant_id` | VARCHAR(255) | NOT NULL | Multi-tenancy isolation (TenantModel) |
| `realm` | VARCHAR(255) | DEFAULT "" | Realm/namespace |
| `name` | VARCHAR(255) | NOT NULL | Human-readable query name |
| `description` | TEXT | DEFAULT "" | Optional description |
| `query_text` | TEXT | NOT NULL | The SQL query text |
| `language` | VARCHAR(32) | DEFAULT "sql" | Query language identifier |
| `parameters` | JSONField | NULL, DEFAULT {} | Parameter definitions for parameterized queries |
| `is_public` | BooleanField | DEFAULT false, INDEX | If true, visible to all tenant users |
| `created_by` | VARCHAR(256) | NOT NULL, INDEX | User ID of creator |
| `created_at` | DateTimeField | AUTO | Creation timestamp |
| `updated_at` | DateTimeField | AUTO | Last modification timestamp |

**Indexes:**

| Index Name | Fields | Purpose |
|---|---|---|
| (unnamed) | (`tenant_id`, `created_by`, `-updated_at`) | User's queries sorted by recency |
| (unnamed) | (`tenant_id`, `is_public`, `-updated_at`) | Public queries lookup |

**Ordering:** `-updated_at` (most recently updated first)

### 5.2 Query Execution Request/Response (Transient)

**`SqlRequest` Schema (not persisted):**

| Field | Type | Constraints | Description |
|---|---|---|---|
| `sql` | str | Required, min_length=1 | SQL query to execute |
| `limit` | int | 1–10000, default 1000 | Max rows to return |
| `parameters` | dict | Optional | Parameterized query values |

**`SqlResponse` Schema (not persisted):**

| Field | Type | Description |
|---|---|---|
| `columns` | list[str] | Column names |
| `rows` | list[list[Any]] | Row data |
| `row_count` | int | Total rows returned |
| `truncated` | bool | True if limit was hit |
| `execution_time_ms` | int | Query execution time |
| `query_id` | str \| None | Trino query ID |

---

## 6. API Endpoints

### 6.1 Query Execution

| Method | Path | Auth | Summary |
|---|---|---|---|
| `POST` | `/sql/query` | `execute:sql` | Execute ad-hoc SQL query via Trino |

**Request:**
```json
{
  "sql": "SELECT * FROM customers WHERE age > 25 LIMIT 100",
  "limit": 1000,
  "parameters": null
}
```

**Response (200):**
```json
{
  "columns": ["id", "name", "email", "age"],
  "rows": [["abc123", "John", "j@mail.com", 32]],
  "row_count": 1,
  "truncated": false,
  "execution_time_ms": 245,
  "query_id": "20260115_123456_00001_abc"
}
```

**Error Responses:**
| Code | Condition | Message |
|---|---|---|
| 400 | Invalid SQL / validation error | `ERR_VALIDATION` |
| 500 | Trino execution failure | `ERR_SQL_INVALID` |
| 503 | System unavailable | `ERR_SYSTEM` |

### 6.2 Schema Exploration

| Method | Path | Auth | Summary |
|---|---|---|---|
| `GET` | `/sql/tables` | `execute:sql` | List accessible tables |
| `GET` | `/sql/tables/{table}/columns` | `execute:sql` | Get column metadata for a table |

**Tables Response:**
```json
{
  "tables": [
    {"name": "customers", "schema": "voyant", "type": "TABLE"},
    {"name": "orders", "schema": "voyant", "type": "TABLE"}
  ],
  "schema": "voyant"
}
```

### 6.3 Saved Queries

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `GET` | `/sql/saved` | `auth_guard` | — | `SavedQueryOut[]` |
| `POST` | `/sql/saved` | `auth_guard` | `SavedQueryIn` | `SavedQueryOut` |
| `GET` | `/sql/saved/{id}` | `auth_guard` | — | `SavedQueryOut` |
| `PUT` | `/sql/saved/{id}` | `auth_guard` | `SavedQueryIn` | `SavedQueryOut` |
| `DELETE` | `/sql/saved/{id}` | `auth_guard` | — | `204 No Content` |
| `POST` | `/sql/saved/{id}/share` | `auth_guard` | `ShareRequest` | `{status: "stub"}` |

**`SavedQueryIn` Schema:**

| Field | Type | Constraints | Default |
|---|---|---|---|
| `name` | str | Required, 1–255 chars | — |
| `description` | str | Optional | `""` |
| `query_text` | str | Required, min 1 char | — |
| `language` | str | Optional | `"sql"` |
| `parameters` | dict | Optional | `{}` |
| `is_public` | bool | Optional | `false` |

**Authorization Rules:**
- **List:** Returns queries where `created_by == current_user OR is_public == True`
- **Get:** Owner or public only; else 404
- **Update:** Owner only; else 404
- **Delete:** Owner only; else 404

### 6.4 Admin Routes

| Method | Path | Auth | Summary |
|---|---|---|---|
| `POST` | `/admin/sql/execute` | Admin | Execute SQL (used by Sources detail panel) |
| `GET` | `/admin/sql/tables` | Admin | List tables (used by SQL Console init) |

---

## 7. Integration Points

### 7.1 Internal Module Connections

| From | To | Integration | Description |
|---|---|---|---|
| SQL Console | Trino Engine | `TrinoClient` shared instance | Both SQL Console and Ontology Query Engine use the same Trino connection |
| SQL Console | Ontology | Shared backing datasets | Iceberg tables defined as `backing_dataset` on ObjectTypes are queryable |
| SQL Console | Sources | Source detail "SQL Query" tab | `view-sources.ts:79` calls `POST /admin/sql/execute` |
| SQL Console | Pipelines | Pipeline step `sql_query` type | Pipeline SQL Query steps use same Trino infrastructure |
| SQL Console | Feature Store | Feature computation | `FeatureComputeService` executes SQL via Trino for feature value computation |

### 7.2 External Systems

| System | Protocol | Purpose |
|---|---|---|
| Trino | HTTP/REST | SQL query execution engine |
| Iceberg | Via Trino connector | Underlying table format |
| PostgreSQL | Django ORM | Saved query persistence |

---

## 8. Quality Attributes

### 8.1 Performance Targets

| Metric | Target | Notes |
|---|---|---|
| Query execution (simple) | < 500ms | `SELECT * FROM table LIMIT 100` |
| Query execution (analytical) | < 5s | Aggregations with GROUP BY |
| Table list load | < 200ms | `SHOW TABLES` via Trino |
| Saved query list | < 100ms | Django ORM query |
| Save/Update query | < 100ms | Single record write |
| Max rows per query | 10,000 | Hard limit enforced in `SqlRequest.limit` |
| Default row limit | 1,000 | Configurable per request |

### 8.2 Security Considerations

| Concern | Mitigation |
|---|---|
| SQL injection | TrinoClient enforces read-only (SELECT only); parameterized queries supported |
| Destructive operations | `TrinoClient` blocks INSERT, UPDATE, DELETE, DROP, ALTER, CREATE statements |
| Cross-tenant data | Tenant-scoped Trino schema; queries run in tenant's namespace |
| Query ownership | Saved queries tied to `created_by`; update/delete restricted to owner |
| Public query exposure | `is_public` flag controls visibility; defaults to private |

### 8.3 Accessibility

| Feature | Implementation |
|---|---|
| ARIA roles | `role="main"`, `role="textbox"`, `role="navigation"`, `role="list"`, `role="listitem"` |
| Keyboard navigation | Tab-based navigation; Enter/Space on list items; Ctrl+Enter to run |
| Screen reader | `aria-label` on all interactive elements; `aria-live="polite"` on results |
| Focus management | `tabindex="0"` on clickable items; proper tab order |

---

## 9. Implementation Details

### 9.1 Key Algorithms

#### Read-Only Enforcement (`apps/core/lib/trino.py`)

The TrinoClient inspects every SQL query before execution:

1. Strips leading whitespace and comments
2. Checks first keyword is `SELECT`, `SHOW`, `DESCRIBE`, or `EXPLAIN`
3. Rejects `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `GRANT`, `REVOKE`
4. Adds `LIMIT` clause if not present (respects client-specified limit)

#### Query History Management (`view-sql.ts:28, 70`)

In-memory array with cap:
```
this.history = [
  { sql: this.sql, time: elapsed, rows: rowCount },
  ...this.history.slice(0, 19)  // Keep last 20
];
```
- Not persisted across page reloads
- Clicking a history item loads the SQL into the editor
- Displayed in reverse-chronological order

#### Saved Query Sharing (`view-sql.ts:145–148`)

Stub implementation:
```typescript
private _shareQuery(q: SavedQuery) {
    api.post(`/sql/saved/${q.id}/share`, { message: '' }).catch(() => {});
    alert(`Sharing for "${q.name}" is not yet implemented.`);
}
```
Backend returns `{ status: "stub" }` — `apps/sql/api.py:245–264`

### 9.2 Design Patterns

| Pattern | Usage | Location |
|---|---|---|
| Singleton Client | `get_trino_client()` returns shared Trino instance | `apps/core/lib/trino.py` |
| Schema/DTO | Django Ninja `Schema` for input/output validation | `apps/sql/api.py:22–53` |
| User-scoped queries | `Q(created_by=uid) OR Q(is_public=True)` | `apps/sql/api.py:80` |
| Monaco Integration | `<voyant-monaco-editor>` with `@change` + `@run` events | `view-sql.ts:170–176` |
| Reactive State | Lit `@state()` decorators for all mutable data | `view-sql.ts:23–35` |
| No Shadow DOM | `createRenderRoot() { return this; }` for global CSS | `view-sql.ts:37` |

### 9.3 File Locations

| Layer | File | Lines | Description |
|---|---|---|---|
| API | `apps/sql/api.py` | 381 | REST endpoints for queries and saved queries |
| Models | `apps/sql/models.py` | 63 | SavedQuery Django model |
| Trino Client | `apps/core/lib/trino.py` | — | Shared Trino connection and query execution |
| UI View | `dashboard/src/views/view-sql.ts` | 325 | SQL Console Lit component |
| Monaco Editor | `dashboard/src/components/voyant-monaco-editor.ts` | — | Code editor component |
| Data Table | `dashboard/src/components/voyant-data-table.ts` | — | Results table with export/filter/sort |

### 9.4 UI Component Architecture

```
<view-sql>
├── <saas-sidebar>                     -- Navigation sidebar
├── <main>
│   ├── <h1> SQL Console</h1>
│   ├── Grid: 1fr | 260px
│   │   ├── Left Column
│   │   │   ├── <voyant-monaco-editor>  -- SQL editor (200px height)
│   │   │   ├── Run bar                 -- [▶ Run] [💾 Save] stats
│   │   │   └── Results                 -- <voyant-data-table> or empty state
│   │   └── Right Column (sidebar)
│   │       ├── Tables card             -- Scrollable table list
│   │       ├── Saved Queries card      -- Saved query cards with actions
│   │       └── History card            -- Recent query history
│   └── Save Dialog (modal)             -- Name, description, public toggle
```

---

# Detailed Design

_Merged from MODULE_DATA_INTELLIGENCE.md (v4.0.0). Original: 1,641 lines._

# Voyant v4.0 — Data Intelligence Stack: Deep Design Document

**Document ID:** VOYANT-DI-4.0.0
**Version:** 4.0.0
**Date:** 2026-09-05
**Scope:** Ingestion, SQL, Search, Streaming, Discovery, Events
**Status:** Design Specification

---

## Table of Contents

1. [Current Implementation (v3.0)](#1-current-implementation-v30)
2. [Databricks Comparison (Deep)](#2-databricks-comparison-deep)
3. [Palantir Comparison (Deep)](#3-palantir-comparison-deep)
4. [Improvements Over Both](#4-improvements-over-both)
5. [Complete API Design (v4.0)](#5-complete-api-design-v40)
6. [Streaming Architecture](#6-streaming-architecture)
7. [Event-Driven Architecture](#7-event-driven-architecture)
8. [Cross-Cutting Concerns](#8-cross-cutting-concerns)

---

## 1. Current Implementation (v3.0)

### 1.1 Ingestion Layer

#### 1.1.1 Model: `IngestionJob` (`apps/ingestion/models.py`)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key (UUIDModel mixin) |
| `tenant_id` | VARCHAR(64) | Multi-tenant isolation key (TenantModel mixin) |
| `source` | FK → `discovery.Source` | Source to ingest from; CASCADE on delete |
| `workflow_instance_id` | VARCHAR(255) | Temporal workflow instance ID; unique, indexed |
| `status` | VARCHAR(16) | One of: `pending`, `queued`, `running`, `succeeded`, `failed`, `cancelled`, `partial` |
| `progress` | FLOAT | 0.0–1.0 progress indicator |
| `stage` | VARCHAR(64) | Current execution stage label (e.g., "validating", "syncing") |
| `params` | JSONB | Job parameters and configuration |
| `result` | JSONB | Nullable result data on completion |
| `error_message` | TEXT | Error details on failure |
| `rows_ingested` | BIGINT | Rows successfully ingested (default 0) |
| `bytes_processed` | BIGINT | Bytes processed (default 0) |
| `started_at` | DATETIME | Nullable execution start timestamp |
| `finished_at` | DATETIME | Nullable completion timestamp |
| `created_at` | DATETIME | Auto-set on creation (TenantModel mixin) |
| `updated_at` | DATETIME | Auto-set on update (TenantModel mixin) |

**Database Table:** `voyant_ingestion_job`

**Indexes:**

| Index | Fields | Purpose |
|-------|--------|---------|
| Composite | `tenant_id`, `status`, `-created_at` | Tenant-scoped status filtering |
| FK search | `source`, `-created_at` | Per-source job history |
| Workflow lookup | `workflow_instance_id` | Temporal workflow → job resolution |

#### 1.1.2 API Endpoints (`apps/ingestion/api.py`)

**Router:** `/api/v1/ingestion` (tag: `ingestion`)

| Method | Path | Auth | Request Schema | Response Schema | Description |
|--------|------|------|----------------|-----------------|-------------|
| `POST` | `/connect` | `write:sources` | `ConnectSourceRequest` | `ConnectSourceResponse` | Provision Airbyte source connector + optional destination |
| `POST` | `/provision-destination` | `write:sources` | `ProvisionDestinationRequest` | `ProvisionDestinationResponse` | Provision standalone Airbyte destination |

**`ConnectSourceRequest` Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_id` | `str` | Yes | Voyant source ID from discovery |
| `source_definition_id` | `str` | Yes | Airbyte source definition (connector) ID |
| `connection_config` | `dict[str, Any]` | Yes | Source-specific config (host, port, auth, etc.) |
| `destination_definition_id` | `str\|None` | No | Optional Airbyte destination definition ID |
| `destination_config` | `dict[str, Any]\|None` | No | Optional destination-specific configuration |

**`ConnectSourceResponse` Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `source_id` | `str` | Voyant source ID |
| `airbyte_source_id` | `str` | Provisioned Airbyte source ID |
| `status` | `str` | Connection status (`"connected"`) |
| `airbyte_destination_id` | `str\|None` | Provisioned Airbyte destination ID |
| `destination_status` | `str\|None` | Destination status (`"provisioned"`) |

**Connect Flow:**
1. Validates source exists and belongs to tenant.
2. Calls `AirbyteClient.connect_source()` to provision the source connector.
3. Optionally calls `AirbyteClient.provision_destination()` for destination.
4. Updates `Source.status` to `"connected"` on success, `"error"` on failure.
5. Applies policy guard (`apply_policy`) before execution.

---

### 1.2 SQL Execution Layer

#### 1.2.1 Trino Client (`apps/core/lib/trino.py`)

**Class:** `TrinoClient` — singleton via `get_trino_client()`

**Configuration (from `Settings`):**

| Setting | Description |
|---------|-------------|
| `trino_host` | Trino coordinator hostname |
| `trino_port` | Trino coordinator port |
| `trino_user` | Trino user for query attribution |
| `trino_catalog` | Default catalog (e.g., `iceberg`) |
| `trino_schema` | Default schema |
| `max_query_rows` | Maximum rows per query |

**3-Layer Validation Pipeline:**

```
SQL Input → Layer 1 (Semicolon) → Layer 2 (Prefix Allowlist) → Layer 3 (Keyword Denylist) → Execute
```

**Layer 1 — Multi-Statement Injection Block:**
- Strips trailing semicolons (harmless, commonly added by tools).
- Rejects any semicolons within the statement body.
- Prevents `DROP TABLE; SELECT ...` style injection.

**Layer 2 — Prefix Allowlist:**
- Only queries starting with these prefixes are permitted:

| Allowed Prefix | Purpose |
|---------------|---------|
| `SELECT` | Standard data queries |
| `WITH` | Common Table Expressions (CTEs) |
| `SHOW` | Schema inspection (`SHOW TABLES`) |
| `DESCRIBE` | Table column metadata |
| `EXPLAIN` | Query plan inspection |

**Layer 3 — 28 Forbidden Keyword Denylist:**

| Category | Keywords | Count |
|----------|----------|-------|
| DDL (Schema Mutation) | `DROP`, `CREATE`, `ALTER`, `TRUNCATE`, `RENAME` | 5 |
| DML (Data Mutation) | `DELETE`, `INSERT`, `UPDATE`, `MERGE`, `UPSERT` | 5 |
| Privilege Escalation | `GRANT`, `REVOKE` | 2 |
| Session/Procedural | `SET`, `RESET`, `CALL`, `EXECUTE`, `PREPARE`, `DEALLOCATE` | 6 |
| UNION Exfiltration | `UNION` | 1 |
| Injection Vectors | `INTO OUTFILE`, `INTO DUMPFILE`, `LOAD_FILE(`, `BENCHMARK(`, `SLEEP(`, `WAITFOR DELAY`, `PG_SLEEP(`, `DBMS_PIPE.RECEIVE_MESSAGE(` | 9 |
| **Total** | | **28** |

**Comment Stripping:** Before validation, single-line (`-- ...`) and multi-line (`/* ... */`) comments are stripped via regex to prevent bypass attempts like `SELECT /* DROP TABLE */ ...`.

**Identifier Validation:** `_validate_identifier()` enforces `^[A-Za-z_][A-Za-z0-9_]*$` on all user-supplied identifiers used in `SHOW TABLES` and `DESCRIBE` to prevent injection in schema/table names.

**Auto-Limit:** If no `LIMIT` clause exists, the query is wrapped: `SELECT * FROM ({original_sql}) AS _q LIMIT {limit}`. The limit is capped at `max_query_rows`.

**`QueryResult` Dataclass:**

| Field | Type | Description |
|-------|------|-------------|
| `columns` | `list[str]` | Column names from `cursor.description` |
| `rows` | `list[list[Any]]` | Result rows as lists |
| `row_count` | `int` | Number of rows returned |
| `truncated` | `bool` | `True` if results hit the limit |
| `execution_time_ms` | `int` | Wall-clock time in milliseconds |
| `query_id` | `str\|None` | Trino engine query ID |

#### 1.2.2 SQL API (`apps/sql/api.py`)

**Router:** `/api/v1/sql` (tag: `sql`, auth: `execute:sql`)

| Method | Path | Auth | Request Schema | Response Schema | Description |
|--------|------|------|----------------|-----------------|-------------|
| `POST` | `/query` | `execute:sql` (via `auth_guard`) | `SqlRequest` | `SqlResponse` | Execute ad-hoc SQL query |
| `GET` | `/tables` | `execute:sql` | query param: `schema` | `{tables: list, schema: str}` | List accessible tables |
| `GET` | `/tables/{table}/columns` | `execute:sql` | path: `table`, query: `schema` | `{table: str, columns: list}` | Get table column metadata |

**`SqlRequest` Schema:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `sql` | `str` | Required | The SQL query string (SELECT only) |
| `limit` | `int` | `ge=1, le=10000`, default=1000 | Max rows to return |
| `parameters` | `dict[str,Any]\|None` | Optional | Parameterized query values |

**`SqlResponse` Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `columns` | `list[str]` | Column names |
| `rows` | `list[list[Any]]` | Result data |
| `row_count` | `int` | Rows returned |
| `truncated` | `bool` | Whether limit was hit |
| `execution_time_ms` | `int` | Execution time |
| `query_id` | `str\|None` | Trino query ID |

---

### 1.3 Semantic Search Layer

#### 1.3.1 Embedding Engine (`apps/search/lib/embeddings.py`)

Four embedding models are available:

| Model | Class | Dimensions | Algorithm | Use Case |
|-------|-------|-----------|-----------|----------|
| `simple` | `SimpleEmbedder` | 64 (configurable) | Character-frequency vector + L2 norm | Test-only (raises `RuntimeError` outside test env) |
| `tfidf` | `TFIDFEmbedder` | 128 (configurable) | TF-IDF with vocabulary truncation + L2 norm | Lightweight production embeddings |
| `dense` | `DenseEmbedder` | 1536 (fixed) | SHA-256 seeded random projection + mean pooling + L2 norm | Production dense vectors for Milvus |
| `sparse` | `SparseEmbedder` | Variable | BM25-like term hashing + L2 norm of weights | Sparse vectors for Milvus hybrid search |

**`DenseEmbedder` Algorithm:**
1. Tokenize text (lowercase, alphanumeric split).
2. For each token, SHA-256 hash → seed a deterministic `random.Random` instance.
3. Generate 1536 Gaussian random values per token.
4. Mean-pool across all tokens.
5. L2-normalize the result.
6. Deterministic across process restarts (no external model API dependency).

**`SparseEmbedder` Algorithm:**
1. Tokenize text.
2. Count term frequencies.
3. For each term, compute BM25 weight: `((k1+1)*freq) / (freq + k1*(1-b+b*(dl/avgdl)))` with k1=1.5, b=0.75.
4. Map term → uint32 index via `SHA-256 hash mod 2^32`.
5. L2-normalize sparse weight values.

**`EmbeddingResult` Dataclass:**

| Field | Type | Description |
|-------|------|-------------|
| `embeddings` | `list[list[float]]` | List of embedding vectors |
| `model` | `str` | Model name used |
| `dimensions` | `int` | Vector dimensionality |
| `count` | `int` | Number of embeddings |

**Similarity Functions:**
- `cosine_similarity(a, b)` — standard cosine similarity.
- `euclidean_distance(a, b)` — L2 distance.
- `reduce_dimensions(embeddings, target_dims)` — variance-based dimensionality reduction (top-variance dimensions, not full PCA).

#### 1.3.2 Milvus Vector Store (`apps/search/lib/milvus_store.py`)

**Collection:** `voyant_documents`

**Schema (9 fields):**

| Field | Milvus Type | Properties | Description |
|-------|------------|------------|-------------|
| `id` | `INT64` | Primary key, auto-increment | Internal Milvus ID |
| `doc_id` | `VARCHAR(256)` | — | Application-level document ID |
| `tenant_id` | `VARCHAR(64)` | **Partition key** | Multi-tenant isolation via Milvus partition keys |
| `realm` | `VARCHAR(64)` | — | Sub-tenant/realm isolation |
| `content` | `VARCHAR(65535)` | — | Text content preview (max 64KB) |
| `embedding` | `FLOAT_VECTOR(1536)` | — | Dense embedding vector |
| `sparse_embedding` | `SPARSE_FLOAT_VECTOR` | — | Sparse BM25 vector |
| `metadata` | `JSON` | — | Arbitrary JSON metadata |
| `source_type` | `VARCHAR(32)` | — | Source type tag |
| `created_at` | `INT64` | — | Unix timestamp |

**Index Configuration:**

| Field | Index Type | Metric | Parameters |
|-------|-----------|--------|------------|
| `embedding` | HNSW | COSINE | M=16, efConstruction=256 |
| `sparse_embedding` | SPARSE_INVERTED_INDEX | IP | drop_ratio_build=0.2 |

**Hybrid Search Algorithm (Weighted RRF Merge):**

```
1. Execute dense search (COSINE, ef=64) → fetch 2k candidates
2. Execute sparse search (IP, drop_ratio_search=0.2) → fetch 2k candidates
3. Weighted RRF merge:
   score(doc) = DENSE_WEIGHT/(RRF_K + rank_dense) + SPARSE_WEIGHT/(RRF_K + rank_sparse)
   where DENSE_WEIGHT=0.7, SPARSE_WEIGHT=0.3, RRF_K=60
4. Sort by merged score, return top-k
```

**Connection Management:**
- Lazy initialization with exponential backoff (1s → 2s → ... → 30s max).
- Liveness probe via `list_collections()` on each request.
- Auto-reconnect on connection failure.
- Auto-collection-creation when `milvus_auto_create=True`.

**`VectorStore` API:**

| Method | Description |
|--------|-------------|
| `add(id, vector, metadata, sparse_vector)` | Insert/upsert a document |
| `get(id) → VectorItem\|None` | Retrieve by `doc_id` |
| `delete(id, tenant_id)` | Delete with optional tenant verification |
| `search(query_vector, k, filter_metadata, query_sparse_vector)` | Hybrid dense+sparse search |

#### 1.3.3 Search API (`apps/search/api.py`)

**Router:** `/api/v1/search` (tag: `Search`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/query` | `read:*` | Semantic search query (hybrid dense+sparse) |
| `POST` | `/index` | `write:documents` | Index a new text item |
| `DELETE` | `/{item_id}` | `write:documents` | Delete an indexed item |
| `GET` | `/{item_id}` | `read:*` | Get an indexed item by ID |

**Search Flow:**
1. Extract dense embedding (1536-dim) from query text.
2. Extract sparse BM25 embedding from query text.
3. Inject `tenant_id` into filter for isolation.
4. Execute hybrid search on Milvus.
5. Return ranked results with similarity scores.

---

### 1.4 Source Discovery Layer

#### 1.4.1 Models (`apps/discovery/models.py`)

**`Source` Model:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `tenant_id` | VARCHAR(64) | Tenant isolation |
| `name` | VARCHAR(255) | Human-readable source name |
| `source_type` | VARCHAR(128) | Type identifier (postgresql, mysql, s3, etc.) |
| `status` | VARCHAR(64) | Status (`pending`, `connected`, `error`) |
| `connection_config` | JSONB | Source connection parameters |
| `credentials` | JSONB | Nullable encrypted credentials |
| `sync_schedule` | VARCHAR(128) | Nullable cron expression |
| `datahub_urn` | VARCHAR(512) | Nullable DataHub URN for lineage |

**`ServiceDefinition` Model (deprecated v3.0, in-memory `DiscoveryRepo` used instead):**

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `tenant_id` | VARCHAR(64) | Tenant isolation |
| `name` | VARCHAR(255) | Unique service name |
| `base_url` | URL(512) | Service base URL |
| `spec_url` | URL(512) | OpenAPI spec URL |
| `version` | VARCHAR(64) | API version |
| `description` | TEXT | Service description |
| `owner` | VARCHAR(255) | Responsible team/person |
| `tags` | JSONB | Categorization tags |
| `endpoints` | JSONB | Extracted API endpoints |
| `auth_type` | VARCHAR(64) | Authentication type |
| `metadata` | JSONB | Additional metadata |
| `first_seen` | DATETIME | Discovery timestamp |
| `last_seen` | DATETIME | Last update timestamp |

#### 1.4.2 Source Type Detection (`apps/discovery/source_detection.py`)

Pattern-matching detection from user-provided hints (URLs, connection strings):

| Pattern | Source Type | Airbyte Connector | Confidence |
|---------|-----------|-------------------|------------|
| `postgresql://` / `postgres://` | `postgresql` | `airbyte/source-postgres` | 0.95 |
| `mysql://` | `mysql` | `airbyte/source-mysql` | 0.95 |
| `mongodb://` / `mongodb+srv://` | `mongodb` | `airbyte/source-mongodb-v2` | 0.95 |
| `*snowflake*` | `snowflake` | `airbyte/source-snowflake` | 0.90 |
| `*.csv` | `csv` | `file` | 0.90 |
| `*.parquet` | `parquet` | `file` | 0.90 |
| `*.json` / `*.jsonl` | `json` | `file` | 0.90 |
| `s3://` | `s3` | `airbyte/source-s3` | 0.90 |
| `sheets.google.com` | `google_sheets` | `airbyte/source-google-sheets` | 0.90 |
| `http://` / `https://` | `api` | `airbyte/source-http` | 0.50 |
| *(anything else)* | `unknown` | `unknown` | 0.10 |

#### 1.4.3 Discovery API (`apps/discovery/api.py`)

**Two routers:**

**Sources Router** (`/api/v1/sources`, tag: `sources`):

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/discover` | `read:*` | Detect source type from hint |
| `POST` | `/` | `write:sources` | Create a new source |
| `GET` | `/` | `read:*` | List all sources (tenant-scoped) |
| `GET` | `/{source_id}` | `read:*` | Get a specific source |
| `PUT` | `/{source_id}` | `write:sources` | Update a source |
| `DELETE` | `/{source_id}` | `write:sources` | Delete a source |

**Discovery Router** (`/api/v1/discovery`, tag: `discovery`):

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/services` | `write:sources` | Register external service (with optional OpenAPI spec parsing) |
| `GET` | `/services` | `read:*` | List registered services (optional `tag` filter) |
| `GET` | `/services/{name}` | `read:*` | Get service by name |
| `POST` | `/scan` | `write:sources` | Scan an OpenAPI spec URL |

**`DiscoveryRepo` (In-Memory Catalog):**
- `register(service)` → add or update by name.
- `get(name)` → retrieve by name.
- `list_services()` → all services.
- `search(query)` → fuzzy match on name/description.

---

### 1.5 Iceberg Integration (`apps/core/lib/iceberg.py`)

**Class:** `IcebergClient` — REST catalog client for Apache Iceberg tables.

**Configuration:**

| Setting | Description |
|---------|-------------|
| `iceberg_catalog_url` | REST catalog endpoint (e.g., `http://catalog:8181`) |
| `iceberg_warehouse` | Warehouse name (default: `voyant-warehouse`) |

**`IcebergTable` Dataclass:**

| Field | Type | Description |
|-------|------|-------------|
| `namespace` | `str` | Namespace (e.g., `default`) |
| `table_name` | `str` | Table name |
| `location` | `str` | S3/MinIO storage location |
| `current_snapshot_id` | `int\|None` | Current snapshot ID |
| `schema_fields` | `list[dict]` | Current schema fields (`id`, `name`, `type`, `required`) |
| `partition_spec` | `list[dict]` | Partition specifications |
| `properties` | `dict[str,str]` | Table properties |
| `snapshot_count` | `int` | Number of snapshots |

**`IcebergSnapshot` Dataclass:**

| Field | Type | Description |
|-------|------|-------------|
| `snapshot_id` | `int` | Snapshot identifier |
| `timestamp_ms` | `int` | Snapshot timestamp |
| `operation` | `str` | Operation type (`append`, `overwrite`, `delete`) |
| `summary` | `dict[str,str]` | Operation summary |
| `manifest_list` | `str` | Manifest list path |

**REST Catalog API Operations:**

| Method | REST Endpoint | Description |
|--------|--------------|-------------|
| `list_namespaces()` | `GET /v1/namespaces` | List all namespaces |
| `list_tables(namespace)` | `GET /v1/namespaces/{ns}/tables` | List tables in namespace |
| `get_table(namespace, table)` | `GET /v1/namespaces/{ns}/tables/{t}` | Full table metadata |
| `get_snapshots(namespace, table)` | `GET /v1/namespaces/{ns}/tables/{t}` | All snapshots |
| `create_namespace(namespace)` | `POST /v1/namespaces` | Create namespace |
| `drop_table(namespace, table, purge)` | `DELETE /v1/namespaces/{ns}/tables/{t}` | Drop table |
| `is_available()` | `GET /v1/config` | Health check |

---

### 1.6 Kafka Events (`apps/core/lib/events.py`)

#### 1.6.1 Event Producer

**Class:** `KafkaProducer` — singleton wrapper around `confluent_kafka.Producer`.

**Configuration:** `kafka_bootstrap_servers` from settings.

**Producer Config:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `client.id` | `voyant-api` | Client identification |
| `acks` | `all` | Wait for all in-sync replicas |
| `retries` | `3` | Retry failed produce requests |

**Topic Registry:**

| Key | Topic | Purpose |
|-----|-------|---------|
| `jobs` | `voyant.jobs` | Job lifecycle events |
| `quality` | `voyant.quality.alerts` | Data quality alerts |
| `lineage` | `voyant.lineage` | Data lineage events |
| `audit` | `voyant.audit` | Audit trail events |

**`VoyantEvent` Dataclass:**

| Field | Type | Description |
|-------|------|-------------|
| `event_type` | `str` | Event type identifier (e.g., `"job.started"`) |
| `event_id` | `str` | UUID for deduplication |
| `timestamp` | `str` | ISO 8601 timestamp |
| `tenant_id` | `str` | Tenant key (used as Kafka message key) |
| `payload` | `dict[str, Any]` | Event-specific data |

**High-Level Emitter Functions:**

| Function | Topic | Description |
|----------|-------|-------------|
| `emit_job_event(event_type, job_id, tenant_id, ...)` | `voyant.jobs` | Job lifecycle (started/completed/failed) |
| `emit_quality_alert(source_id, tenant_id, score, failed_checks)` | `voyant.quality.alerts` | Quality threshold breach |
| `emit_ontology_event(event_type, tenant_id, object_type, ...)` | `voyant.ontology` | Ontology object lifecycle |
| `emit_ml_event(event_type, tenant_id, entity_type, ...)` | `voyant.ml` | ML experiment/model events |
| `emit_intent_event(event_type, tenant_id, intent, ...)` | `voyant.intent` | Intent engine events |
| `emit_governance_event(event_type, tenant_id, policy_type, ...)` | `voyant.governance` | Policy evaluation events |
| `emit_scraper_event(event_type, tenant_id, ...)` | `voyant.scraper` | Scraper lifecycle events |

#### 1.6.2 Event Schema Registry (`apps/core/lib/event_schema.py`)

**In-memory schema registry** with semver support and JSON Schema generation.

**`EventSchema` Dataclass:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Event type (e.g., `"job.started"`) |
| `version` | `str` | Semver version (e.g., `"1.0.0"`) |
| `fields` | `list[FieldSpec]` | Payload field specifications |
| `description` | `str` | Human-readable description |
| `created_at` | `str` | Registration timestamp |
| `deprecated` | `bool` | Deprecation flag |
| `deprecation_message` | `str` | Deprecation reason |

**`FieldSpec` — 8 Supported Types:**

| FieldType | JSON Schema Type | Validation |
|-----------|-----------------|------------|
| `STRING` | `string` | `isinstance(v, str)` |
| `INTEGER` | `integer` | `isinstance(v, int) and not bool` |
| `FLOAT` | `number` | `isinstance(v, (int, float)) and not bool` |
| `BOOLEAN` | `boolean` | `isinstance(v, bool)` |
| `DATETIME` | `string` (format: `date-time`) | `isinstance(v, str)` |
| `ARRAY` | `array` | `isinstance(v, list)` |
| `OBJECT` | `object` | `isinstance(v, dict)` |
| `ENUM` | string + `enum` | `isinstance(v, str) and v in enum_values` |

**Registered Canonical Schemas:**

| Schema Name | Version | Key Fields |
|-------------|---------|------------|
| `job.started` | 1.0.0 | `job_id`, `tenant_id`, `job_type`, `source_id?`, `started_at` |
| `job.completed` | 1.0.0 | `job_id`, `tenant_id`, `job_type`, `completed_at`, `duration_seconds`, `artifact_count` |
| `job.failed` | 1.0.0 | `job_id`, `tenant_id`, `job_type`, `error_code`, `error_message`, `retryable` |
| `artifact.created` | 1.0.0 | `artifact_key`, `job_id`, `tenant_id`, `artifact_type` (enum), `size_bytes` |
| `data.ingested` | 1.0.0 | `source_id`, `tenant_id`, `table_name`, `row_count`, `ingested_at` |
| `data.drift_detected` | 1.0.0 | `source_id`, `tenant_id`, `drift_score`, `columns_drifted` |
| `quota.warning` | 1.0.0 | `tenant_id`, `quota_type` (enum), `current_usage`, `limit`, `percentage` |

---

### 1.7 Job Queue (`apps/core/lib/job_queue.py`)

**Two implementations:** `InMemoryJobQueue` (dev/test) and `RedisJobQueue` (production).

**`QueuedJob` Dataclass:**

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | `str` | Unique job identifier |
| `tenant_id` | `str` | Tenant isolation |
| `job_type` | `str` | Job type (default: `"analyze"`) |
| `priority` | `int` | Lower = higher priority |
| `created_at` | `float` | Unix timestamp |
| `status` | `JobStatus` | `queued` / `running` / `completed` / `failed` / `cancelled` |
| `worker_id` | `str\|None` | Assigned worker |
| `lease_expires_at` | `float\|None` | Lease expiry (prevents zombie jobs) |
| `metadata` | `dict\|None` | Job metadata |

**Redis Key Schema:**

| Key Pattern | Type | Purpose |
|-------------|------|---------|
| `voyant:queue:{tenant_id}` | Sorted Set | Priority queue (score=priority) |
| `voyant:job:{job_id}` | Hash | Job metadata (JSON serialized) |
| `voyant:running:{tenant_id}` | Set | Currently running job IDs |

**Features:**
- Per-tenant concurrency limits.
- Priority-based FIFO ordering.
- Lease-based ownership (300s default, configurable).
- Automatic requeue of expired leases.
- Transactional acquire (Redis pipeline with optimistic locking).

---

### 1.8 Temporal Workflows

#### 1.8.1 Ingestion Workflow (`apps/worker/workflows/ingest_workflow.py`)

**Class:** `IngestDataWorkflow`

**Pipeline:**
```
validate_contract_activity → run_ingestion → record_lineage_activity
```

| Step | Activity | Timeout | Retry | Description |
|------|----------|---------|-------|-------------|
| 1 | `validate_contract_activity` | 1 min | 3 attempts, 1s→2s→4s→...→60s | Validate data contract before ingestion |
| 2 | `run_ingestion` | 10 min | Same policy | Execute data transfer from source to storage |
| 3 | `record_lineage_activity` | 1 min | Same policy | Record data provenance for audit |

**Input Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `job_id` | `str` | Unique job identifier |
| `source_id` | `str` | Data source identifier |
| `tenant_id` | `str` | Tenant identifier |
| `mode` | `str` | `"full"` or `"incremental"` |
| `tables` | `list[str]\|None` | Specific tables to ingest |

**Non-Retryable Errors:** `ValidationError`, `AuthenticationError`, `AuthorizationError`, `ApplicationError`.

#### 1.8.2 Profile Workflow (`apps/worker/workflows/profile_workflow.py`)

**Class:** `ProfileWorkflow`

**Pipeline:** Single activity `profile_data` with 15-minute timeout.

**Input:** `source_id`, `table`, `sample_size`, `job_id`, `tenant_id`.

**Retry:** Uses `EXTERNAL_SERVICE_RETRY` policy (3 attempts, exponential backoff).

#### 1.8.3 Quality Workflow (`apps/worker/workflows/quality_workflow.py`)

**Class:** `QualityWorkflow`

**Pipeline:**
```
quality_fetch_sample → run_quality_checks
```

| Step | Activity | Timeout | Description |
|------|----------|---------|-------------|
| 1 | `quality_fetch_sample` | 5 min | Fetch data sample from table |
| 2 | `run_quality_checks` | 10 min | Execute quality checks on sample |

**Output:** `{table, rows_analyzed, quality: {...}}`

#### 1.8.4 Analyze Workflow (`apps/worker/workflows/analyze_workflow.py`)

**Class:** `AnzeWorkflow` — the end-to-end data analysis pipeline.

**Pipeline (4 stages, each toggleable):**
```
Stage 1: profile_data (profiling)
Stage 2: fetch_sample → run_analyzers (analysis)
Stage 3: run_kpis (KPI calculation)
Stage 4: run_generators (chart/narrative generation)
```

| Stage | Activities | Timeout | Toggle Param | Description |
|-------|-----------|---------|--------------|-------------|
| 1. Profiling | `profile_data` | 15 min | `profile=True` | Statistical summary of dataset |
| 2. Analysis | `fetch_sample` + `run_analyzers` | 5 + 10 min | `run_analyzers=True` | Execute analyzer plugins on sample |
| 3. KPIs | `run_kpis` | 10 min | `kpis=[...]` (presence) | Execute custom KPI queries |
| 4. Artifacts | `run_generators` | 10 min | `generate_artifacts=True` | Generate charts and narratives |

**Full Pipeline Flow:**
```
Data Source → Profile → Sample → Analyzers → KPIs → Charts → Narrative → Artifacts
```

#### 1.8.5 Streaming Workflow (`apps/streaming/workflow.py`)

**Class:** `StreamingJobWorkflow`

**Pipeline:**
```
get_cluster_overview (health check) → submit_streaming_job
```

**Input:** `StreamingJobInput` — `job_name`, `job_type`, `source_topic`, `sink_topic`, `config`.

**Status:** Stub — validates cluster health then submits a Flink job.

#### 1.8.6 Workflow Types (`apps/worker/workflows/types.py`)

**`IngestParams` Dataclass:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `job_id` | `str` | — | Unique job identifier |
| `source_id` | `str` | — | Data source identifier |
| `mode` | `str` | `"full"` | Ingestion mode |
| `tables` | `list[str]\|None` | `None` | Specific tables |

**`IngestResult` Dataclass:**

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | `str` | Completed job ID |
| `source_id` | `str` | Source identifier |
| `status` | `str` | Final status |
| `rows_ingested` | `int` | Total rows ingested |
| `tables_synced` | `list[str]` | Synced table names |
| `completed_at` | `str` | ISO 8601 completion timestamp |

---

### 1.9 Streaming Layer (`apps/streaming/`)

#### 1.9.1 Flink Client (`apps/streaming/flink_client.py`)

**Class:** `FlinkClient` — REST API client for Apache Flink JobManager.

| Method | REST Endpoint | Description |
|--------|--------------|-------------|
| `get_overview()` | `GET /overview` | Cluster stats (slots, task managers) |
| `list_jobs()` | `GET /jobs/overview` | List all running jobs |
| `submit_jar(jar_id, ...)` | `POST /jars/{jar_id}/run` | Submit a JAR for execution |
| `upload_jar(jar_path)` | `POST /jars/upload` | Upload a JAR file to the cluster |

**Configuration:** `FLINK_JOBMANAGER_URL` from settings.

#### 1.9.2 Streaming Activities (`apps/streaming/activities.py`)

**Class:** `StreamingActivities` — Temporal activities for Flink operations.

| Activity | Description |
|----------|-------------|
| `get_cluster_overview()` | Health check / capacity planning |
| `list_running_jobs()` | Enumerate active Flink jobs |
| `submit_streaming_job(job_name, job_config)` | Submit a streaming job |

**`FlinkJobResult` Dataclass:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Operation success |
| `job_id` | `str\|None` | Flink job ID |
| `message` | `str` | Status message |
| `details` | `dict\|None` | Additional metadata |

**Submit Flow:**
1. Check cluster has available slots.
2. Upload JAR if `jar_path` provided (instead of `jar_id`).
3. Submit JAR with entry class, program args, parallelism.
4. Return `FlinkJobResult` with job ID or error.

---

## 2. Databricks Comparison (Deep)

### 2.1 Compute Engine: Databricks Photon+Spark vs Voyant Trino

| Dimension | Databricks Photon + Spark | Voyant Trino |
|-----------|--------------------------|--------------|
| **Architecture** | Unified compute engine; Photon is a C++ vectorized engine layered on Spark's JVM runtime | Distributed SQL query engine; separate compute from storage |
| **Execution Model** | DAG-based; stages, tasks, RDD lineage | MPP (Massively Parallel Processing); pipelined stages |
| **Language Support** | Scala, Python, SQL, R, Java | SQL only (read-only enforced) |
| **Batch Processing** | Native Spark batch; optimized shuffle | Trino batch queries |
| **Interactive Queries** | Photon-accelerated SQL | Sub-second for small queries; scales linearly |
| **Vectorized Execution** | Photon: SIMD-optimized columnar processing | Trino: vectorized operators since v419 |
| **Adaptive Query Execution** | Spark AQE: runtime optimization, partition coalescing, skew join handling | Trino: rule-based optimizer; no runtime adaptation |
| **Fault Tolerance** | RDD lineage, speculative execution, stage retry | Query-level retry; no speculative execution |
| **Resource Management** | Native cluster autoscaling, job queues | External (Kubernetes, YARN); no native autoscaling |
| **Cost Model** | DBU-based pricing ($0.07–$0.55/DBU); serverless option | Self-hosted compute; cost = infrastructure only |
| **Concurrency** | Multi-cluster autoscaling; SQL Warehouses | Per-query resource allocation; no native queuing |
| **Security** | Unity Catalog enforcement at compute layer | Read-only enforcement via 28-keyword denylist |

**Key Architectural Differences:**

| Aspect | Databricks | Voyant |
|--------|-----------|--------|
| Compute-storage coupling | Tightly coupled via Delta/Unity | Fully decoupled (Trino + Iceberg + MinIO) |
| Serverless capability | Instant-start SQL Warehouses | Requires pre-provisioned Trino cluster |
| Write capability | Full DML (INSERT/UPDATE/DELETE/MERGE) | Read-only (SELECT/WITH/SHOW/DESCRIBE/EXPLAIN) |
| Multi-language | Python/Scala/SQL/R/Java | SQL-only through API; Python for workflows |
| Cost transparency | Opaque DBU pricing | Infrastructure-only cost (open source) |

### 2.2 Storage: Databricks Delta Lake vs Voyant Iceberg

| Feature | Delta Lake (Databricks) | Apache Iceberg (Voyant) |
|---------|------------------------|------------------------|
| **ACID Transactions** | Full ACID via transaction log | Full ACID via manifest files |
| **Time Travel** | `VERSION AS OF`, `TIMESTAMP AS OF` | Snapshot-based time travel via REST catalog |
| **Schema Evolution** | Add/rename columns; type widening | Full schema evolution with field IDs |
| **Partition Evolution** | Partition evolution supported | Partition evolution with hidden partitioning |
| **Data Layout** | Z-ordering, liquid clustering | Sort orders, partition transforms |
| **Format** | Parquet + transaction log JSON | Parquet/ORC/Avro + manifest files |
| **Catalog** | Unity Catalog (proprietary) | REST Catalog (open standard) |
| **Multi-Engine** | Databricks-native; limited interop | Trino, Spark, Flink, Hive, Presto all supported |
| **Vendor Lock-in** | Tightly coupled to Databricks runtime | Fully open; any Iceberg-compatible engine |
| **Snapshot Management** | VACUUM command; configurable retention | REST catalog API; explicit snapshot operations |
| **Row-Level Deletes** | DELETE via Delta log | Position delete files, copy-on-write, merge-on-read |
| **Table Maintenance** | OPTIMIZE, Z-ORDER, VACUUM | Compaction, snapshot expiration (via catalog API) |
| **Metadata Layer** | Transaction log (JSON) + checkpointing | Metadata file chain (JSON) + manifest lists |

**Voyant Iceberg Client Capabilities (Implemented):**

| Operation | Status | REST API |
|-----------|--------|----------|
| List namespaces | ✅ Done | `GET /v1/namespaces` |
| List tables | ✅ Done | `GET /v1/namespaces/{ns}/tables` |
| Get table metadata | ✅ Done | `GET /v1/namespaces/{ns}/tables/{t}` |
| Get snapshots | ✅ Done | From table metadata |
| Create namespace | ✅ Done | `POST /v1/namespaces` |
| Drop table | ✅ Done | `DELETE /v1/namespaces/{ns}/tables/{t}` |
| Health check | ✅ Done | `GET /v1/config` |
| Create table | ❌ Missing | `POST /v1/namespaces/{ns}/tables` |
| Update table schema | ❌ Missing | `POST /v1/namespaces/{ns}/tables/{t}` |
| Commit snapshots | ❌ Missing | `POST /v1/namespaces/{ns}/tables/{t}/transactions` |

### 2.3 Catalog: Databricks Unity Catalog vs Voyant Discovery + Governance

| Feature | Unity Catalog | Voyant Discovery + Governance |
|---------|--------------|-------------------------------|
| **Scope** | Tables, files, ML models, notebooks | Sources, services, APIs |
| **Metastore** | 3-level hierarchy: metastore → catalog → schema → table | Database models: Source, ServiceDefinition |
| **RBAC** | GRANT/REVOKE at any level | SpiceDB + Keycloak (global RBAC) |
| **Data Lineage** | Built-in column-level lineage | DataHub client integration |
| **Auditing** | System tables with full audit trail | AuditLog model |
| **Data Discovery** | Built-in search, tags, descriptions | DiscoveryRepo (in-memory); DataHub |
| **External Locations** | Managed storage credentials | Source connection_config + credentials |
| **Data Sharing** | Delta Sharing protocol | Not implemented |
| **API Access** | REST API, SDKs | REST API (Django Ninja) |
| **Openness** | Proprietary (Databricks-only) | Open source, self-hosted |

### 2.4 Data Engineering: Databricks Lakeflow DLT vs Voyant Temporal Workflows

| Feature | Lakeflow Declarative Pipelines (DLT) | Voyant Temporal Workflows |
|---------|--------------------------------------|---------------------------|
| **Programming Model** | Declarative (Python/SQL `@dlt.table`) | Imperative Python (Temporal SDK) |
| **Pipeline Definition** | Auto-DAG from table dependencies | Manual step sequencing |
| **Incremental Processing** | Auto CDC with `APPLY CHANGES` | Manual incremental mode in IngestParams |
| **Quality Expectations** | `@dlt.expect_all()`, `@dlt.expect_or_drop()` | Contract validation activity |
| **Orchestration** | Managed by Databricks | Self-hosted Temporal Server |
| **Monitoring** | Pipeline event log, data quality dashboard | Temporal UI + IngestionJob model |
| **Idempotency** | Framework-managed | Activity-level idempotency |
| **Retry/Recovery** | Automatic per-table retry | Configurable RetryPolicy per activity |
| **Scheduling** | Built-in triggers (file, time, manual) | Temporal schedules, cron triggers |
| **Cost** | Databricks compute (DBU) | Self-hosted workers (infrastructure cost) |
| **Multi-Step** | Auto-resolved from dependencies | Explicit 3-step pipeline (validate → ingest → lineage) |
| **Streaming** | Continuous mode | Streaming via Flink (stub) |

### 2.5 Streaming: Databricks Structured Streaming vs Voyant Flink Stub

| Feature | Databricks Structured Streaming | Voyant Flink (Current) |
|---------|-------------------------------|----------------------|
| **Maturity** | Production-grade since 2016 | Stub (362 LOC) |
| **Engine** | Spark Structured Streaming | Apache Flink REST API |
| **Processing Model** | Micro-batch + continuous | Not implemented (REST client only) |
| **Exactly-Once** | Checkpointing + WAL | Not implemented |
| **State Management** | RocksDB state store | Not implemented |
| **Window Support** | Tumbling, sliding, session windows | Not implemented |
| **Watermarks** | Event-time watermarks | Not implemented |
| **Sources** | Kafka, Delta, Kinesis, files | Not implemented |
| **Sinks** | Kafka, Delta, JDBC, console | Not implemented |
| **CDC** | Auto CDC with APPLY CHANGES | Not implemented |
| **Monitoring** | Streaming metrics, progress tracking | Flink REST API `get_overview` |

**Current Voyant Flink Implementation (What Exists):**
- `FlinkClient`: REST API client for Flink JobManager (overview, list jobs, submit JAR, upload JAR).
- `StreamingActivities`: Temporal activities wrapping Flink operations.
- `StreamingJobWorkflow`: Temporal workflow for health check → job submission.
- No actual streaming logic (Flink SQL, windowing, CDC, state management).

### 2.6 NL BI: Databricks Genie vs Voyant Intent Engine

| Feature | Databricks Genie | Voyant Intent Engine (Planned) |
|---------|-----------------|-------------------------------|
| **Approach** | NL → SQL via Unity Catalog context | NL → SQL via Intent Engine + MCP tools |
| **Context** | Table schemas, sample data, descriptions | Source schemas, Trino metadata, ontology |
| **LLM Backend** | Databricks-hosted models | External LLM (configurable) |
| **Verification** | Human-in-the-loop approval | Confidence scoring + human override |
| **Data Access** | Unity Catalog permissions | RBAC + read-only Trino enforcement |
| **Follow-up** | Conversational follow-up queries | Not yet implemented |
| **Visualization** | Auto-generated charts | KPI + chart generation in AnalyzeWorkflow |
| **API Access** | Genie API | Intent Engine API (planned) |

---

## 3. Palantir Comparison (Deep)

### 3.1 Pipeline Builder: Palantir vs Voyant Pipeline (Planned)

| Feature | Palantir Pipeline Builder | Voyant Pipeline (Planned) |
|---------|--------------------------|--------------------------|
| **Visual Editor** | Drag-and-drop DAG builder | React Flow DAG editor (Phase 4) |
| **Transformations** | 200+ built-in transforms | Custom Python transforms |
| **Language Support** | Python, Spark SQL, Java | Python |
| **Incremental** | Auto-incremental with watermarking | Manual via `mode=incremental` |
| **Connectors** | 200+ (native) | Airbyte client (300+ via Airbyte) |
| **Quality** | Data expectations framework | Great Expectations integration |
| **Scheduling** | Visual scheduling with dependencies | Temporal cron triggers |
| **Parameters** | Pipeline parameters with defaults | Not yet implemented |
| **Subgraphs** | Reusable pipeline blocks | Not yet implemented |
| **Streaming** | Flink-backed streaming pipelines | Flink client stub |
| **Monitoring** | Real-time pipeline health dashboard | Temporal UI + job status API |
| **Dataset Branching** | Git-like dataset branches | Not implemented |
| **LLM Transforms** | AI-powered data transformations | Not implemented |
| **Geospatial** | Native geospatial transforms | Not implemented |

### 3.2 SQL Studio: Palantir vs Voyant SQL Console

| Feature | Palantir SQL Studio | Voyant SQL Console |
|---------|--------------------|--------------------|
| **Query Editor** | Full IDE with autocomplete | REST API only (frontend planned) |
| **Query Engine** | Palantir compute | Trino (read-only) |
| **Result Limit** | Configurable | 1000 default, max 10,000 |
| **Schema Browser** | Visual schema tree | `GET /tables` + `GET /tables/{t}/columns` |
| **Query History** | Persistent query history | Not implemented |
| **Saved Queries** | Shared query library | Not implemented |
| **Export** | CSV, Parquet export | Not implemented |
| **Visualization** | Auto-chart from results | Via AnalyzeWorkflow generators |
| **Collaboration** | Shared queries, comments | Not implemented |
| **Write Access** | Full DML on managed datasets | **Read-only** (28 forbidden keywords) |
| **Performance** | Result caching, materialized views | No caching |
| **Security** | Row/column-level security in query | Tenant isolation via Trino config |

### 3.3 Data Lineage: Palantir vs Voyant DataHub Lineage

| Feature | Palantir Data Lineage | Voyant DataHub Lineage |
|---------|----------------------|----------------------|
| **Granularity** | Column-level lineage | Dataset-level lineage |
| **Tracking** | Automatic from pipeline transforms | Manual recording via `record_lineage_activity` |
| **Visualization** | Graph-based lineage explorer | DataHub UI (external) |
| **Impact Analysis** | Downstream impact calculation | Via DataHub |
| **Governance** | Integrated with access policies | Linked via `datahub_urn` on Source model |
| **Storage** | Built-in lineage store | DataHub (external service) |
| **Real-time** | Lineage updated per pipeline run | Batch recording after ingestion |
| **API** | Lineage API integrated with OSDK | DataHub REST/GraphQL API |
| **Audit** | Full lineage history with timestamps | DataHub versioning |

---

## 4. Improvements Over Both

### 4.1 Agent-First Data Operations

Voyant's defining advantage: **every data operation is an MCP tool** that AI agents can invoke directly.

| Data Operation | MCP Tool | Databricks Equivalent | Palantir Equivalent |
|---------------|----------|----------------------|---------------------|
| SQL query execution | `execute_sql` | ❌ No MCP | ❌ No MCP |
| Semantic search | `search_query` | ❌ No MCP | ❌ No MCP |
| Source discovery | `discover_source` | ❌ No MCP | ❌ No MCP |
| Ingestion trigger | `trigger_ingestion` | ❌ No MCP | ❌ No MCP |
| Table metadata | `list_tables`, `get_columns` | ❌ No MCP | ❌ No MCP |
| Data quality check | `run_quality_check` | ❌ No MCP | ❌ No MCP |
| Service registration | `register_service` | ❌ No MCP | ❌ No MCP |
| **Total MCP tools** | **46 (current) → 80+ (v4.0)** | **0** | **0** |

**Why This Matters:**
- AI agents can autonomously explore, query, ingest, and analyze data.
- No human-in-the-loop needed for routine data operations.
- Agent workflows compose MCP tools into multi-step pipelines.
- Natural language → MCP tool chain → SQL → results.

### 4.2 Intent-Driven Queries

**Voyant's NL→SQL Pipeline (Planned):**

```
Natural Language Query
  → Intent Engine (classify: SQL / search / action)
  → Schema-aware SQL generation (Trino metadata as context)
  → Read-only validation (28-keyword denylist)
  → Trino execution
  → Result formatting
  → KPI/chart generation (AnalyzeWorkflow)
  → Narrative summary
```

| Step | Databricks Genie | Palantir AIP | Voyant Intent Engine |
|------|-----------------|--------------|---------------------|
| NL Parsing | Unity Catalog context | Ontology context | Trino schema + Source metadata |
| SQL Generation | Proprietary LLM | Proprietary LLM | Configurable external LLM |
| Safety Layer | Unity Catalog permissions | Object security policies | 28-keyword denylist + RBAC |
| Execution | Databricks SQL | Palantir compute | Trino (read-only) |
| Visualization | Auto-chart | Workshop widgets | AnalyzeWorkflow generators |
| Agent Integration | ❌ No agent protocol | ❌ No agent protocol | ✅ MCP tools (agent-native) |

### 4.3 Temporal Durability: Every Ingestion Is Replayable

**Voyant's Unique Architecture:**

| Property | Description | Databricks | Palantir |
|----------|-------------|-----------|----------|
| **Workflow Durability** | Every ingestion is a Temporal workflow with guaranteed completion | Managed by Databricks | Managed by Palantir |
| **Replayability** | Any workflow can be replayed from scratch | Not possible | Not possible |
| **Auditability** | Full workflow history in Temporal UI | Pipeline event log | Pipeline monitoring |
| **Idempotency** | Activity-level idempotency guarantees | Framework-managed | Framework-managed |
| **Failure Recovery** | Automatic retry with exponential backoff | Automatic | Automatic |
| **Observability** | Workflow graph + activity logs | Pipeline UI | Pipeline UI |
| **Cross-Service** | Workflows span Django, Airbyte, Trino, Kafka, Flink | Databricks-only | Palantir-only |

**Voyant Workflow Stack:**

```
┌─────────────────────────────────────────────────────────┐
│                     Temporal Server                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ Ingest   │ │ Profile  │ │ Quality  │ │ Analyze  │   │
│  │ Workflow │ │ Workflow │ │ Workflow │ │ Workflow │   │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │
│       │             │            │             │         │
│  ┌────┴─────┐ ┌────┴─────┐ ┌───┴──────┐ ┌───┴──────┐  │
│  │ Validate │ │ Profile  │ │ Fetch    │ │ Profile  │  │
│  │ Contract │ │ Data     │ │ Sample   │ │ + KPIs   │  │
│  │ Ingest   │ │          │ │ Run      │ │ Analyzers│  │
│  │ Lineage  │ │          │ │ Quality  │ │ Generators│ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 4.4 Self-Hosted Iceberg: No Vendor Lock-in

| Aspect | Databricks Delta | Voyant Iceberg |
|--------|-----------------|---------------|
| **Hosting** | Databricks-managed (cloud-only) | Self-hosted Docker (any infra) |
| **Storage** | Cloud storage (S3/ADLS/GCS) | MinIO (S3-compatible) or any S3 |
| **Catalog** | Unity Catalog (proprietary) | Iceberg REST Catalog (open standard) |
| **Query Engine** | Databricks Photon/Spark | Trino (open source) |
| **Format** | Delta (proprietary log format) | Iceberg (open standard) |
| **Portability** | Locked to Databricks runtime | Any Iceberg-compatible engine |
| **Cost** | DBU-based pricing | Infrastructure only |
| **Data Governance** | Unity Catalog | SpiceDB + Keycloak + DataHub |
| **Multi-Engine** | Databricks-only | Trino + Spark + Flink + Hive |
| **Vendor Risk** | Single vendor dependency | No vendor dependency |

---

## 5. Complete API Design (v4.0)

### 5.1 Ingestion API

| Method | Endpoint | Auth | MCP Tool | Description |
|--------|----------|------|----------|-------------|
| `POST` | `/api/v1/ingestion/connect` | `write:sources` | `connect_source` | Provision Airbyte source connector |
| `POST` | `/api/v1/ingestion/provision-destination` | `write:sources` | `provision_destination` | Provision Airbyte destination |
| `POST` | `/api/v1/ingestion/jobs` | `write:sources` | `trigger_ingestion` | **NEW:** Start ingestion job |
| `GET` | `/api/v1/ingestion/jobs` | `read:*` | `list_ingestion_jobs` | **NEW:** List ingestion jobs |
| `GET` | `/api/v1/ingestion/jobs/{job_id}` | `read:*` | `get_ingestion_job` | **NEW:** Get job status |
| `POST` | `/api/v1/ingestion/jobs/{job_id}/cancel` | `write:sources` | `cancel_ingestion_job` | **NEW:** Cancel running job |
| `GET` | `/api/v1/ingestion/jobs/{job_id}/logs` | `read:*` | — | **NEW:** Get job execution logs |

### 5.2 SQL API

| Method | Endpoint | Auth | MCP Tool | Description |
|--------|----------|------|----------|-------------|
| `POST` | `/api/v1/sql/query` | `execute:sql` | `execute_sql` | Execute read-only SQL |
| `GET` | `/api/v1/sql/tables` | `execute:sql` | `list_tables` | List available tables |
| `GET` | `/api/v1/sql/tables/{table}/columns` | `execute:sql` | `get_columns` | Get table columns |
| `POST` | `/api/v1/sql/explain` | `execute:sql` | `explain_query` | **NEW:** Explain query plan |
| `GET` | `/api/v1/sql/history` | `read:*` | — | **NEW:** Query execution history |
| `POST` | `/api/v1/sql/save` | `write:sql` | `save_query` | **NEW:** Save named query |

### 5.3 Search API

| Method | Endpoint | Auth | MCP Tool | Description |
|--------|----------|------|----------|-------------|
| `POST` | `/api/v1/search/query` | `read:*` | `search_query` | Semantic search (hybrid dense+sparse) |
| `POST` | `/api/v1/search/index` | `write:documents` | `index_document` | Index text for search |
| `DELETE` | `/api/v1/search/{item_id}` | `write:documents` | `delete_document` | Delete indexed item |
| `GET` | `/api/v1/search/{item_id}` | `read:*` | `get_document` | Get indexed item |
| `POST` | `/api/v1/search/bulk-index` | `write:documents` | `bulk_index` | **NEW:** Bulk index items |
| `POST` | `/api/v1/search/reindex` | `write:documents` | — | **NEW:** Reindex collection |

### 5.4 Sources/Discovery API

| Method | Endpoint | Auth | MCP Tool | Description |
|--------|----------|------|----------|-------------|
| `POST` | `/api/v1/sources/discover` | `read:*` | `discover_source` | Detect source type |
| `POST` | `/api/v1/sources` | `write:sources` | `create_source` | Create source |
| `GET` | `/api/v1/sources` | `read:*` | `list_sources` | List sources |
| `GET` | `/api/v1/sources/{source_id}` | `read:*` | `get_source` | Get source |
| `PUT` | `/api/v1/sources/{source_id}` | `write:sources` | `update_source` | Update source |
| `DELETE` | `/api/v1/sources/{source_id}` | `write:sources` | `delete_source` | Delete source |
| `POST` | `/api/v1/sources/{source_id}/test` | `read:*` | `test_connection` | **NEW:** Test source connectivity |
| `GET` | `/api/v1/sources/{source_id}/schema` | `read:*` | `get_source_schema` | **NEW:** Get source schema |
| `POST` | `/api/v1/discovery/services` | `write:sources` | `register_service` | Register external service |
| `GET` | `/api/v1/discovery/services` | `read:*` | `list_services` | List services |
| `GET` | `/api/v1/discovery/services/{name}` | `read:*` | `get_service` | Get service |
| `POST` | `/api/v1/discovery/scan` | `write:sources` | `scan_spec` | Scan OpenAPI spec |

### 5.5 Streaming API (v4.0 Planned)

| Method | Endpoint | Auth | MCP Tool | Description |
|--------|----------|------|----------|-------------|
| `GET` | `/api/v1/streaming/overview` | `read:*` | `get_cluster_overview` | Flink cluster status |
| `GET` | `/api/v1/streaming/jobs` | `read:*` | `list_streaming_jobs` | List running Flink jobs |
| `POST` | `/api/v1/streaming/jobs` | `write:streaming` | `submit_streaming_job` | Submit streaming job |
| `DELETE` | `/api/v1/streaming/jobs/{job_id}` | `write:streaming` | `cancel_streaming_job` | Cancel streaming job |
| `GET` | `/api/v1/streaming/jobs/{job_id}` | `read:*` | `get_streaming_job` | Get job details |

### 5.6 Iceberg API (v4.0 Planned)

| Method | Endpoint | Auth | MCP Tool | Description |
|--------|----------|------|----------|-------------|
| `GET` | `/api/v1/iceberg/namespaces` | `read:*` | `list_namespaces` | List namespaces |
| `POST` | `/api/v1/iceberg/namespaces` | `write:iceberg` | `create_namespace` | Create namespace |
| `GET` | `/api/v1/iceberg/namespaces/{ns}/tables` | `read:*` | `list_iceberg_tables` | List tables |
| `GET` | `/api/v1/iceberg/namespaces/{ns}/tables/{t}` | `read:*` | `get_iceberg_table` | Get table metadata |
| `GET` | `/api/v1/iceberg/namespaces/{ns}/tables/{t}/snapshots` | `read:*` | `get_table_snapshots` | Get table snapshots |
| `DELETE` | `/api/v1/iceberg/namespaces/{ns}/tables/{t}` | `write:iceberg` | `drop_iceberg_table` | Drop table |

### 5.7 Data Quality API (v4.0 Planned)

| Method | Endpoint | Auth | MCP Tool | Description |
|--------|----------|------|----------|-------------|
| `POST` | `/api/v1/quality/check` | `read:*` | `run_quality_check` | Run quality checks on table |
| `GET` | `/api/v1/quality/results/{source_id}` | `read:*` | `get_quality_results` | Get quality results |
| `POST` | `/api/v1/quality/rules` | `write:quality` | `create_quality_rule` | Define quality rule |
| `GET` | `/api/v1/quality/rules` | `read:*` | `list_quality_rules` | List quality rules |
| `GET` | `/api/v1/quality/alerts` | `read:*` | `get_quality_alerts` | Get quality alerts |

### 5.8 Pipeline API (v4.0 Planned)

| Method | Endpoint | Auth | MCP Tool | Description |
|--------|----------|------|----------|-------------|
| `POST` | `/api/v1/pipelines` | `write:pipelines` | `create_pipeline` | Create pipeline |
| `GET` | `/api/v1/pipelines` | `read:*` | `list_pipelines` | List pipelines |
| `GET` | `/api/v1/pipelines/{id}` | `read:*` | `get_pipeline` | Get pipeline |
| `PUT` | `/api/v1/pipelines/{id}` | `write:pipelines` | `update_pipeline` | Update pipeline |
| `POST` | `/api/v1/pipelines/{id}/run` | `write:pipelines` | `run_pipeline` | Trigger pipeline run |
| `GET` | `/api/v1/pipelines/{id}/runs` | `read:*` | `get_pipeline_runs` | Get pipeline run history |

---

## 6. Streaming Architecture

### 6.1 Current State vs Target

| Component | v3.0 Status | v4.0 Target |
|-----------|-------------|-------------|
| Flink Client | REST API wrapper (95 LOC) | Full Flink SQL client |
| Streaming Activities | 3 Temporal activities | 8+ activities |
| Streaming Workflow | Health check → submit | Full lifecycle management |
| Kafka Producer | Fully implemented | Add consumer support |
| Event Schema | 7 canonical schemas | 20+ schemas |
| Flink SQL | Not implemented | Flink SQL DDL/DML |
| Windowing | Not implemented | Tumbling, sliding, session |
| CDC | Not implemented | Debezium → Flink CDC |
| State Management | Not implemented | RocksDB state backend |
| Exactly-Once | Not implemented | Checkpointing + Kafka transactions |

### 6.2 Full Streaming Architecture (v4.0 Design)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Data Sources                              │
│  PostgreSQL  MySQL  MongoDB  S3  APIs  Files  Scrapers           │
└──────────┬──────────────────────────────────────┬───────────────┘
           │                                      │
           ▼                                      ▼
┌──────────────────┐                    ┌──────────────────┐
│  Airbyte         │                    │  Debezium CDC    │
│  Batch Sync      │                    │  Change Capture  │
└──────────┬───────┘                    └──────────┬───────┘
           │                                      │
           ▼                                      ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Apache Kafka                                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐    │
│  │voyant.raw  │ │voyant.cdc  │ │voyant.jobs │ │voyant.qual │    │
│  │(raw data)  │ │(changes)   │ │(lifecycle) │ │(quality)   │    │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘    │
└──────────┬──────────────────────────────────────┬────────────────┘
           │                                      │
           ▼                                      ▼
┌──────────────────┐                    ┌──────────────────┐
│  Trino Batch     │                    │  Flink Streaming │
│  (SQL queries)   │                    │  ┌────────────┐  │
│                  │                    │  │ Tumbling   │  │
│  - SELECT        │                    │  │ Sliding    │  │
│  - Aggregations  │                    │  │ Session    │  │
│  - Joins         │                    │  │ CDC        │  │
│                  │                    │  └────────────┘  │
└──────────┬───────┘                    └──────────┬───────┘
           │                                      │
           ▼                                      ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Apache Iceberg Tables                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ Raw tables   │ │ Aggregated   │ │ Materialized views       │ │
│  │ (full load)  │ │ (streaming)  │ │ (pre-computed KPIs)      │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Milvus Vector Store                             │
│  Semantic search over indexed data, documents, metadata          │
└──────────────────────────────────────────────────────────────────┘
```

### 6.3 Kafka Topic Design (v4.0)

| Topic | Partitions | Retention | Key | Description |
|-------|-----------|-----------|-----|-------------|
| `voyant.raw.ingestion` | 12 | 7 days | `source_id` | Raw ingested data events |
| `voyant.cdc.changes` | 12 | 3 days | `table_name` | Debezium CDC change events |
| `voyant.jobs.lifecycle` | 6 | 30 days | `tenant_id` | Job started/completed/failed |
| `voyant.quality.alerts` | 6 | 30 days | `tenant_id` | Quality threshold breaches |
| `voyant.lineage.updates` | 6 | 90 days | `dataset_urn` | Lineage graph updates |
| `voyant.audit.events` | 12 | 365 days | `tenant_id` | Audit trail events |
| `voyant.ml.experiments` | 3 | 30 days | `experiment_id` | ML experiment events |
| `voyant.intent.queries` | 3 | 7 days | `tenant_id` | Intent engine query logs |
| `voyant.governance.policies` | 3 | 90 days | `tenant_id` | Policy evaluation events |
| `voyant.stream.kpi` | 12 | 1 day | `metric_name` | Real-time KPI aggregation results |
| `voyant.stream.anomalies` | 6 | 7 days | `source_id` | Streaming anomaly detection alerts |

### 6.4 Event Schema (v4.0 Expansion)

**Current Canonical Schemas (7):**

| Schema | Version | Status |
|--------|---------|--------|
| `job.started` | 1.0.0 | ✅ Registered |
| `job.completed` | 1.0.0 | ✅ Registered |
| `job.failed` | 1.0.0 | ✅ Registered |
| `artifact.created` | 1.0.0 | ✅ Registered |
| `data.ingested` | 1.0.0 | ✅ Registered |
| `data.drift_detected` | 1.0.0 | ✅ Registered |
| `quota.warning` | 1.0.0 | ✅ Registered |

**New Schemas for v4.0 (13 additional):**

| Schema | Version | Key Fields | Topic |
|--------|---------|------------|-------|
| `pipeline.started` | 1.0.0 | `pipeline_id`, `tenant_id`, `run_id` | `voyant.jobs.lifecycle` |
| `pipeline.completed` | 1.0.0 | `pipeline_id`, `duration_seconds`, `rows_processed` | `voyant.jobs.lifecycle` |
| `pipeline.failed` | 1.0.0 | `pipeline_id`, `error_code`, `failed_step` | `voyant.jobs.lifecycle` |
| `streaming.job_submitted` | 1.0.0 | `flink_job_id`, `job_type`, `parallelism` | `voyant.jobs.lifecycle` |
| `streaming.anomaly_detected` | 1.0.0 | `metric`, `value`, `threshold`, `source_id` | `voyant.stream.anomalies` |
| `streaming.kpi_updated` | 1.0.0 | `kpi_name`, `value`, `window_start`, `window_end` | `voyant.stream.kpi` |
| `quality.check_completed` | 1.0.0 | `source_id`, `score`, `passed_checks`, `failed_checks` | `voyant.quality.alerts` |
| `quality.rule_violated` | 1.0.0 | `rule_id`, `table`, `column`, `violation_count` | `voyant.quality.alerts` |
| `lineage.updated` | 1.0.0 | `dataset_urn`, `upstream`, `downstream`, `operation` | `voyant.lineage.updates` |
| `lineage.impact_detected` | 1.0.0 | `source_urn`, `affected_datasets`, `change_type` | `voyant.lineage.updates` |
| `iceberg.schema_evolved` | 1.0.0 | `namespace`, `table`, `changes`, `snapshot_id` | `voyant.audit.events` |
| `intent.query_executed` | 1.0.0 | `intent`, `generated_sql`, `confidence`, `row_count` | `voyant.intent.queries` |
| `governance.policy_evaluated` | 1.0.0 | `policy_id`, `decision`, `resource`, `principal` | `voyant.governance.policies` |

### 6.5 Flink Streaming Pipeline Design (v4.0)

#### 6.5.1 Flink SQL Pipeline Template

```sql
-- Real-time KPI Aggregation Pipeline
CREATE TABLE kafka_source (
    event_time TIMESTAMP(3),
    source_id STRING,
    metric_name STRING,
    metric_value DOUBLE,
    WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'voyant.raw.ingestion',
    'properties.bootstrap.servers' = '${KAFKA_BOOTSTRAP_SERVERS}',
    'format' = 'json'
);

CREATE TABLE kpi_sink (
    window_start TIMESTAMP(3),
    window_end TIMESTAMP(3),
    metric_name STRING,
    avg_value DOUBLE,
    max_value DOUBLE,
    min_value DOUBLE,
    count BIGINT,
    PRIMARY KEY (metric_name, window_start) NOT ENFORCED
) WITH (
    'connector' = 'kafka',
    'topic' = 'voyant.stream.kpi',
    'format' = 'json'
);

INSERT INTO kpi_sink
SELECT
    TUMBLE_START(event_time, INTERVAL '1' MINUTE) AS window_start,
    TUMBLE_END(event_time, INTERVAL '1' MINUTE) AS window_end,
    metric_name,
    AVG(metric_value) AS avg_value,
    MAX(metric_value) AS max_value,
    MIN(metric_value) AS min_value,
    COUNT(*) AS count
FROM kafka_source
GROUP BY TUMBLE(event_time, INTERVAL '1' MINUTE), metric_name;
```

#### 6.5.2 New Temporal Activities (v4.0)

| Activity | Description |
|----------|-------------|
| `submit_flink_sql` | Submit Flink SQL job via REST API |
| `cancel_flink_job` | Cancel a running Flink job |
| `get_flink_job_status` | Get status of a specific Flink job |
| `get_flink_job_metrics` | Get metrics (throughput, latency, backpressure) |
| `savepoint_flink_job` | Trigger a savepoint for state snapshotting |
| `restore_flink_job` | Restore from a savepoint |
| `list_flink_jars` | List available JARs on the cluster |
| `deploy_flink_sql_jar` | Deploy a Flink SQL JAR with pipeline config |

#### 6.5.3 Extended StreamingJobWorkflow (v4.0)

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│ Validate     │───▶│ Health Check │───▶│ Deploy Pipeline │
│ Config       │    │ (Flink)      │    │ (SQL or JAR)    │
└─────────────┘    └──────────────┘    └────────┬────────┘
                                                │
                   ┌────────────────────────────┘
                   ▼
┌──────────────┐    ┌──────────────┐    ┌─────────────────┐
│ Monitor      │───▶│ Collect      │───▶│ Record Lineage  │
│ (heartbeat)  │    │ Metrics      │    │ & Emit Events   │
└──────────────┘    └──────────────┘    └─────────────────┘
```

---

## 7. Event-Driven Architecture

### 7.1 Current Event Flow

```
Application Code
    │
    ├── emit_job_event()     → KafkaProducer.emit("jobs", VoyantEvent)
    ├── emit_quality_alert() → KafkaProducer.emit("quality", VoyantEvent)
    ├── emit_ontology_event() → KafkaProducer.emit("ontology", VoyantEvent)
    ├── emit_ml_event()      → KafkaProducer.emit("ml", VoyantEvent)
    ├── emit_intent_event()  → KafkaProducer.emit("intent", VoyantEvent)
    ├── emit_governance_event() → KafkaProducer.emit("governance", VoyantEvent)
    └── emit_scraper_event() → KafkaProducer.emit("scraper", VoyantEvent)
         │
         ▼
    ┌──────────────┐     ┌──────────────────┐
    │ Kafka        │────▶│ Schema Registry  │
    │ Producer     │     │ (validate_event) │
    └──────────────┘     └──────────────────┘
         │
         ▼
    ┌──────────────┐
    │ Kafka Broker │
    │ Topics:      │
    │ - voyant.jobs│
    │ - voyant.qual│
    │ - voyant.line│
    │ - voyant.aud │
    └──────────────┘
```

### 7.2 Proposed v4.0 Event Flow

```
┌─────────────────────── Data Plane ───────────────────────┐
│                                                           │
│  Airbyte Sync ──▶ Kafka ──▶ Flink ──▶ Iceberg           │
│  Debezium CDC ──▶ Kafka ──▶ Flink ──▶ Iceberg + Milvus  │
│  Scrapers ──────▶ Kafka ──▶ Flink ──▶ Iceberg           │
│                                                           │
└───────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────── Event Bus ────────────────────────┐
│                                                           │
│  11 Kafka Topics (partitioned by tenant_id)              │
│  Schema Registry (in-memory, semver, JSON Schema)        │
│                                                           │
└───────────┬────────────────────┬─────────────────────────┘
            │                    │
            ▼                    ▼
┌───────────────────┐  ┌───────────────────┐
│ Consumers:        │  │ Consumers:        │
│ - Quality Worker  │  │ - Lineage Worker  │
│ - Alert Worker    │  │ - ML Pipeline     │
│ - Dashboard       │  │ - Search Indexer  │
└───────────────────┘  └───────────────────┘
```

---

## 8. Cross-Cutting Concerns

### 8.1 Multi-Tenancy

| Layer | Isolation Mechanism |
|-------|-------------------|
| Django Models | `TenantModel` mixin with `tenant_id` field |
| Trino | Separate schema/catalog per tenant |
| Milvus | Partition key on `tenant_id` field |
| Kafka | Message key = `tenant_id` |
| Redis Job Queue | Per-tenant sorted sets (`voyant:queue:{tenant_id}`) |
| Iceberg | Namespace per tenant (planned) |

### 8.2 Retry Policies

| Policy | Initial | Backoff | Max Interval | Max Attempts | Use Case |
|--------|---------|---------|-------------|-------------|----------|
| `EXTERNAL_SERVICE_RETRY` | 1s | 2.0x | 60s | 3 | Airbyte, Trino, external APIs |
| `DATA_PROCESSING_RETRY` | 2s | 2.0x | 120s | 2 | ML, quality checks, profiling |
| `NO_RETRY` | — | — | — | 1 | Idempotency-critical operations |

### 8.3 Timeout Budgets

| Activity | Timeout | Category |
|----------|---------|----------|
| Contract validation | 1 min | Governance |
| Data ingestion (small) | 10 min | Ingestion |
| Data ingestion (large/Airbyte) | 45 min | Ingestion |
| Data profiling | 15 min | Analysis |
| Quality check (sample) | 5 min | Quality |
| Quality check (run) | 10 min | Quality |
| Analyzer execution | 10 min | Analysis |
| KPI calculation | 10 min | Analysis |
| Chart generation | 10 min | Analysis |
| Flink cluster overview | 30 sec | Streaming |
| Flink job submission | 5 min | Streaming |

### 8.4 Security Model

| Component | Security Layer |
|-----------|---------------|
| API Authentication | Keycloak JWT tokens |
| Authorization | SpiceDB RBAC (permissions: `read:*`, `write:sources`, `execute:sql`, etc.) |
| SQL Injection | 3-layer validation (semicolon, prefix allowlist, 28-keyword denylist) |
| Identifier Injection | Regex `^[A-Za-z_][A-Za-z0-9_]*$` enforcement |
| Tenant Isolation | TenantModel mixin + middleware extraction |
| Search Isolation | `tenant_id` filter injected into every Milvus query |
| Credential Storage | HashiCorp Vault integration |
| Event Schema | Pre-emit validation against registered schemas |
| Input Length | 10,000 char limit on embeddings, 100,000 on index text |

---

## 9. Connector Framework (Deep Specification)

*Sourced from Deep-Dive Module & Function Spec §2.2.1*

Every connector in Voyant SHALL implement the `IConnector` interface. This provides a uniform abstraction over all data sources — relational, NoSQL, cloud storage, streaming, APIs, and files.

### 9.1 IConnector Interface (8 Methods)

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONNECTOR FRAMEWORK                           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  IConnector Interface                                    │   │
│  │                                                          │   │
│  │  + discover_schema()        → SchemaDescriptor           │   │
│  │  + discover_datasets()      → List<DatasetDescriptor>    │   │
│  │  + test_connection()        → ConnectionTestResult       │   │
│  │  + create_reader(config)    → IDataReader                │   │
│  │  + create_writer(config)    → IDataWriter                │   │
│  │  + create_stream(config)    → IStreamReader              │   │
│  │  + get_capabilities()       → ConnectorCapabilities      │   │
│  │  + get_health()             → HealthStatus               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  IDataReader Interface                                   │   │
│  │                                                          │   │
│  │  + read_batch(config)       → Iterator<RecordBatch>      │   │
│  │  + read_incremental(        → Iterator<RecordBatch>      │   │
│  │      watermark, config)                                  │   │
│  │  + read_cdc(config)         → Iterator<ChangeEvent>      │   │
│  │  + get_row_count()          → Long                       │   │
│  │  + estimate_size()          → Long (bytes)               │   │
│  │  + close()                  → void                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  IStreamReader Interface                                 │   │
│  │                                                          │   │
│  │  + subscribe(config)        → Flux<StreamRecord>         │   │
│  │  + commit_offset(offset)    → void                       │   │
│  │  + seek_to(offset)          → void                       │   │
│  │  + get_lag()                → Long                       │   │
│  │  + pause() / resume()       → void                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  ConnectorCapabilities                                   │   │
│  │                                                          │   │
│  │  supports_batch_read:       Boolean                      │   │
│  │  supports_incremental:      Boolean                      │   │
│  │  supports_cdc:              Boolean                      │   │
│  │  supports_streaming:        Boolean                      │   │
│  │  supports_write_back:       Boolean                      │   │
│  │  supports_schema_discovery: Boolean                      │   │
│  │  supports_predicate_pushdown: Boolean                    │   │
│  │  supports_projection_pushdown: Boolean                   │   │
│  │  max_parallelism:           Integer                      │   │
│  │  supported_formats:         List<DataFormat>             │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 Method Descriptions

| Method | Return Type | Description |
|--------|------------|-------------|
| `discover_schema()` | `SchemaDescriptor` | Introspects the source and returns the full schema (tables, columns, types, constraints) |
| `discover_datasets()` | `List<DatasetDescriptor>` | Enumerates all available datasets/tables at the source |
| `test_connection()` | `ConnectionTestResult` | Validates connectivity, credentials, and permissions; returns pass/fail with latency |
| `create_reader(config)` | `IDataReader` | Creates a batch/incremental/CDC reader for the given config |
| `create_writer(config)` | `IDataWriter` | Creates a writer that can push data back to the source |
| `create_stream(config)` | `IStreamReader` | Creates a streaming reader for real-time data consumption |
| `get_capabilities()` | `ConnectorCapabilities` | Returns a bitmask of supported features (batch, CDC, streaming, etc.) |
| `get_health()` | `HealthStatus` | Returns current health status (healthy, degraded, down) with diagnostics |

---

## 10. Ingestion Validation Engine (Deep Specification)

*Sourced from Deep-Dive Module & Function Spec §2.2.4*

The Ingestion Validation Engine runs every incoming record through a configurable set of validation rules. Records that fail validation are routed to a quarantine dataset for review, not silently dropped.

### 10.1 Validation Rule Types (7 Types)

```
┌─────────────────────────────────────────────────────────────────┐
│                VALIDATION RULE TYPES                             │
│                                                                  │
│  Type: NOT_NULL                                                  │
│  Config: { "columns": ["id", "email"] }                         │
│  Action on fail: QUARANTINE row, log warning                     │
│                                                                  │
│  Type: DATA_TYPE                                                 │
│  Config: { "column": "age", "expected_type": "INTEGER",         │
│            "range": [0, 150] }                                  │
│  Action on fail: QUARANTINE row, log error                       │
│                                                                  │
│  Type: REGEX                                                     │
│  Config: { "column": "email", "pattern": "^[\\w.+-]+@[\\w.-]+  │
│            \\.[a-zA-Z]{2,}$" }                                  │
│  Action on fail: QUARANTINE row, log warning                     │
│                                                                  │
│  Type: REFERENTIAL                                               │
│  Config: { "source_column": "customer_id",                      │
│            "reference_dataset": "customers",                     │
│            "reference_column": "id" }                            │
│  Action on fail: QUARANTINE row, log error                       │
│                                                                  │
│  Type: UNIQUENESS                                                │
│  Config: { "columns": ["order_id"] }                            │
│  Action on fail: QUARANTINE duplicate, log warning               │
│                                                                  │
│  Type: CUSTOM_SQL                                                │
│  Config: { "expression": "amount > 0 AND currency IN ('USD',    │
│            'EUR', 'GBP')" }                                     │
│  Action on fail: QUARANTINE row, log warning                     │
│                                                                  │
│  Type: STATISTICAL                                               │
│  Config: { "column": "price", "method": "zscore",               │
│            "threshold": 3.0 }                                   │
│  Action on fail: FLAG row (not quarantine), log info             │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Quarantine Dataset Schema

Records that fail validation are stored in a dedicated quarantine dataset with full provenance:

| Column | Type | Description |
|--------|------|-------------|
| `_quarantine_id` | UUID | Primary key for the quarantine record |
| `_source_row` | JSONB | Full original row data (preserved for reprocessing) |
| `_rule_id` | UUID | Reference to the validation rule that caught the failure |
| `_rule_type` | VARCHAR | Rule type enum (NOT_NULL, DATA_TYPE, REGEX, etc.) |
| `_error_message` | TEXT | Human-readable description of the failure |
| `_quarantined_at` | TIMESTAMPTZ | When the record was quarantined |
| `_resolved` | BOOLEAN | Whether this record has been reviewed and resolved |
| `_resolved_by` | UUID | User who resolved the quarantine |
| `_resolved_at` | TIMESTAMPTZ | When the quarantine was resolved |

### 10.3 Quarantine Resolution Workflow

```
1. Review quarantined rows (filter by rule, source, date)
2. Fix row data or adjust rule
3. Re-process quarantined rows
4. Mark as resolved with notes
```

---

## 11. CDC Pipeline Architecture (Deep Specification)

*Sourced from Deep-Dive Module & Function Spec §2.2.3*

CDC (Change Data Capture) is supported as a first-class ingestion pattern. The CDC pipeline captures row-level changes from source databases and propagates them to the platform with sub-5-second latency.

```
┌─────────────────────────────────────────────────────────────────┐
│                    CDC PIPELINE ARCHITECTURE                      │
│                                                                  │
│  Source DB                                                        │
│  ┌──────────────────┐                                           │
│  │ WAL / Binlog /   │     ┌───────────────────┐                │
│  │ Change Stream    │────▶│ CDC Connector     │                │
│  │                  │     │ (Debezium engine)  │                │
│  └──────────────────┘     └────────┬──────────┘                │
│                                    │                             │
│                                    ▼                             │
│                         ┌───────────────────┐                   │
│                         │ Change Event Queue│                   │
│                         │ (Kafka topic)      │                   │
│                         └────────┬──────────┘                   │
│                                  │                               │
│                    ┌─────────────┼─────────────┐                 │
│                    ▼             ▼             ▼                 │
│            ┌───────────┐ ┌───────────┐ ┌───────────┐           │
│            │ Iceberg   │ │ Ontology  │ │ Downstream│           │
│            │ Table     │ │ Sync      │ │ Pipelines │           │
│            │ (append)  │ │ (real-time)│ │ (trigger) │           │
│            └───────────┘ └───────────┘ └───────────┘           │
│                                                                  │
│  Change Event Schema:                                            │
│  {                                                               │
│    "op": "c" | "u" | "d" | "r",  // create, update, delete, read│
│    "ts_ms": 1694234567890,                                       │
│    "source": { "db": "prod", "table": "orders", "lsn": 45231 },│
│    "before": { ... },         // null for inserts                │
│    "after": { ... },          // null for deletes                │
│    "transaction_id": "txn_abc123"                               │
│  }                                                               │
│                                                                  │
│  Guarantees:                                                     │
│  • At-least-once delivery (exactly-once at Iceberg level)        │
│  • Ordering guaranteed per source table (LSN/offset ordering)    │
│  • Latency: < 5 seconds from source commit to platform           │
│  • Schema change propagation: automatic for additive changes     │
└─────────────────────────────────────────────────────────────────┘
```

### 11.1 CDC Operation Types

| Operation | Code | Description | `before` | `after` |
|-----------|------|-------------|----------|---------|
| Create | `c` | New row inserted | `null` | Full row |
| Update | `u` | Existing row modified | Previous state | New state |
| Delete | `d` | Row removed | Full row | `null` |
| Read/Snapshot | `r` | Initial full table scan | `null` | Full row |

### 11.2 Supported CDC Sources

| Source | Mechanism | Connector |
|--------|-----------|-----------|
| PostgreSQL 14+ | Logical replication (pg_logical) | Debezium PostgreSQL connector |
| MySQL 8+ | Binlog | Debezium MySQL connector |
| MongoDB 6+ | Change Streams | Debezium MongoDB connector |
| DynamoDB | DynamoDB Streams | AWS-native connector |

---

**Created:** 2026-09-05
**Author:** Voyant Engineering
**Source:** Analysis of 12 source files across `apps/ingestion`, `apps/sql`, `apps/search`, `apps/streaming`, `apps/discovery`, `apps/core/lib`, `apps/worker/workflows`
**Next review:** 2026-09-19
