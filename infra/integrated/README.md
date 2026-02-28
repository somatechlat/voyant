# Voyant Integrated Mode (SomaAgentHub)

Minimal Voyant deployment that connects to SomaAgentHub services.

## Prerequisites

SomaAgentHub must be running with:
- Policy Engine (port 10020)
- Memory Gateway (port 8000)
- Orchestrator (port 10001)
- Shared infrastructure (Postgres, Redis, Kafka, Temporal)

## Quick Start

```bash
# 1. Ensure SomaAgentHub is running
cd /path/to/somaAgentHub
docker compose up -d

# 2. Start Voyant integrated
cd /path/to/voyant/infra/integrated
docker compose --env-file .env.integrated up -d
```

## Services (3 Total)

| Service | Port | Purpose |
|---------|------|---------|
| voyant-api | 8080 | REST API (Hub-connected) |
| voyant-mcp | 8081 | MCP Server for Agents |
| voyant-worker | - | Temporal Workers |

## Integration Points

| Voyant Uses | From SomaAgentHub |
|-------------|-------------------|
| Policy checks | Policy Engine `/v1/evaluate` |
| Memory persistence | Memory Gateway `/v1/remember` |
| Job callbacks | Orchestrator `/v1/sessions` |
| Shared DB | PostgreSQL |
| Shared cache | Redis |
| Shared events | Kafka |

## Verification

```bash
# Check Voyant health
curl "${VOYANT_API_HEALTHCHECK_URL}"

# Test MCP (from agent)
curl -X POST "${VOYANT_MCP_API_URL}/mcp" \
  -H "Content-Type: application/json" \
  -d '{"method": "voyant.analyze", "params": {...}}'
```
