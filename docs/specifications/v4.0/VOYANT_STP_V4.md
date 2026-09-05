# Voyant v4.0 — Software Test Plan

**Document ID:** VOYANT-STP-4.0.0
**Version:** 4.0.0-draft
**Date:** 2026-09-05
**Standard:** ISO/IEC/IEEE 29119-1:2013
**Status:** Draft for Review

---

## 1. Test Strategy

### 1.1 Current State (Measured)

| Metric | Value |
|--------|-------|
| Test files | 148 |
| Test functions | 2,203 |
| Passing | 2,128 |
| Skipped | 51 |
| Failing | 0 |
| Coverage target | >80% |

### 1.2 Test Pyramid

```
        ┌─────────┐
        │  E2E    │  10 tests (Playwright)
       ┌┴─────────┴┐
       │Integration │  200+ tests (API, DB, Temporal)
      ┌┴───────────┴┐
      │    Unit      │  2000+ tests (functions, models, utils)
      └─────────────┘
```

### 1.3 Test Types

| Type | Tool | Scope | Frequency |
|------|------|-------|-----------|
| Unit | pytest | Functions, models, utils | Every commit |
| Integration | pytest + Docker | API endpoints, DB, Temporal | Every commit |
| E2E | Playwright | Dashboard UI, critical paths | Every PR |
| Performance | pytest + timing | SLA validation (<200ms p95) | Weekly |
| Security | Manual + ruff | Auth bypass, SSRF, injection | Every phase |
| Contract | OpenAPI validator | Endpoint schemas | Every commit |

---

## 2. Test Plan by Domain

### 2.1 Ontology Engine (65 tests)

| ID | Test | Type | Priority |
|----|------|------|----------|
| ONT-T-001 | Create ObjectType with valid data | Unit | P0 |
| ONT-T-002 | Create Property with all 11 types | Unit | P0 |
| ONT-T-003 | Required property enforcement | Unit | P0 |
| ONT-T-004 | Validation rules (regex, min, max) | Unit | P0 |
| ONT-T-005 | Schema version increment on update | Unit | P0 |
| ONT-T-006 | Soft delete with referential integrity | Unit | P0 |
| ONT-T-007 | Batch create 1000+ objects | Integration | P0 |
| ONT-T-008 | Upsert by unique key | Integration | P0 |
| ONT-T-009 | Optimistic concurrency conflict | Unit | P0 |
| ONT-T-010 | Multi-hop traversal (10 hops) | Integration | P0 |
| ONT-T-011 | Link type cardinality enforcement | Unit | P0 |
| ONT-T-012 | Interface polymorphism | Unit | P1 |
| ONT-T-013 | Struct nested properties | Unit | P1 |
| ONT-T-014 | Shared property reuse | Unit | P1 |
| ONT-T-015 | Value type constraints | Unit | P1 |
| ONT-T-016 | Action type with rules | Integration | P1 |
| ONT-T-017 | Action side effects | Integration | P1 |
| ONT-T-018 | Action undo/revert | Integration | P1 |
| ONT-T-019 | Function execution | Integration | P1 |
| ONT-T-020 | Function versioning | Unit | P1 |
| ONT-T-021 | Subscription notifications | Integration | P1 |
| ONT-T-022 | Object Set query/filter/aggregate | Integration | P1 |
| ONT-T-023 | Ontology Explorer UI loads | E2E | P0 |
| ONT-T-024 | Object Type Builder creates type | E2E | P0 |
| ONT-T-025 | Graph view renders | E2E | P1 |
| ONT-T-026–065 | Additional edge cases | Unit/Integration | P1/P2 |

### 2.2 Data Intelligence (14 tests)

| ID | Test | Type | Priority |
|----|------|------|----------|
| DATA-T-001 | Register PostgreSQL source | Integration | P0 |
| DATA-T-002 | Register S3 source | Integration | P0 |
| DATA-T-003 | Ingest data via Airbyte | Integration | P0 |
| DATA-T-004 | SQL query via Trino (read-only) | Integration | P0 |
| DATA-T-005 | SQL injection blocked | Security | P0 |
| DATA-T-006 | Data profiling with sampling | Integration | P0 |
| DATA-T-007 | Anomaly detection (Z-score) | Unit | P0 |
| DATA-T-008 | Time series forecasting | Unit | P0 |
| DATA-T-009 | Scrape static HTML page | Integration | P0 |
| DATA-T-010 | Scrape JavaScript SPA | Integration | P0 |
| DATA-T-011 | OCR on image | Integration | P0 |
| DATA-T-012 | PDF parsing | Integration | P0 |
| DATA-T-013 | Streaming job submission | Integration | P2 |
| DATA-T-014 | Pipeline builder execution | Integration | P1 |

### 2.3 Scraper Module (25 tests)

| ID | Test | Type | Priority |
|----|------|------|----------|
| SCR-T-001 | Create task with URL + selectors | Unit | P0 |
| SCR-T-002 | Run task on static HTML | Integration | P0 |
| SCR-T-003 | Run task on JavaScript SPA | Integration | P0 |
| SCR-T-004 | Pagination (next button) | Integration | P0 |
| SCR-T-005 | Infinite scroll | Integration | P0 |
| SCR-T-006 | Login automation | Integration | P0 |
| SCR-T-007 | Solve reCAPTCHA v2 | Integration | P0 |
| SCR-T-008 | Solve hCaptcha | Integration | P0 |
| SCR-T-009 | IP rotation | Integration | P1 |
| SCR-T-010 | Fingerprint randomization | Unit | P1 |
| SCR-T-011 | Template execution (Amazon) | Integration | P0 |
| SCR-T-012 | Template execution (Google Maps) | Integration | P0 |
| SCR-T-013 | Visual builder create workflow | E2E | P0 |
| SCR-T-014 | Export to CSV | Unit | P0 |
| SCR-T-015 | Export to JSONL streaming | Integration | P1 |
| SCR-T-016 | Export to PostgreSQL | Integration | P0 |
| SCR-T-017 | MCP tool template.list | Integration | P0 |
| SCR-T-018 | MCP tool template.run | Integration | P0 |
| SCR-T-019 | NL-to-scraper generation | Integration | P1 |
| SCR-T-020 | Parent-child task chaining | Integration | P1 |
| SCR-T-021 | Incremental extraction | Integration | P1 |
| SCR-T-022 | CLI task execution | CLI | P1 |
| SCR-T-023 | 50 concurrent tasks | Performance | P0 |
| SCR-T-024 | SSRF protection | Security | P0 |
| SCR-T-025 | Credential encryption | Security | P0 |

### 2.4 ML Platform (6 tests)

| ID | Test | Type | Priority |
|----|------|------|----------|
| ML-T-001 | Create experiment + log runs | Integration | P1 |
| ML-T-002 | Register model + version | Integration | P1 |
| ML-T-003 | Model serving endpoint | Integration | P1 |
| ML-T-004 | MLflow API compatibility | Integration | P1 |
| ML-T-005 | Agent definition + evaluation | Integration | P1 |
| ML-T-006 | Model drift detection | Integration | P1 |

### 2.5 Intent Engine (5 tests)

| ID | Test | Type | Priority |
|----|------|------|----------|
| INT-T-001 | Query intent → SQL generation | Integration | P0 |
| INT-T-002 | Pipeline intent → NiFi flow | Integration | P0 |
| INT-T-003 | Scraper intent → template selection | Integration | P0 |
| INT-T-004 | Plan validation against ontology | Unit | P0 |
| INT-T-005 | Plan caching + reuse | Integration | P0 |

### 2.6 Governance (7 tests)

| ID | Test | Type | Priority |
|----|------|------|----------|
| GOV-T-001 | RBAC enforcement (SpiceDB) | Integration | P0 |
| GOV-T-002 | Row-level security (Ranger) | Integration | P1 |
| GOV-T-003 | Column-level masking | Integration | P1 |
| GOV-T-004 | Audit logging | Integration | P0 |
| GOV-T-005 | Policy enforcement middleware | Integration | P0 |
| GOV-T-006 | Data contract validation | Integration | P1 |
| GOV-T-007 | Tenant isolation | Integration | P0 |

### 2.7 API Contract (8 tests)

| ID | Test | Type | Priority |
|----|------|------|----------|
| API-T-001 | All endpoints return valid JSON | Contract | P0 |
| API-T-002 | All endpoints require auth | Security | P0 |
| API-T-003 | OpenAPI spec matches implementation | Contract | P0 |
| API-T-004 | MCP tools all callable | Integration | P0 |
| API-T-005 | Rate limiting enforced | Integration | P0 |
| API-T-006 | CORS headers correct | Contract | P0 |
| API-T-007 | Error responses follow schema | Contract | P0 |
| API-T-008 | Pagination works correctly | Integration | P0 |

### 2.8 UI/E2E (12 tests)

| ID | Test | Type | Priority |
|----|------|------|----------|
| UI-T-001 | Login page renders | E2E | P0 |
| UI-T-002 | Dashboard loads with data | E2E | P0 |
| UI-T-003 | Jobs page: create, list, cancel | E2E | P0 |
| UI-T-004 | Sources page: create, delete | E2E | P0 |
| UI-T-005 | SQL console: execute + results | E2E | P0 |
| UI-T-006 | Scraper: all 6 tabs functional | E2E | P0 |
| UI-T-007 | Ontology Explorer: table view | E2E | P0 |
| UI-T-008 | Object Type Builder: create type | E2E | P0 |
| UI-T-009 | Pipeline Builder: create workflow | E2E | P1 |
| UI-T-010 | Graph View: renders | E2E | P1 |
| UI-T-011 | Settings: edit value | E2E | P0 |
| UI-T-012 | All 13 routes: zero JS errors | E2E | P0 |

### 2.9 Performance (10 tests)

| ID | Test | Type | Target |
|----|------|------|--------|
| PERF-T-001 | API response time (simple) | Performance | <200ms p95 |
| PERF-T-002 | API response time (complex) | Performance | <500ms p95 |
| PERF-T-003 | Object query (1M objects) | Performance | <50ms |
| PERF-T-004 | SQL query (100K rows) | Performance | <2s |
| PERF-T-005 | Scrape task (simple page) | Performance | <5s |
| PERF-T-006 | Scrape task (complex SPA) | Performance | <30s |
| PERF-T-007 | 50 concurrent tasks | Performance | No degradation |
| PERF-T-008 | Export 10K rows | Performance | <10s |
| PERF-T-009 | Dashboard load time | Performance | <3s |
| PERF-T-010 | MCP tool response time | Performance | <500ms |

### 2.10 Security (10 tests)

| ID | Test | Type | Priority |
|----|------|------|----------|
| SEC-T-001 | SSRF protection on all URLs | Security | P0 |
| SEC-T-002 | SQL injection blocked | Security | P0 |
| SEC-T-003 | XSS prevention | Security | P0 |
| SEC-T-004 | CSRF protection | Security | P0 |
| SEC-T-005 | Auth bypass prevention | Security | P0 |
| SEC-T-006 | Tenant isolation (cross-tenant blocked) | Security | P0 |
| SEC-T-007 | Credential encryption at rest | Security | P0 |
| SEC-T-008 | TLS enforcement | Security | P0 |
| SEC-T-009 | Rate limiting | Security | P0 |
| SEC-T-010 | Audit logging completeness | Security | P0 |

---

## 3. Test Infrastructure

### 3.1 Configuration
- Framework: pytest + pytest-asyncio + pytest-django + pytest-cov
- Django settings: `voyant_project.settings` (test mode)
- Database: PostgreSQL test instance (isolated)
- Fixtures: `conftest.py` at root + per-app conftest

### 3.2 Running Tests
```bash
# Full suite
docker exec voyant_api python -m pytest tests/ -q

# Specific domain
docker exec voyant_api python -m pytest tests/ontology/ -v

# With coverage
docker exec voyant_api python -m pytest tests/ --cov=apps --cov-report=term-missing

# E2E (Playwright)
cd dashboard && bun run test:e2e
```

---

**Created:** 2026-09-05
**Next review:** 2026-09-12
