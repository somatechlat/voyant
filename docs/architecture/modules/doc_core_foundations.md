# Core Foundations Module

> **Source date**: 2026-09-04
> **Files examined**: `apps/core/models.py`, `apps/core/middleware.py`, `apps/core/config.py`

## Overview

The core foundations module provides three pillars that every other module depends on: **abstract base models** for multi-tenancy and audit trails, **middleware** for request-scoped context (tenant, request ID, RBAC, API versioning), and **typed application configuration** via `pydantic-settings` with Vault and Docker secrets support.

---

## `apps/core/models.py`

**Path**: `apps/core/models.py` (249 lines)

### Abstract Base Models

#### `TimeStampedModel`

All Voyant models inherit this. Provides:

| Field | Type | Details |
|---|---|---|
| `created_at` | `DateTimeField` | `auto_now_add=True`, `db_index=True` |
| `updated_at` | `DateTimeField` | `auto_now=True`, `db_index=True` |

Default ordering: `["-created_at"]`. **Abstract** — no DB table.

#### `TenantModel(TimeStampedModel)`

Adds multi-tenancy with realm isolation:

| Field | Type | Details |
|---|---|---|
| `realm` | `CharField(64)` | Default `"default"`, indexed |
| `tenant_id` | `CharField(128)` | Indexed |

Custom manager: **`RBACManager`** — auto-filters querysets by `realm` + `tenant_id` for non-admin users. Admins (with `"voyant-admin"` in `roles`) get unfiltered querysets.

Composite indexes: `(tenant_id, -created_at)`, `(realm, tenant_id, created_at)`.

#### `UUIDModel`

Uses `UUIDField` as primary key (`uuid.uuid4` default). **Abstract** — no DB table.

### Concrete Models

#### `AuditLog(TenantModel, UUIDModel)`

**Table**: `voyant_audit_log`

Immutable audit trail for compliance and security monitoring.

| Field | Type | Notes |
|---|---|---|
| `actor` | `CharField(256)` | User or service |
| `action` | `CharField(128)` | Indexed, e.g. `"job.created"` |
| `resource_type` | `CharField(64)` | Indexed |
| `resource_id` | `CharField(256)` | Indexed |
| `outcome` | `CharField(32)` | Choices: `success`, `failure`, `denied` |
| `details` | `JSONField` | Additional details |
| `ip_address` | `GenericIPAddressField` | Nullable |
| `user_agent` | `TextField` | Client user agent |

Indexes: `(tenant_id, action, -created_at)`, `(tenant_id, resource_type, resource_id)`, `(actor, -created_at)`.

#### `SystemSetting`

**Table**: `voyant_system_setting`

Runtime configuration stored in the database. Allows changing settings without code deploys.

| Field | Type | Notes |
|---|---|---|
| `key` | `CharField(255)` | Unique, indexed |
| `value` | `TextField` | Stored as text |
| `value_type` | `CharField(16)` | Choices: `string`, `integer`, `float`, `boolean`, `json` |
| `description` | `TextField` | Optional |
| `is_secret` | `BooleanField` | Masks value in `__str__` |
| `updated_at` | `DateTimeField` | `auto_now=True` |

Method `get_value()` — type-casts the stored value based on `value_type`.

---

## `apps/core/middleware.py`

**Path**: `apps/core/middleware.py` (186 lines)

### Context Variables (thread-safe via `contextvars`)

| Variable | Default | Set by |
|---|---|---|
| `request_id_var` | `""` | `RequestIdMiddleware` |
| `tenant_id_var` | `"default"` | `TenantMiddleware` |
| `api_version_var` | `"v1"` | `APIVersionMiddleware` |
| `soma_session_id_var` | `""` | `SomaContextMiddleware` |
| `soma_user_id_var` | `""` | `SomaContextMiddleware` |
| `traceparent_var` | `""` | `SomaContextMiddleware` |
| `authorization_var` | `""` | `SomaContextMiddleware` |
| `current_user_var` | `None` | `RBACMiddleware` |

### Middleware Classes

#### `RequestIdMiddleware`
- Reads `X-Request-ID` header (generates UUID4 if absent)
- Sets `request_id_var` for the request lifetime
- Attaches `X-Request-ID` to the response

#### `TenantMiddleware`
- Reads `X-Tenant-ID` header (defaults to `"default"`)
- Sets `tenant_id_var`

#### `SomaContextMiddleware`
- Captures `X-Soma-Session-ID`, `X-User-ID`, `traceparent`, `Authorization` headers into context vars
- Used for agent context injection and distributed tracing

#### `RBACMiddleware`
- Resolves user from `Authorization: Bearer <token>` header
- Calls `apps.core.security.auth.get_auth().validate_token(token)`
- Sets `current_user_var` (resets to `None` after response to prevent leakage)
- **Does not raise** on invalid tokens — endpoint-level decorators enforce strict auth

#### `APIVersionMiddleware`
- Extracts version from `X-API-Version` header or `Accept: application/vnd.voyant.v{N}+json`
- Supported versions: `["v1"]`, default `"v1"`
- Returns 406 for unsupported versions
- Skips versioning for health check paths (`/health`, `/ready`, `/healthz`, `/readyz`)
- Attaches `X-API-Version` to every response

### Accessor Functions

| Function | Returns |
|---|---|
| `get_request_id()` | Current request ID |
| `get_tenant_id(request=None)` | Tenant ID (prefers request header, falls back to context var) |
| `get_api_version()` | API version string |
| `get_soma_session_id()` | Soma session ID |
| `get_soma_user_id()` | Soma user ID |
| `get_traceparent()` | W3C traceparent |
| `get_authorization()` | Authorization header value |
| `get_current_user()` | Resolved user object or `None` |
| `get_version_info()` | Dict with version metadata |

---

## `apps/core/config.py`

**Path**: `apps/core/config.py` (824 lines)

### Docker Secrets Resolution

`_resolve_docker_secrets()` runs at import time. For every env var ending with `_FILE`, reads the file content and sets the base key (e.g., `VOYANT_SECRET_KEY_FILE` → `VOYANT_SECRET_KEY`). Explicit env vars take precedence.

### `Settings` (pydantic-settings `BaseSettings`)

**Prefix**: `VOYANT_` (all env vars prefixed automatically)

**Secret keys** (enforced to come from Vault in non-local environments): `minio_access_key`, `minio_secret_key`, `keycloak_client_secret`, `serper_api_key`, `mcp_api_token`, `spicedb_grpc_preshared_key`, `motherduck_token`, `unstructured_api_key`, and 5 OAuth provider secrets.

**Runtime env keys**: `env`, `debug`, `secrets_backend`, `database_url`, `redis_url`, `kafka_bootstrap_servers`, `temporal_host`, `temporal_namespace`, `temporal_task_queue`, `minio_endpoint`, `datahub_gms_url`, `keycloak_url`, `keycloak_realm`, `soma_policy_url`, `soma_memory_url`, `soma_orchestrator_url`, `flink_jobmanager_url`, `scraper_allow_local_hosts`, and more.

### Key Configuration Groups

| Group | Fields | Notes |
|---|---|---|
| **Core Application** | `env`, `deployment_mode`, `worker_mode`, `debug`, `secret_key`, `allowed_hosts` | `env` default `"local"`; `worker_mode` default `"full"` |
| **Infrastructure** | `database_url`, `duckdb_path`, `redis_url` | PostgreSQL + DuckDB + Redis |
| **Email** | `email_host`, `email_port`, `email_use_tls`, `email_host_user`, `email_host_password`, `default_from_email` | SMTP config |
| **Kafka** | `kafka_bootstrap_servers` | Event streaming |
| **Temporal** | `temporal_host`, `temporal_namespace`, `temporal_task_queue`, `temporal_activity_max_workers` | Task queue default `"voyant-tasks"` |
| **MinIO** | `minio_endpoint`, `minio_access_key`, `minio_secret_key`, `minio_bucket_name`, `minio_secure` | Default bucket `"voyant-artifacts"` |
| **Trino** | `trino_host`, `trino_port`, `trino_user`, `trino_catalog`, `trino_schema` | Default catalog `"iceberg"`, port `45090` |
| **Milvus** | `milvus_host`, `milvus_port`, `milvus_uri`, `milvus_db_name`, `milvus_token`, `milvus_auto_create` | Default DB `"voyant"`, port `19530` |
| **SpiceDB** | `spicedb_endpoint`, `spicedb_tls`, `spicedb_grpc_preshared_key` | gRPC auth engine |
| **DuckDB/MotherDuck** | `db_backend`, `db_path`, `motherduck_token`, `db_max_connections`, `db_query_timeout` | Backends: `duckdb_local`, `duckdb_memory`, `motherduck` |
| **OAuth** | `oauth_google`, `oauth_github`, `oauth_microsoft`, `oauth_okta`, `oauth_generic` | Per-provider dicts |
| **Prune Scheduler** | `prune_enabled`, `prune_interval_seconds`, `prune_max_job_age_days`, `prune_max_artifact_age_days`, `prune_max_artifacts_per_tenant`, `prune_dry_run` | Default 30-day retention |
| **Scraper** | 20+ fields for engine, timeout, TLS, Playwright, OCR, transcription | See scraper config |
| **Feature Toggles** | `enable_quality`, `enable_datahub`, `enable_mfa`, `enable_charts`, `enable_narrative`, `metrics_mode` | |
| **API Limits** | `api_host`, `api_port`, `mcp_host`, `mcp_port`, `api_workers`, `max_query_rows`, `max_upload_size_mb` | Default max 10,000 rows |

### Validators

- **`validate_secrets_backend`** — Forbids `secrets_backend="env"` in staging/production. Enforces Vault or K8s secrets.
- **`validate_required_external_config`** — In non-local envs, requires: `database_url`, `redis_url`, `kafka_bootstrap_servers`, `temporal_host`, `minio_endpoint`, `minio_access_key`, `minio_secret_key`, `datahub_gms_url`, `keycloak_url`, `keycloak_realm`, `keycloak_client_id`, `keycloak_client_secret`, `mcp_api_url`.

### `_resolve_vault_secrets(settings)`

Fetches all `SECRET_KEYS` from HashiCorp Vault (via `hvac` library). Only empty values are overridden — explicit env vars still take precedence for local development.

### `get_settings()` — Cached Singleton

Load order (last writer wins):
1. Defaults and env vars (pydantic-settings)
2. Docker secrets (`_FILE` env vars)
3. Vault secrets (for all `SECRET_KEYS`)
4. ORM overrides (`SystemSetting` model, for non-secret runtime config)
