# Voyant Documentation: Search & SQL API Gateways (`apps/search`, `apps/sql`)

## 1. Overview
These modules provide the external, agent-facing and frontend-facing REST APIs for executing data queries. They act as the secure routing layer sitting on top of the raw data engines (Vector Store and Trino, respectively).

## 2. File-by-File Breakdown

### `apps/search/api.py`
Provides Semantic Search capabilities, integrating strictly with the Vector Store (Milvus) and embedding extractors.
*   **Security & Isolation:** Every endpoint enforces `auth_guard` and isolates all data manipulation using `get_tenant_id(request)`.
*   **Indexing (`POST /index`):**
    *   Takes raw text and an optional `item_id` and metadata.
    *   Generates a vector embedding using `get_embedding_extractor(model="tfidf", dimensions=128)`.
    *   Injects `tenant_id` into the metadata for hard isolation.
    *   Saves the vector synchronously to `get_vector_store()`.
*   **Querying (`POST /query`):**
    *   Takes a `query` string, an optional `limit` (max 100), and optional exact-match `filters`.
    *   Generates the embedding for the query string.
    *   Forces `filters["tenant_id"] = tenant_id` to guarantee the search cannot bleed across tenants.
    *   Returns ranked `SemanticSearchResult` objects using Cosine Similarity.
*   **Management (`GET /{item_id}`, `DELETE /{item_id}`):** Both endpoints fetch the item from the vector store first, and throw a `403 Access denied` if the item's stored `tenant_id` does not match the requester's `tenant_id`.

### `apps/sql/api.py`
Provides ad-hoc SQL querying capabilities, federated through Trino.
*   **Query Execution (`POST /query`):**
    *   Takes a raw `sql` string and a `limit` (capped at 10,000 for the API payload).
    *   Relies entirely on `get_trino_client().execute()` which internally enforces the read-only command denylist (blocking `DROP`, `DELETE`, etc.).
    *   Translates the raw `cursor.fetchall()` into a structured `SqlResponse` containing `columns`, `rows` (nested list), `row_count`, and `execution_time_ms`.
*   **Schema Discovery (`GET /tables`, `GET /tables/{table}/columns`):**
    *   Uses Trino's `SHOW TABLES` and `DESCRIBE` capabilities to provide schema introspection.
    *   Allows an optional `schema` override parameter, falling back to the client's default configured schema if omitted.

## 3. Core Principles Reflected
*   **Zero-Bleed Tenancy:** The Search API actively injects `tenant_id` into the vector metadata upon creation and actively forces it into the search filter upon querying.
*   **Read-Only SQL Protocol:** The `/query` endpoint completely lacks write capabilities. Any destructive SQL command sent to this endpoint will be intercepted and raised as a `ValueError` by the underlying `.execute()` method in the core library.
