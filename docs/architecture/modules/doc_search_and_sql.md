# Search and SQL Module

> **Source date**: 2026-09-04
> **Files examined**: `apps/search/`, `apps/sql/`

## Overview

The search and SQL module provides two data access surfaces:

1. **Search** (`apps/search/`) — Semantic search with hybrid dense+sparse vector embeddings stored in Milvus, with tenant isolation
2. **SQL** (`apps/sql/`) — Read-only SQL query execution via Trino, with full validation and identifier sanitization

---

## Search (`apps/search/`)

### Directory Structure

```
apps/search/
├── api.py          # REST API endpoints
├── apps.py         # Django app config
└── lib/
    ├── milvus_store.py   # Vector store (documented in doc_data_engines.md)
    └── embeddings.py     # Embedding extractors
```

### API (`api.py`, 345 lines)

#### Search Router (`/v1/search`)

| Method | Path | Auth | Response | Description |
|---|---|---|---|---|
| `POST` | `/query` | `read:*` | `list[SemanticSearchResult]` | Semantic search query |
| `POST` | `/index` | `write:documents` | `IndexResponse` | Index a new text item |
| `DELETE` | `/{item_id}` | `write:documents` | `{"status", "item_id"}` | Delete indexed item |
| `GET` | `/{item_id}` | `read:*` | `SemanticSearchResult` | Get item by ID |

### Schemas

#### `SearchQuery`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `query` | `str` | Required, 1–10,000 chars | Search query text |
| `limit` | `int` | 1–100, default 5 | Max results |
| `filters` | `dict \| None` | Optional | Metadata filters |

#### `SemanticSearchResult`

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Indexed item ID |
| `score` | `float` | Similarity score (0.0–1.0) |
| `metadata` | `dict` | Item metadata |

#### `IndexRequest`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `text` | `str` | Required, 1–100,000 chars | Text to index |
| `metadata` | `dict \| None` | Optional | Metadata |
| `item_id` | `str \| None` | Optional | Custom ID (auto UUID if absent) |

#### `IndexResponse`

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Assigned item ID |
| `status` | `str` | Status message |
| `dimensions` | `int` | Embedding dimensionality |

### Endpoint Details

#### `POST /query` — Semantic Search

1. Gets tenant ID from request context
2. Creates dense (1536d) and sparse embedding extractors
3. Extracts embeddings from query text
4. Adds `tenant_id` to filters for isolation
5. Performs hybrid search via `VectorStore.search()` (dense + sparse with weighted RRF)
6. Returns results ranked by similarity score (rounded to 6 decimals)

**Error handling**: 400 for invalid queries, 500 for search failures.

#### `POST /index` — Index Item

1. Gets tenant ID
2. Extracts dense + sparse embeddings
3. Generates UUID or uses provided `item_id`
4. Sets `tenant_id` and `text_preview` in metadata
5. Calls `VectorStore.add()` with upsert semantics

**Error handling**: 400 for invalid text or embedding failures, 500 for index failures.

#### `DELETE /{item_id}` — Delete Item

1. Gets tenant ID
2. Retrieves item and verifies ownership (`item.metadata.tenant_id == tenant_id`)
3. Returns 403 if tenant mismatch, 404 if not found
4. Deletes from vector store

#### `GET /{item_id}` — Get Item

1. Gets tenant ID
2. Retrieves item and verifies ownership
3. Returns 403 if tenant mismatch, 404 if not found
4. Returns with `score=1.0` (exact match)

### Embedding Pipeline

- **Dense**: `get_embedding_extractor(model="dense", dimensions=1536)` — 1536-dimensional embeddings
- **Sparse**: `get_sparse_embedder()` — Sparse vector embeddings
- Both extractors used in hybrid search for optimal retrieval quality

---

## SQL (`apps/sql/`)

### API (`api.py`, 122 lines)

#### SQL Router (`/v1/sql`)

| Method | Path | Auth | Response | Description |
|---|---|---|---|---|
| `POST` | `/query` | `execute:sql` (via `auth_guard`) | `SqlResponse` | Execute ad-hoc SQL query |
| `GET` | `/tables` | `execute:sql` (via `auth_guard`) | `{"tables", "schema"}` | List available tables |
| `GET` | `/tables/{table}/columns` | `execute:sql` (via `auth_guard`) | `{"table", "columns"}` | Get table column details |

### Schemas

#### `SqlRequest`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `sql` | `str` | Required | SQL query (only SELECT permitted) |
| `limit` | `int` | 1–10,000, default 1000 | Max rows |
| `parameters` | `dict \| None` | Optional | Parameterized query args |

#### `SqlResponse`

| Field | Type | Description |
|---|---|---|
| `columns` | `list[str]` | Column names |
| `rows` | `list[list[Any]]` | Result rows |
| `row_count` | `int` | Row count |
| `truncated` | `bool` | Whether results were truncated |
| `execution_time_ms` | `int` | Execution time |
| `query_id` | `str \| None` | Trino query ID |

### Endpoint Details

#### `POST /query` — Execute SQL

1. Gets Trino client singleton
2. Calls `client.execute(sql, limit, parameters)`
3. TrinoClient validates SQL (read-only enforcement, keyword denylist, multi-statement blocking)
4. Auto-wraps with `LIMIT` if not present

**Error handling**:
- 400 for `ValueError` (validation failures — forbidden SQL keywords, multi-statement, invalid query type)
- 503 for `RuntimeError` (missing Trino client library)
- 500 for all other exceptions

#### `GET /tables` — List Tables

Calls `TrinoClient.get_tables(schema)` which executes `SHOW TABLES FROM {schema}`.

#### `GET /tables/{table}/columns` — Get Columns

Calls `TrinoClient.get_columns(table, schema)` which executes `DESCRIBE {schema}.{table}`.

---

## Security Measures

### Search

- **Tenant isolation**: All search/index/delete/get operations filter by `tenant_id`
- **Ownership verification**: Delete and get operations verify the item belongs to the requesting tenant
- **Auth**: `read:*` for queries and gets, `write:documents` for index and delete

### SQL

- **Read-only enforcement**: `TrinoClient._validate_sql()` blocks all DDL and DML (SELECT, WITH, SHOW, DESCRIBE, EXPLAIN only)
- **Keyword denylist**: 28 forbidden keywords including injection vectors (`SLEEP`, `BENCHMARK`, `PG_SLEEP`, `UNION`, etc.)
- **Multi-statement blocking**: Rejects semicolons in query body
- **Comment stripping**: Removes `--` and `/* */` comments before validation
- **Identifier sanitization**: Regex `^[A-Za-z_][A-Za-z0-9_]*$` for schema/table names
- **Row limits**: Enforced at 10,000 max rows
- **Auth**: `execute:sql` permission required

## Dependencies

- **Milvus** — Vector database (via `VectorStore` / `get_vector_store()`)
- **Trino** — SQL engine (via `TrinoClient` / `get_trino_client()`)
- **Embedding extractors** — Dense (1536d) and sparse models from `apps.search.lib.embeddings`
