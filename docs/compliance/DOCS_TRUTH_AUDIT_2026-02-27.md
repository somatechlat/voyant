# Documentation Truth Audit

Date: 2026-02-27  
Scope: `docs/**/*.md` (full repository documentation tree)

## Method
- Checked internal markdown link targets for missing local files.
- Validated key architecture claims against current code paths.
- Verified measured runtime/documentation counts directly from source files:
  - Django app domains from `apps/`
  - API routers from `apps/core/api.py`
  - MCP tool registrations from `apps/mcp/tools.py`

## Verified Snapshot
- Django app domains in repository: **18**
- API routers mounted in `apps/core/api.py`: **10**
- MCP tools registered in `apps/mcp/tools.py`: **45**

## Corrections Applied
- Fixed canonical documentation path drift:
  - `docs/SRS.md` -> `docs/specifications/SRS.md`
  - `docs/TASKS.md` -> `docs/management/TASKS.md`
  - `docs/DESIGN.md` -> `docs/architecture/DESIGN.md`
- Updated `docs/management/AGENT_CONTINUITY.md`:
  - Removed unverified external repository size claims.
  - Replaced stale MCP count language with code-verified snapshot.
  - Updated quality-gate status to current repo results.
- Updated `docs/specifications/srs/Voyant_SRS.md`:
  - Added historical-draft status note and canonical pointer.
  - Corrected critical path/count mismatches (`apps/worker/activities`, MCP count, security/api module naming).
- Updated `docs/specifications/SRS_SCRAPER.md`:
  - Added status note and canonical pointer.
  - Replaced stale module tree with current repo layout.
  - Marked NiFi/Tika integrations as planned.
- Updated `docs/management/TASKS.md`:
  - Fixed migration and scraper test path references.
  - Marked missing e2e smoke file as planned (`new`).

## Remaining Intentional Gaps
- Some docs reference planned files that do not exist yet (explicitly marked as `planned` or `new`):
  - `apps/core/lib/iceberg.py`
  - `apps/governance/lib/atlas.py`
  - `apps/observability/skywalking.py`
  - `apps/ingestion/lib/nifi.py`
  - `apps/bi/superset.py`
  - `apps/olap/druid.py`
  - `apps/olap/pinot.py`
  - `apps/ingestion/lib/tika.py`
  - `tests/test_e2e_smoke.py`

## Result
- Documentation now uses correct canonical paths and verified repository counts.
- Historical detailed specs are explicitly labeled to prevent misinterpretation as current implementation truth.
