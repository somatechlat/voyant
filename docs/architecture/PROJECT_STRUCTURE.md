# Voyant v3.0.0 — Project Structure

**Document ID:** VOYANT-STRUCTURE-3.0.0
**Date:** 2026-09-04

---

## Top-Level Layout

```
voyant/
├── apps/                    # 16 Django applications
│   ├── core/                # Base models, config, middleware, security, lib/
│   ├── analysis/            # Statistical analysis, ML, NLP, forecasting
│   ├── capsules/            # Installable intelligence recipes
│   ├── discovery/           # Service catalog, OpenAPI parser
│   ├── governance/          # Data contracts, lineage, policies, quotas
│   ├── ingestion/           # DuckDB loader, Airbyte, quality rules
│   ├── mcp/                 # MCP tool server (45 tools)
│   ├── ontology/            # Entity/relationship management
│   ├── scraper/             # OCTOPUS 9-ARM engine, Deep Research v2
│   ├── search/              # Milvus vector store, embeddings
│   ├── sql/                 # Trino SQL execution API
│   ├── streaming/           # Apache Flink REST API bridge
│   ├── uptp_core/           # Universal Parametric Template Pattern
│   ├── worker/              # Temporal worker (activities + workflows)
│   └── workflows/           # Job, Artifact, Preset models and API
├── voyant_project/          # Django project config
│   ├── settings.py          # Main settings (403 lines)
│   ├── security_settings.py # Security-specific config (316 lines)
│   ├── urls.py              # URL routing
│   ├── asgi.py              # ASGI with MCP mount at /mcp
│   ├── wsgi.py              # WSGI fallback
│   └── __init__.py
├── tests/                   # 121 test files, 2,202 test functions
│   ├── analysis/            # 10 test files
│   ├── capsules/            # 6 test files
│   ├── core/                # 8 test files
│   ├── discovery/           # 2 test files
│   ├── governance/          # 5 test files
│   ├── mcp_tools/           # 3 test files
│   ├── ontology/            # 4 test files
│   ├── scraper/             # 10 test files
│   ├── search/              # 3 test files
│   ├── security/            # 1 test file
│   ├── sql/                 # 1 test file
│   ├── streaming/           # 3 test files
│   ├── unit/                # 20+ test files
│   ├── uptp_core/           # 2 test files
│   ├── worker/              # 11 test files
│   ├── workflows/           # 4 test files
│   └── *.py                 # 15 root-level test files
├── infra/                   # Deployment infrastructure
│   ├── standalone/          # Full 20-service Docker Compose
│   └── integrated/          # Minimal 3-service mode
├── docs/                    # Documentation (56 files)
├── scripts/                 # Dev, ops, verification, examples
├── examples/                # Usage examples
├── dashboard/               # Frontend (Lit 3 Web Components)
├── docker/                  # Sandbox Dockerfile
├── manage.py                # Django management
├── pyproject.toml           # Project config, pytest, ruff, mypy
├── requirements.txt         # Python dependencies
├── Makefile                 # Dev shortcuts
├── RULES.md                 # 12 VIBE coding rules
└── README.md                # Project overview
```

---

## Core Library Modules (`apps/core/lib/`)

| Module | Purpose |
|--------|---------|
| `artifact_store.py` | Content-addressable storage (SHA256/512/BLAKE2B) with MinIO |
| `circuit_breaker.py` | Thread-safe CLOSED/OPEN/HALF_OPEN pattern |
| `contracts.py` | Schema validation and sensitivity classification |
| `druid_client.py` | Druid + Pinot OLAP SQL queries |
| `errors.py` | Canonical VYNT-XXXX error catalog |
| `event_schema.py` | In-memory event schema registry with semver |
| `events.py` | Kafka producer for VoyantEvent |
| `iceberg.py` | Apache Iceberg REST catalog client |
| `interceptors.py` | Temporal activity/workflow metrics interceptor |
| `job_queue.py` | Redis-backed per-tenant concurrency queue |
| `metrics.py` | Prometheus mode-gated metrics (off/basic/full) |
| `monitoring.py` | MetricsRegistry singleton |
| `namespace_analyzer.py` | Tenant table isolation (PREFIX/SCHEMA/METADATA) |
| `pdf_engine.py` | WeasyPrint + Jinja2 PDF rendering |
| `plotly_engine.py` | Plotly/Kaleido chart rendering |
| `plugin_registry.py` | Extensible analyzer/generator plugins |
| `policy.py` | OPA-based external policy integration |
| `python_sandbox.py` | Docker-isolated Python execution |
| `quotas.py` | Tiered tenant resource quotas |
| `r_bridge.py` | Rserve statistical engine bridge |
| `retry_config.py` | Temporal retry policies |
| `secrets.py` | Multi-backend secrets (memory/env/k8s/file/vault) |
| `skywalking.py` | OpenTelemetry + SkyWalking OTLP tracing |
| `spicedb_rbac.py` | Realm-aware RBAC via Authzed gRPC |
| `superset_client.py` | Apache Superset BI integration |
| `temporal_client.py` | Singleton Temporal client |
| `tenant_quotas.py` | Resource limits + usage tracking |
| `trino.py` | Read-only Trino SQL client with hardened validation |
| `workflow_utils.py` | Job dispatch utilities |

---

## OCTOPUS Engine (`apps/scraper/octopus/`)

| ARM | Name | Technology |
|-----|------|-----------|
| ARM-1 | Static | httpx + parsel (CSS/XPath, OpenGraph) |
| ARM-2 | Dynamic | Playwright + Chromium (JS rendering) |
| ARM-3 | Evasion | curl-cffi + camoufox (anti-bot) |
| ARM-4 | Crawl | Scrapy (large-scale site crawl) |
| ARM-5 | API Intercept | Playwright XHR/JSON capture |
| ARM-6 | Document | pdfplumber + unstructured (20+ formats) |
| ARM-7a | OCR | Tesseract (image text + bounding boxes) |
| ARM-7b | Transcribe | OpenAI Whisper (audio/video) |
| ARM-8 | Archive | Playwright interactive deep archiving |

---

## Deep Research v2 (`apps/scraper/deep_research/`)

10-step deterministic pipeline (zero LLM):

1. Query expansion (QueryGenerator)
2. Multi-engine search (SearXNG + Brave + Google CSE)
3. Parallel content fetch (Octopus ARM-2/3)
4. Content extraction (trafilatura / readability / newspaper / crawl4ai)
5. Source scoring (domain credibility DB + freshness)
6. Deduplication (MinHash/LSH)
7. Synthesis (TF-IDF sentence clustering)
8. Recursive follow-up (depth > 1)
9. Cross-validation (>=2 independent sources)
10. Markdown report generation

---

## Django Patterns

- All app code under `apps/<domain>/`
- Shared libraries under `apps/core/lib/`
- HTTP APIs in per-domain `api.py`, registered centrally in `apps/core/api.py`
- Workflows/activities under `apps/worker/workflows/` and `apps/worker/activities/`
- Settings/routing only in `voyant_project/`
- Migrations per app in `apps/<domain>/migrations/`

---

**Document Version:** 3.0.0
**Last Updated:** 2026-09-04
