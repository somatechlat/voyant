# Voyant Admin Module — ISO 29148 Specification

| Field             | Value                                      |
|-------------------|--------------------------------------------|
| **Document ID**   | VOY-SPEC-ADMIN-v4.0                        |
| **Module**        | `apps.admin_panel`                         |
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
7. [Integration Points](#7-integration-points)
8. [Infrastructure Health Checks](#8-infrastructure-health-checks)
9. [Non-Functional Requirements](#9-non-functional-requirements)
10. [Traceability Matrix](#10-traceability-matrix)

---

## 1. Module Overview

The **Admin** module provides the operational control plane for the Voyant platform. It is accessible only to users with the `voyant-admin` role and provides management interfaces for every Voyant domain:

1. **System Dashboard** — real-time overview of jobs, sources, artifacts, capsules, tenants, audit events, and service health.
2. **Job Management** — list, inspect, cancel, and reset jobs across all tenants.
3. **Source Management** — list, create, and delete data sources.
4. **Governance Administration** — list policies, contracts, and quota usage.
5. **Capsule Management** — list, activate, suspend, and archive capsules.
6. **Ontology Administration** — browse object types, properties, and link types.
7. **Audit Log** — search and filter audit events across the entire platform.
8. **System Settings** — list and update key-value configuration settings.
9. **SQL Console** — execute read-only SQL queries via Trino.
10. **Search Index** — index, query, and delete vector search documents.
11. **Scraper Management** — list scrape jobs.
12. **Tenant Management** — list all tenants with activity summaries.

### 1.1 Scope

| In Scope                                          | Out of Scope                        |
|---------------------------------------------------|-------------------------------------|
| System dashboard and health monitoring            | Infrastructure provisioning         |
| Cross-tenant job management                       | Per-tenant job views (see Jobs API) |
| Source CRUD (admin override)                      | Source discovery logic              |
| Governance policy/contract/quota listing          | Policy enforcement (see Governance) |
| Capsule lifecycle management                      | Capsule marketplace                 |
| Ontology browsing (read-only)                     | Ontology CRUD (see Ontology API)    |
| Audit log search and filtering                    | Audit log generation (middleware)   |
| System setting management                         | Vault secret management             |
| SQL console (read-only Trino)                     | Write operations on data            |
| Vector search management                          | Embedding model training            |
| Scraper job listing                               | Scraper template management         |
| Tenant listing and activity summary               | Tenant provisioning                 |

### 1.2 References

| Reference                         | Description                           |
|-----------------------------------|---------------------------------------|
| ISO 29148:2018                    | Requirements engineering standard     |
| `apps/admin_panel/api.py`         | Admin REST API (1010 lines)           |
| `apps/admin_panel/schemas.py`     | Admin request/response schemas        |
| `dashboard/src/views/view-governance.ts` | Governance dashboard view      |
| `dashboard/src/views/view-audit.ts`      | Audit log view                 |
| `dashboard/src/views/view-settings.ts`   | Settings view                  |
| `dashboard/src/views/view-tenants.ts`    | Tenants view                   |
| `dashboard/src/views/view-jobs.ts`       | Jobs management view           |

---

## 2. Actors and Roles

### 2.1 Actor Definitions

| Actor ID         | Description                                          | Source                |
|------------------|------------------------------------------------------|-----------------------|
| `voyant-admin`   | Platform administrator with full admin panel access  | `voyant-admin` Keycloak role |
| `platform_ops`   | Infrastructure operations (read-only health checks)  | Subset of admin       |
| `system`         | Internal automated processes                         | Service accounts      |

### 2.2 Role-Permission Matrix

| Permission                    | voyant-admin | platform_ops | system |
|-------------------------------|:------------:|:------------:|:------:|
| View system dashboard         |      ✓       |      ✓       |   ✗    |
| List/manage jobs              |      ✓       |      ✓       |   ✗    |
| Cancel/reset jobs             |      ✓       |      ✗       |   ✗    |
| Create/delete sources         |      ✓       |      ✗       |   ✗    |
| View governance data          |      ✓       |      ✓       |   ✗    |
| Manage capsules               |      ✓       |      ✗       |   ✗    |
| Browse ontology               |      ✓       |      ✓       |   ✗    |
| View audit log                |      ✓       |      ✓       |   ✗    |
| Update system settings        |      ✓       |      ✗       |   ✗    |
| Execute SQL queries           |      ✓       |      ✗       |   ✗    |
| Manage search index           |      ✓       |      ✗       |   ✗    |
| List tenants                  |      ✓       |      ✓       |   ✗    |

**Auth:** All admin endpoints require `require_role("voyant-admin")`.

---

## 3. Screen Mockups

### 3.1 System Dashboard

```
┌──────────────────────────────────────────────────────────────────────┐
│  [Sidebar]  Dashboard                                                │
│                                                                      │
│  Voyant v3.0.0  |  env: production  |  uptime: 14d 7h 23m          │
│                                                                      │
│  ┌─ Stats ──────────────────────────────────────────────────────────┐│
│  │                                                                  ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            ││
│  │  │  1,247   │ │    45    │ │    12    │ │    89    │            ││
│  │  │  Jobs    │ │ Running  │ │  Queued  │ │  Failed  │            ││
│  │  │  Total   │ │          │ │          │ │          │            ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘            ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            ││
│  │  │    34    │ │    28    │ │    5     │ │  1,892   │            ││
│  │  │ Sources  │ │  Active  │ │ Tenants  │ │ Audit 24h│            ││
│  │  │  Total   │ │          │ │  Active  │ │          │            ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘            ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌─ Services ───────────────────────────────────────────────────────┐│
│  │                                                                  ││
│  │  postgres    ● healthy     │  redis       ● healthy              ││
│  │  trino       ● healthy     │  kafka       ● healthy              ││
│  │  temporal    ● healthy     │  milvus      ● healthy              ││
│  │  vault       ● healthy     │  minio       ● healthy              ││
│  │  ml_platform ● degraded    │  scraper     ● healthy              ││
│  │                                                                  ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌─ Policy Violations (24h) ────────────────────────────────────────┐│
│  │  3 violations detected                                            ││
│  │  Last: "PII access denied for analyst-02 at 14:32 UTC"           ││
│  └──────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 Jobs Management

```
┌──────────────────────────────────────────────────────────────────────┐
│  [Sidebar]  Jobs                                                     │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ [Status ▼] [Type ▼] [Refresh]  [+ New Job]                     │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─ Create New Job ────────────────────────────────────────────────┐ │
│  │  Type: [ingest ▼]  Source ID: [source-uuid____]                 │ │
│  │  Table: [________]  Sample Size: [10000]                        │ │
│  │                                        [Create Job]             │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ Job ID  │ Type    │ Tenant     │ Status     │ Progress │ Actions ││
│  ├─────────┼─────────┼────────────┼────────────┼──────────┼─────────││
│  │ a1b2c3  │ ingest  │ tenant-abc │ ● running  │ ████░ 65%│ [Cancel]││
│  │ d4e5f6  │ profile │ tenant-xyz │ ● queued   │ ░░░░░  0%│ [Cancel]││
│  │ g7h8i9  │ quality │ tenant-abc │ ● completed│ █████100%│         ││
│  │ j0k1l2  │ analyze │ tenant-lmn │ ○ failed   │ ███░░ 45%│ [Reset] ││
│  │ m3n4o5  │ ingest  │ tenant-abc │ ○ cancelled│ ██░░░ 20%│         ││
│  └─────────┴─────────┴────────────┴────────────┴──────────┴─────────┘│
│                                                                      │
│  ┌─ Job Detail Drawer (slide-in) ──────────────────────────────────┐│
│  │  Job ID: a1b2c3d4e5f6                                           ││
│  │  Type: ingest     Status: running     Progress: 65%             ││
│  │  Tenant: tenant-abc    Source: source-uuid-123                   ││
│  │  Created: 2026-01-15 09:30                                      ││
│  │                                                                 ││
│  │  Parameters:                                                    ││
│  │  { "mode": "full", "tables": ["orders", "customers"] }          ││
│  │                                                                 ││
│  │  Result Summary:                                                ││
│  │  { "rows_ingested": 1_247_893, "tables_processed": 2 }          ││
│  │                                                                 ││
│  │  Artifacts (2):                                                 ││
│  │  ┌─────────────┬──────────┬────────────┐                        ││
│  │  │ profile     │ parquet  │ 2.3MB      │ [Download]             ││
│  │  │ quality     │ json     │ 45KB       │ [Download]             ││
│  │  └─────────────┴──────────┴────────────┘                        ││
│  │                                                                 ││
│  │  [Cancel Job]                                                   ││
│  └─────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### 3.3 Audit Log

```
┌──────────────────────────────────────────────────────────────────────┐
│  [Sidebar]  Audit Log                                                │
│                                                                      │
│  Audit Log                            [Filter by action...] [Refresh]│
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ Actor        │ Action         │ Resource      │ Outcome  │ Time  ││
│  ├──────────────┼────────────────┼───────────────┼──────────┼───────││
│  │ alice        │ policy.create  │ Policy:a1b2   │ success  │ 14:32 ││
│  │ bob          │ job.cancel     │ Job:c3d4      │ success  │ 14:28 ││
│  │ analyst-02   │ query.execute  │ Table:orders  │ denied   │ 14:25 ││
│  │ carol        │ source.delete  │ Source:e5f6   │ success  │ 14:20 ││
│  │ system       │ quota.exceeded │ Tenant:xyz    │ warning  │ 14:15 ││
│  │ dave         │ auth.login     │ Session:g7h8  │ failure  │ 14:10 ││
│  └──────────────┴────────────────┴───────────────┴──────────┴───────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### 3.4 System Settings

```
┌──────────────────────────────────────────────────────────────────────┐
│  [Sidebar]  System Settings                                          │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ ◆ max_concurrent_jobs                                            ││
│  │   [int]                                                          ││
│  │   Maximum concurrent running jobs across all tenants             ││
│  │   Value: 20                                      [Edit]          ││
│  ├──────────────────────────────────────────────────────────────────┤│
│  │ ◆ default_sample_size                                            ││
│  │   [int]                                                          ││
│  │   Default sample size for profiling and quality checks           ││
│  │   Value: 10000                                   [Edit]          ││
│  ├──────────────────────────────────────────────────────────────────┤│
│  │ ◆ datahub_gms_token                                              ││
│  │   [str]  [secret]                                                ││
│  │   DataHub GMS authentication token                               ││
│  │   Value: ***                                       (no edit)     ││
│  ├──────────────────────────────────────────────────────────────────┤│
│  │ ◆ scrape_rate_limit                                              ││
│  │   [int]                                                          ││
│  │   Max pages per minute for scraper                               ││
│  │   Value: 30                                      [Edit]          ││
│  └──────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### 3.5 Tenants

```
┌──────────────────────────────────────────────────────────────────────┐
│  [Sidebar]  Tenants                                                  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ Tenant ID     │ Realm    │ Jobs  │ Sources │ Artifacts │ Activity││
│  ├───────────────┼──────────┼───────┼─────────┼───────────┼─────────││
│  │ tenant-abc    │ default  │ 847   │ 12      │ 234       │ 2m ago  ││
│  │ tenant-xyz    │ default  │ 234   │ 5       │ 89        │ 1h ago  ││
│  │ tenant-lmn    │ default  │ 156   │ 8       │ 45        │ 3h ago  ││
│  │ tenant-qrs    │ default  │ 10    │ 2       │ 3         │ 2d ago  ││
│  └───────────────┴──────────┴───────┴─────────┴───────────┴─────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Functional Requirements

### 4.1 System Dashboard

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| ADM-F-001     | The system SHALL provide a dashboard showing total jobs, running, queued, failed, and completed counts. | P0 | Implemented |
| ADM-F-001.1   | The dashboard SHALL show total sources and active (connected) sources. | P0 | Implemented |
| ADM-F-001.2   | The dashboard SHALL show total artifacts, capsules, and tenants.   | P0 | Implemented |
| ADM-F-001.3   | The dashboard SHALL show audit events in the last 24 hours and policy violation count. | P0 | Implemented |
| ADM-F-001.4   | The dashboard SHALL display service health status for all infrastructure components. | P0 | Implemented |
| ADM-F-001.5   | Service health SHALL map circuit breaker states (closed/half_open/open) to status (healthy/degraded/down). | P0 | Implemented |

### 4.2 Job Management

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| ADM-F-002     | The system SHALL list all jobs across all tenants with filtering by status, job_type, and tenant_id. | P0 | Implemented |
| ADM-F-002.1   | The system SHALL show job details including parameters, result_summary, error_message, and artifacts. | P0 | Implemented |
| ADM-F-002.2   | The system SHALL allow cancelling running/queued jobs.             | P0 | Implemented |
| ADM-F-002.3   | Job cancellation SHALL cancel the associated Temporal workflow.    | P0 | Implemented |
| ADM-F-002.4   | The system SHALL allow resetting failed jobs back to queued status. | P0 | Implemented |
| ADM-F-002.5   | Job reset SHALL clear progress, error_message, started_at, and completed_at. | P0 | Implemented |

### 4.3 Source Management

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| ADM-F-003     | The system SHALL list all data sources across tenants.             | P0 | Implemented |
| ADM-F-003.1   | The system SHALL allow admin creation of new data sources (bypassing tenant restrictions). | P0 | Implemented |
| ADM-F-003.2   | The system SHALL allow deletion of data sources.                  | P0 | Implemented |

### 4.4 Governance Administration

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| ADM-F-004     | The system SHALL list all governance policies with optional tenant filtering. | P0 | Implemented |
| ADM-F-004.1   | The system SHALL list all data contracts with optional tenant filtering. | P0 | Implemented |
| ADM-F-004.2   | The system SHALL list quota usage for all tenants, showing jobs/artifacts/sources against limits. | P0 | Implemented |

### 4.5 Capsule Management

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| ADM-F-005     | The system SHALL list all capsules across tenants with optional status filtering. | P0 | Implemented |
| ADM-F-005.1   | The system SHALL allow activating certified capsules.             | P0 | Implemented |
| ADM-F-005.2   | The system SHALL allow suspending capsules with a reason.          | P0 | Implemented |
| ADM-F-005.3   | The system SHALL allow archiving capsules.                        | P1 | Implemented |

### 4.6 Ontology Administration

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| ADM-F-006     | The system SHALL list all ontology object types with property and instance counts. | P0 | Implemented |
| ADM-F-006.1   | The system SHALL list properties for a given object type.          | P0 | Implemented |
| ADM-F-006.2   | The system SHALL list all link types with source/target type names. | P0 | Implemented |

### 4.7 Audit Log

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| ADM-F-007     | The system SHALL list audit log entries with filtering by action, actor, resource_type, and tenant_id. | P0 | Implemented |
| ADM-F-007.1   | Each audit entry SHALL include: actor, action, resource_type, resource_id, outcome, details, ip_address, created_at. | P0 | Implemented |

### 4.8 System Settings

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| ADM-F-008     | The system SHALL list all system settings with key, value, type, description, and secret flag. | P0 | Implemented |
| ADM-F-008.1   | Secret settings SHALL display `***` instead of actual values.      | P0 | Implemented |
| ADM-F-008.2   | The system SHALL allow updating non-secret settings.               | P0 | Implemented |

### 4.9 SQL Console

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| ADM-F-009     | The system SHALL allow executing read-only SQL queries via Trino.  | P0 | Implemented |
| ADM-F-009.1   | SQL results SHALL include columns, rows, row_count, truncated flag, execution_time_ms, and query_id. | P0 | Implemented |
| ADM-F-009.2   | The system SHALL list all available tables with optional schema filtering. | P0 | Implemented |

### 4.10 Search Index

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| ADM-F-010     | The system SHALL allow indexing documents for vector search with dense + sparse embeddings. | P0 | Implemented |
| ADM-F-010.1   | The system SHALL support semantic search queries returning ranked results with scores. | P0 | Implemented |
| ADM-F-010.2   | The system SHALL allow deleting indexed items.                    | P0 | Implemented |

### 4.11 Scraper Management

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| ADM-F-011     | The system SHALL list scrape jobs with optional status filtering.  | P0 | Implemented |
| ADM-F-011.1   | Each scrape job SHALL show: job_id, status, tenant, pages_fetched, bytes_processed, artifact_count, error_count. | P0 | Implemented |

### 4.12 Tenant Management

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| ADM-F-012     | The system SHALL list all known tenants with activity summary.     | P0 | Implemented |
| ADM-F-012.1   | Each tenant entry SHALL show: tenant_id, realm, job_count, source_count, artifact_count, last_activity. | P0 | Implemented |

---

## 5. Data Models

The Admin module does not define its own models. It reads from and operates on models defined in other modules. The key models consumed are:

### 5.1 Referenced Models

| Model               | Module           | Admin Usage                          |
|---------------------|------------------|--------------------------------------|
| `Job`               | `apps.workflows` | List, detail, cancel, reset          |
| `Artifact`          | `apps.workflows` | Listed in job detail                 |
| `Source`            | `apps.discovery` | List, create, delete                 |
| `Policy`            | `apps.governance`| List (admin view)                    |
| `DataContract`      | `apps.governance`| List (admin view)                    |
| `Capsule`           | `apps.capsules`  | List, activate, suspend, archive     |
| `ObjectType`        | `apps.ontology`  | List with counts                     |
| `Property`          | `apps.ontology`  | List by type                         |
| `LinkType`          | `apps.ontology`  | List                                 |
| `AuditLog`          | `apps.core`      | List with filters                    |
| `SystemSetting`     | `apps.core`      | List, update                         |
| `ScrapeJob`         | `apps.scraper`   | List                                 |

### 5.2 Admin Response Schemas

#### SystemOverview

```json
{
  "version": "3.0.0",
  "env": "production",
  "debug": false,
  "uptime_seconds": 1234567,
  "services": [
    {
      "name": "postgres",
      "status": "healthy",
      "circuit_breaker_state": "closed",
      "details": "Connected"
    }
  ],
  "stats": {
    "total_jobs": 1247,
    "jobs_running": 45,
    "jobs_queued": 12,
    "jobs_failed": 89,
    "jobs_completed": 1101,
    "total_sources": 34,
    "sources_active": 28,
    "total_artifacts": 567,
    "total_capsules": 23,
    "total_tenants": 5,
    "active_tenants": 5,
    "audit_events_24h": 1892,
    "policy_violations_24h": 3
  }
}
```

#### JobListItem

```json
{
  "job_id": "a1b2c3d4",
  "tenant_id": "tenant-abc",
  "job_type": "ingest",
  "status": "running",
  "progress": 65,
  "source_id": "source-uuid",
  "created_at": "2026-01-15T09:30:00Z",
  "started_at": "2026-01-15T09:30:05Z",
  "completed_at": null,
  "error_message": null
}
```

#### JobDetail (extends JobListItem)

```json
{
  "...": "all JobListItem fields plus:",
  "soma_session_id": "session-123",
  "parameters": {"mode": "full", "tables": ["orders"]},
  "result_summary": {"rows_ingested": 1247893},
  "artifacts": [
    {
      "artifact_id": "art-001",
      "artifact_type": "profile",
      "format": "parquet",
      "storage_path": "s3://voyant/artifacts/art-001.parquet",
      "size_bytes": 2412544
    }
  ]
}
```

#### ServiceHealth

```json
{
  "name": "trino",
  "status": "healthy",
  "circuit_breaker_state": "closed",
  "details": "Connected"
}
```

#### TenantInfo

```json
{
  "tenant_id": "tenant-abc",
  "realm": "default",
  "job_count": 847,
  "source_count": 12,
  "artifact_count": 234,
  "last_activity": "2026-01-15T14:32:00Z"
}
```

---

## 6. API Endpoints

All endpoints are mounted under `/v1/admin/` and require `voyant-admin` role.

| Method   | Path                               | FR-ID       | Description                       |
|----------|------------------------------------|-------------|-----------------------------------|
| `GET`    | `/dashboard`                       | ADM-F-001   | System overview with health + stats |
| `GET`    | `/jobs`                            | ADM-F-002   | List all jobs (cross-tenant)      |
| `GET`    | `/jobs/{job_id}`                   | ADM-F-002.1 | Get job detail with artifacts     |
| `POST`   | `/jobs/{job_id}/cancel`            | ADM-F-002.2 | Cancel a running/queued job       |
| `POST`   | `/jobs/{job_id}/reset`             | ADM-F-002.4 | Reset failed job to queued        |
| `GET`    | `/sources`                         | ADM-F-003   | List all data sources             |
| `POST`   | `/sources`                         | ADM-F-003.1 | Create data source (admin)        |
| `DELETE` | `/sources/{source_id}`             | ADM-F-003.2 | Delete data source                |
| `GET`    | `/governance/policies`             | ADM-F-004   | List all governance policies      |
| `GET`    | `/governance/contracts`            | ADM-F-004.1 | List all data contracts           |
| `GET`    | `/governance/quotas`               | ADM-F-004.2 | List quota usage for all tenants  |
| `GET`    | `/capsules`                        | ADM-F-005   | List all capsules                 |
| `POST`   | `/capsules/{id}/activate`          | ADM-F-005.1 | Activate capsule                  |
| `POST`   | `/capsules/{id}/suspend`           | ADM-F-005.2 | Suspend capsule                   |
| `POST`   | `/capsules/{id}/archive`           | ADM-F-005.3 | Archive capsule                   |
| `GET`    | `/ontology/types`                  | ADM-F-006   | List ontology object types        |
| `GET`    | `/ontology/types/{id}/properties`  | ADM-F-006.1 | List properties for a type        |
| `GET`    | `/ontology/links`                  | ADM-F-006.2 | List link types                   |
| `GET`    | `/audit`                           | ADM-F-007   | List audit log entries            |
| `GET`    | `/settings`                        | ADM-F-008   | List system settings              |
| `PUT`    | `/settings/{key}`                  | ADM-F-008.2 | Update a system setting           |
| `POST`   | `/sql/execute`                     | ADM-F-009   | Execute read-only SQL query       |
| `GET`    | `/sql/tables`                      | ADM-F-009.2 | List available tables             |
| `POST`   | `/search/index`                    | ADM-F-010   | Index document for vector search  |
| `GET`    | `/search/query`                    | ADM-F-010.1 | Query vector search index         |
| `DELETE` | `/search/{item_id}`               | ADM-F-010.2 | Delete search index item          |
| `GET`    | `/scraper/jobs`                    | ADM-F-011   | List scrape jobs                  |
| `GET`    | `/tenants`                         | ADM-F-012   | List all tenants                  |

### 6.1 Query Parameters

| Endpoint       | Parameter      | Type   | Description                           |
|----------------|----------------|--------|---------------------------------------|
| `/jobs`        | `status`       | string | Filter by status                      |
| `/jobs`        | `job_type`     | string | Filter by job type                    |
| `/jobs`        | `tenant_id`    | string | Filter by tenant                      |
| `/jobs`        | `limit`        | int    | Max results (default 100)             |
| `/sources`     | `tenant_id`    | string | Filter by tenant                      |
| `/governance/policies` | `tenant_id` | string | Filter by tenant                  |
| `/governance/contracts`| `tenant_id` | string | Filter by tenant                  |
| `/capsules`    | `status`       | string | Filter by status                      |
| `/ontology/types`| `tenant_id`  | string | Filter by tenant                      |
| `/audit`       | `action`       | string | Filter by action (icontains)          |
| `/audit`       | `actor`        | string | Filter by actor (icontains)           |
| `/audit`       | `resource_type`| string | Filter by resource type              |
| `/audit`       | `tenant_id`    | string | Filter by tenant                      |
| `/audit`       | `limit`        | int    | Max results (default 100)             |
| `/scraper/jobs`| `status`       | string | Filter by status                      |
| `/scraper/jobs`| `limit`        | int    | Max results (default 50)              |
| `/search/query`| `q`            | string | Search query text                     |
| `/search/query`| `limit`        | int    | Max results (default 10)              |

---

## 7. Integration Points

| System         | Integration Type    | Direction | Description                                      |
|----------------|---------------------|-----------|--------------------------------------------------|
| **Trino**      | SQL execution       | Outbound  | SQL console queries + table listing              |
| **Milvus**     | Vector store        | Outbound  | Search index management (dense + sparse)         |
| **Temporal**   | Workflow cancel      | Outbound  | Job cancellation via Temporal client             |
| **Circuit Breakers** | Internal     | Read      | Health status from circuit breaker state map     |
| **PostgreSQL** | Health check        | Outbound  | `SELECT 1` ping                                 |
| **Redis**      | Health check        | Outbound  | Cache set/get ping                               |
| **Vault**      | Health check        | Outbound  | `/v1/sys/health` GET                            |
| **Temporal**   | Health check        | Outbound  | TCP socket connect                               |
| **MinIO**      | Health check        | Outbound  | `/minio/health/live` GET                        |
| **Kafka**      | Health check        | Outbound  | TCP socket connect                               |
| **Milvus**     | Health check        | Outbound  | `/healthz` GET                                  |
| **Trino**      | Health check        | Outbound  | TCP socket connect                               |

---

## 8. Infrastructure Health Checks

The admin dashboard performs active health checks against all infrastructure components:

| Component    | Check Method                | Healthy Condition             |
|--------------|-----------------------------|-------------------------------|
| PostgreSQL   | `SELECT 1` via Django ORM   | Query succeeds                |
| Redis        | `cache.set/get` ping        | Value round-trips correctly   |
| Vault        | `GET /v1/sys/health`        | HTTP 200                      |
| Temporal     | TCP socket connect          | Connection succeeds (3s timeout) |
| MinIO        | `GET /minio/health/live`    | HTTP 200                      |
| Kafka        | TCP socket connect          | Connection succeeds (3s timeout) |
| Milvus       | `GET /healthz`              | HTTP 200                      |
| Trino        | TCP socket connect          | Connection succeeds (3s timeout) |

### 8.1 Circuit Breaker Mapping

External services also report health via circuit breaker state:

| Circuit Breaker State | Dashboard Status | Description              |
|-----------------------|------------------|--------------------------|
| `closed`              | `healthy`        | Normal operation         |
| `half_open`           | `degraded`       | Recovering from failure  |
| `open`                | `down`           | Service unavailable      |

---

## 9. Non-Functional Requirements

| NFR-ID      | Requirement                                                           | Target     |
|-------------|-----------------------------------------------------------------------|------------|
| ADM-NF-001  | Dashboard SHALL load within 3 seconds.                               | 3s p95     |
| ADM-NF-002  | Job listing SHALL return within 2 seconds for <10,000 jobs.          | 2s p95     |
| ADM-NF-003  | SQL console SHALL execute queries with a 60-second timeout.          | 60s        |
| ADM-NF-004  | Health checks SHALL complete within 5 seconds per component.         | 5s each    |
| ADM-NF-005  | Audit log SHALL support up to 200 results per request.               | 200 max    |
| ADM-NF-006  | All admin actions SHALL be audit-logged.                             | 100%       |
| ADM-NF-007  | Search indexing SHALL support documents up to 100KB text.            | 100KB max  |
| ADM-NF-008  | The admin API SHALL be rate-limited to prevent abuse.                | 100 req/s  |

---

## 10. Traceability Matrix

| Requirement  | API Endpoint                        | UI Component            | Health Check           |
|--------------|-------------------------------------|-------------------------|------------------------|
| ADM-F-001    | `/admin/dashboard`                  | System Dashboard        | All infra checks       |
| ADM-F-002    | `/admin/jobs` (GET/POST)            | Jobs View               | —                      |
| ADM-F-003    | `/admin/sources` (GET/POST/DELETE)  | —                       | —                      |
| ADM-F-004    | `/admin/governance/*`               | Governance View         | —                      |
| ADM-F-005    | `/admin/capsules` (GET/POST)        | —                       | —                      |
| ADM-F-006    | `/admin/ontology/*`                 | —                       | —                      |
| ADM-F-007    | `/admin/audit`                      | Audit View              | —                      |
| ADM-F-008    | `/admin/settings` (GET/PUT)         | Settings View           | —                      |
| ADM-F-009    | `/admin/sql/execute`                | SQL Console             | Trino health           |
| ADM-F-010    | `/admin/search/*`                   | —                       | Milvus health          |
| ADM-F-011    | `/admin/scraper/jobs`               | —                       | —                      |
| ADM-F-012    | `/admin/tenants`                    | Tenants View            | —                      |
