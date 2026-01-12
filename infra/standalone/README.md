# Voyant Standalone Deployment

Full self-contained deployment with all infrastructure services.

## Quick Start

```bash
# Development mode
docker compose up -d

# Production mode (with persistent volumes)
cp .env.production.example .env.production
# Edit .env.production with secure values
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d
```

## Services Included (17 Total)

| Service | Port | Purpose |
|---------|------|---------|
| voyant-api | 45000 | Main REST API |
| voyant-mcp | 45001 | MCP Server for Agents |
| voyant-worker | - | Temporal Workers |
| postgres | 45432 | PostgreSQL 16 |
| redis | 45379 | Redis 7 Cache |
| kafka | 45092 | Kafka 3.7 KRaft |
| minio | 45900/45901 | Object Storage (S3) |
| temporal | 45233 | Workflow Orchestration |
| temporal-ui | 45089 | Temporal Dashboard |
| spark-master | 45088 | Spark Master |
| spark-worker | - | Spark Worker |
| r-engine | 45311 | R Statistical Engine |
| trino | 45090 | SQL Federation |
| elasticsearch | - | DataHub Search |
| datahub-gms | 45080 | DataHub Backend |
| datahub-frontend | 45002 | DataHub UI |
| keycloak | 45180 | Identity & Auth |
| lago-api | 45300 | Billing API |

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
curl http://localhost:45000/health

# Check all services
docker compose ps
```

## Files

- `docker-compose.yml` - Main stack (dev mode)
- `docker-compose.prod.yml` - Production overrides
- `.env.example` - Environment template
- `.env.production.example` - Production secrets template
- `Dockerfile` - App image
- `config/` - Service configurations
- `scripts/` - Init and utility scripts
- `k8s/` - Kubernetes manifests
- `helm/` - Helm charts
