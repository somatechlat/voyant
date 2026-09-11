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
