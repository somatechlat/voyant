# Security Overview

UDB is designed with a security-first posture emphasizing least privilege, isolation, and observability.

## Principles
- Minimize stored secrets / credentials (rotate & scope).
- Deny-by-default networking with explicit egress allowlists.
- Never persist raw secrets in logs or artifacts.
- Tenant isolation across schemas & artifact paths.

## Secrets Management
- Stored in Kubernetes Secrets or external vault (future integration).
- Accessed at runtime via environment variables / mounted files.
- Redacted logging layer ensures patterns (e.g., API keys) are scrubbed.

## Authentication & Authorization
- MCP trust boundary assumed (agent-level auth handled upstream) — future: signed tool invocations.
- HTTP API: optional API key / OIDC middleware (future).
- RBAC stub: roles (`reader`, `operator`, `admin`) for future policy expansion.

## Network Policies
- Default deny-all for pods.
- Allow egress only to: Airbyte services, OAuth endpoints, explicitly configured domains, object storage (future), internal Postgres/Redis/Kafka.

## Data Protection
- DuckDB on encrypted PVC where provider supports.
- Artifact storage separated; optional encryption at rest.
- PII classifier (future) for column detection; masking rules applied to views and artifact redaction.

## Audit Logging
- Structured events for: source creation, sync start/finish, analyze start/finish, SQL execution, artifact access.
- Kafka sink + optional long-term storage pipeline (future).

## OAuth Flows
- Device code fallback for limited environments.
- State parameter integrity check; short-lived temporary secrets.
- Scopes minimized (e.g., `Files.Read` not `Files.ReadWrite`).

## SQL Guard
- Whitelisted statements for KPI queries (SELECT only); reject DDL/DML (except controlled `CREATE VIEW`).
- Parameterized templates to reduce injection risk.

## Supply Chain
- Dependency pinning & vulnerability scan (CI) with tools like Trivy / pip-audit.
- Container image based on slim Python base with non-root user.

## Incident Response (Future)
- Playbooks for credential revocation, data purge, compromised connector.
- Alerting rules on anomaly detection (unexpected spike in `/sql` calls, large artifact retrieval volume).

## Roadmap Additions
- Row-level security & column encryption (stretch).
- Integration with enterprise IAM (SAML/OIDC multi-provider).
- Signed artifact URLs with short TTL (expiring links) for external exposure.

---
This document will evolve alongside threat modeling and operational experience.
