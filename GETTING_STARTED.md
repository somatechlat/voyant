# Getting Started with Universal Data Box (UDB)

This guide walks you through standing up the full (real, no mocks) stack locally, ingesting data two ways (file upload + Airbyte sync), running an analysis, exploring artifacts, lineage, events, and metrics, and understanding the key security / feature toggles.

> TL;DR quickstart
> 1. `docker compose up -d --build`
> 2. Wait ~60s for Airbyte to finish bootstrapping.
> 3. `curl -s localhost:8000/readyz | jq` (status should be `ready` or `degraded` if optional deps down)
> 4. Upload sample data: `curl -s -X POST -H 'X-UDB-Role: analyst' -F 'file=@examples/data/sample_customers.csv' -F 'table=customers' localhost:8000/ingest/upload | jq`
> 5. Run analyze: `curl -s -X POST -H 'X-UDB-Role: analyst' localhost:8000/analyze -H 'Content-Type: application/json' -d '{"kpis":[{"name":"customer_count","sql":"select count(*) as cnt from customers"}]}' | jq`
> 6. Fetch manifest: `curl -s localhost:8000/artifact_manifest/<JOB_ID_FROM_ANALYZE> | jq`
> 7. View recent events: `curl -s localhost:8000/events/recent | jq`
> 8. Core metrics: `curl -s localhost:8000/metrics/select?mode=core | grep udb_`

---

## 1. Prerequisites
- Docker & Docker Compose
- (Optional) Kubernetes cluster + Helm for cluster deployment
- curl & jq for quick API exploration
- Python 3.11+ if you want to run the example script outside containers

## 2. Launch Local Full Stack
The repository includes a `docker-compose.yml` provisioning:
- Kafka (KRaft)
- Redis
- Kestra (optional orchestration)
- Airbyte (server + worker in monolith)
- UDB API (FastAPI + MCP server)

Start everything:
```
docker compose up -d --build
```
Check container health logs if something stalls (initial Airbyte bootstrap can take ~60s).

## 3. Environment & Feature Flags
Key environment variables (see `.env.example` + README):
- `UDB_ENABLE_EVENTS=1` enable Kafka lifecycle events
- `UDB_ENABLE_QUALITY=1` enable profiling & quality/drift artifacts (default on in code if flagged)
- `UDB_ENABLE_CHARTS=1` enable Plotly chart generation
- `UDB_ENABLE_NARRATIVE=1` narrative summarization
- `UDB_DISABLE_RATE_LIMIT=1` disable rate limiting locally
- `UDB_ENABLE_RBAC=1` enforce role header (`X-UDB-Role`)
- `UDB_ENABLE_TRACING=1` emit OpenTelemetry spans if OTLP endpoint also configured
- `UDB_ENABLE_KESTRA=1` enable `/kestra/trigger`

Headers of note:
- `X-UDB-Role`: viewer | analyst | admin (use at least analyst for ingest/sql/analyze)
- `X-UDB-Tenant`: optional multi-tenant namespace; isolates job IDs & artifacts

## 4. Ingest Path A: File Upload (Unstructured / CSV)
Upload a CSV (sample provided below in examples directory):
```
curl -s -X POST -H 'X-UDB-Role: analyst' \
  -F 'file=@examples/data/sample_customers.csv' \
  -F 'table=customers' \
  localhost:8000/ingest/upload | jq
```
Response includes `jobId` (ingest) plus fragments count.

Verify table materialized (role analyst required):
```
curl -s -X POST -H 'X-UDB-Role: analyst' localhost:8000/sql \
  -H 'Content-Type: application/json' \
  -d '{"sql":"select * from customers limit 5"}' | jq
```

## 5. Ingest Path B: Airbyte Source Discovery & Sync
Discovery + connect using a simple hint (example: a fictional public CSV host or domain). Adjust `hint` for real connectors.
```
curl -s -X POST localhost:8000/sources/discover_connect \
  -H 'Content-Type: application/json' \
  -d '{"hint":"https://example.com/data"}' | jq
```
You receive: `sourceId`, `destinationId`, `connectionId`, `jobId` (sync). Poll status:
```
curl -s localhost:8000/status/<SYNC_JOB_ID> | jq
```
Or watch events:
```
curl -s localhost:8000/events/recent | jq
```

## 6. Run an Analysis Job
Minimal analyze body with KPI list:
```
ANALYZE_PAYLOAD='{"kpis":[{"name":"customer_count","sql":"select count(*) as cnt from customers"}]}'
curl -s -X POST -H 'X-UDB-Role: analyst' localhost:8000/analyze \
  -H 'Content-Type: application/json' \
  -d "$ANALYZE_PAYLOAD" | jq
```
Result: `jobId`, `summary`, `kpis` array, `artifacts` map (paths).

## 7. Retrieve Artifacts & Manifest
List all files for an analysis job:
```
curl -s localhost:8000/artifact_manifest/<ANALYZE_JOB_ID> | jq
```
Fetch a single artifact (e.g., profiling HTML):
```
curl -s localhost:8000/artifact/<ANALYZE_JOB_ID>/profile.html > profile.html
open profile.html  # macOS
```

## 8. Lineage View
Generate a lightweight lineage graph for a job:
```
curl -s localhost:8000/lineage/<ANALYZE_JOB_ID> | jq
```
Nodes include source, connection, job, and artifacts edge.

## 9. Events & Ring Buffer
Recent events (up to ring buffer depth):
```
curl -s localhost:8000/events/recent | jq
```
Event schema (for forward contracts):
```
curl -s localhost:8000/events/schema | jq
```

## 10. Metrics (Prometheus)
Core subset:
```
curl -s localhost:8000/metrics/select?mode=core
```
Full metrics:
```
curl -s localhost:8000/metrics | grep udb_
```
Key metrics to inspect early: `udb_sufficiency_score`, `udb_job_duration_seconds`, `udb_artifact_size_bytes`.

## 11. SQL Execution
Ad-hoc query (auto LIMIT injection if you omit one):
```
curl -s -X POST -H 'X-UDB-Role: analyst' localhost:8000/sql \
  -H 'Content-Type: application/json' \
  -d '{"sql":"select count(*) from customers"}' | jq
```

## 12. Multi-Tenancy (Optional)
Provide header to namespace artifacts and job IDs:
```
-H 'X-UDB-Tenant: acme'
```
Same table names across tenants will resolve to namespaced physical tables internally.

## 13. Security & Access Controls
- RBAC: analyst required for ingest, sql, analyze; admin for `/admin/prune`.
- ABAC helper (example usage in code base) can enforce header equality on sensitive endpoints.
- SQL Allowlist: enforced in validator (`udb_api/security.py`). Only safe statements permitted.
- Rate limiting: disable with `UDB_DISABLE_RATE_LIMIT=1` for local dev.

## 14. Cleanup & Pruning
Manual prune (admin role):
```
curl -s -X POST -H 'X-UDB-Role: admin' localhost:8000/admin/prune | jq
```
Background pruning can be enabled via env intervals (see code comments in `app.py`).

## 15. Example Script
See `examples/ingest_and_analyze.py` for an end-to-end Python script performing: upload -> analyze -> manifest -> metrics.
Run (from repo root with venv):
```
python examples/ingest_and_analyze.py
```

## 16. Helm / Kubernetes Quick Outline
1. Inspect chart values: `helm show values helm/voyant-udb`.
2. Install: `helm install udb helm/voyant-udb -n data --create-namespace`.
3. (Optional) Enable ServiceMonitor & feature flags via `--set` or custom values file.
4. Port-forward API service to test endpoints as above.

## 17. Troubleshooting
| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| `/readyz` degraded (Airbyte) | Airbyte still booting | Wait or check Airbyte logs |
| Analyze missing quality artifacts | Quality flag disabled | Ensure `UDB_ENABLE_QUALITY=1` |
| 429 errors | Rate limit active | Set `UDB_DISABLE_RATE_LIMIT=1` |
| Kafka event endpoints empty | Events disabled or no jobs yet | Set `UDB_ENABLE_EVENTS=1` and run jobs |
| Lineage missing nodes | Only recent events stored | Re-run job to refresh buffer |

## 18. Next Steps / Extensions
- Persist lineage beyond ring buffer (e.g., dedicated table)
- Add OpenLineage, external object storage exporter
- Expand KPI templating + parameterization

---
You now have a functioning Universal Data Box able to ingest, analyze, and observe data workflows locally with production-grade patterns. Iterate from here! 🚀
