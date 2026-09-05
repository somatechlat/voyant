# Recursive Code Sweep Report

Date: 2026-02-27  
Scope: full tracked repository (`git ls-files`), folder-by-folder recursive audit

## Inventory Snapshot
- Tracked files: 382
- Python files: 244
- Markdown files: 45

Top-level tracked distribution:
- `apps`: 194 files
- `infra`: 51 files
- `docs`: 34 files
- `tests`: 30 files
- `dashboard`: 19 files
- `scripts`: 18 files
- `voyant_project`: 6 files
- other root/support files: remainder

## Quality Gates
- `python3 -m compileall -q apps tests scripts voyant_project`: pass
- `python3 -m ruff check .`: pass
- `python3 manage.py check`: pass (warnings only)
- `python3 -m pytest -q --collect-only`: pass (253 tests collected)
- `pyright`: fail (366 errors)

## Folder-by-Folder Findings

### `apps/`
- Structure and imports are syntactically valid (`compileall` pass).
- Lint baseline is clean (`ruff` pass).
- No TODO/FIXME placeholder scaffolding detected in active app code.
- Notes:
  - Placeholder mentions in `apps/core/lib/kpi_templates.py` are functional SQL template semantics, not stubs.

### `voyant_project/`
- Django project checks pass (`manage.py check`).
- Audit log default path normalized to `/var/log/udb/audit.log`.

### `tests/`
- Recursive collection succeeds (253 tests discovered).
- Scraper tests are under `apps/scraper/tests/` and project tests under `tests/`.
- No structural import errors detected during collection.

### `scripts/`
- Reorganized into `dev/`, `ops/`, `verification/`, `examples/`, `sql/`.
- Current script paths are coherent with docs/infra references.

### `docs/`
- Internal markdown links are clean (no broken local links found).
- Canonical path alignment now points to:
  - `docs/specifications/SRS.md`
  - `docs/management/TASKS.md`
  - `docs/architecture/DESIGN.md`
- Legacy detailed specs are now explicitly marked as draft/non-canonical where relevant.

### `infra/`
- Compose reference updated to `scripts/sql/init-db.sql`.
- MinIO bootstrap alias normalized from `voyant` to `minio` to avoid stale naming.

## Detected Remaining Risks

### High
- Type-checking debt remains unresolved:
  - `pyright` reports 366 errors across workflows, core libs, models, and tests.

### Medium
- Planned-file references in specs/tasks intentionally point to not-yet-implemented modules (e.g., Iceberg/NiFi/Atlas/Tika paths).

## Conclusion
- Recursive folder-by-folder sweep completed.
- Runtime integrity gates (Django check, lint, syntax, pytest collection) are passing.
- Primary blocker for "perfect" engineering baseline is unresolved `pyright` error backlog.
