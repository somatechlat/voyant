# Core Framework Module

> **Source date**: 2026-09-04
> **Files examined**: `voyant_project/settings.py`, `voyant_project/urls.py`, `voyant_project/asgi.py`, `apps/core/api.py`

## Overview

The core framework is the Django project skeleton that wires together all application modules. It defines the Django settings, URL routing, ASGI application with MCP transport, and the centralized NinjaAPI REST router that mounts every sub-application's endpoints under `/v1/`.

---

## `voyant_project/settings.py`

**Path**: `voyant_project/settings.py` (405 lines)

The single Django settings module for the Voyant project. Configuration is driven by the `pydantic-settings` model in `apps/core.config.Settings` (accessed via `get_settings()`).

### Key responsibilities

| Concern | Detail |
|---|---|
| Environment loading | Loads `.env` only when `VOYANT_ENV=local` via `python-dotenv` |
| Secret key | From `Settings.secret_key`; falls back to `VOYANT_LOCAL_FALLBACK_SECRET_KEY` in local/test only |
| Database | Parses `DATABASE_URL` (PostgreSQL) via `_parse_database_url()`; supports SSL params from `security_settings` |
| Vector DB | Milvus connection config (`MILVUS` dict) built from `Settings.milvus_uri` / `milvus_host` + `milvus_port` |
| Installed apps | 13 apps: `core`, `workflows`, `analysis`, `sql`, `search`, `discovery`, `ingestion`, `governance`, `scraper`, `uptp_core`, `capsules`, `ontology` plus 3rd-party (`corsheaders`, `ninja`, `django_mcp`) |
| Middleware stack (order) | CorsMiddleware → SecurityMiddleware → SessionMiddleware → CommonMiddleware → CsrfViewMiddleware → AuthenticationMiddleware → MessageMiddleware → XFrameOptionsMiddleware → **RequestIdMiddleware** → **TenantMiddleware** → **RBACMiddleware** → **SomaContextMiddleware** → **GovernancePolicyMiddleware** → **APIVersionMiddleware** |
| Security headers | HSTS, content-type nosniff, XSS filter, referrer policy — all gated by `security_settings.security_enabled` |
| CORS | `CORS_ALLOW_ALL_ORIGINS=False` always; origins/methods/headers from `security_settings` |
| Sessions | Redis-backed cache sessions (`SESSION_ENGINE=django.contrib.sessions.backends.cache`), secure + httponly + SameSite=Lax |
| Password validation | 4 Django validators with `min_length=12` |
| Email | SMTP backend; host/port/TLS/user/password from `Settings` |
| Logging | 4 handlers: `console`, `file` (10 MB, 5 backups), `security` (10 MB, 30 backups), `audit` (10 MB, 365 backups). Loggers: `django`, `voyant`, `voyant.security`, `voyant.audit` |
| Caching | Redis via `django_redis` |
| Rate limiting | `RATELIMIT_USE_CACHE="default"`, prefix `"rl"` |
| MCP config | `django-mcp` settings: title `"Voyant Data Intelligence"`, version `"3.0.0"`, instructions for AI agents |

### Helper function: `_parse_database_url(url)`

Parses a `postgresql://` or `postgres://` URL into a Django `DATABASES` dict. Applies SSL config from `security_settings` when `database_ssl_require` is `True`.

---

## `voyant_project/urls.py`

**Path**: `voyant_project/urls.py` (33 lines)

### URL Patterns

| Path | View / Target | Auth | Description |
|---|---|---|---|
| `health` | `apps.core.views.health` | None | Kubernetes liveness probe (lightweight) |
| `ready` | `apps.core.views.ready` | None | Kubernetes readiness probe (full deps) |
| `healthz` | `apps.core.views.health` | None | Alias for liveness |
| `readyz` | `apps.core.views.ready` | None | Alias for readiness |
| `status` | `apps.core.views.status_view` | — | Administrative status report |
| `version` | `apps.core.views.version_view` | — | API version metadata |
| `v1/` | `apps.core.api.api.urls` | Varies | All REST API routes (Django Ninja) |

All operational endpoints (`health`, `ready`, etc.) are stateless views defined in `apps/core/views.py`. The `v1/` prefix mounts the entire NinjaAPI surface.

---

## `voyant_project/asgi.py`

**Path**: `voyant_project/asgi.py` (15 lines)

The ASGI entrypoint. Creates the Django ASGI application and mounts the MCP server at `/mcp` using `django_mcp.mount_mcp_server()`. This allows AI agents to connect via HTTP/SSE for MCP tool invocation.

```python
application = mount_mcp_server(django_http_app=django_asgi_app, mcp_base_path="/mcp")
```

**Key detail**: The MCP transport is only available when the application is served via an ASGI server (e.g., Daphne, uvicorn). The WSGI application (`voyant_project.wsgi`) does not include MCP.

---

## `apps/core/api.py`

**Path**: `apps/core/api.py` (46 lines)

The centralized API router. Creates a single `NinjaAPI` instance (`api`) and registers all sub-application routers.

### NinjaAPI Configuration

- **Title**: `"Voyant API"`
- **Description**: `"Autonomous Data Intelligence for AI Agents"`
- **Version**: `"3.0.0"`
- **URL namespace**: `"v1"` (unique per test run to avoid registry collisions)

### Registered Routers

| Prefix | Router | Tag | Source Module |
|---|---|---|---|
| `/sources` | `sources_router` | `sources` | `apps.discovery.api` |
| `/jobs` | `jobs_router` | `jobs` | `apps.workflows.api` |
| `/sql` | `sql_router` | `sql` | `apps.sql.api` |
| `/governance` | `governance_router` | `governance` | `apps.governance.api` |
| `/presets` | `presets_router` | `presets` | `apps.workflows.api` |
| `/artifacts` | `artifacts_router` | `artifacts` | `apps.workflows.api` |
| `/analyze` | `analyze_router` | `analyze` | `apps.analysis.api` |
| `/discovery` | `discovery_router` | `discovery` | `apps.discovery.api` |
| `/search` | `router` | `search` | `apps.search.api` |
| `/scrape` | `scrape_router` | `scrape` | `apps.scraper.api` |
| `/capsules` | `capsules_router` | `capsules` | `apps.capsules.api` |
| `/ingestion` | `ingestion_router` | `ingestion` | `apps.ingestion.api` |

### Testing Safeguard

When running under `pytest`, the NinjaAPI registry is cleared and a unique namespace (`v1_<uuid>`) is generated to prevent test isolation collisions.

---

## Integration Points

- **Django ORM** — PostgreSQL via `DATABASE_URL`
- **Redis** — Caching and sessions
- **Milvus** — Vector database (config in `MILVUS` dict)
- **Temporal** — Workflow orchestration (config via `Settings.temporal_host`)
- **MinIO** — Object storage for artifacts
- **DataHub** — Metadata governance
- **Keycloak** — Identity and access management
- **SpiceDB** — Authorization engine
- **Kafka** — Event streaming
- **Apache Flink** — Stream processing
- **DuckDB/MotherDuck** — Analytics database backend
- **django-mcp** — MCP transport for AI agents at `/mcp`

## Security Measures

- `SECRET_KEY` required; no hardcoded fallback in production
- `DEBUG=False` enforced for production
- SSL redirect, secure cookies, HSTS all gated by `security_settings.security_enabled`
- CORS restricted (`CORS_ALLOW_ALL_ORIGINS=False`)
- CSRF trusted origins configurable
- Password validation with 12-char minimum
- Comprehensive audit logging (separate `security.log` and `audit.log`)
- Rate limiting via Redis cache
