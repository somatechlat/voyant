# Voyant Infrastructure

Integrated mode is the default platform state.

## Modes

| Mode | Folder | Use Case |
|------|--------|----------|
| [Integrated](integrated/) | `infra/integrated/` | Default: connects to SomaAgentHub (3 services) |
| [Standalone](standalone/) | `infra/standalone/` | Optional full self-contained stack |

## Quick Reference

### Integrated (Default)
```bash
# Start SomaAgentHub first, then:
cd infra/integrated
docker compose --env-file .env.integrated up -d
```

### Standalone (Optional Full Stack)
```bash
cd infra/standalone
docker compose --env-file .env.example up -d                # Dev defaults
docker compose --env-file .env.production.example up -d     # Prod-like config
```

## Environment Detection

Set `VOYANT_DEPLOYMENT_MODE`:
- `integrated` (default): Connect to SomaAgentHub
- `standalone`: Full infrastructure

```python
# voyant/core/config.py
if settings.deployment_mode == "integrated":
    # Use Hub services (policy, memory, orchestrator)
else:
    # Self-contained operation
```
