# Scaling Guide

This document outlines how to evolve the deployment as workload and tenancy grow.

## 1. Database / Storage
Current: DuckDB single-process file.  
Paths to scale:
- Offload cold artifacts to object storage (S3/GCS) – mount read-only for replay.
- External warehouse (Postgres, ClickHouse, Snowflake) for large multi-tenant KPI queries.
- Use DuckDB for rapid profiling; persist curated tables in warehouse.

## 2. Concurrency Control
DuckDB writes serialized by global async lock. If queue grows:
- Introduce job queue (Redis streams / Kafka) for analyze tasks processed by worker pods.
- Separate ingest & analyze worker deployments.

## 3. Kafka
Current: Single-node KRaft for dev.
- Production: 3–5 broker cluster, replication factor 3, retention tuned to 7–30 days.
- Add topic-level ACLs and enable TLS if multi-team.

## 4. Redis
Current: Single instance (no persistence required).  
Scale by enabling replication + Sentinel or switch to managed Redis (or KeyDB) with multi-AZ.

## 5. Horizontal Scaling API
State kept minimal (artifact files + DuckDB).  
Options:
- Sticky sessions not required.
- Use ReadWriteMany PVC / object storage abstraction for artifacts if multiple replicas need access.
- Move DuckDB to ephemeral per-request mode once warehouse externalized.

## 6. KPI Execution
If KPI latency increases:
- Pre-materialize heavy join views.
- Cache results per job in Redis with hash keyed by normalized SQL.
- Introduce vectorized / compiled queries via DuckDB extensions.

## 7. Memory & CPU
Tune via:
- Profiling buckets in `udb_job_duration_seconds` and `udb_kpi_exec_latency_seconds`.
- Monitor `udb_duckdb_queue_length`; sustained >2–3 suggests scaling or decoupling.

## 8. Multi-Tenancy
- Separate artifact roots by tenant already in place.
- Optionally prefix Kafka topic with tenant or emit tenant label (avoid high cardinality—use dedicated topics if >50 tenants).
- Enforce tenant-specific rate limits (extend rate_limited decorator with tenant key).

## 9. Observability at Scale
- Push metrics to remote write; downsample high-churn histograms.
- Retain only 0.5, 0.9, 0.99 quantile views for KPI latency if storage pressure.

## 10. Security & Isolation
- NetworkPolicies segment Kafka/Redis.
- Secrets: adopt external secret manager (Vault, AWS Secrets Manager) and mount via CSI driver.

## 11. Disaster Recovery
- Periodic snapshot of DuckDB file (rsync/object store).  
- Reconstruct Kafka topics from change events if lineage added.

## 12. Roadmap Hooks
Planned enhancements enabling scale transitions: OpenLineage, external warehouse adapter, object storage artifact exporter.

---
Iterate incrementally—only adopt next tier when corresponding metric threshold is consistently exceeded.
