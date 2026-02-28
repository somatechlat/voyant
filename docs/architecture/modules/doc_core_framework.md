# Voyant Documentation: Core Routing & Security (`voyant_project/`)

## 1. Overview
The `voyant_project/` directory serves as the root Django configuration package. It wires together all operational endpoints, basic web server protocols (ASGI/WSGI), the primary API router, and defense-in-depth security policies.

## 2. File-by-File Breakdown

### `urls.py`
This file is the primary URL router for the entire Voyant application.
*   **Operational Endpoints (Unauthenticated):**
    *   `/health` (or `/healthz`): Returns a basic JSON `{"status": "healthy", "version": "3.0.0"}`.
    *   `/ready` (or `/readyz`): A deeper probe that performs a synchronous check on:
        *   DuckDB file accessibility.
        *   R Engine responsiveness (via `apps.core.lib.r_bridge.REngine`).
        *   Temporal client connection (3.0s timeout).
        *   Circuit Breaker states (Fails if `rserve` or `temporal` breakers are "open").
    *   `/status`: Exposes administrative metrics including the environment label and detailed circuit breaker metrics.
    *   `/version`: Delegates to `apps.core.middleware.get_version_info`.
*   **API Router:**
    *   `/v1/`: Includes the combined application router from `apps.core.api.v1_api`.

### `security_settings.py`
This file uses Pydantic Settings (`VOYANT_SECURITY_` prefix via `.env`) to define rigorous, ISO/IEC 27001 compliant security controls.
*   **Authentication:** Mandates JWT (RS256 algorithm by default) with configurable issuers and audiences.
*   **Security Headers (`get_security_headers()`):**
    *   Enforces HSTS (Strict-Transport-Security) for 1 year with subdomains and preload by default.
    *   Applies a strict Content-Security-Policy blocking remote scripts and iframes (`default-src 'self'`).
    *   Enforces `X-Frame-Options: DENY` and `X-Content-Type-Options: nosniff`.
*   **Rate Limiting:** Defaults to 60 requests/minute (burst size 10) per client.
*   **CORS (`get_cors_headers()`):** Provides configurable CORS allowed origins, defaulting aggressively to allow credentials.
*   **Database Security:** Can enforce SSL/TLS for PostgreSQL connections (`database_ssl_require=True`).
*   **Secrets Backend:** Configurable routing for secrets (Env, Vault, K8s, File) with HashiCorp Vault integrations.
*   **Audit Logging & Monitoring:** Allows configuring thresholds for failed logins (default 5) and suspicious requests, with automatic IP blocking (default 30 mins) on failure.
*   **Safety Net:** The Pydantic validator throws an immediate `ValueError` if `env == "production"` and `security_enabled` is False.

### `settings.py` (Previous Context)
Configures the 10 core domain apps, PostgreSQL database connections (via `DATABASE_URL`), Soma Stack injections (via middleware), and fundamental Django properties.

### `wsgi.py` & `asgi.py`
Standard Django entry points for Web Server Gateway Interface (synchronous workers) and Asynchronous Server Gateway Interface (async, websockets, and long-polling), pointing to `voyant_project.settings`.

## 3. Interaction with Other Modules
*   **API Registration:** `urls.py` directly binds the `NinjaAPI` instance initialized in `apps.core.api.py`.
*   **System Readiness:** Depends directly on `apps.core.lib` to verify the operational state of Trino, Temporal, and DuckDB.
