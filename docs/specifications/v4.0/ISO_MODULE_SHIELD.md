# Voyant Governance Shield Module — ISO 29148 Specification

| Field             | Value                                      |
|-------------------|--------------------------------------------|
| **Document ID**   | VOY-SPEC-SHIELD-v4.0                       |
| **Module**        | `apps.governance`                          |
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
7. [RBAC / RLS / Column Masking Architecture](#7-rbac--rls--column-masking-architecture)
8. [Integration Points](#8-integration-points)
9. [Non-Functional Requirements](#9-non-functional-requirements)
10. [Traceability Matrix](#10-traceability-matrix)

---

## 1. Module Overview

The **Governance Shield** is Voyant's cross-cutting data governance subsystem. It enforces data access policies at query time via three cooperating mechanisms:

1. **Row-Level Security (RLS)** — injects `WHERE` clause fragments into Trino SQL queries based on the user's role and the target table.
2. **Column-Level Masking** — rewrites `SELECT` clauses to wrap sensitive columns with masking functions (null, hash, partial, redact).
3. **Data Classification** — tags tables and columns with sensitivity levels (public / internal / confidential / restricted) per ISO/IEC 27001 A.8.

The Shield also manages:
- **Governance Policies** (access control, data retention, data quality, compliance, usage).
- **Data Contracts** (schema + quality rule agreements between producers and consumers).
- **Quota Tiers** (rate-limiting resources: jobs/day, storage GB, sources, concurrent jobs).
- **Catalog Browser** (Iceberg REST / Trino metadata explorer).
- **Lineage Graph** (upstream/downstream data dependency tracking).
- **GDPR Article 17 Right-to-Deletion** (Temporal workflow orchestration).

### 1.1 Scope

| In Scope                                          | Out of Scope                        |
|---------------------------------------------------|-------------------------------------|
| RLS policy CRUD + enforcement                     | Network-level firewall rules        |
| Column mask CRUD + enforcement                    | Keycloak realm configuration        |
| Data classification tagging                       | Application-level RBAC (see Auth)   |
| Data contract lifecycle                           | Data quality scoring algorithms     |
| Quota tier management                             | Trino server-side configuration     |
| Catalog browsing (Iceberg / Trino)                | DataHub deployment                  |
| Lineage graph (in-memory + DataHub)               | ML model governance                 |
| GDPR deletion workflow orchestration              | Manual data deletion                |

### 1.2 References

| Reference                         | Description                           |
|-----------------------------------|---------------------------------------|
| ISO/IEC 27001:2022 A.8            | Asset Management / Classification     |
| GDPR Article 17                   | Right to Erasure                      |
| ISO 29148:2018                    | Requirements engineering standard     |
| `apps/governance/models.py`       | ORM model definitions                 |
| `apps/governance/api.py`          | REST API endpoints                    |
| `apps/core/lib/trino.py`          | Trino client with RLS injection       |
| `apps/core/lib/tenant_quotas.py`  | Quota tier enum + manager             |

---

## 2. Actors and Roles

### 2.1 Actor Definitions

| Actor ID         | Description                                          | Source                |
|------------------|------------------------------------------------------|-----------------------|
| `data_steward`   | Creates/manages governance policies and classifications | Keycloak role mapping |
| `admin`          | Full platform access; manages quotas and contracts     | `voyant-admin` role   |
| `analyst`        | Reads governed data; subject to RLS/masking            | Keycloak role mapping |
| `viewer`         | Read-only access to catalog and lineage                | Keycloak role mapping |
| `system`         | Automated service (Temporal workflows, event triggers) | Internal              |
| `sdk_client`     | External client using Python/TypeScript SDK            | Bearer token          |

### 2.2 Role-Permission Matrix

| Permission               | data_steward | admin | analyst | viewer | system | sdk_client |
|--------------------------|:------------:|:-----:|:-------:|:------:|:------:|:----------:|
| Read policies            |      ✓       |   ✓   |    ✓    |   ✓    |   ✓    |     ✓      |
| Create/update policies   |      ✓       |   ✓   |    ✗    |   ✗    |   ✗    |     ✗      |
| Delete policies          |      ✗       |   ✓   |    ✗    |   ✗    |   ✗    |     ✗      |
| RLS check (dry-run)      |      ✓       |   ✓   |    ✗    |   ✗    |   ✗    |     ✗      |
| Manage column masks      |      ✓       |   ✓   |    ✗    |   ✗    |   ✗    |     ✗      |
| Manage classifications   |      ✓       |   ✓   |    ✗    |   ✗    |   ✗    |     ✗      |
| Browse catalog           |      ✓       |   ✓   |    ✓    |   ✓    |   ✓    |     ✓      |
| View lineage             |      ✓       |   ✓   |    ✓    |   ✓    |   ✓    |     ✓      |
| Set quota tier           |      ✗       |   ✓   |    ✗    |   ✗    |   ✗    |     ✗      |
| Trigger GDPR deletion    |      ✗       |   ✓   |    ✗    |   ✗    |   ✗    |     ✗      |
| View GDPR status         |      ✓       |   ✓   |    ✓    |   ✗    |   ✓    |     ✓      |

---

## 3. Screen Mockups

### 3.1 Policies Tab

```
┌──────────────────────────────────────────────────────────────────────┐
│  [Sidebar]  Governance                                               │
│                                                                      │
│  ┌──────────┬──────────┬──────────┬──────────┐                       │
│  │ Policies │ Contracts│  Quotas  │ Catalog  │   ← Tab bar           │
│  └──────────┴──────────┴──────────┴──────────┘                       │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │  Name          │ Type           │ Status  │ Level  │ Tenant      ││
│  ├────────────────┼────────────────┼─────────┼────────┼─────────────││
│  │ PII Access     │ access_control │ ● active│ strict │ tenant-abc  ││
│  │ Retention 90d  │ data_retention │ ● active│ warn   │ tenant-abc  ││
│  │ Quality SLA    │ data_quality   │ ○ draft │ audit  │ tenant-xyz  ││
│  │ GDPR Export    │ compliance     │ ● active│ strict │ tenant-abc  ││
│  │ Usage Limits   │ usage          │ ○ draft │ warn   │ tenant-xyz  ││
│  └────────────────┴────────────────┴─────────┴────────┴─────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 Quotas Tab

```
┌──────────────────────────────────────────────────────────────────────┐
│  ┌──────────┬──────────┬──────────┬──────────┐                       │
│  │ Policies │ Contracts│  Quotas  │ Catalog  │                       │
│  └──────────┴──────────┴──────────┴──────────┘                       │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │  Tenant      │ Tier    │ Jobs         │ Artifacts     │ Sources   ││
│  ├──────────────┼─────────┼──────────────┼───────────────┼───────────││
│  │ tenant-abc   │ [pro]   │ 45/100       │ 2.1GB/10GB    │ 5/10      ││
│  │ tenant-xyz   │ [free]  │ 8/10         │ 0.3GB/1GB     │ 2/3       ││
│  │ tenant-lmn   │ [pro]   │ 98/100       │ 8.7GB/10GB    │ 10/10     ││
│  └──────────────┴─────────┴──────────────┴───────────────┴───────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### 3.3 Catalog Browser Tab

```
┌──────────────────────────────────────────────────────────────────────┐
│  Schema: [default________] [Browse]                                  │
│                                                                      │
│  42 tables in default                                                │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ ▶ customer_orders                        12 columns              ││
│  │ ▼ user_profiles                                                   │
│  │   ┌──────────────┬──────────────┐                                ││
│  │   │ Column       │ Type         │                                ││
│  │   ├──────────────┼──────────────┤                                ││
│  │   │ id           │ varchar      │                                ││
│  │   │ email        │ varchar      │                                ││
│  │   │ full_name    │ varchar      │                                ││
│  │   │ created_at   │ timestamp    │                                ││
│  │   └──────────────┴──────────────┘                                ││
│  │ ▶ product_catalog                     8 columns                   ││
│  │ ▶ audit_log                           15 columns                  ││
│  └──────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### 3.4 Security Policies (RLS) Dashboard

```
┌──────────────────────────────────────────────────────────────────────┐
│  Row-Level Security Policies                     [+ New Policy]      │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │  Name              │ Table           │ Filter Type  │ Status      ││
│  ├────────────────────┼─────────────────┼──────────────┼─────────────││
│  │ Tenant Isolation   │ orders          │ user_match   │ ● active    ││
│  │ Dept Filter        │ expenses        │ role_based   │ ● active    ││
│  │ Custom Region      │ sales_data      │ custom_sql   │ ● active    ││
│  │ Test Policy        │ staging_*       │ user_match   │ ○ inactive  ││
│  └────────────────────┴─────────────────┴──────────────┴─────────────┘│
│                                                                      │
│  ┌─ RLS Check (Dry Run) ──────────────────────────────────────────┐  │
│  │  SQL: SELECT * FROM orders WHERE amount > 1000                  │  │
│  │  User: analyst-01  Roles: [analyst]                             │  │
│  │  ─────────────────────────────────────────────────────────────  │  │
│  │  ✓ Allowed | 1 RLS filter applied                              │  │
│  │  Modified: SELECT * FROM orders WHERE amount > 1000             │  │
│  │           AND tenant_id = 'tenant-abc'                          │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Functional Requirements

### 4.1 Governance Policies

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| GOV-F-001     | The system SHALL allow admins to create, read, update, and delete governance policies scoped to a tenant. | P0 | Implemented |
| GOV-F-001.1   | Each policy SHALL have a name, type, status, enforcement level, owner, and JSON rules/scope. | P0 | Implemented |
| GOV-F-001.2   | Policy types SHALL include: `access_control`, `data_retention`, `data_quality`, `compliance`, `usage`. | P0 | Implemented |
| GOV-F-001.3   | Policy statuses SHALL include: `draft`, `active`, `inactive`, `archived`. | P0 | Implemented |
| GOV-F-001.4   | Enforcement levels SHALL include: `strict` (block), `warn` (log + allow), `audit` (log only). | P0 | Implemented |

### 4.2 Data Contracts

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| GOV-F-002     | The system SHALL support versioned data contracts with schema definitions and quality rules. | P0 | Implemented |
| GOV-F-002.1   | Contracts SHALL be unique per (tenant_id, name, version).          | P0 | Implemented |
| GOV-F-002.2   | Contract statuses SHALL include: `draft`, `active`, `deprecated`, `archived`. | P0 | Implemented |
| GOV-F-002.3   | Each contract SHALL reference a dataset URN from DataHub.          | P1 | Implemented |

### 4.3 Row-Level Security (RLS)

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| GOV-F-003     | The system SHALL enforce row-level security policies by injecting SQL WHERE clauses at query time. | P0 | Implemented |
| GOV-F-003.1   | RLS filter types SHALL include: `user_match` (column = current_user), `role_based` (column IN allowed_values), `custom_sql`. | P0 | Implemented |
| GOV-F-003.2   | RLS policies SHALL be scoped to specific tables and optionally specific columns. | P0 | Implemented |
| GOV-F-003.3   | RLS policies SHALL be assignable to specific roles and/or specific user IDs. | P0 | Implemented |
| GOV-F-003.4   | The system SHALL provide a dry-run endpoint (`POST /rls/check`) that returns the modified SQL without executing it. | P0 | Implemented |
| GOV-F-003.5   | RLS enforcement SHALL occur transparently via the Trino client; users SHALL NOT see the injected clauses in normal operation. | P1 | Implemented |

### 4.4 Column-Level Masking

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| GOV-F-004     | The system SHALL support column-level masking policies that transform values at query time. | P0 | Implemented |
| GOV-F-004.1   | Mask types SHALL include: `full` (replace with ***), `partial` (show first/last N), `hash` (SHA-256), `redact` ([REDACTED]), `null`, `custom`. | P0 | Implemented |
| GOV-F-004.2   | Column masks SHALL be role-gated: `applies_to_roles` defines which roles are masked; `exempt_roles` overrides. | P0 | Implemented |
| GOV-F-004.3   | Masking config SHALL be stored as JSON (`mask_config`) with fields: `show_first`, `show_last`, `mask_char`. | P0 | Implemented |

### 4.5 Data Classification

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| GOV-F-005     | The system SHALL allow tagging of tables, columns, and ontology object types with classification levels. | P0 | Implemented |
| GOV-F-005.1   | Classification levels SHALL map to: `public`, `internal`, `confidential`, `restricted`. | P0 | Implemented |
| GOV-F-005.2   | Each classification SHALL specify whether encryption is required, masking is required, and retention period (days). | P1 | Implemented |

### 4.6 SecurityPolicy (GOV-F-006)

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| GOV-F-006     | The system SHALL support SecurityPolicy entries defining row filters for query-time WHERE clause injection. | P0 | Implemented |
| GOV-F-006.1   | SecurityPolicies SHALL have full CRUD endpoints (list, create, get, update, delete). | P0 | Implemented |
| GOV-F-006.2   | Each SecurityPolicy SHALL specify: `table_name`, `column_name`, `filter_expression`, `roles`, `status`. | P0 | Implemented |
| GOV-F-006.3   | The `filter_expression` SHALL be a SQL WHERE clause fragment injected into matching queries. | P0 | Implemented |

### 4.7 ColumnMask (GOV-F-007)

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| GOV-F-007     | The system SHALL support ColumnMask entries for column-level masking with full CRUD. | P0 | Implemented |
| GOV-F-007.1   | Mask types SHALL include: `null`, `hash`, `partial`, `redact`.     | P0 | Implemented |
| GOV-F-007.2   | ColumnMasks SHALL support role-scoped application and exemptions.  | P0 | Implemented |

### 4.8 Catalog Browser (GOV-F-008)

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| GOV-F-008     | The system SHALL provide a catalog browser that enumerates databases → tables → columns. | P0 | Implemented |
| GOV-F-008.1   | The catalog SHALL prefer the Iceberg REST catalog when available and fall back to Trino metadata queries. | P1 | Implemented |
| GOV-F-008.2   | Users SHALL be able to filter by schema name.                      | P0 | Implemented |

### 4.9 Lineage Graph (GOV-F-009)

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| GOV-F-009     | The system SHALL provide a lineage graph API returning nodes and edges. | P0 | Implemented |
| GOV-F-009.1   | The lineage graph SHALL support centering on a specific node with configurable depth. | P0 | Implemented |
| GOV-F-009.2   | The lineage graph SHALL integrate with DataHub for upstream/downstream relationships. | P1 | Implemented |

### 4.10 GDPR Right-to-Deletion (GOV-F-010)

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| GOV-F-010     | The system SHALL provide a GDPR Article 17 right-to-erasure endpoint. | P0 | Implemented |
| GOV-F-010.1   | GDPR deletion SHALL be orchestrated as a Temporal workflow.         | P0 | Implemented |
| GOV-F-010.2   | The system SHALL provide a status endpoint for tracking deletion progress. | P0 | Implemented |
| GOV-F-010.3   | GDPR deletion SHALL be restricted to users with `write:governance` permission. | P0 | Implemented |

### 4.11 Quota Management

| FR-ID         | Requirement                                                        | Priority | Status  |
|---------------|--------------------------------------------------------------------|----------|---------|
| GOV-F-011     | The system SHALL enforce per-tenant resource quotas based on configurable tiers. | P0 | Implemented |
| GOV-F-011.1   | Quota resources SHALL include: `JOBS_PER_DAY`, `TOTAL_STORAGE_MB`, `WORKFLOWS_PER_DAY`, `JOBS_CONCURRENT`. | P0 | Implemented |
| GOV-F-011.2   | The system SHALL provide endpoints to list tiers, view usage, view limits, and set tenant tier. | P0 | Implemented |

---

## 5. Data Models

### 5.1 DataContract

**Table:** `voyant_data_contract`

| Field              | Type             | Constraints                   | Description                           |
|--------------------|------------------|-------------------------------|---------------------------------------|
| `id`               | UUID             | PK, auto-generated            | Primary key                           |
| `tenant_id`        | VARCHAR(255)     | NOT NULL, indexed             | Owning tenant                         |
| `name`             | VARCHAR(255)     | NOT NULL                      | Contract name                         |
| `description`      | TEXT             | nullable                      | Detailed description                  |
| `dataset_urn`      | VARCHAR(512)     | NOT NULL, indexed             | DataHub dataset URN                   |
| `schema_definition`| JSON             | default `{}`                  | JSON schema for data structure        |
| `quality_rules`    | JSON             | default `[]`                  | List of quality rules/constraints     |
| `status`           | VARCHAR(16)      | `draft`/`active`/`deprecated`/`archived` | Current status            |
| `version`          | VARCHAR(32)      | default `"1.0.0"`             | Semantic version                      |
| `owner`            | VARCHAR(255)     | NOT NULL                      | Owner/team                            |
| `metadata`         | JSON             | default `{}`                  | Additional metadata                   |
| `created_at`       | DATETIME         | auto_now_add                  | Creation timestamp                    |
| `updated_at`       | DATETIME         | auto_now                      | Last update timestamp                 |

**Indexes:**
- `(tenant_id, status, -created_at)`
- `(dataset_urn)`
- UNIQUE `(tenant_id, name, version)` — `unique_contract_version_per_tenant`

### 5.2 LineageNode

**Table:** `voyant_lineage_node`

| Field          | Type         | Constraints         | Description                          |
|----------------|--------------|---------------------|--------------------------------------|
| `id`           | UUID         | PK                  | Primary key                          |
| `tenant_id`    | VARCHAR(255) | NOT NULL, indexed   | Owning tenant                        |
| `urn`          | VARCHAR(512) | UNIQUE, indexed     | Unique resource name                 |
| `name`         | VARCHAR(255) | NOT NULL            | Human-readable name                  |
| `node_type`    | VARCHAR(32)  | indexed             | `dataset`/`transformation`/`model`/`report`/`api` |
| `platform`     | VARCHAR(128) | nullable, indexed   | Platform or system                   |
| `description`  | TEXT         | nullable            | Description                          |
| `upstream_urns`| JSON         | default `[]`        | Upstream dependency URNs             |
| `downstream_urns`| JSON       | default `[]`        | Downstream consumer URNs             |
| `metadata`     | JSON         | default `{}`        | Additional metadata                  |

### 5.3 Policy

**Table:** `voyant_policy`

| Field               | Type         | Constraints                    | Description                     |
|---------------------|--------------|--------------------------------|---------------------------------|
| `id`                | UUID         | PK                             | Primary key                     |
| `tenant_id`         | VARCHAR(255) | NOT NULL                       | Owning tenant                   |
| `name`              | VARCHAR(255) | NOT NULL                       | Policy name                     |
| `description`       | TEXT         | nullable                       | Description                     |
| `policy_type`       | VARCHAR(32)  | indexed                        | `access_control`/`data_retention`/`data_quality`/`compliance`/`usage` |
| `status`            | VARCHAR(16)  | indexed                        | `draft`/`active`/`inactive`/`archived` |
| `rules`             | JSON         | default `{}`                   | Policy rules (JSON)             |
| `scope`             | JSON         | default `{}`                   | Scope (datasets, users, ops)    |
| `enforcement_level` | VARCHAR(32)  | default `"strict"`             | `strict`/`warn`/`audit`        |
| `owner`             | VARCHAR(255) | NOT NULL                       | Owner/team                      |
| `metadata`          | JSON         | default `{}`                   | Additional metadata             |

**Indexes:**
- `(tenant_id, policy_type, status)`
- `(status, -created_at)`
- UNIQUE `(tenant_id, name)` — `unique_policy_name_per_tenant`

### 5.4 RowSecurityPolicy

**Table:** `governance_row_security_policy`

| Field              | Type         | Constraints        | Description                               |
|--------------------|--------------|--------------------|-------------------------------------------|
| `id`               | UUID         | PK                 | Primary key                               |
| `tenant_id`        | VARCHAR(255) | NOT NULL           | Owning tenant                             |
| `name`             | VARCHAR(255) | NOT NULL           | Policy name                               |
| `description`      | TEXT         | default `""`       | Description                               |
| `status`           | VARCHAR(20)  | indexed            | `active`/`inactive`                       |
| `table_name`       | VARCHAR(255) | NOT NULL           | Target table                              |
| `column_name`      | VARCHAR(255) | nullable           | Filter column (optional)                  |
| `filter_type`      | VARCHAR(50)  | NOT NULL           | `user_match`/`role_based`/`custom_sql`    |
| `filter_config`    | JSON         | default `{}`       | Filter configuration                      |
| `custom_sql`       | TEXT         | nullable           | Custom SQL WHERE clause                   |
| `applies_to_roles` | JSON         | default `[]`       | Roles this policy applies to              |
| `applies_to_users` | JSON         | default `[]`       | Specific user IDs                         |

**Indexes:**
- `(tenant_id, table_name)`
- `(tenant_id, status)`

### 5.5 ColumnMaskPolicy

**Table:** `governance_column_mask`

| Field              | Type         | Constraints        | Description                          |
|--------------------|--------------|--------------------|--------------------------------------|
| `id`               | UUID         | PK                 | Primary key                          |
| `tenant_id`        | VARCHAR(255) | NOT NULL           | Owning tenant                        |
| `name`             | VARCHAR(255) | NOT NULL           | Policy name                          |
| `description`      | TEXT         | default `""`       | Description                          |
| `status`           | VARCHAR(20)  | indexed            | `active`/`inactive`                  |
| `table_name`       | VARCHAR(255) | NOT NULL           | Target table                         |
| `column_name`      | VARCHAR(255) | NOT NULL           | Column to mask                       |
| `mask_type`        | VARCHAR(50)  | NOT NULL           | `full`/`partial`/`hash`/`redact`/`null`/`custom` |
| `mask_config`      | JSON         | default `{}`       | `{show_first, show_last, mask_char}` |
| `applies_to_roles` | JSON         | default `[]`       | Roles this mask applies to           |
| `exempt_roles`     | JSON         | default `[]`       | Roles exempt from masking            |

### 5.6 DataClassification

**Table:** `governance_classification`

| Field                | Type         | Constraints        | Description                              |
|----------------------|--------------|--------------------|------------------------------------------|
| `id`                 | UUID         | PK                 | Primary key                              |
| `tenant_id`          | VARCHAR(255) | NOT NULL           | Owning tenant                            |
| `name`               | VARCHAR(255) | NOT NULL           | Classification name (e.g. `PII`)         |
| `level`              | VARCHAR(20)  | NOT NULL           | `public`/`internal`/`confidential`/`restricted` |
| `description`        | TEXT         | default `""`       | Description                              |
| `target_type`        | VARCHAR(50)  | NOT NULL           | `table`/`column`/`object_type`           |
| `target_name`        | VARCHAR(255) | NOT NULL           | Target name                              |
| `requires_encryption`| BOOLEAN      | default `false`    | Encryption required?                     |
| `requires_masking`   | BOOLEAN      | default `false`    | Masking required?                        |
| `retention_days`     | INTEGER      | nullable           | Data retention period                    |

### 5.7 SecurityPolicy (GOV-F-006)

**Table:** `governance_security_policy`

| Field               | Type         | Constraints        | Description                          |
|---------------------|--------------|--------------------|--------------------------------------|
| `id`                | UUID         | PK                 | Primary key                          |
| `tenant_id`         | VARCHAR(255) | NOT NULL           | Owning tenant                        |
| `name`              | VARCHAR(255) | NOT NULL           | Policy name                          |
| `description`       | TEXT         | default `""`       | Description                          |
| `status`            | VARCHAR(20)  | indexed            | `active`/`inactive`                  |
| `table_name`        | VARCHAR(255) | NOT NULL           | Fully-qualified table name           |
| `column_name`       | VARCHAR(255) | default `""`       | Column (documentation only)          |
| `filter_expression` | TEXT         | NOT NULL           | SQL WHERE clause fragment            |
| `roles`             | JSON         | default `[]`       | Roles this policy applies to         |

### 5.8 ColumnMask (GOV-F-007)

**Table:** `governance_column_mask_def`

| Field          | Type         | Constraints   | Description                                  |
|----------------|--------------|---------------|----------------------------------------------|
| `id`           | UUID         | PK            | Primary key                                  |
| `tenant_id`    | VARCHAR(255) | NOT NULL      | Owning tenant                                |
| `name`         | VARCHAR(255) | NOT NULL      | Policy name                                  |
| `description`  | TEXT         | default `""`  | Description                                  |
| `status`       | VARCHAR(20)  | indexed       | `active`/`inactive`                          |
| `table_name`   | VARCHAR(255) | NOT NULL      | Fully-qualified table name                   |
| `column_name`  | VARCHAR(255) | NOT NULL      | Column to mask                               |
| `mask_type`    | VARCHAR(20)  | NOT NULL      | `null`/`hash`/`partial`/`redact`             |
| `mask_config`  | JSON         | default `{}`  | `{show_first, show_last, mask_char}`         |
| `roles`        | JSON         | default `[]`  | Roles this mask applies to (empty = all)     |
| `exempt_roles` | JSON         | default `[]`  | Roles exempt from masking                    |

---

## 6. API Endpoints

All endpoints are mounted under `/v1/governance/`.

| Method   | Path                                | FR-ID      | Description                          | Auth                      |
|----------|-------------------------------------|------------|--------------------------------------|---------------------------|
| `GET`    | `/search`                           | GOV-F-009  | Search governed datasets via DataHub | `read:*`                  |
| `GET`    | `/lineage/{urn}`                    | GOV-F-009  | Get lineage graph for a dataset URN  | `read:*`                  |
| `GET`    | `/schema/{urn}`                     | GOV-F-008  | Get schema for a dataset             | `read:*`                  |
| `GET`    | `/quotas/tiers`                     | GOV-F-011  | List all quota tiers                 | `read:*`                  |
| `GET`    | `/quotas/usage`                     | GOV-F-011  | Get current tenant quota usage       | `read:*`                  |
| `GET`    | `/quotas/limits`                    | GOV-F-011  | Get current tenant quota limits      | `read:*`                  |
| `POST`   | `/quotas/set-tier`                  | GOV-F-011  | Set tenant's quota tier              | `read:*`                  |
| `GET`    | `/row-security-policies`            | GOV-F-003  | List RLS policies                    | `read:*`                  |
| `POST`   | `/row-security-policies`            | GOV-F-003  | Create RLS policy                    | `read:*`                  |
| `POST`   | `/rls/check`                        | GOV-F-003  | Dry-run RLS check for a SQL query    | `read:*`                  |
| `GET`    | `/rls/policies`                     | GOV-F-003  | List RLS policies (typed response)   | `read:*`                  |
| `GET`    | `/column-masks`                     | GOV-F-004  | List column masks (legacy endpoint)  | `read:*`                  |
| `POST`   | `/column-masks`                     | GOV-F-004  | Create column mask (legacy endpoint) | `read:*`                  |
| `GET`    | `/masks`                            | GOV-F-004  | List column masks (typed response)   | `read:*`                  |
| `GET`    | `/classifications`                  | GOV-F-005  | List data classifications            | `read:*`                  |
| `POST`   | `/classifications`                  | GOV-F-005  | Create data classification           | `read:*`                  |
| `GET`    | `/security-policies`                | GOV-F-006  | List security policies               | `read:*`                  |
| `POST`   | `/security-policies`                | GOV-F-006  | Create security policy               | `read:*`                  |
| `GET`    | `/security-policies/{id}`           | GOV-F-006  | Get security policy by ID            | `read:*`                  |
| `PUT`    | `/security-policies/{id}`           | GOV-F-006  | Update security policy               | `read:*`                  |
| `DELETE` | `/security-policies/{id}`           | GOV-F-006  | Delete security policy               | `read:*`                  |
| `GET`    | `/column-mask-defs`                 | GOV-F-007  | List column masks                    | `read:*`                  |
| `POST`   | `/column-mask-defs`                 | GOV-F-007  | Create column mask                   | `read:*`                  |
| `GET`    | `/column-mask-defs/{id}`            | GOV-F-007  | Get column mask by ID                | `read:*`                  |
| `PUT`    | `/column-mask-defs/{id}`            | GOV-F-007  | Update column mask                   | `read:*`                  |
| `DELETE` | `/column-mask-defs/{id}`            | GOV-F-007  | Delete column mask                   | `read:*`                  |
| `GET`    | `/catalog`                          | GOV-F-008  | Browse data catalog                  | `read:*`                  |
| `GET`    | `/lineage-graph`                    | GOV-F-009  | Get lineage graph (in-memory)        | `read:*`                  |
| `POST`   | `/gdpr/delete`                      | GOV-F-010  | Trigger GDPR right-to-erasure        | `write:governance`        |
| `GET`    | `/gdpr/status/{workflow_id}`        | GOV-F-010  | Check GDPR deletion workflow status  | `read:governance`         |

### 6.1 Key Request/Response Schemas

#### RLS Check Request

```json
{
  "sql": "SELECT * FROM orders WHERE amount > 1000",
  "user_id": "analyst-01",
  "user_roles": ["analyst"]
}
```

#### RLS Check Response

```json
{
  "allowed": true,
  "applied_policies": 1,
  "injected_filters": ["Tenant Isolation: tenant_id = 'tenant-abc'"],
  "modified_sql": "SELECT * FROM orders WHERE amount > 1000 AND tenant_id = 'tenant-abc'",
  "reason": "1 RLS filter(s) would be applied"
}
```

#### GDPR Delete Response

```json
{
  "workflow_id": "gdpr-delete-a1b2c3d4e5f6",
  "tenant_id": "tenant-abc",
  "user_id": "user-123",
  "status": "started",
  "message": "GDPR deletion workflow started. Use GET /v1/governance/gdpr/status/{workflow_id} to track progress."
}
```

---

## 7. RBAC / RLS / Column Masking Architecture

### 7.1 Enforcement Pipeline

```
                        ┌─────────────────────────────────────┐
                        │           Trino SQL Client           │
                        └──────────────┬──────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
          ┌─────────────────┐ ┌───────────────┐ ┌─────────────────┐
          │  1. Parse SQL    │ │ 2. Extract    │ │ 3. Identify     │
          │     (AST)        │ │    table refs │ │    SELECT cols   │
          └────────┬────────┘ └──────┬────────┘ └────────┬────────┘
                   │                 │                   │
                   ▼                 ▼                   ▼
          ┌─────────────────┐ ┌───────────────┐ ┌─────────────────┐
          │  4. Match RLS    │ │ 5. Match RLS  │ │ 6. Match Column │
          │     policies     │ │    by table   │ │    Mask policies│
          └────────┬────────┘ └──────┬────────┘ └────────┬────────┘
                   │                 │                   │
                   ▼                 ▼                   ▼
          ┌─────────────────┐ ┌───────────────┐ ┌─────────────────┐
          │  7. Build filter │ │ 8. Build      │ │ 9. Rewrite      │
          │     WHERE clause │ │    mask expr  │ │    SELECT clause │
          └────────┬────────┘ └──────┬────────┘ └────────┬────────┘
                   │                 │                   │
                   └────────┬────────┘                   │
                            ▼                            ▼
                   ┌─────────────────┐         ┌─────────────────┐
                   │ 10. Inject RLS  │         │ 11. Inject masks│
                   │     WHERE into  │         │     into SELECT │
                   │     query       │         │     columns     │
                   └────────┬────────┘         └────────┬────────┘
                            │                           │
                            └─────────┬─────────────────┘
                                      ▼
                            ┌──────────────────┐
                            │ 12. Execute      │
                            │     modified SQL │
                            │     on Trino     │
                            └──────────────────┘
```

### 7.2 RLS Policy Evaluation Flow

```
For each RowSecurityPolicy where status == "active":
  1. Check: does policy.table_name appear in the query's FROM/JOIN clauses?
     → No: skip
  2. Check: does policy apply to this user?
     → If applies_to_users is non-empty: user_id must be in list
     → If applies_to_roles is non-empty: at least one user role must match
     → Both empty: policy applies to all users
  3. Build filter clause based on filter_type:
     → user_match:    "{column_name} = '{user_id}'"
     → role_based:    "{column_name} IN ({allowed_values_for_role})"
     → custom_sql:    use custom_sql directly
  4. Inject: add "AND ({clause})" to WHERE
```

### 7.3 Column Mask Evaluation Flow

```
For each ColumnMaskPolicy where status == "active":
  1. Check: does policy.table_name.column_name appear in the SELECT clause?
     → No: skip
  2. Check: is the user's role in applies_to_roles? (empty = all)
     → No: skip
  3. Check: is the user's role in exempt_roles?
     → Yes: skip (no masking)
  4. Rewrite column expression based on mask_type:
     → full:    "***"
     → partial: CONCAT(LEFT(col, show_first), '***', RIGHT(col, show_last))
     → hash:    SHA256(CAST(col AS VARCHAR))
     → redact:  '[REDACTED]'
     → null:    NULL
     → custom:  apply custom function from mask_config
```

### 7.4 Group Naming Convention

Channel-layer groups for WebSocket events follow the pattern:

```
voyant_{tenant_id}_{channel}
```

Where `channel` is one of: `ontology_changes`, `job_status`, `agent_events`, `scraper_events`.

---

## 8. Integration Points

| System         | Integration Type    | Direction | Description                                      |
|----------------|---------------------|-----------|--------------------------------------------------|
| **Trino**      | SQL injection       | Outbound  | RLS/mask enforcement via query rewriting          |
| **DataHub**    | GraphQL API         | Outbound  | Metadata search, lineage, schema retrieval        |
| **Iceberg REST** | REST catalog      | Outbound  | Catalog browsing (namespaces, tables, columns)    |
| **Temporal**   | Workflow orchestration| Outbound  | GDPR deletion workflow execution                  |
| **Keycloak**   | JWT authentication  | Inbound   | Token validation for all API + WebSocket auth     |
| **Django ORM** | PostgreSQL          | Internal  | All policy/config persistence                     |
| **Dashboard**  | REST API            | Inbound   | `view-governance.ts` consumes all governance APIs |
| **Python SDK** | REST API            | Inbound   | `GovernanceResource` class wraps governance endpoints |
| **TypeScript SDK** | REST API        | Inbound   | `GovernanceResource` class wraps governance endpoints |

---

## 9. Non-Functional Requirements

| NFR-ID     | Requirement                                                         | Target     |
|------------|---------------------------------------------------------------------|------------|
| GOV-NF-001 | RLS policy evaluation SHALL complete within 50ms per query.         | 50ms p99   |
| GOV-NF-002 | Column mask rewriting SHALL add no more than 10ms overhead.         | 10ms p99   |
| GOV-NF-003 | Catalog browsing SHALL return within 5 seconds for schemas with <1000 tables. | 5s p95 |
| GOV-NF-004 | GDPR deletion workflows SHALL complete within 24 hours.            | 24h SLA    |
| GOV-NF-005 | All governance data SHALL be tenant-isolated (no cross-tenant leakage). | 100% |
| GOV-NF-006 | The system SHALL support at least 500 concurrent RLS policies per tenant. | 500 min |
| GOV-NF-007 | All governance mutations SHALL be audit-logged.                    | 100%       |

---

## 10. Traceability Matrix

| Requirement  | Data Model              | API Endpoint                    | UI Component            |
|--------------|-------------------------|---------------------------------|-------------------------|
| GOV-F-001    | `Policy`                | Admin: `/governance/policies`   | Policies Tab            |
| GOV-F-002    | `DataContract`          | Admin: `/governance/contracts`  | Contracts Tab           |
| GOV-F-003    | `RowSecurityPolicy`     | `/row-security-policies`, `/rls/check` | RLS Dashboard   |
| GOV-F-004    | `ColumnMaskPolicy`      | `/column-masks`, `/masks`       | Mask management UI      |
| GOV-F-005    | `DataClassification`    | `/classifications`              | Classification tags     |
| GOV-F-006    | `SecurityPolicy`        | `/security-policies` (CRUD)     | Security Policy UI      |
| GOV-F-007    | `ColumnMask`            | `/column-mask-defs` (CRUD)      | Column Mask UI          |
| GOV-F-008    | —                       | `/catalog`, `/schema/{urn}`     | Catalog Tab             |
| GOV-F-009    | `LineageNode`           | `/lineage/{urn}`, `/lineage-graph` | Lineage viewer      |
| GOV-F-010    | — (Temporal workflow)   | `/gdpr/delete`, `/gdpr/status`  | GDPR management UI      |
| GOV-F-011    | `QuotaTier`, `TenantQuota` | `/quotas/*`                  | Quotas Tab              |
