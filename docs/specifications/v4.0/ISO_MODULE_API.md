# Voyant API Module — ISO 29148 Specification

| Field             | Value                                      |
|-------------------|--------------------------------------------|
| **Document ID**   | VOY-SPEC-API-v4.0                          |
| **Module**        | `apps.core.api` + SDKs + CLI               |
| **Version**       | 4.0.0                                      |
| **Status**        | Draft                                      |
| **Classification**| Internal                                   |
| **Authors**       | Voyant Platform Engineering                |
| **Last Updated**  | 2026-01-15                                 |

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Actors and Roles](#2-actors-and-roles)
3. [Screen Mockups](#3-screen-mockups)
4. [Functional Requirements](#4-functional-requirements)
5. [Data Models](#5-data-models)
6. [API Endpoints](#6-api-endpoints)
7. [SDK Usage Examples](#7-sdk-usage-examples)
8. [CLI Command Reference](#8-cli-command-reference)
9. [Integration Points](#9-integration-points)
10. [Non-Functional Requirements](#10-non-functional-requirements)
11. [Traceability Matrix](#11-traceability-matrix)

---

## 1. Module Overview

The **API** module defines the unified REST API surface of the Voyant Data Intelligence platform. It is the single entry point for all client interactions, aggregating 25+ domain routers into a cohesive `NinjaAPI` instance.

### 1.1 Architecture

```
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Python SDK   │   │ TypeScript SDK│   │  CLI (Click)  │
│  (httpx)      │   │  (fetch)      │   │               │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────┬───────┴───────────────────┘
                    ▼
        ┌───────────────────────┐
        │   Voyant REST API     │
        │   (Django Ninja)      │
        │                       │
        │   /v1/*               │
        └───────────┬───────────┘
                    │
    ┌───────┬───────┼───────┬───────┬───────┐
    ▼       ▼       ▼       ▼       ▼       ▼
┌───────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐
│Sources││ Jobs ││  SQL ││ Gov  ││ Onto ││  ML  ││
│       ││      ││      ││      ││      ││      │
└───────┘└──────┘└──────┘└──────┘└──────┘└──────┘
```

### 1.2 Scope

| In Scope                                          | Out of Scope                        |
|---------------------------------------------------|-------------------------------------|
| REST API surface (25+ routers)                    | GraphQL API                         |
| Python SDK (`voyant` package, httpx-based)        | gRPC interface                      |
| TypeScript SDK (`@voyant/sdk`, fetch-based)       | WebSocket protocol (see Workspace)  |
| CLI (`voyant` command, Click-based)               | Web dashboard (see Dashboard)       |
| Authentication (Keycloak JWT)                     | OAuth2 provider implementation      |
| Multi-tenancy (X-Tenant-ID header)                | Tenant provisioning API             |

### 1.3 References

| Reference                         | Description                           |
|-----------------------------------|---------------------------------------|
| ISO 29148:2018                    | Requirements engineering standard     |
| `apps/core/api.py`                | NinjaAPI registration (85 lines)      |
| `sdk/python/voyant/client.py`     | Python SDK (996 lines)                |
| `sdk/typescript/src/index.ts`     | TypeScript SDK (879 lines)            |
| `cli/main.py`                     | CLI entry point (110 lines)           |

---

## 2. Actors and Roles

### 2.1 Actor Definitions

| Actor ID         | Description                                          | Source                |
|------------------|------------------------------------------------------|-----------------------|
| `api_user`       | Authenticated user accessing the REST API            | Keycloak JWT          |
| `sdk_developer`  | Developer using Python or TypeScript SDK             | SDK instantiation     |
| `cli_user`       | Operator using the CLI tool                          | `voyant auth login`   |
| `service_account`| Automated service or CI/CD pipeline                  | Machine token         |
| `voyant-admin`   | Administrator with full platform access              | `voyant-admin` role   |

### 2.2 Authentication Methods

| Method           | Mechanism                     | Used By          |
|------------------|-------------------------------|------------------|
| Bearer Token     | `Authorization: Bearer <jwt>` | SDK, API clients |
| X-Tenant-ID      | `X-Tenant-ID: <tenant-id>`   | SDK, API clients |
| Query Param      | `?token=<jwt>`                | WebSocket        |
| CLI Config       | Stored in `~/.voyant/config`  | CLI              |

### 2.3 Permission Model

Permissions are checked via two decorators:

| Decorator                         | Description                              |
|-----------------------------------|------------------------------------------|
| `require_permission("read:*")`    | Requires any read permission             |
| `require_permission("write:X")`   | Requires write permission for resource X |
| `require_role("voyant-admin")`    | Requires specific Keycloak role          |

---

## 3. Screen Mockups

### 3.1 CLI Session Flow

```
$ voyant config set api-url https://voyant.example.com/v1
Set api-url = https://voyant.example.com/v1

$ voyant config set tenant-id tenant-abc
Set tenant-id = tenant-abc

$ voyant auth login
Opening browser for Keycloak authentication...
✓ Authenticated as alice@example.com

$ voyant status
Voyant v3.0.0 (production)
Uptime: 14d 7h 23m
Services:
  postgres    ● healthy
  redis       ● healthy
  trino       ● healthy
  temporal    ● healthy
  minio       ● healthy
  kafka       ● healthy
  milvus      ● healthy

$ voyant jobs list
┌──────────┬─────────┬────────────┬────────────┬──────────┐
│ Job ID   │ Type    │ Tenant     │ Status     │ Progress │
├──────────┼─────────┼────────────┼────────────┼──────────┤
│ a1b2c3d4 │ ingest  │ tenant-abc │ running    │ 65%      │
│ d4e5f6g7 │ profile │ tenant-abc │ completed  │ 100%     │
│ h8i9j0k1 │ quality │ tenant-abc │ failed     │ 45%      │
└──────────┴─────────┴────────────┴────────────┴──────────┘

$ voyant jobs get a1b2c3d4
Job ID:    a1b2c3d4
Type:      ingest
Status:    running (65%)
Tenant:    tenant-abc
Source:    source-uuid-123
Created:   2026-01-15 09:30:00
Parameters: {"mode": "full", "tables": ["orders"]}

$ voyant sql query "SELECT COUNT(*) FROM orders"
┌──────────┐
│ count(*) │
├──────────┤
│ 1247893  │
└──────────┘
(1 row, 45ms)

$ voyant ontology types list
┌────────────────┬─────────────────────┬──────────┬──────────┐
│ ID             │ Name                │ Props    │ Instances│
├────────────────┼─────────────────────┼──────────┼──────────┤
│ ot-001         │ Customer            │ 8        │ 12450    │
│ ot-002         │ Order               │ 12       │ 89234    │
│ ot-003         │ Product             │ 6        │ 3456     │
└────────────────┴─────────────────────┴──────────┴──────────┘

$ voyant scrape templates list
┌────────────┬──────────────────────┬──────────┐
│ ID         │ Name                 │ Status   │
├────────────┼──────────────────────┼──────────┤
│ tpl-001    │ E-commerce Product   │ active   │
│ tpl-002    │ News Articles        │ active   │
│ tpl-003    │ Government Data      │ draft    │
└────────────┴──────────────────────┴──────────┘
```

### 3.2 Python SDK Interactive Session

```python
>>> from voyant import VoyantClient
>>> client = VoyantClient(base_url="http://localhost:8000", token="eyJ...")
>>> sources = client.sources.list()
>>> len(sources)
34
>>> job = client.jobs.ingest(source_id="src-123", tables=["orders"])
>>> job["job_id"]
'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
>>> result = client.sql.query("SELECT * FROM orders LIMIT 5")
>>> result["columns"]
['id', 'customer_id', 'amount', 'created_at']
```

---

## 4. Functional Requirements

### 4.1 API Framework

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| API-F-001     | The API SHALL be implemented using Django Ninja with OpenAPI auto-documentation. | P0 | Implemented |
| API-F-001.1   | The API SHALL be versioned at `/v1/` prefix.                       | P0 | Implemented |
| API-F-001.2   | The API SHALL register 25+ domain routers under `/v1/`.           | P0 | Implemented |
| API-F-001.3   | The API SHALL support a separate MLflow-compatible API at `/api/2.0/mlflow/`. | P1 | Implemented |

### 4.2 Router Registration

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| API-F-002     | The API SHALL register the following routers:                      | P0 | Implemented |

| Router Tag            | Prefix              | Module                            |
|-----------------------|---------------------|-----------------------------------|
| `sources`             | `/v1/sources`       | `apps.discovery.api`              |
| `jobs`                | `/v1/jobs`          | `apps.workflows.api`              |
| `sql`                 | `/v1/sql`           | `apps.sql.api`                    |
| `governance`          | `/v1/governance`    | `apps.governance.api`             |
| `presets`             | `/v1/presets`       | `apps.workflows.api`              |
| `artifacts`           | `/v1/artifacts`     | `apps.workflows.api`              |
| `analyze`             | `/v1/analyze`       | `apps.analysis.api`               |
| `discovery`           | `/v1/discovery`     | `apps.discovery.api`              |
| `search`              | `/v1/search`        | `apps.search.api`                 |
| `scrape`              | `/v1/scrape`        | `apps.scraper.api`                |
| `scraper-templates`   | `/v1/scraper`       | `apps.scraper.template_api`       |
| `scraper-v2`          | `/v1/scraper/v2`    | `apps.scraper.api`                |
| `capsules`            | `/v1/capsules`      | `apps.capsules.api`               |
| `ingestion`           | `/v1/ingestion`     | `apps.ingestion.api`              |
| `admin`               | `/v1/admin`         | `apps.admin_panel.api`            |
| `ontology`            | `/v1/ontology`      | `apps.ontology.api`               |
| `ml`                  | `/v1/ml`            | `apps.ml_platform.api`            |
| `intent`              | `/v1/intent`        | `apps.intent.api`                 |
| `llm-providers`       | `/v1/llm`           | `apps.llm_providers.api`          |
| `auth`                | `/v1/auth`          | `apps.core.auth_api`              |
| `pipelines`           | `/v1/pipelines`     | `apps.pipelines.api`              |
| `dashboards`          | `/v1/dashboards`    | `apps.dashboard_builder.api`      |
| `features`            | `/v1/features`      | `apps.features.api`               |
| `notifications`       | `/v1/notifications` | `apps.notifications.api`          |
| `workspaces`          | `/v1/workspaces`    | `apps.workspaces.api`             |
| `approvals`           | `/v1/approvals`     | `apps.approvals.api`              |

### 4.3 Python SDK

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| API-F-003     | The Python SDK SHALL provide a `VoyantClient` class wrapping all API resources. | P0 | Implemented |
| API-F-003.1   | The SDK SHALL use `httpx` as the HTTP transport.                   | P0 | Implemented |
| API-F-003.2   | The SDK SHALL support `Bearer` token authentication.               | P0 | Implemented |
| API-F-003.3   | The SDK SHALL support `X-Tenant-ID` header for multi-tenancy.     | P0 | Implemented |
| API-F-003.4   | The SDK SHALL raise `VoyantAPIError` for non-2xx responses.       | P0 | Implemented |
| API-F-003.5   | The SDK SHALL support context manager (`with` statement) for cleanup. | P0 | Implemented |
| API-F-003.6   | The SDK SHALL provide resource namespaces: sources, jobs, artifacts, sql, ontology, scraper, ml, governance, auth, search, intent, capsules, discovery, admin. | P0 | Implemented |

### 4.4 TypeScript SDK

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| API-F-004     | The TypeScript SDK SHALL provide a `VoyantClient` class with resource namespaces. | P0 | Implemented |
| API-F-004.1   | The SDK SHALL use native `fetch` as the HTTP transport.            | P0 | Implemented |
| API-F-004.2   | The SDK SHALL support `AbortController` for request timeout.      | P0 | Implemented |
| API-F-004.3   | The SDK SHALL raise `VoyantAPIError` for non-OK responses.        | P0 | Implemented |
| API-F-004.4   | The SDK SHALL provide resource namespaces: sources, jobs, sql, ontology, scraper, ml, governance, auth, search, capsules, admin. | P0 | Implemented |

### 4.5 CLI

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| API-F-005     | The CLI SHALL be implemented using Click with command groups.       | P0 | Implemented |
| API-F-005.1   | The CLI SHALL support configuration via `voyant config set/show`.  | P0 | Implemented |
| API-F-005.2   | The CLI SHALL support authentication via `voyant auth login`.      | P0 | Implemented |
| API-F-005.3   | The CLI SHALL provide command groups: auth, jobs, ontology, sql, scrape, pipelines, dashboards, status. | P0 | Implemented |
| API-F-005.4   | The CLI SHALL display version via `voyant --version`.              | P0 | Implemented |

---

## 5. Data Models

### 5.1 API Error Model

```python
class VoyantAPIError(Exception):
    status_code: int     # HTTP status code
    error_code: str      # Application error code
    detail: Any          # Response body (JSON or text)
```

### 5.2 Client Configuration

#### Python

```python
class VoyantClient:
    base_url: str    # Default: "http://localhost:8000"
    token: str       # Bearer token
    timeout: float   # Default: 60.0 seconds
    tenant_id: str   # Sent as X-Tenant-ID header
```

#### TypeScript

```typescript
interface VoyantClientOptions {
    baseUrl?: string;    // Default: "http://localhost:8000"
    token?: string;      // Bearer token
    timeout?: number;    // Default: 60_000 ms
    tenantId?: string;   // Sent as X-Tenant-ID header
}
```

### 5.3 Resource Namespace Mapping

| SDK Resource        | Python Class           | TypeScript Class       | API Prefix             |
|---------------------|------------------------|------------------------|------------------------|
| `sources`           | `SourcesResource`      | `SourcesResource`      | `/v1/sources`          |
| `jobs`              | `JobsResource`         | `JobsResource`         | `/v1/jobs`             |
| `artifacts`         | `ArtifactsResource`    | —                      | `/v1/artifacts`        |
| `sql`               | `SQLResource`          | `SQLResource`          | `/v1/sql`              |
| `ontology`          | `OntologyResource`     | `OntologyResource`     | `/v1/ontology`         |
| `scraper`           | `ScraperResource`      | `ScraperResource`      | `/v1/scrape`           |
| `ml`                | `MLResource`           | `MLResource`           | `/v1/ml`               |
| `governance`        | `GovernanceResource`   | `GovernanceResource`   | `/v1/governance`       |
| `auth`              | `AuthResource`         | `AuthResource`         | `/v1/auth`             |
| `search`            | `SearchResource`       | `SearchResource`       | `/v1/search`           |
| `intent`            | `IntentResource`       | —                      | `/v1/intent`           |
| `capsules`          | `CapsulesResource`     | `CapsulesResource`     | `/v1/capsules`         |
| `discovery`         | `DiscoveryResource`    | —                      | `/v1/discovery`        |
| `admin`             | `AdminResource`        | `AdminResource`        | `/v1/admin`            |

---

## 6. API Endpoints

### 6.1 Sources

| Method   | Path                        | Description                    |
|----------|-----------------------------|--------------------------------|
| `GET`    | `/v1/sources`               | List data sources              |
| `GET`    | `/v1/sources/{id}`          | Get source by ID               |
| `POST`   | `/v1/sources`               | Create data source             |
| `PUT`    | `/v1/sources/{id}`          | Update source                  |
| `DELETE` | `/v1/sources/{id}`          | Delete source                  |
| `POST`   | `/v1/sources/discover`      | Discover source type from hint |
| `POST`   | `/v1/ingestion/connect`     | Provision Airbyte connector    |

### 6.2 Jobs

| Method   | Path                        | Description                    |
|----------|-----------------------------|--------------------------------|
| `GET`    | `/v1/jobs`                  | List jobs                      |
| `GET`    | `/v1/jobs/{id}`             | Get job details                |
| `POST`   | `/v1/jobs/{id}/cancel`      | Cancel job                     |
| `POST`   | `/v1/jobs/ingest`           | Start ingestion job            |
| `POST`   | `/v1/jobs/profile`          | Start profiling job            |
| `POST`   | `/v1/jobs/quality`          | Start quality check job        |
| `POST`   | `/v1/analyze`               | Start full analysis job        |

### 6.3 SQL

| Method   | Path                        | Description                    |
|----------|-----------------------------|--------------------------------|
| `GET`    | `/v1/sql/tables`            | List tables                    |
| `GET`    | `/v1/sql/tables/{table}/columns` | List table columns       |
| `POST`   | `/v1/sql/query`             | Execute SQL query              |

### 6.4 Artifacts

| Method   | Path                                      | Description              |
|----------|-------------------------------------------|--------------------------|
| `GET`    | `/v1/artifacts/{job_id}`                  | List artifacts for job   |
| `GET`    | `/v1/artifacts/{job_id}/{type}/download`  | Download artifact        |

### 6.5 Governance

| Method   | Path                                | Description                    |
|----------|-------------------------------------|--------------------------------|
| `GET`    | `/v1/governance/search`             | Search datasets via DataHub    |
| `GET`    | `/v1/governance/lineage/{urn}`      | Get lineage graph              |
| `GET`    | `/v1/governance/schema/{urn}`       | Get dataset schema             |
| `GET`    | `/v1/governance/quotas/tiers`       | List quota tiers               |
| `GET`    | `/v1/governance/quotas/usage`       | Get quota usage                |
| `GET`    | `/v1/governance/quotas/limits`      | Get quota limits               |
| `POST`   | `/v1/governance/quotas/set-tier`    | Set tenant tier                |
| `GET`    | `/v1/governance/classifications`    | List classifications           |
| `POST`   | `/v1/governance/classifications`    | Create classification          |
| `GET`    | `/v1/governance/security-policies`  | List security policies         |
| `POST`   | `/v1/governance/security-policies`  | Create security policy         |
| `GET`    | `/v1/governance/security-policies/{id}` | Get security policy      |
| `PUT`    | `/v1/governance/security-policies/{id}` | Update security policy    |
| `DELETE` | `/v1/governance/security-policies/{id}` | Delete security policy    |
| `GET`    | `/v1/governance/column-mask-defs`   | List column masks              |
| `POST`   | `/v1/governance/column-mask-defs`   | Create column mask             |
| `GET`    | `/v1/governance/column-mask-defs/{id}` | Get column mask           |
| `PUT`    | `/v1/governance/column-mask-defs/{id}` | Update column mask         |
| `DELETE` | `/v1/governance/column-mask-defs/{id}` | Delete column mask         |
| `GET`    | `/v1/governance/catalog`            | Browse data catalog            |
| `GET`    | `/v1/governance/lineage-graph`      | Get lineage graph (in-memory)  |
| `POST`   | `/v1/governance/gdpr/delete`        | Trigger GDPR deletion          |
| `GET`    | `/v1/governance/gdpr/status/{id}`   | Check GDPR deletion status     |

### 6.6 Other Domains

| Domain       | Prefix                  | Key Operations                                         |
|--------------|-------------------------|--------------------------------------------------------|
| Ontology     | `/v1/ontology`          | Types CRUD, Objects CRUD, Links, Actions, Functions    |
| Scraper      | `/v1/scrape`            | Fetch, Extract, OCR, PDF, Transcribe, Deep Archive     |
| Scraper v2   | `/v1/scraper/v2`        | Workflows, Proxies, Schedules, Runs, Fingerprints      |
| ML           | `/v1/ml`                | Models, Experiments, Agents, Endpoints                 |
| Auth         | `/v1/auth`              | Login, Logout, Refresh, Me, Token                      |
| Search       | `/v1/search`            | Index, Query, Delete                                   |
| Intent       | `/v1/intent`            | Query, Execute, Config, Cache                          |
| Capsules     | `/v1/capsules`          | Registry, Create, Install, Run, Uninstall              |
| Ingestion    | `/v1/ingestion`         | Connect (Airbyte)                                      |
| Pipelines    | `/v1/pipelines`         | Pipeline CRUD, Execute                                 |
| Dashboards   | `/v1/dashboards`        | Dashboard CRUD                                         |
| Features     | `/v1/features`          | Feature flags                                          |
| LLM          | `/v1/llm`               | LLM provider management                               |
| Notifications| `/v1/notifications`     | List, Create, Mark read, Preferences                   |
| Workspaces   | `/v1/workspaces`        | CRUD, Members, Assets, Comments, Activity              |
| Approvals    | `/v1/approvals`         | Approve, Reject, Rules                                 |
| Admin        | `/v1/admin`             | Dashboard, Jobs, Sources, Governance, Settings, SQL    |

---

## 7. SDK Usage Examples

### 7.1 Python SDK

#### Installation

```bash
pip install voyant-sdk
```

#### Client Initialization

```python
from voyant import VoyantClient

# Basic usage
client = VoyantClient(
    base_url="https://voyant.example.com",
    token="your-bearer-token",
    tenant_id="tenant-abc",
)

# Context manager (recommended)
with VoyantClient(base_url="http://localhost:8000", token="eyJ...") as client:
    sources = client.sources.list()
```

#### Sources

```python
# List all sources
sources = client.sources.list()
for s in sources:
    print(f"{s['name']} ({s['source_type']}) — {s['status']}")

# Create a new source
source = client.sources.create(
    name="Production DB",
    source_type="postgres",
    connection_config={
        "host": "db.example.com",
        "port": 5432,
        "database": "analytics",
    },
    credentials={"username": "reader", "password": "***"},
)

# Discover source type
hint = client.sources.discover(hint="jdbc:postgresql://...")
```

#### Jobs

```python
# Start an ingestion job
job = client.jobs.ingest(
    source_id="source-uuid",
    tables=["orders", "customers"],
    mode="full",
)
print(f"Job created: {job['job_id']}")

# Start profiling
profile_job = client.jobs.profile(
    source_id="source-uuid",
    table="orders",
    sample_size=50000,
)

# Run quality checks
quality_job = client.jobs.quality(
    source_id="source-uuid",
    table="orders",
    checks=["null_check", "uniqueness", "range"],
)

# Full analysis
result = client.jobs.analyze(
    source_id="source-uuid",
    table="orders",
    analyzers=["distribution", "correlation", "outlier"],
    kpis=[{"name": "revenue", "sql": "SELECT SUM(amount) FROM orders"}],
    sample_size=10000,
)

# Monitor job
job_detail = client.jobs.get(job["job_id"])
print(f"Status: {job_detail['status']}, Progress: {job_detail['progress']}%")

# Cancel if needed
client.jobs.cancel(job["job_id"])

# List jobs with filters
running_jobs = client.jobs.list(status="running")
ingest_jobs = client.jobs.list(job_type="ingest")
```

#### SQL

```python
# List tables
tables = client.sql.tables()

# List columns
columns = client.sql.columns("orders")

# Execute query
result = client.sql.query("SELECT COUNT(*) as cnt FROM orders WHERE amount > 100")
print(result["rows"])  # [[1247893]]
```

#### Ontology

```python
# List object types
types = client.ontology.list_types()

# Create a new type
new_type = client.ontology.create_type(
    name="Customer",
    description="Customer entity",
    properties=[
        {"name": "email", "property_type": "string", "required": True},
        {"name": "lifetime_value", "property_type": "float"},
    ],
)

# Create an object
customer = client.ontology.create_object(
    object_type_id=new_type["id"],
    properties={"email": "alice@example.com", "lifetime_value": 12500.0},
)

# Traverse relationships
graph = client.ontology.traverse(customer["id"], depth=3)
```

#### Scraper

```python
# Fetch a web page
result = client.scraper.fetch(
    url="https://example.com/products",
    engine="playwright",
    wait_for=".product-list",
    scroll=True,
)

# Extract data from HTML
data = client.scraper.extract(
    html=result["html"],
    selectors={
        "titles": {"selector": "h2.product-title", "type": "list"},
        "prices": {"selector": ".price", "type": "list"},
    },
)

# OCR an image
text = client.scraper.ocr(image_url="https://example.com/scan.png")

# Parse a PDF
pdf_data = client.scraper.parse_pdf(
    pdf_url="https://example.com/report.pdf",
    extract_tables=True,
)

# Transcribe audio
transcript = client.scraper.transcribe(media_url="https://example.com/audio.mp3")
```

#### Governance

```python
# Search governed datasets
results = client.governance.search("customer_data", limit=10)

# Get lineage
lineage = client.governance.lineage("urn:li:dataset:abc123")
for node in lineage["nodes"]:
    print(f"  {node['name']} ({node['type']})")

# Get schema
schema = client.governance.schema("urn:li:dataset:abc123")
for field in schema["fields"]:
    print(f"  {field['name']}: {field['type']}")

# Check quota usage
usage = client.governance.quota_usage()
print(f"Jobs: {usage['jobs_today']}/{usage['jobs_limit']}")
print(f"Storage: {usage['artifacts_gb']}GB/{usage['artifacts_limit_gb']}GB")

# List classifications
classifications = client.governance.list_classifications()
```

#### ML Platform

```python
# List models
models = client.ml.list_models()

# Create model and version
model = client.ml.create_model(name="churn-predictor")
version = client.ml.create_model_version(model["id"], version="2.0", stage="staging")

# Experiment tracking
experiment = client.ml.create_experiment(name="hyperparam-search")
run = client.ml.create_run(experiment["id"])
client.ml.log_metrics(run["id"], {"accuracy": 0.942, "f1": 0.918})

# Manage agents
agent = client.ml.create_agent(name="data-analyst-agent")
```

#### Admin

```python
# System overview
overview = client.admin.dashboard()
print(f"Version: {overview['version']}, Uptime: {overview['uptime_seconds']}s")

# List tenants
tenants = client.admin.list_tenants()

# Update a setting
client.admin.update_setting("max_concurrent_jobs", 20)

# Execute SQL (admin)
result = client.admin.sql_execute("SHOW SCHEMAS")
```

### 7.2 TypeScript SDK

#### Installation

```bash
npm install @voyant/sdk
```

#### Client Initialization

```typescript
import { VoyantClient } from "@voyant/sdk";

const client = new VoyantClient({
  baseUrl: "https://voyant.example.com",
  token: "your-bearer-token",
  tenantId: "tenant-abc",
  timeout: 60_000,
});
```

#### Sources

```typescript
// List sources
const sources = await client.sources.list();

// Create source
const source = await client.sources.create({
  name: "Production DB",
  sourceType: "postgres",
  connectionConfig: { host: "db.example.com", port: 5432 },
});
```

#### Jobs

```typescript
// Start ingestion
const job = await client.jobs.ingest({
  sourceId: "source-uuid",
  tables: ["orders"],
  mode: "full",
});

// Monitor
const detail = await client.jobs.get(job.job_id);
console.log(`Status: ${detail.status}, Progress: ${detail.progress}%`);

// Full analysis
const analysis = await client.jobs.analyze({
  sourceId: "source-uuid",
  table: "orders",
  analyzers: ["distribution", "correlation"],
  sampleSize: 50000,
});
```

#### Scraper

```typescript
// Fetch page
const result = await client.scraper.fetch({
  url: "https://example.com",
  engine: "playwright",
  waitFor: ".content",
  scroll: true,
});

// OCR
const ocrResult = await client.scraper.ocr({
  imageUrl: "https://example.com/scan.png",
  language: "eng",
});
```

#### Governance

```typescript
// Search datasets
const results = await client.governance.search("customer_data");

// Get lineage
const lineage = await client.governance.lineage("urn:li:dataset:abc123");

// Quota usage
const usage = await client.governance.quotaUsage();
console.log(`Jobs: ${usage.jobs_today}/${usage.jobs_limit}`);
```

#### Capsules

```typescript
// Browse registry
const registry = await client.capsules.registry();

// Install and run
const install = await client.capsules.install({ capsuleId: "cap-001" });
const result = await client.capsules.run({
  installationId: install.id,
  parameterValues: { threshold: 0.95 },
});
```

---

## 8. CLI Command Reference

### 8.1 Global Commands

| Command                   | Description                        |
|---------------------------|------------------------------------|
| `voyant --version`        | Show CLI version                   |
| `voyant --help`           | Show help text                     |
| `voyant config set K V`   | Set configuration value            |
| `voyant config show`      | Show current configuration         |

### 8.2 Configuration Keys

| Key              | Description                        | Example                          |
|------------------|------------------------------------|----------------------------------|
| `api-url`        | Voyant API base URL                | `https://voyant.example.com/v1`  |
| `tenant-id`      | Default tenant ID                  | `tenant-abc`                     |
| `keycloak-url`   | Keycloak authentication URL        | `https://keycloak.example.com`   |

### 8.3 Auth Commands

| Command                   | Description                        |
|---------------------------|------------------------------------|
| `voyant auth login`       | Authenticate via Keycloak          |
| `voyant auth logout`      | Clear stored credentials           |

### 8.4 Jobs Commands

| Command                              | Description                   |
|--------------------------------------|-------------------------------|
| `voyant jobs list`                   | List background jobs          |
| `voyant jobs get <job_id>`           | Get job details               |
| `voyant jobs cancel <job_id>`        | Cancel a running job          |

### 8.5 Ontology Commands

| Command                                        | Description                    |
|------------------------------------------------|--------------------------------|
| `voyant ontology types list`                   | List object types              |
| `voyant ontology objects list <type_id>`       | List objects by type           |

### 8.6 SQL Commands

| Command                        | Description                   |
|--------------------------------|-------------------------------|
| `voyant sql query "<SQL>"`    | Execute SQL query             |

### 8.7 Scrape Commands

| Command                            | Description                    |
|------------------------------------|--------------------------------|
| `voyant scrape templates list`     | List scrape templates          |

### 8.8 Pipelines Commands

| Command                      | Description                   |
|------------------------------|-------------------------------|
| `voyant pipelines list`      | List pipelines                |

### 8.9 Dashboards Commands

| Command                       | Description                   |
|-------------------------------|-------------------------------|
| `voyant dashboards list`      | List dashboards               |

### 8.10 Status Command

| Command              | Description                              |
|----------------------|------------------------------------------|
| `voyant status`      | Show system status and service health    |

---

## 9. Integration Points

| System         | Integration Type    | Direction | Description                                      |
|----------------|---------------------|-----------|--------------------------------------------------|
| **Keycloak**   | JWT authentication  | Inbound   | Token validation for all API requests            |
| **PostgreSQL** | Django ORM          | Internal  | All data persistence                             |
| **Trino**      | SQL execution       | Outbound  | SQL query execution, table/column metadata       |
| **DataHub**    | GraphQL API         | Outbound  | Metadata search, lineage, schema                 |
| **Temporal**   | Workflow orchestration| Outbound | Async job execution, GDPR deletion               |
| **Redis**      | Cache + Channel layer| Internal | Caching, WebSocket pub/sub                       |
| **Kafka**      | Event streaming     | Outbound  | Domain event publishing                          |
| **Milvus**     | Vector store        | Outbound  | Semantic search indexing and querying            |
| **MinIO**      | Object storage      | Outbound  | Artifact storage                                 |
| **Vault**      | Secrets management  | Outbound  | Credential and secret storage                    |
| **Airbyte**    | Data integration    | Outbound  | Source connector provisioning                    |

---

## 10. Non-Functional Requirements

| NFR-ID      | Requirement                                                           | Target     |
|-------------|-----------------------------------------------------------------------|------------|
| API-NF-001  | API response time SHALL be <500ms for CRUD operations.               | 500ms p95  |
| API-NF-002  | The API SHALL support 1,000 concurrent requests.                     | 1,000      |
| API-NF-003  | SDK default timeout SHALL be 60 seconds.                             | 60s        |
| API-NF-004  | The CLI SHALL start and display help within 1 second.                | 1s         |
| API-NF-005  | All API errors SHALL return structured JSON with status code and detail. | 100%    |
| API-NF-006  | The API SHALL enforce tenant isolation on all endpoints.             | 100%       |
| API-NF-007  | OpenAPI documentation SHALL be auto-generated and always current.    | 100%       |
| API-NF-008  | SDK packages SHALL have >90% test coverage.                         | 90%        |
| API-NF-009  | The API SHALL support CORS for dashboard frontend origins.           | Required   |
| API-NF-010  | Rate limiting SHALL be enforced: 100 requests/second per token.      | 100 req/s  |

---

## 11. Traceability Matrix

| Requirement  | Component                  | Source File                        | Line Range |
|--------------|----------------------------|------------------------------------|------------|
| API-F-001    | NinjaAPI setup             | `apps/core/api.py`                 | 41-46      |
| API-F-001.2  | Router registration        | `apps/core/api.py`                 | 48-74      |
| API-F-001.3  | MLflow API                 | `apps/core/api.py`                 | 78-85      |
| API-F-002    | All routers                | `apps/core/api.py`                 | 48-74      |
| API-F-003    | Python SDK client          | `sdk/python/voyant/client.py`      | 887-996    |
| API-F-003.1  | httpx transport            | `sdk/python/voyant/client.py`      | 916-919    |
| API-F-003.6  | Resource namespaces        | `sdk/python/voyant/client.py`      | 922-935    |
| API-F-004    | TypeScript SDK client      | `sdk/typescript/src/index.ts`      | 763-877    |
| API-F-004.1  | fetch transport            | `sdk/typescript/src/index.ts`      | 847-852    |
| API-F-004.4  | Resource namespaces        | `sdk/typescript/src/index.ts`      | 799-809    |
| API-F-005    | CLI entry point            | `cli/main.py`                      | 35-61      |
| API-F-005.1  | Config commands            | `cli/main.py`                      | 63-101     |
| API-F-005.3  | Command groups             | `cli/main.py`                      | 53-60      |
