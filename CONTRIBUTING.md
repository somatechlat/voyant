# Contributing

We welcome contributions. Core principle: **no mocking of critical integration paths** (Airbyte, DuckDB, Kafka, Redis, Kestra) in tests—exercise real behavior.

## Development Workflow
1. Fork & clone repository.
2. Create virtual environment & install dependencies.
3. `docker compose up -d --build` for real-mode stack, or deploy via Helm.
4. Run `pytest` (ensures no forbidden monkeypatch).  
5. Update `CHANGELOG.md` (Unreleased section) if user-visible change.
6. Open PR referencing roadmap phase / issue.

## Standards
- Python 3.11+ (target 3.12 compatibility; avoid 3.13-only features until verified).
- Type hints required for all new modules & function signatures.
- Structured JSON logging only (no ad-hoc prints in core code).
- Functions ideally < 75 lines—refactor large blocks.
- Feature flags via `UDB_ENABLE_*` env; no scattered conditional logic—centralize in settings.

## Commit Messages
Format: `<scope>: <imperative summary>`  
Examples:
- `analyze: add dependency health gauges`
- `events: emit sufficiency components in completion event`

## Testing Guidelines
- Use `pytest` integration style; avoid heavy unit mocking.
- Negative test for each validator (e.g., SQL guard) and failure-path event emission.
- Assert metrics for new behaviors (grep `/metrics`).
- Kafka event schema changes must update `/events/schema` endpoint.

## No-Mock Enforcement
`tests/conftest.py` blocks monkeypatch of `httpx`, `redis`, `aiokafka`. If you need a new exception, discuss before merging.

## Security
- Never log secrets or plaintext tokens.
- Use SQL allowlist validator for user-provided statements.
- Tenant isolation: prefix artifacts & tables—keep changes consistent.

## Code Review Focus
- Clarity & failure handling.
- Idempotent startup & shutdown.
- Metric + log completeness (does every new path emit something observable?).

## Roadmap Alignment
Update `docs/ROADMAP.md` when scope shifts or a phase completes. Reference phase in PR description.

## Release Process
1. Ensure Unreleased section captures changes.
2. Bump chart/app version if deployment-impacting changes.
3. Tag (`v0.x.y`), push tag, build & publish image.
4. Move Unreleased items under new version heading.

---
Thank you for contributing!
