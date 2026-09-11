# SOC 2 Type II Readiness Assessment — Voyant Platform

**Version**: 4.0  
**Date**: 2026-01-15  
**Status**: Draft — Pre-audit gap analysis  

---

## Executive Summary

This document maps each SOC 2 Trust Services Criteria (TSC) control relevant to the Voyant platform to its current implementation, identifies gaps, and lists evidence artifacts. Voyant is a multi-tenant data intelligence platform with governance, RBAC, audit logging, and automated compliance features that provide a strong foundation for SOC 2 Type II readiness.

---

## CC6.1 — Logical Access Security

**Objective**: The entity implements logical access security software, infrastructure, and architectures over protected information assets to protect them from security events.

### Implementation

| Component | Status | Description |
|-----------|--------|-------------|
| **SpiceDB RBAC** | Implemented | Fine-grained permission checks via `auth/permissions/` module. Resources are namespaced by tenant and role. Permissions evaluated at API gateway level via `require_permission()` decorator. |
| **Keycloak Auth** | Implemented | External identity provider for user authentication. SSO integration via OpenID Connect. Federated identity management across tenants. |
| **JWT Tokens** | Implemented | Short-lived access tokens (15 min) + refresh tokens. Tokens validated on every API request via `auth_guard` middleware. Token refresh handled by `tryRefreshToken()` in dashboard client. |
| **Tenant Isolation** | Implemented | Every model extends `TenantModel` which enforces `tenant_id` scoping. Middleware injects tenant context from JWT claims. |
| **API Gateway** | Implemented | Django Ninja routers with per-endpoint permission requirements (`auth=require_permission("read:*")`). |

### Gaps

- [ ] SpiceDB schema definitions not yet version-controlled alongside app code
- [ ] Token revocation / blacklist not implemented (relies on TTL expiration)
- [ ] No IP allowlisting for admin endpoints

### Evidence Files

- `apps/core/security/auth.py` — `require_permission()`, JWT validation
- `apps/core/middleware.py` — tenant context injection
- `apps/governance/api.py` — governance endpoint permissions
- `dashboard/src/lib/api.ts` — client-side token management
- `apps/governance/models.py:367-438` — `RowSecurityPolicy` model

---

## CC6.2 — Authentication

**Objective**: Prior to issuing system credentials and providing system access, the entity registers and authorizes new internal and external users.

### Implementation

| Component | Status | Description |
|-----------|--------|-------------|
| **Keycloak SSO** | Implemented | Centralized identity provider with OIDC integration. Supports SAML and OAuth2 federation. |
| **MFA Support** | Partially Implemented | Keycloak supports TOTP/WebAuthn MFA; Voyant does not enforce MFA at platform level. MFA policy is configured in Keycloak. |
| **Session Management** | Implemented | JWT-based stateless sessions. Access tokens expire in 15 minutes. Refresh tokens rotate on use. Dashboard auto-redirects to login on 401. |
| **Password Policy** | Delegated to Keycloak | Minimum length, complexity, and lockout configured in Keycloak realm settings. |
| **User Provisioning** | Implemented | Admin API endpoints for tenant and user management. `view-tenants.ts` dashboard for admin user management. |

### Gaps

- [ ] Platform-level MFA enforcement toggle not exposed in Voyant admin UI
- [ ] No session invalidation on password change (relies on token TTL)
- [ ] No login attempt logging / brute-force detection in Voyant (delegated to Keycloak)

### Evidence Files

- `apps/core/security/auth.py` — JWT verification, token decode
- `apps/core/config.py` — Keycloak configuration settings
- `dashboard/src/views/view-login.ts` — login flow
- `dashboard/src/views/view-tenants.ts` — user/tenant management

---

## CC6.3 — Authorization

**Objective**: The entity authorizes, modifies, or removes access to data, software, functions, and other protected information assets based on roles, responsibilities, or the system design and changes.

### Implementation

| Component | Status | Description |
|-----------|--------|-------------|
| **RBAC** | Implemented | Role-based permissions via `require_permission("verb:resource")` pattern. Roles: admin, analyst, viewer, data_steward. Permissions checked on every API endpoint. |
| **Row-Level Security (RLS)** | Implemented | `RowSecurityPolicy` model (GOV-F-003). Enforced at query time by Trino client. Filters injected as WHERE clauses. `governance/rls/check` endpoint for dry-run validation. |
| **Column Masking** | Implemented | `ColumnMaskPolicy` and `ColumnMask` models (GOV-F-004, GOV-F-007). Supports null, hash, partial, redact strategies. Enforced at query time by Trino client SELECT rewriting. |
| **Security Policies** | Implemented | `SecurityPolicy` model (GOV-F-006) for declarative row filters. Full CRUD API with audit trail. |
| **SpiceDB Integration** | Implemented | Authorization decisions delegated to SpiceDB for cross-service consistency. |

### Gaps

- [ ] No UI for RLS/ColumnMask policy management (API-only)
- [ ] Column masking not enforced in dashboard API responses (only Trino queries)
- [ ] No automated policy testing / regression suite

### Evidence Files

- `apps/governance/models.py:367-438` — `RowSecurityPolicy`
- `apps/governance/models.py:446-505` — `ColumnMaskPolicy`
- `apps/governance/models.py:571-628` — `SecurityPolicy`
- `apps/governance/models.py:636-707` — `ColumnMask`
- `apps/governance/api.py:448-498` — RLS check endpoint
- `apps/governance/api.py:528-601` — Column mask CRUD
- `apps/governance/api.py:650-807` — Security policy CRUD

---

## CC6.6 — Data Classification

**Objective**: The entity uses detection policies and procedures to identify threats, anomalies, and data that require protection.

### Implementation

| Component | Status | Description |
|-----------|--------|-------------|
| **DataClassification Model** | Implemented | 4-level classification: public, internal, confidential, restricted. Applied to tables, columns, and ontology object types. Tracks encryption and masking requirements. |
| **Retention Policies** | Implemented | `retention_days` field on `DataClassification` model. Linked to governance policy enforcement. |
| **PII Tagging** | Partially Implemented | Classification model supports PII designation. No automated PII detection. Manual tagging via API. |
| **Encryption Flags** | Implemented | `requires_encryption` and `requires_masking` boolean flags on classification entries. |

### Gaps

- [ ] No automated PII detection / auto-classification engine
- [ ] No UI for managing data classifications
- [ ] Classification not enforced automatically (requires downstream policy evaluation)
- [ ] No integration with data profiling to suggest classifications

### Evidence Files

- `apps/governance/models.py:513-563` — `DataClassification` model
- `apps/governance/api.py:604-648` — Classification CRUD endpoints
- `apps/governance/api.py:986-1105` — Catalog browser for discovering unclassified data

---

## CC6.7 — Data Disposal

**Objective**: The entity uses procedures to dispose of data, software, and assets when they are no longer needed.

### Implementation

| Component | Status | Description |
|-----------|--------|-------------|
| **GDPR Deletion Workflow** | Implemented | `GDPRDeletionWorkflow` — Temporal workflow implementing Article 17 right-to-erasure. Deletes data across ontology, scraper, ML domains. Anonymizes audit logs. Verifies completeness. Generates and stores deletion certificate. |
| **Deletion Certificates** | Implemented | JSON certificates with integrity hash stored in MinIO. Includes per-domain deletion counts, verification results, timestamp. |
| **Retention Policies** | Implemented | `retention_days` on `DataClassification`. `Policy` model supports `DATA_RETENTION` type. |
| **Audit Log Anonymization** | Implemented | `anonymize_audit_logs` activity replaces PII with deterministic hash while preserving analytical value. |

### Gaps

- [ ] No automated retention-based deletion scheduler (manual trigger only)
- [ ] No UI for triggering GDPR deletion (API-only)
- [ ] Deletion certificate download/viewer not in dashboard
- [ ] No soft-delete / grace period before permanent deletion

### Evidence Files

- `apps/worker/workflows/gdpr_deletion.py` — GDPR deletion workflow
- `apps/worker/activities/gdpr_activities.py` — GDPR deletion activities
- `apps/governance/api.py` — GDPR delete/status endpoints
- `apps/governance/models.py:513-563` — `DataClassification` with `retention_days`

---

## CC7.1 — Monitoring

**Objective**: The entity monitors system components and the operation of those components for anomalies that indicate malicious acts, natural disasters, and errors affecting the entity's ability to meet its objectives.

### Implementation

| Component | Status | Description |
|-----------|--------|-------------|
| **AuditLog Model** | Implemented | Comprehensive audit logging of all API operations. Captures user_id, action, resource, IP address, user agent, request/response metadata. |
| **Prometheus Metrics** | Implemented | `MetricsRegistry` and `MetricsInterceptor` for Temporal workflows and activities. Worker-level metrics server. API-level request metrics. |
| **Grafana Dashboards** | Implemented | Pre-built dashboards for job throughput, error rates, workflow durations, API latency. |
| **Job Status Events** | Implemented | `publish_job_status()` real-time event system for workflow state changes. |
| **Temporal Observability** | Implemented | Temporal UI for workflow execution history, retry visibility, and failure inspection. |

### Gaps

- [ ] No alerting rules configured for anomalous patterns
- [ ] Audit log retention policy not defined
- [ ] No centralized log aggregation (logs are per-service)
- [ ] No automated incident creation from monitoring alerts

### Evidence Files

- `apps/audit/models.py` — AuditLog model
- `apps/core/lib/monitoring.py` — MetricsRegistry
- `apps/core/lib/interceptors.py` — MetricsInterceptor
- `apps/core/events.py` — `publish_job_status()`
- `dashboard/src/views/view-audit.ts` — Audit log viewer

---

## CC7.2 — Anomaly Detection

**Objective**: The entity evaluates, communicates, and responds to anomalies identified through monitoring activities.

### Implementation

| Component | Status | Description |
|-----------|--------|-------------|
| **Anomaly Detection Engine** | Implemented | `DetectAnomaliesWorkflow` — Temporal workflow using Isolation Forest and statistical methods. `OperationalActivities.detect_anomalies` activity. |
| **Analysis App** | Implemented | `apps/analysis/` — Full analytics pipeline with profiling, KPIs, and anomaly detection primitives. |
| **Quality Checks** | Implemented | `QualityWorkflow` — Automated data quality validation. Detects schema drift, null rates, distribution anomalies. |
| **Job Failure Detection** | Implemented | Failed jobs tracked in `Job` model with `error_message`. Status events propagated via `publish_job_status()`. |

### Gaps

- [ ] No automated alerting on anomaly detection results
- [ ] No anomaly severity classification (critical/warning/info)
- [ ] No integration between anomaly detection and incident management
- [ ] No anomaly trending / baseline comparison across time

### Evidence Files

- `apps/worker/workflows/operational_workflows.py` — `DetectAnomaliesWorkflow`
- `apps/worker/activities/operational_activities.py` — anomaly detection activities
- `apps/analysis/lib/ml_primitives.py` — Isolation Forest implementation
- `apps/worker/workflows/quality_workflow.py` — quality check workflow

---

## CC8.1 — Change Management

**Objective**: The entity authorizes, designs, develops or acquires, configures, documents, tests, approves, and implements changes to infrastructure, data, software, and procedures to meet its objectives.

### Implementation

| Component | Status | Description |
|-----------|--------|-------------|
| **Git Version Control** | Implemented | All source code in Git. Branch protection rules enforced. Pull request reviews required for main branch. |
| **CI/CD Pipeline** | Implemented | Automated testing and deployment pipeline. Test suite runs on every PR. |
| **Database Migrations** | Implemented | Django migration framework. All schema changes tracked as versioned migration files. Migration history preserved in Git. |
| **Infrastructure as Code** | Implemented | Docker Compose / Kubernetes manifests versioned in Git. Configuration managed via environment variables and settings files. |
| **Schema Versioning** | Implemented | Data contracts use semantic versioning (`DataContract.version`). Contract changes require version bump. |

### Gaps

- [ ] No formal change advisory board / approval workflow
- [ ] No automated rollback on failed deployments
- [ ] No change impact analysis tooling
- [ ] Production deployment approval not automated

### Evidence Files

- `apps/workflows/models.py` — `Job` model with status lifecycle
- `apps/governance/models.py:10-86` — `DataContract` with version tracking
- Git commit history — all changes tracked
- CI/CD configuration files

---

## Control Summary Matrix

| Control | Category | Status | Confidence |
|---------|----------|--------|------------|
| CC6.1 | Logical Access | Implemented | High |
| CC6.2 | Authentication | Partial | Medium |
| CC6.3 | Authorization | Implemented | High |
| CC6.6 | Data Classification | Partial | Medium |
| CC6.7 | Data Disposal | Implemented | High |
| CC7.1 | Monitoring | Implemented | High |
| CC7.2 | Anomaly Detection | Implemented | Medium |
| CC8.1 | Change Management | Implemented | Medium |

## Priority Remediation Items

1. **MFA Enforcement** (CC6.2) — Expose MFA toggle in Voyant admin UI
2. **Auto-Classification** (CC6.6) — Add PII detection to profiling pipeline
3. **Retention Scheduler** (CC6.7) — Implement automated data disposal based on `retention_days`
4. **Alerting** (CC7.1) — Configure Prometheus alerting rules for error rate spikes
5. **Token Revocation** (CC6.1) — Implement Redis-backed token blacklist
6. **Anomaly Alerting** (CC7.2) — Route anomaly detection results to alerting system
7. **Change Approval** (CC8.1) — Add deployment approval gates to CI/CD

---

*Generated by Voyant Governance Module v4.0*
