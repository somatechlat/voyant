# Real Data Test Plan: Universal Data Box

_Last updated: 2025-10-02_

## Objectives
Validate end-to-end ingestion + analysis using: (1) public remote structured source, (2) local file upload, (3) optional unstructured document, (4) sufficiency scoring artifact integrity.

## Environments
| Environment | Purpose | Notes |
|-------------|---------|-------|
| Local Dev | Functional validation | Run UDB API + Airbyte locally |
| Container Compose | Reproducible demo | Optional docker-compose extension |

## Preconditions
- Airbyte running and reachable (export AIRBYTE_URL=http://localhost:8001)
- `DUCKDB_PATH` points to writable location (e.g. ./data/warehouse.duckdb)
- Feature flags (example minimal core):
  ```
  export UDB_ENABLE_QUALITY=1
  export UDB_ENABLE_CHARTS=1
  export UDB_ENABLE_UNSTRUCTURED=1
  export UDB_ENABLE_NARRATIVE=1
  export UDB_ENABLE_RBAC=0  # simplify for manual tests
  ```

## Test Dataset Candidates
| Scenario | Source | Access Method | Rationale |
|----------|--------|---------------|-----------|
| Public CSV | COVID-19 sample (Johns Hopkins daily) | HTTP URL via Airbyte HTTP CSV source | Stable, small subset |
| Public JSON API | GitHub public events (sample) | Airbyte HTTP API source | Semi-structured, dynamic |
| Local File | Local `data/sample_sales.csv` | `/ingest/upload` | Validates upload pipeline |
| Unstructured | A PDF (e.g. sample SEC filing excerpt) | `/ingest/upload` with unstructured flag | Fragment ingestion test |

## Step-by-Step Cases
### Case 1: Public CSV Sync + Analyze
1. Call `POST /sources/discover_connect` with body:
   ```json
   { "hint": "https://raw.githubusercontent.com/datasets/covid-19/main/data/countries-aggregated.csv" }
   ```
2. Poll `GET /status/{jobId}` until `state` in [succeeded, failed].
3. Invoke `POST /analyze` with:
   ```json
   { "connectionIds": ["<connectionId from step 1>"] }
   ```
4. Verify response contains:
   - `artifacts.profileHtml`
   - `artifacts.sufficiencyJson`
   - `kpis[]` non-empty (if KPIs configured) or empty acceptable
5. Fetch sufficiency artifact: `GET /artifact/{jobId}/sufficiency.json` and confirm JSON keys `score`, `components`, `needs`.

### Case 2: Local File Upload + Analyze
1. Prepare `sample_sales.csv` (columns: date, region, product, amount).
2. Upload:
   ```
   curl -F "file=@sample_sales.csv" http://localhost:8088/ingest/upload
   ```
3. Capture returned `table` and `jobId`.
4. Run analyze with KPI:
   ```json
   { "kpis": [ {"name":"total_sales","sql":"SELECT SUM(amount) AS total_sales FROM <table>"} ] }
   ```
5. Validate KPI row contains numeric value; sufficiency file exists.

### Case 3: Unstructured Document Ingestion
1. Export a small PDF as `doc.pdf`.
2. Upload via `/ingest/upload`.
3. Query DuckDB manually (optional) via `/sql`:
   ```json
   { "sql": "SELECT COUNT(*) as fragments FROM doc_fragments" }
   ```
4. Analyze again including narrative (if enabled) to see fragments not breaking pipeline.

### Case 4: Feature Flag Disabling
1. Set `UDB_ENABLE_QUALITY=0` and restart API.
2. Run analyze; ensure `qualityHtml` / `driftHtml` not present; sufficiency still emitted.
3. Set `UDB_ENABLE_CHARTS=0`; run again to confirm charts suppressed.

### Case 5: Stress Minimal Data
1. Create a tiny CSV with 2 rows and many NULLs.
2. Upload + analyze.
3. Expect low sufficiency score and non-empty `needs` array including null density warning.

## Success Criteria
| Metric | Expected |
|--------|----------|
| Analyze completion (public CSV) | < 90s |
| Sufficiency score presence | 100% of analyze runs |
| Failure rate | 0 critical errors across cases |
| Quality artifacts when enabled | Present for supported numeric columns |

## KPI Suggestions (Optional)
| Name | SQL |
|------|-----|
| total_rows | `SELECT SUM(rows) AS total_rows FROM (SELECT COUNT(*) AS rows FROM countries_aggregated)` |
| distinct_countries | `SELECT COUNT(DISTINCT Country) as distinct_countries FROM countries_aggregated` |
| latest_date | `SELECT MAX(Date) as latest_date FROM countries_aggregated` |

## Troubleshooting
| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| Missing sufficiency.json | Analyze exception or write permission issue | Check logs; ensure artifacts root writable |
| No tables after sync | Airbyte source mis-detected | Inspect Airbyte UI; verify source definition |
| Low freshness score | No timestamp column inferred | Add synthetic column via view or connector config |
| High null ratio reported | Sparse columns | Drop irrelevant columns or enrich upstream |

## Post-Test Checklist
- Archive artifacts from at least one successful run
- Record sufficiency score baseline for sample dataset
- Capture metrics endpoint snapshot for documentation

---
This plan evolves with new modules (contracts, lineage); update when sufficiency model parameters change.
