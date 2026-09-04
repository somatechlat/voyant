# Voyant v3.0.0 — Testing Strategy

**Document ID:** VOYANT-TESTING-3.0.0
**Status:** Active
**Date:** 2026-09-04

---

## 1. Test Infrastructure

### 1.1 Framework

- **pytest** with pytest-django, pytest-asyncio, pytest-cov, pytest-env
- **Configuration:** `pyproject.toml [tool.pytest.ini_options]`
- **Async mode:** `asyncio_mode = "auto"`
- **Test paths:** `tests/`

### 1.2 Test Environment

Environment variables set via `pyproject.toml` `env` section:

```
VOYANT_ENV=test
DATABASE_URL=postgresql://voyant:voyant@localhost:45432/voyant_test
REDIS_URL=redis://:voyant@localhost:45379/1
VOYANT_SECRETS_BACKEND=env
VOYANT_SECURITY_ENABLED=false
```

### 1.3 CI Pipeline

`.github/workflows/ci.yml` runs on push/PR to main:

1. **Lint:** ruff check + ruff format --check
2. **Test:** pytest with `--cov-fail-under=50` (coverage gate)
3. **Security:** pip-audit
4. **Docker:** build image (requires lint + test + security to pass)

---

## 2. Test Inventory

### 2.1 Summary

| Metric | Count |
|--------|-------|
| Test files | 121 |
| Test functions | 2,202 |
| Test directories | 15 |

### 2.2 Coverage by Module

| Module | Test Files | Test Functions | Coverage |
|--------|-----------|---------------|----------|
| `tests/core/` | 8 | ~120 | Config, auth, policy, RBAC, schema evolution |
| `tests/unit/core/` | 20 | ~500 | All core/lib modules (artifact_store, circuit_breaker, contracts, druid, errors, events, iceberg, job_queue, metrics, middleware, namespace, pdf, plotly, plugin_registry, policy, quotas, sandbox, secrets, skywalking, superset, tenant_quotas, trino, views) |
| `tests/worker/` | 11 | ~161 | All activity modules (analysis, discovery, generation, ingest, kpi, ml, operational, profile, quality, sandbox, stats) |
| `tests/workflows/` | 4 | ~207 | Workflow models, API, types, all 13 workflow classes |
| `tests/scraper/` | 10 | ~200 | Security, fetch/parse/storage/search activities, deep research (activities, agents, sources, credibility) |
| `tests/analysis/` | 10 | ~200 | Adaptive sampling, anomaly, cleaning, forecasting, ml, nlp, segmentation, stats |
| `tests/capsules/` | 6 | ~150 | Signing (Ed25519), core, execution, registry, integration, unit |
| `tests/search/` | 3 | ~80 | Embeddings, Milvus store, search API |
| `tests/governance/` | 5 | ~200 | API, contract validator, lineage, policy enforcer, schema evolution, policy enforcement middleware |
| `tests/streaming/` | 3 | ~40 | Flink client, activities, workflow |
| `tests/ontology/` | 4 | ~60 | Models, services, validators |
| `tests/mcp_tools/` | 3 | ~50 | Tools core, catalog, scrape |
| `tests/sql/` | 1 | ~20 | SQL API |
| `tests/discovery/` | 2 | ~30 | Catalog, spec parser |
| `tests/uptp_core/` | 2 | ~30 | Engine, parser |
| `tests/ingestion/` | 2 | ~14 | Airbyte connect, connect activity |
| `tests/security/` | 1 | ~10 | Security conftest |
| Root-level tests | 15 | ~150 | Health, analytics, config, contracts, MCP, quotas, SQL guard, stats |

---

## 3. Testing Rules

### 3.1 No Mocks (Project Rule)

Per RULES.md §2: No mocks/placeholders/stubs in production paths. Tests use real objects. Exceptions:
- External HTTP calls use httpx response objects or MonkeyTransport
- Docker-dependent tests skip when Docker unavailable (`@pytest.mark.skipif`)
- NLTK/Prophet tests skip when optional deps unavailable

### 3.2 Database Tests

Tests requiring PostgreSQL use `@pytest.mark.django_db`. These only pass in Docker CI (port 45432).

### 3.3 Async Tests

All async tests use `asyncio_mode = "auto"` — no manual `@pytest.mark.asyncio` needed.

---

## 4. Running Tests

### 4.1 Local (without Docker)

```bash
.venv/bin/pytest tests/unit/ tests/analysis/ tests/capsules/ tests/scraper/ -v --ignore=tests/e2e --ignore=tests/integration
```

### 4.2 Docker CI

```bash
docker compose exec voyant_api python -m pytest --cov=apps --cov-report=term-missing -v
```

### 4.3 Specific Module

```bash
.venv/bin/pytest tests/unit/core/test_trino.py -v
```

---

## 5. Known Test Limitations

| Limitation | Reason | Mitigation |
|-----------|--------|------------|
| E2E tests need full cluster | Require Postgres, Redis, Temporal | Run in Docker CI only |
| Integration tests need services | Require MinIO, Kafka, Milvus | Skip in local, run in CI |
| NLTK tests may skip | VADER lexicon not installed | `pytest.importorskip` |
| Prophet tests skip | Not in test venv | `pytest.importorskip` |
| SpiceDB tests skip | `authzed` module not in local env | Run in Docker CI only |

---

**Document Version:** 3.0.0
**Last Updated:** 2026-09-04
