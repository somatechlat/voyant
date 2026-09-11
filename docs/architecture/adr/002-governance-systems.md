# ADR 002: Governance Systems Consolidation — Keycloak + SpiceDB, Ranger/Atlas Deferred

- **Status:** Accepted
- **Date:** 2026-09-08
- **Context:** VOYANT-SAD-4.0.0 §9 prescribes a six-system governance/security chain: APISIX → Keycloak → SpiceDB → Ranger → Atlas → Vault, plus DataHub for metadata. The v4.0 codebase audit found: Keycloak JWT and SpiceDB ReBAC fully implemented (`apps/core/security/`, `apps/core/lib/spicedb_rbac.py`); Vault wired via `apps/core/config.py`; DataHub GMS client functional (`apps/governance/lib/datahub*`); **Ranger and Atlas clients are stubs** (`apps/governance/lib/ranger_client.py`, `atlas_client.py`); APISIX is not deployed in either compose stack. Meanwhile SRS requirements GOV-F-003 (row-level security) and GOV-F-004 (column masking) remain unimplemented and are P1 gaps.
- **Forces:** A 4.5-person team cannot operate 24–30 infrastructure services; every additional governance system is an upgrade/backup/security surface. Ranger's policy model overlaps with SpiceDB (app ReBAC) and with query-time enforcement in the Trino client (data RBAC). Atlas lineage overlaps with DataHub, which is already integrated and working.

## Decision

1. **Authentication/authorization stack is Keycloak (JWT) + SpiceDB (ReBAC) + Vault (secrets).** This is the complete, normative chain for V4.0.0.
2. **Row-level security and column masking are implemented in the Trino query path** (`apps/core/lib/trino.py` + `apps/governance`), where SQL actually flows — not via Apache Ranger. Ranger is deferred to integrate-on-demand for deployments that mandate it.
3. **DataHub is the single metadata/lineage system.** Apache Atlas is deferred; the stub client is removed or marked deprecated.
4. **APISIX is deferred.** nginx (dashboard) plus Django middleware (rate limiting, TLS termination at the edge) suffice until multi-tenant gateway metering/billing is required.
5. Re-entering any deferred system requires a new ADR with an operational-cost justification.

## Alternatives Considered

- **Full SAD stack (Ranger + Atlas + APISIX):** rejected — ~5 extra stateful services, duplicate policy planes (Ranger vs SpiceDB vs middleware), no requirement that only they satisfy.
- **Ranger-only for data RBAC:** rejected — policy evaluation outside the query path adds latency and an operationally heavy Java service; query-time enforcement in the Trino client already has the full SQL parse context (existing `_validate_sql` pipeline).

## Consequences

- **Positive:** Governance P1 requirements (GOV-F-003/004) delivered with zero new infrastructure; one policy plane for app authz (SpiceDB), one for data authz (Trino path); smaller deploy footprint (~24 services); clearer audit story for SOC 2.
- **Negative:** Enterprises standardized on Ranger/Atlas must integrate later (documented as V4.1+ roadmap); Trino-client enforcement must be kept bypass-proof — any new query path (e.g. Spark SQL direct) must route through the same policy layer.
- **Follow-ups:** PDP-4.0.0 Track T4 items T4-01/T4-02 implement RLS/masking; T4-06 removes or deprecates the Atlas stub.
