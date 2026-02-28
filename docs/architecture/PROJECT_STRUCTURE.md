# Project Structure (Django Enterprise Layout)

## Runtime Domains

- `voyant_project/`: Django project configuration (`settings`, `urls`, `asgi`, `wsgi`).
- `apps/`: bounded Django application domains and shared libraries.
- `tests/`: repository-level automated tests grouped by test scope.

## Platform Domains

- `infra/`: deployment and environment assets (`integrated/`, `standalone/`, Helm/K8s manifests).
- `dashboard/`: frontend application and build tooling.
- `docs/`: architecture, specifications, operations, and compliance documentation.

## Operational Domains

- `scripts/`: organized by intent (`dev/`, `ops/`, `verification/`, `examples/`, `sql/`).
- `examples/`: higher-level Python usage examples for product flows.

## Django Pattern Rules

- Keep all Django app code under `apps/<domain>/`.
- Keep reusable shared libraries under `apps/core/lib/`.
- Keep HTTP APIs in per-domain `api.py` modules and register centrally in `apps/core/api.py`.
- Keep background workflows/activities under `apps/worker/workflows/` and `apps/worker/activities/`.
- Keep project-level settings/routing only in `voyant_project/`.

## Repository Hygiene Rules

- Do not keep orphan runtime files at repository root.
- Keep generated artifacts and local data outside versioned source paths.
- Update docs when moving files between domains.
