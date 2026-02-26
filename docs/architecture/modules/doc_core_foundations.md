# Voyant Documentation: Core App (`apps/core/`)

## 1. Overview
The `apps/core/` module is the beating heart of Voyant's Django architecture. It provides the abstract base models that enforce multi-tenancy rules globally, the HTTP middleware that injects context (like Tenant ID and Soma Session data) down to the logic layer, and the core NinjaAPI router wrapper. The `lib/` subdirectory here contains the heavy-duty connectors to the underlying data and orchestration tools (Trino, Temporal, MinIO, etc., to be documented in a separate Data Engines file).

## 2. File-by-File Breakdown

### `models.py`
Defines the authoritative base abstract models that **all** domain models MUST inherit from, guaranteeing isolation and auditability.
*   **`TimeStampedModel` (Abstract):** Automatically tracks `created_at` and `updated_at` (indexed).
*   **`TenantModel` (Abstract):** Enforces multi-tenancy by mandating a `tenant_id` (CharField, indexed). This is critical for data sovereignty.
*   **`UUIDModel` (Abstract):** Replaces standard auto-increment integer IDs with UUIDv4 (`id`) to prevent enumeration attacks.
*   **`AuditLog`:** A concrete model tracking exhaustive operations (`actor`, `action`, `resource_type`, `outcome`, `ip_address`). Critical for ISO compliance.
*   **`SystemSetting`:** A concrete model storing typed configuration overrides injected into the DB at runtime (`STRING`, `INTEGER`, `JSON`, etc.), supporting secrets (`is_secret`).

### `middleware.py`
Enforces context injection into Python `contextvars`, making tenant and session info globally accessible without explicitly passing the `request` object deep into service functions.
*   **`RequestIdMiddleware`:** Looks for an `X-Request-ID` header, generating a UUID if missing, and sets `request_id_var`.
*   **`TenantMiddleware`:** Extracts the `X-Tenant-ID` header (defaulting to `"default"`). This is the gatekeeper for `TenantModel` isolation. Sets `tenant_id_var`.
*   **`SomaContextMiddleware`:** Crucial for integration with the wider Soma Stack. Extracts `X-Soma-Session-ID`, `X-User-ID`, `traceparent`, and `Authorization`.
*   **`APIVersionMiddleware`:** Checks the `X-API-Version` or `Accept` header. Blocks unsupported versions with an HTTP 406 response. Bypasses health checks. Default is `v1`.

### `api.py`
Initializes the primary instance of the `NinjaAPI`.
*   Uses a unique test namespace to avoid router collision during pytest runs (`v1_{uuid}`).
*   Serves as the central aggregator, using `api.add_router()` to mount all domain routers:
    *   `/sources` (Discovery)
    *   `/jobs` (Workflows)
    *   `/sql` (SQL)
    *   `/governance` (Governance)
    *   `/presets` & `/artifacts` (Workflows)
    *   `/analyze` (Analysis)
    *   `/discovery` (Discovery)
    *   `/search` (Search)
    *   `/scrape` (Scraper)

## 3. Data Flow
1. **Ingress:** An HTTP request enters the Django WSGI/ASGI server.
2. **Middleware:** `TenantMiddleware` and `SomaContextMiddleware` immediately extract header data and populate `contextvars`.
3. **Routing:** `api.py` routes the request to the appropriate namespace (`/scrape`, `/jobs`, etc.).
4. **Logic:** Deep internal services call `get_tenant_id()` from `middleware.py`, retrieving the value populated in Step 2.
5. **Data Isolation:** The code queries ORM models extending `TenantModel`, filtering strictly via `tenant_id` to guarantee zero data bleed between customers.
