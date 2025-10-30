# Principles

1. No Mocks in Core Flows
   Real integrations (Airbyte, DuckDB, Kafka, Redis, Kestra). Tests must exercise real I/O.
2. Fail Fast
   If a required dependency is unavailable at startup in strict mode, abort.
3. Deterministic Minimalism
   Keep external workloads minimal (narrow catalogs, small sample sources) while staying real.
4. Observability First
   Every critical operation emits metrics, structured logs, and (optionally) traces.
5. Secure by Default
   Principle of least privilege, tenant isolation, SQL allowlist, PII masking.
6. Incremental Evolution
   Ship vertical slices that produce user-observable value over horizontal scaffolding.
7. Transparency
   Endpoint /startupz and metrics expose system health without guessing.
8. Extensibility
   Feature flags gate optional capabilities; config-driven without code branches where possible.

These principles guide review and acceptance; regressions require justification or compensating controls.
# Project Principles

We adhere to a set of guiding principles that shape all architecture and implementation decisions.

## 1. Truth Over Convenience
- Favor real integrations over simulated behavior.
- Avoid hard-coded shortcuts that deviate from production behavior.
- Tests should exercise true system flows (with fallback skips only when an external dependency is legitimately unreachable, never replaced by logic fakes).

## 2. No Mocking in Core Paths
- We do not mock or mimic core external systems (Airbyte, DuckDB, Redis, Kafka) for mainline tests or runtime logic.
- Unit tests may isolate pure functions, but integration tests MUST run against real service instances (local docker compose or ephemeral environments).
- Stubs are transitional and must be tracked and removed before milestone releases (tracked in roadmap).

## 3. Elegance
- Design minimal, coherent abstractions rather than sprawling utility layers.
- Prefer explicit data structures and type-hinted contracts.
- Optimize for maintainability and clarity before micro-optimizations.

## 4. Simplicity
- Minimize configuration surface; provide strong defaults.
- Avoid premature generalization—extend based on real needs.
- Narrow interfaces: each module has a single, clear responsibility.

## 5. Observability as a First-Class Feature
- Every job/action should emit structured logs, metrics, and trace context.
- Debuggability is a design requirement, not an afterthought.

## 6. Security by Default
- Least privilege for credentials & network access.
- No secrets in logs or artifacts.
- Guardrails (SQL allowlist, masking hooks) always enabled.

## 7. Deterministic & Reproducible
- Pin dependencies; document environment boot sequence.
- Infrastructure manifests and Helm charts define the authoritative deployment path.

## 8. Artifact Integrity
- Generated artifacts must be traceable to input sources & job IDs.
- No silent mutation or overwriting without versioning intent.

## 9. Fail Fast, Fail Loud
- Surface errors immediately with actionable context.
- No silent exception swallowing.

## 10. Continuous Hardening
- Replace provisional stubs incrementally with production-grade subsystems.
- Maintain a living backlog of technical debt with clear removal criteria.

---
These principles are living; propose changes via PR referencing this document.
