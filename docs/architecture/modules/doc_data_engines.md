# Data Engines Module

> **Source date**: 2026-09-04
> **Files examined**: `apps/core/lib/trino.py`, `apps/core/lib/temporal_client.py`, `apps/search/lib/milvus_store.py`

## Overview

The data engines module provides the three core data-access clients used throughout Voyant:

1. **TrinoClient** — Read-only SQL query engine against Trino (Iceberg catalog)
2. **TemporalClient** — Singleton async connection to the Temporal workflow orchestrator
3. **VectorStore (Milvus)** — Hybrid vector search engine with dense + sparse embeddings and tenant isolation

---

## `apps/core/lib/trino.py`

**Path**: `apps/core/lib/trino.py` (215 lines)

### `QueryResult` (dataclass)

| Field | Type | Description |
|---|---|---|
| `columns` | `list[str]` | Column names from cursor description |
| `rows` | `list[list[Any]]` | Result rows as lists |
| `row_count` | `int` | Number of rows returned |
| `truncated` | `bool` | `True` if row count >= limit |
| `execution_time_ms` | `int` | Wall-clock execution time |
| `query_id` | `str \| None` | Trino-assigned query ID |

### `TrinoClient`

**Purpose**: Validated, read-only Trino SQL client. All queries are validated before execution.

**Configuration** (from `Settings`): `trino_host`, `trino_port`, `trino_user`, `trino_catalog` (default `"iceberg"`), `trino_schema`, `max_query_rows` (default 10,000).

**Constructor**: `TrinoClient()` — lazy connection via `trino.dbapi.connect()`.

#### Public Methods

| Method | Signature | Description |
|---|---|---|
| `execute` | `(sql, limit=None, parameters=None) -> QueryResult` | Execute validated SQL with auto-limit wrapping |
| `get_tables` | `(schema=None) -> list[str]` | `SHOW TABLES FROM {schema}` |
| `get_columns` | `(table, schema=None) -> list[dict]` | `DESCRIBE {schema}.{table}` → `[{"name": ..., "type": ...}]` |
| `close` | `() -> None` | Close connection |

#### SQL Validation (`_validate_sql`)

Enforces read-only policy with three layers:

1. **Multi-statement blocking** — Rejects any semicolons except trailing
2. **Prefix allowlist** — Only `SELECT`, `WITH`, `SHOW`, `DESCRIBE`, `EXPLAIN`
3. **Keyword denylist** — Blocks: `DROP`, `CREATE`, `ALTER`, `TRUNCATE`, `RENAME`, `DELETE`, `INSERT`, `UPDATE`, `MERGE`, `UPSERT`, `GRANT`, `REVOKE`, `SET`, `RESET`, `CALL`, `EXECUTE`, `PREPARE`, `DEALLOCATE`, `UNION`, `INTO OUTFILE`, `INTO DUMPFILE`, `LOAD_FILE(`, `BENCHMARK(`, `SLEEP(`, `WAITFOR DELAY`, `PG_SLEEP(`, `DBMS_PIPE.RECEIVE_MESSAGE(`

SQL comments (`--` and `/* */`) are stripped before validation.

#### Identifier Validation (`_validate_identifier`)

Regex `^[A-Za-z_][A-Za-z0-9_]*$` — rejects injection-viable characters in schema/table names.

#### Limit Application (`_apply_limit`)

Wraps query in `SELECT * FROM ({sql}) AS _q LIMIT {limit}` unless a `LIMIT` clause already exists.

### `get_trino_client()` — Singleton

Global singleton factory. Creates `TrinoClient` on first call, returns cached instance thereafter.

---

## `apps/core/lib/temporal_client.py`

**Path**: `apps/core/lib/temporal_client.py` (73 lines)

### `get_temporal_client()` — Async Singleton

Returns a connected `temporalio.client.Client` instance.

**Connection flow**:
1. Returns existing client if already connected
2. Reads `temporal_host` and `temporal_namespace` from `Settings`
3. Calls `Client.connect(target_host, namespace=namespace)`
4. On connection failures (connect/refused/timeout), raises `ExternalServiceError` with code `VYNT-5001`
5. Other exceptions are re-raised directly

**Security note** (in code): Production connections must be secured with TLS (`tls_config` argument). Default config is local-only.

**Error handling**: Specific error codes and messages for connection failures. Resolution guidance included in error: "Ensure the Temporal service is running and accessible from the application."

---

## `apps/search/lib/milvus_store.py`

**Path**: `apps/search/lib/milvus_store.py` (340 lines)

### Collection Schema

**Collection name**: `voyant_documents`

| Field | Type | Details |
|---|---|---|
| `id` | `INT64` | Primary key, auto-generated |
| `doc_id` | `VARCHAR(256)` | Application-level document ID |
| `tenant_id` | `VARCHAR(64)` | **Partition key** for tenant isolation |
| `realm` | `VARCHAR(64)` | RBAC realm |
| `content` | `VARCHAR(65535)` | Text content (truncated to 65535) |
| `embedding` | `FLOAT_VECTOR(1536)` | Dense embedding |
| `sparse_embedding` | `SPARSE_FLOAT_VECTOR` | Sparse embedding |
| `metadata` | `JSON` | Arbitrary metadata |
| `source_type` | `VARCHAR(32)` | Source classification |
| `created_at` | `INT64` | Unix timestamp |

### Indexes

- **Dense**: HNSW index on `embedding`, metric `COSINE`, M=16, efConstruction=256
- **Sparse**: `SPARSE_INVERTED_INDEX` on `sparse_embedding`, metric `IP`, drop_ratio_build=0.2

### `_MilvusConnection` (internal)

Lazy, resilient connection manager with exponential backoff (1s–30s).

- **`client()`** — Returns live `MilvusClient`, reconnecting if connection test (`list_collections()`) fails
- **`ensure_collection()`** — Creates collection and indexes if not present (respects `milvus_auto_create` setting)
- **Backoff**: On failure, backs off exponentially up to 30s

### `VectorStore`

**Purpose**: Milvus 2.4+ vector store with hybrid search and tenant isolation.

#### CRUD Operations

| Method | Signature | Description |
|---|---|---|
| `add` | `(id, vector, metadata=None, sparse_vector=None)` | Insert/upsert document |
| `get` | `(id) -> VectorItem \| None` | Query by `doc_id` |
| `delete` | `(id, tenant_id=None)` | Delete with optional tenant verification |

**Upsert fallback**: If upsert fails, retries with insert.

#### `search()` — Hybrid Search

```python
search(query_vector, k=5, filter_metadata=None, query_sparse_vector=None) -> list[tuple[VectorItem, float]]
```

**Algorithm**:
1. Runs dense search on `embedding` (COSINE, ef=64, limit=2k)
2. If `query_sparse_vector` provided, runs sparse search on `sparse_embedding` (IP, drop_ratio_search=0.2)
3. **Weighted RRF merge**: dense weight 0.7, sparse weight 0.3, RRF k=60
4. Returns top-k results sorted by merged score

**Tenant isolation**: Filters by `tenant_id` (required) and `realm` (optional).

### `VectorItem` (dataclass)

| Field | Type |
|---|---|
| `id` | `str` |
| `vector` | `list[float]` |
| `metadata` | `dict[str, Any]` |

### `get_vector_store()` — Singleton

Global singleton factory for `VectorStore`.

---

## Dependencies and Integration Points

| Engine | External Service | Protocol | Auth |
|---|---|---|---|
| Trino | Trino cluster | TCP (trino.dbapi) | Username only |
| Temporal | Temporal server | gRPC | None (local) / TLS (production) |
| Milvus | Milvus cluster | HTTP/gRPC | Token-based (`milvus_token`) |

## Error Handling Patterns

- **Trino**: `ValueError` for SQL validation failures; `RuntimeError` for missing client library
- **Temporal**: `ExternalServiceError` (code `VYNT-5001`) for connection failures with resolution guidance
- **Milvus**: `MilvusException` for connection failures with exponential backoff; fallback from upsert to insert
