# Voyant Infrastructure

Two deployment modes, completely isolated.

## Modes

| Mode | Folder | Use Case |
|------|--------|----------|
| [Standalone](standalone/) | `infra/standalone/` | Full self-contained stack (17 services) |
| [Integrated](integrated/) | `infra/integrated/` | SomaAgentHub tool (3 services) |

## Quick Reference

### Standalone (Full Stack)
```bash
cd infra/standalone
docker compose up -d                    # Dev
docker compose -f docker-compose.yml \
  -f docker-compose.prod.yml up -d      # Prod
```

### Integrated (SomaAgentHub)
```bash
# Start SomaAgentHub first, then:
cd infra/integrated
docker compose --env-file .env.integrated up -d
```

## Environment Detection

Set `VOYANT_DEPLOYMENT_MODE`:
- `standalone` (default): Full infrastructure
- `integrated`: Connect to SomaAgentHub

```python
# voyant/core/config.py
if settings.deployment_mode == "integrated":
    # Use Hub services (policy, memory, orchestrator)
else:
    # Self-contained operation
```
