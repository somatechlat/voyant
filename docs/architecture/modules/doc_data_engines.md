# Voyant Documentation: Core Data Engines (`apps/core/lib/`)

## 1. Overview
The `apps/core/lib/` directory houses the critical singleton clients that connect Voyant's Python logic to its heavy-duty infrastructure: the SQL engine, the workflow orchestrator, and the vector database.

## 2. File-by-File Breakdown

### `temporal_client.py`
Provides a singleton connection to the Temporal cluster used for orchestrating all long-running asynchronous jobs.
*   **Initialization:** Lazily connects on the first call to `get_temporal_client()` using `temporal_host` and `temporal_namespace` from settings.
*   **Error Handling:** Pragmatically catches connection refused/timeouts and raises a domain-specific `ExternalServiceError` (`VYNT-5001`).
*   **Security Posture:** Notes that TLS must be configured via `tls_config` for production, though the default is insecure for local environments.

### `trino.py`
The primary SQL execution engine for Voyant. It is built strictly as a **Read-Only** federated query client.
*   **`TrinoClient` (Singleton):** Caches a single `trino.dbapi.Connection`.
*   **Query Safety (`_validate_sql`):** This is a critical security gate. It enforces a strict allowlist of prefixes (`SELECT`, `WITH`, `SHOW`, `DESCRIBE`, `EXPLAIN`). It also scans for and actively blocks forbidden keywords like `DROP`, `DELETE`, `UPDATE`, `ALTER`, etc., raising a `ValueError`.
*   **Runaway Query Prevention (`_apply_limit`):** Automatically wraps queries in a subquery `SELECT * FROM ({sql}) AS _q LIMIT {limit}` if a limit isn't provided, capping at `max_query_rows`.
*   **Metadata Helpers:** provides `get_tables()` and `get_columns()` for quick schema introspection without writing raw queries.

### `vector_store.py`
A simple, JSON-backed persistent vector store for semantic search embeddings.
*   **In-Memory Architecture:** Loads all vectors into a Python dictionary (`_items`) in memory for fast scanning during search.
*   **Persistence (`save`/`load`):** Saves the state to disk (e.g., `data/vectors.json`). Uses an atomic write (writing to `.tmp` then os.replace) to prevent corruption.
*   **Search (`search`):** Iterates over all vectors, optionally applying exact-match metadata filters, and calculates the **Cosine Similarity**. Sorts descending and returns the top `k`.
*   **Tenant Isolation:** While the store itself doesn't enforce tenancy structurally, the `metadata` dictionary is expected to hold `tenant_id` which is then used in `filter_metadata` during search operations.

## 3. Interaction with Other Modules
*   **Temporal** is heavily utilized by `apps/workflows/` and `apps/scraper/` to execute robust retries.
*   **Trino** is the backend for `apps/sql/api.py` and the KPI templates, reading from Iceberg/Postgres.
*   **Vector Store** is exclusively used by `apps/search/api.py` for indexing and retrieving semantic information.
