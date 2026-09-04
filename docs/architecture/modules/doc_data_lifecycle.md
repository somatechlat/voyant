# Data Lifecycle Module

> **Source date**: 2026-09-04
> **Files examined**: `apps/discovery/`, `apps/ingestion/`, `apps/governance/`

## Overview

The data lifecycle module manages the end-to-end journey of data through Voyant: **discovery** (finding and registering data sources and services), **ingestion** (provisioning Airbyte connectors and loading data), and **governance** (data contracts, lineage tracking, policies, and resource quotas).

---

## Discovery (`apps/discovery/`)

### Models (`models.py`, 114 lines)

#### `Source(TenantModel, UUIDModel)`

**Table**: `voyant_source`

| Field | Type | Notes |
|---|---|---|
| `name` | `CharField(255)` | Source name |
| `source_type` | `CharField(128)` | Type identifier (e.g. `"postgresql"`) |
| `status` | `CharField(64)` | Default `"pending"` |
| `connection_config` | `JSONField` | Connection parameters |
| `credentials` | `JSONField` | Nullable |
| `sync_schedule` | `CharField(128)` | Nullable, cron-like schedule |
| `datahub_urn` | `CharField(512)` | Nullable, DataHub URN |

#### `ServiceDefinition(TenantModel, UUIDModel)`

**Table**: `voyant_service_definition`

**Deprecated** (not used by current API — uses in-memory `DiscoveryRepo` instead; scheduled for removal v4.0.0).

| Field | Type |
|---|---|
| `name` | `CharField(255)` |
| `base_url` | `URLField(512)` |
| `spec_url` | `URLField(512)` |
| `version` | `CharField(64)` |
| `description` | `TextField` |
| `owner` | `CharField(255)` |
| `tags` | `JSONField` |
| `endpoints` | `JSONField` |
| `auth_type` | `CharField(64)` |
| `metadata` | `JSONField` |
| `first_seen` | `DateTimeField` |
| `last_seen` | `DateTimeField` |

Unique constraint: `(tenant_id, name)`.

### Source Detection (`source_detection.py`, 86 lines)

`detect_source_type(hint: str) -> dict` — Pattern-matching function that identifies source types from connection hints.

| Pattern | Source Type | Connector | Confidence |
|---|---|---|---|
| `postgresql://` / `postgres://` | `postgresql` | `airbyte/source-postgres` | 0.95 |
| `mysql://` | `mysql` | `airbyte/source-mysql` | 0.95 |
| `mongodb://` / `mongodb+srv://` | `mongodb` | `airbyte/source-mongodb-v2` | 0.95 |
| Contains `snowflake` | `snowflake` | `airbyte/source-snowflake` | 0.90 |
| `*.csv` | `csv` | `file` | 0.90 |
| `*.parquet` | `parquet` | `file` | 0.90 |
| `*.json` / `*.jsonl` | `json` | `file` | 0.90 |
| `s3://` | `s3` | `airbyte/source-s3` | 0.90 |
| Google Sheets URL | `google_sheets` | `airbyte/source-google-sheets` | 0.90 |
| `http://` / `https://` | `api` | `airbyte/source-http` | 0.50 |
| Anything else | `unknown` | `unknown` | 0.10 |

Returns: `{"source_type", "connector", "properties", "confidence"}`

### API (`api.py`, 222 lines)

#### Sources Router (`/v1/sources`)

| Method | Path | Auth | Response | Description |
|---|---|---|---|---|
| `POST` | `/discover` | `read:*` | `DiscoverResponse` | Auto-detect source type from hint |
| `POST` | `/` | `write:sources` | 201 `SourceResponse` | Create a new source |
| `GET` | `/` | `read:*` | `list[SourceResponse]` | List sources for tenant |
| `GET` | `/{source_id}` | `read:*` | `SourceResponse` | Get source (tenant check) |
| `DELETE` | `/{source_id}` | `write:sources` | 200 `{"status", "source_id"}` | Delete source (tenant check) |

**Security**: Tenant isolation enforced — `get_source` and `delete_source` verify `source.tenant_id == tenant_id`.

#### Discovery Router (`/v1/discovery`)

| Method | Path | Auth | Response | Description |
|---|---|---|---|---|
| `POST` | `/services` | `write:sources` | `ServiceDef` | Register a service (optionally parse OpenAPI spec) |
| `GET` | `/services` | `read:*` | `list[ServiceDef]` | List services (optional tag filter) |
| `GET` | `/services/{name}` | `read:*` | `ServiceDef` | Get service by name |
| `POST` | `/scan` | `write:sources` | `dict` | Scan OpenAPI spec URL (title, version, endpoints) |

---

## Ingestion (`apps/ingestion/`)

### Models (`models.py`, 100 lines)

#### `IngestionJob(TenantModel, UUIDModel)`

**Table**: `voyant_ingestion_job`

| Field | Type | Notes |
|---|---|---|
| `source` | `ForeignKey(Source)` | `on_delete=CASCADE`, `related_name="ingestion_jobs"` |
| `workflow_instance_id` | `CharField(255)` | Unique, Temporal workflow ID |
| `status` | `CharField(16)` | Choices: `pending`, `queued`, `running`, `succeeded`, `failed`, `cancelled`, `partial` |
| `progress` | `FloatField` | 0.0 to 1.0 |
| `stage` | `CharField(64)` | Current execution stage |
| `params` | `JSONField` | Job parameters |
| `result` | `JSONField` | Nullable |
| `error_message` | `TextField` | Error details |
| `rows_ingested` | `BigIntegerField` | Default 0 |
| `bytes_processed` | `BigIntegerField` | Default 0 |
| `started_at` | `DateTimeField` | Nullable |
| `finished_at` | `DateTimeField` | Nullable |

Indexes: `(tenant_id, status, -created_at)`, `(source, -created_at)`, `(workflow_instance_id)`.

### API (`api.py`, 212 lines)

#### Ingestion Router (`/v1/ingestion`)

| Method | Path | Auth | Response | Description |
|---|---|---|---|---|
| `POST` | `/connect` | `write:sources` | `ConnectSourceResponse` | Provision Airbyte source + optional destination |
| `POST` | `/provision-destination` | `write:sources` | `ProvisionDestinationResponse` | Provision standalone Airbyte destination |

**`connect_source` flow**:
1. Validates source exists and belongs to tenant
2. Calls `apply_policy()` for governance check
3. Provisions Airbyte source connector via `AirbyteClient`
4. Optionally provisions destination and creates connection
5. Updates Source status to `"connected"`
6. On failure, sets source status to `"error"` and raises 500

**Dependencies**: `apps.ingestion.lib.airbyte_client` (lazy import).

---

## Governance (`apps/governance/`)

### Models (`models.py`, 359 lines)

#### `DataContract(TenantModel, UUIDModel)`

**Table**: `voyant_data_contract`

Schema validation and quality rules between data producers and consumers.

| Field | Type | Notes |
|---|---|---|
| `name` | `CharField(255)` | |
| `description` | `TextField` | |
| `dataset_urn` | `CharField(512)` | DataHub URN, indexed |
| `schema_definition` | `JSONField` | JSON schema |
| `quality_rules` | `JSONField` | List of quality constraints |
| `status` | `CharField(16)` | `draft`, `active`, `deprecated`, `archived` |
| `version` | `CharField(32)` | Default `"1.0.0"` |
| `owner` | `CharField(255)` | |
| `metadata` | `JSONField` | |

Unique constraint: `(tenant_id, name, version)`.

#### `LineageNode(TenantModel, UUIDModel)`

**Table**: `voyant_lineage_node`

| Field | Type | Notes |
|---|---|---|
| `urn` | `CharField(512)` | Unique, indexed |
| `name` | `CharField(255)` | |
| `node_type` | `CharField(32)` | `dataset`, `transformation`, `model`, `report`, `api` |
| `platform` | `CharField(128)` | Indexed |
| `description` | `TextField` | |
| `upstream_urns` | `JSONField` | List of upstream URNs |
| `downstream_urns` | `JSONField` | List of downstream URNs |
| `metadata` | `JSONField` | |

#### `Policy(TenantModel, UUIDModel)`

**Table**: `voyant_policy`

| Field | Type | Notes |
|---|---|---|
| `name` | `CharField(255)` | |
| `description` | `TextField` | |
| `policy_type` | `CharField(32)` | `access_control`, `data_retention`, `data_quality`, `compliance`, `usage` |
| `status` | `CharField(16)` | `draft`, `active`, `inactive`, `archived` |
| `rules` | `JSONField` | Policy rules and conditions |
| `scope` | `JSONField` | Scope definition |
| `enforcement_level` | `CharField(32)` | `strict`, `warn`, `audit` |
| `owner` | `CharField(255)` | |
| `metadata` | `JSONField` | |

Unique constraint: `(tenant_id, name)`.

#### `QuotaTier` (model)

**Table**: `voyant_quota_tier`

**Deprecated** (not used by current API — uses `QuotaTier` enum from `apps.core.lib.tenant_quotas` instead; scheduled for removal v4.0.0).

#### `TenantQuota(TenantModel)`

**Table**: `voyant_tenant_quota`

Tracks which tier a tenant is on and current resource usage.

### Governance Middleware (`middleware.py`, 350 lines)

**`GovernancePolicyMiddleware`** — Intercepts every Django request (except exempt paths).

**Exempt paths**: `/health`, `/ready`, `/healthz`, `/readyz`, `/admin`, `/static`, `/favicon.ico`

**Flow**:
1. Builds context from request (method, path, user, roles, tenant, headers)
2. Fetches active `Policy` objects for tenant
3. Evaluates policies via `PolicyEnforcer`
4. For mutation requests (POST/PUT/PATCH/DELETE), checks `DataContract` compliance
5. **Strict enforcement**: Returns 403 if policy denies with `enforcement_level="strict"`
6. **Warn/audit**: Logs violation but allows request to proceed
7. Attaches `X-Governance-Policy-ID` and `X-Governance-Decision` response headers

**Data contract validation** checks `required_field` and `not_null` rules against request body.

**Audit logging**: Both structured `voyant.audit` logger and `AuditLog` ORM model.

### API (`api.py`, 366 lines)

#### Governance Router (`/v1/governance`)

| Method | Path | Auth | Response | Description |
|---|---|---|---|---|
| `GET` | `/search` | `auth_guard` | `SearchResponse` | Search DataHub metadata via GraphQL |
| `GET` | `/lineage/{urn}` | `auth_guard` | `LineageResponse` | Fetch upstream/downstream lineage from DataHub |
| `GET` | `/schema/{urn}` | `auth_guard` | `SchemaResponse` | Fetch schema metadata from DataHub REST API |
| `GET` | `/quotas/tiers` | `auth_guard` | `list[QuotaTierInfo]` | List quota tiers |
| `GET` | `/quotas/usage` | `auth_guard` | `QuotaUsageStatus` | Get current tenant quota usage |
| `GET` | `/quotas/limits` | `auth_guard` | `QuotaUsageStatus` | Get tenant quota limits |
| `POST` | `/quotas/set-tier` | `auth_guard` | `{"tenant_id", "tier", "status"}` | Update tenant quota tier |

**DataHub integration**: Async `httpx` calls to DataHub GMS GraphQL API with 30s timeout.

---

## Dependencies and Integration Points

- **Airbyte** — Source/destination connector provisioning (`apps.ingestion.lib.airbyte_client`)
- **DataHub GMS** — Metadata search, lineage, and schema via GraphQL/REST
- **Temporal** — Workflow orchestration for ingestion jobs
- **SpiceDB** — Authorization (via `require_permission()` decorators)
- **tenant_quotas** — Resource quota management (`apps.core.lib.tenant_quotas`)

## Error Handling

- 404 for missing sources, services, schemas, and jobs
- 403 for tenant ownership violations and policy denials
- 400 for invalid tier names and scan failures
- 500 for internal errors with `ERR_SYSTEM` messages
- 503 for DataHub unavailability (`ERR_DATAHUB_UNAVAILABLE`)
- Best-effort audit logging (swallows errors to never break request pipeline)
