# Voyant Standalone Deployment

Full self-contained deployment with all infrastructure services.

## Quick Start

```bash
# Standalone mode (full local stack)
docker compose up -d
```

Resilient startup (recommended):

```bash
./scripts/start-stack-resilient.sh
```

This command:
- bootstraps missing local secrets into `infra/standalone/.env`
- recreates the cluster
- waits for core services to be healthy/running
- runs smoke checks on API, MinIO, Keycloak, and Trino

## Services Included (18 Total)

| Service | Port | Purpose |
|---------|------|---------|
| voyant_api | 45000 | Main REST API |
| voyant_worker | 45090 | Temporal Workers |
| voyant_postgres | 45432 | PostgreSQL 16 |
| voyant_redis | 45379 | Redis 7 Cache |
| voyant_kafka | 45092 | Kafka 3.7 KRaft |
| voyant_minio | 45900/45901 | Object Storage (S3) |
| voyant_minio_init | - | MinIO bucket bootstrap |
| voyant_temporal | 45233 | Workflow Orchestration |
| voyant_temporal_ui | 45089 | Temporal Dashboard |
| voyant_trino | 45080 | SQL Federation |
| voyant_elasticsearch | 45200 | DataHub Search |
| voyant_datahub_gms | 45081 | DataHub Backend |
| voyant_datahub_frontend | 45002 | DataHub UI |
| voyant_keycloak | 45180 | Identity & Auth |
| voyant_lago_api | 45300 | Billing API |
| voyant_lago_worker | - | Billing worker |
| voyant_flink_jobmanager | 45082 | Flink JobManager UI |
| voyant_flink_taskmanager | - | Flink TaskManager |

## Memory Budget

Total: ~10GB allocated across all services.

## Persistent Volumes (Production)

- `voyant-postgres-prod`: PostgreSQL data
- `voyant-redis-prod`: Redis AOF
- `voyant-kafka-prod`: Kafka logs
- `voyant-minio-prod`: Object storage
- `voyant-elasticsearch-prod`: Search indices

## Verification

```bash
# Check health
curl "${VOYANT_API_HEALTHCHECK_URL}"

# Check all services
docker compose ps
```

## Files

- `docker-compose.yml` - Main stack (dev mode)
- `.env.example` - Environment template
- `.env.production.example` - Production secrets template
- `Dockerfile` - App image
- `config/` - Service configurations
- `scripts/` - Init and utility scripts
- `k8s/` - Kubernetes manifests
- `helm/` - Helm charts
