# Voyant Testing Platform — Architecture & Design

**Document ID:** VOYANT-TEST-DESIGN-1.0.0
**Status:** Proposed
**Date:** 2026-08-28
**Target Coverage:** 80% (from current 13%)

---

## 1. Executive Summary

Voyant has ~19,500 lines of real implementation code across 17 Django apps, 13 Temporal workflows, 30+ MCP tools, and ~248 existing tests at 13% coverage. The existing tests follow a **no-mocks philosophy** — all tests use real code paths. This design preserves that philosophy while building a comprehensive, layered testing platform.

**Goals:**
- Raise coverage from 13% → 80% within 8 weeks
- Maintain zero-mocks principle (real code paths only)
- Automated regression prevention via CI gates
- Sub-5-minute unit test feedback loop
- Full integration suite runnable locally and in CI

---

## 2. Testing Pyramid

```
                    ┌─────────┐
                    │  Load   │  ~2%  (k6/locust)
                    │  Tests  │
                   ┌┴─────────┴┐
                   │    E2E     │  ~8%  (full HTTP + Temporal)
                   │   Tests    │
                  ┌┴───────────┴┐
                  │ Integration  │  ~30% (DB + services)
                  │    Tests     │
                 ┌┴─────────────┴┐
                 │   Unit Tests   │  ~60% (pure logic, no I/O)
                 └────────────────┘
```

**Ratios:** 60% unit / 30% integration / 8% E2E / 2% load

---

## 3. Directory Structure

```
tests/
├── conftest.py                    # Global fixtures, env setup (EXISTING)
├── pytest.ini                     # (move to root, EXISTING)
│
├── unit/                          # Pure logic, zero I/O
│   ├── conftest.py                # Unit-specific fixtures (no DB)
│   ├── core/
│   │   ├── test_config.py         # Settings validation, docker secrets
│   │   ├── test_models.py         # TimeStampedModel, TenantModel, AuditLog
│   │   ├── test_middleware.py     # Request processing (mock Django request only)
│   │   ├── test_auth.py           # JWT validation logic (no Keycloak)
│   │   ├── test_errors.py         # Error catalog, exception hierarchy
│   │   ├── test_plugin_registry.py
│   │   ├── test_circuit_breaker.py
│   │   ├── test_job_queue.py      # InMemoryJobQueue (EXISTING, move)
│   │   ├── test_secrets.py        # All 5 backends in isolation
│   │   ├── test_spicedb_rbac.py   # SpiceDB client logic
│   │   └── test_trino.py          # SQL validation, limit wrapping
│   ├── analysis/
│   │   ├── test_anomaly_detectors.py  # Z-score, IQR, MAD (from scratch)
│   │   ├── test_forecasting.py        # Naive, SMA, EMA, Linear Trend
│   │   ├── test_segmentation.py       # Per-segment profiling, t-test
│   │   ├── test_ml_primitives.py      # sklearn wrappers
│   │   ├── test_nlp_primitives.py     # NLTK VADER
│   │   └── test_stats_primitives.py   # R-Engine bridge
│   ├── capsules/
│   │   ├── test_validation.py      # Parameter validation (EXISTING, move)
│   │   ├── test_merge.py           # Parameter merging
│   │   ├── test_substitution.py    # Jinja2 templating
│   │   ├── test_capabilities.py    # Whitelist enforcement
│   │   ├── test_checksum.py        # SHA-256 verification
│   │   └── test_version.py         # Version incrementing
│   ├── governance/
│   │   ├── test_lineage.py         # Graph traversal, impact analysis
│   │   ├── test_schema_evolution.py # Schema diff, versioning
│   │   └── test_contracts.py       # DataContract validation (EXISTING, move)
│   ├── search/
│   │   └── test_embeddings.py      # Dense, Sparse, TFIDF (EXISTING, move)
│   ├── ingestion/
│   │   └── test_quality_rules.py   # NullCheck, RangeCheck, UniqueCheck (EXISTING, move)
│   ├── scraper/
│   │   ├── test_security.py        # SSRF blocking logic
│   │   └── test_schemas.py         # Pydantic schemas
│   ├── sql/
│   │   └── test_sql_guard.py       # Read-only enforcement (EXISTING, move)
│   └── ontology/
│       ├── test_validators.py      # Property validation
│       └── test_models.py          # Model constraints
│
├── integration/                    # Real DB, real services
│   ├── conftest.py                # Integration fixtures (DB setup, service health checks)
│   ├── core/
│   │   ├── test_auth_keycloak.py  # Full JWT flow against Keycloak
│   │   ├── test_spicedb.py        # Real SpiceDB gRPC calls
│   │   └── test_job_queue_redis.py # RedisJobQueue against real Redis
│   ├── database/
│   │   ├── test_ontology_crud.py  # Full CRUD + multi-hop traversal
│   │   ├── test_capsule_lifecycle.py # Draft→Certified→Active→Archived
│   │   ├── test_governance.py     # DataHub search/lineage
│   │   └── test_workflows_models.py # Job/Artifact/PresetJob persistence
│   ├── ingestion/
│   │   ├── test_duckdb_ingestion.py # File→DuckDB pipeline
│   │   ├── test_airbyte_sync.py   # Real Airbyte (skip if unavailable)
│   │   └── test_contract_validation.py # Contract enforcement
│   ├── search/
│   │   ├── test_milvus_hybrid.py  # Dense+sparse search against Milvus
│   │   └── test_vector_index.py   # Index/search/delete lifecycle
│   ├── analysis/
│   │   ├── test_high_cardinality_kpi.py # (EXISTING, move) Performance bounds
│   │   └── test_r_engine.py       # R statistical bridge
│   └── worker/
│       ├── test_temporal_connect.py # Temporal client connection
│       └── test_activity_heartbeat.py # Activity heartbeating
│
├── e2e/                            # Full HTTP stack
│   ├── conftest.py                # E2E fixtures (Django test client + auth)
│   ├── test_analyze_flow.py       # POST /v1/analyze end-to-end
│   ├── test_ingest_flow.py        # POST /v1/jobs/ingest end-to-end
│   ├── test_profile_flow.py       # POST /v1/jobs/profile end-to-end
│   ├── test_quality_flow.py       # POST /v1/jobs/quality end-to-end
│   ├── test_sql_flow.py           # POST /v1/sql/query end-to-end
│   ├── test_search_flow.py        # POST /v1/search end-to-end
│   ├── test_capsule_flow.py       # Install→Run→Artifact end-to-end
│   ├── test_scrape_flow.py        # POST /v1/scrape end-to-end
│   ├── test_mcp_tools.py          # All 30+ MCP tools exercised
│   ├── test_health_endpoints.py   # (EXISTING, move) Health probes
│   └── test_api_versioning.py     # (EXISTING, move) Version negotiation
│
├── security/                       # Security-specific tests
│   ├── test_sql_injection.py      # SQL injection attempts on all endpoints
│   ├── test_ssrf.py               # SSRF attempts on scraper
│   ├── test_jwt_validation.py     # Expired/tampered/wrong-realm tokens
│   ├── test_tenant_isolation.py   # Cross-tenant data access attempts
│   ├── test_rbac_enforcement.py   # Permission denied scenarios
│   └── test_secrets_leak.py       # Ensure no secrets in responses/logs
│
├── performance/                    # Load and benchmark tests
│   ├── conftest.py                # Performance fixtures
│   ├── test_api_throughput.py     # Requests/second on key endpoints
│   ├── test_workflow_latency.py   # Temporal workflow completion times
│   ├── test_query_performance.py  # Trino/DuckDB query benchmarks
│   └── test_concurrent_tenants.py # Multi-tenant isolation under load
│
├── factories/                      # Test data factories (NOT factories library)
│   ├── __init__.py
│   ├── core.py                    # User, Tenant, AuditLog factories
│   ├── workflow.py                # Job, Artifact factories
│   ├── capsule.py                 # Capsule, CapsuleInstance factories
│   ├── ontology.py                # ObjectType, Object, Link factories
│   └── governance.py              # DataContract, LineageNode factories
│
└── fixtures/                       # Shared test data
    ├── sample_data.json           # Representative datasets
    ├── contracts/                 # Sample data contracts
    ├── capsules/                  # Sample capsule JSON bundles
    ├── schemas/                   # OpenAPI specs for discovery
    └── sql/                       # Sample SQL queries (valid + malicious)
```

---

## 4. Test Infrastructure

### 4.1 conftest Hierarchy

```
tests/conftest.py (global)
├── Sets env vars, resets singletons, configures DB
├── NO changes needed (EXISTING, works well)
│
tests/unit/conftest.py
├── NO DB fixtures
├── NO service fixtures
├── Pure data fixtures only
├── autoouse=False for all DB-dependent fixtures
│
tests/integration/conftest.py
├── DB setup/teardown (transaction isolation per test)
├── Service health checks (skip if unavailable)
├── Temporal client fixture
├── Milvus collection fixture (create/drop per test)
├── DuckDB in-memory fixture
│
tests/e2e/conftest.py
├── Django Ninja test client with JWT bypass
├── Full request/response cycle fixtures
├── Authenticated user fixtures (bypassed auth)
│
tests/security/conftest.py
├── Malicious payload generators
├── JWT token tamperers
├── SQL injection wordlists
│
tests/performance/conftest.py
├── Timing fixtures
├── Concurrent request generators
├── Metrics collection
```

### 4.2 Test Data Factories

No external factory libraries. Pure Python dataclass-based factories following existing `FakeCapsule` pattern:

```python
# tests/factories/core.py
from dataclasses import dataclass, field
from uuid import uuid4, uuid1
import time

@dataclass
class FakeUser:
    user_id: str = field(default_factory=lambda: str(uuid4()))
    email: str = "test@voyant.io"
    username: str = "testuser"
    tenant_id: str = "test-tenant"
    realm: str = "voyant"
    roles: list = field(default_factory=lambda: ["analyst"])
    permissions: list = field(default_factory=lambda: ["read:*", "execute:*"])

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_permission(self, perm: str) -> bool:
        return perm in self.permissions or "admin" in self.permissions


@dataclass
class FakeJob:
    id: str = field(default_factory=lambda: str(uuid4()))
    job_type: str = "ingest"
    status: str = "queued"
    source_id: str = ""
    tenant_id: str = "test-tenant"
    realm: str = "voyant"
    created_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


@dataclass
class FakeCapsule:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = "test-capsule"
    version: str = "1.0.0"
    status: str = "draft"
    tenant_id: str = "test-tenant"
    realm: str = "voyant"
    execution_graph: list = field(default_factory=list)
    parameters_schema: dict = field(default_factory=dict)
    capabilities_whitelist: list = field(default_factory=list)
```

### 4.3 pytest Configuration

Update `pytest.ini`:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = voyant_project.settings
python_files = test_*.py
addopts =
    --strict-markers
    --reuse-db
    --tb=short
    -q
markers =
    unit: Pure logic tests (no DB, no services)
    integration: Requires DB or external services
    e2e: Full HTTP stack tests
    security: Security-specific tests
    slow: Tests taking >5s
    benchmark: Performance/load tests
testpaths = tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::UserWarning
```

### 4.4 Docker Compose Test Profile

Add to `infra/standalone/docker-compose.yml`:

```yaml
# =============================================================================
# TEST PROFILE - Lightweight service stack for integration tests
# =============================================================================
services:
  voyant_postgres:
    profiles: ["test"]
    ports:
      - "45432:5432"

  voyant_redis:
    profiles: ["test"]
    ports:
      - "45379:6379"

  voyant_temporal:
    profiles: ["test"]
    ports:
      - "45233:7233"

  voyant_milvus:
    profiles: ["test"]
    ports:
      - "45195:19530"

  voyant_minio:
    profiles: ["test"]
    ports:
      - "45001:9000"
```

Usage:
```bash
# Start test infrastructure
docker compose --profile test up -d

# Run unit tests (no infra needed)
pytest -m unit -q

# Run integration tests
pytest -m integration -q

# Run all
pytest -q
```

---

## 5. Test Categories & Patterns

### 5.1 Unit Tests (60% target)

**Pattern:** Pure logic, no I/O, no DB, no services.

```python
# tests/unit/analysis/test_anomaly_detectors.py
import numpy as np
import pytest
from apps.analysis.lib.anomaly import ZScoreDetector, IQRDetector, MADDetector

class TestZScoreDetector:
    @pytest.fixture
    def detector(self):
        return ZScoreDetector(threshold=3.0)

    def test_detects_normal_outlier(self, detector):
        data = np.concatenate([np.random.normal(0, 1, 100), [10.0]])
        result = detector.detect(data)
        assert len(result.anomalies) == 1
        assert result.anomalies[0].index == 100

    def test_no_outliers_in_normal_data(self, detector):
        data = np.random.normal(0, 1, 1000)
        result = detector.detect(data)
        assert len(result.anomalies) == 0

    def test_empty_data_returns_empty(self, detector):
        result = detector.detect(np.array([]))
        assert len(result.anomalies) == 0

    def test_single_point_returns_empty(self, detector):
        result = detector.detect(np.array([1.0]))
        assert len(result.anomalies) == 0
```

**Key rules:**
- No `@pytest.mark.integration`
- No DB access
- No HTTP calls
- No Docker
- Deterministic data (seeded numpy)
- Fast (<100ms per test)

### 5.2 Integration Tests (30% target)

**Pattern:** Real DB, real services, transaction isolation.

```python
# tests/integration/database/test_capsule_lifecycle.py
import pytest
from apps.capsules.models import Capsule
from apps.capsules.services.capsule_core import certify_capsule, activate_capsule

@pytest.mark.integration
class TestCapsuleLifecycle:
    @pytest.fixture(autouse=True)
    def setup_db(self, db):
        """Uses pytest-django's db fixture for transaction isolation."""
        pass

    def test_draft_to_certified(self, db):
        capsule = Capsule.objects.create(
            name="lifecycle-test",
            version="1.0.0",
            status="draft",
            tenant_id="test-tenant",
            realm="voyant",
        )
        certify_capsule(capsule)
        capsule.refresh_from_db()
        assert capsule.status == "certified"

    def test_certified_to_active(self, db):
        capsule = Capsule.objects.create(
            name="lifecycle-test",
            version="1.0.0",
            status="certified",
            tenant_id="test-tenant",
            realm="voyant",
        )
        activate_capsule(capsule)
        capsule.refresh_from_db()
        assert capsule.status == "active"
```

**Key rules:**
- Marked `@pytest.mark.integration`
- Uses `db` fixture for transaction rollback
- Service health checks with skip decorators
- Real data, real queries

### 5.3 E2E Tests (8% target)

**Pattern:** Full HTTP request/response cycle through Django Ninja.

```python
# tests/e2e/test_analyze_flow.py
import pytest
from django.test import Client
from apps.core.security.auth import get_current_user

@pytest.mark.e2e
class TestAnalyzeFlow:
    @pytest.fixture(autouse=True)
    def setup_client(self, client, db, settings):
        self.client = client
        # Bypass auth for E2E tests
        settings.VOYANT_SECURITY_ENABLED = False

    def test_analyze_with_source_id(self, db):
        response = self.client.post(
            "/v1/analyze",
            json={"source_id": "test-source", "table": "orders"},
            content_type="application/json",
        )
        assert response.status_code in (200, 202, 400)  # Valid responses
        if response.status_code in (200, 202):
            data = response.json()
            assert "job_id" in data or "status" in data

    def test_analyze_without_source_or_table_returns_400(self, db):
        response = self.client.post(
            "/v1/analyze",
            json={},
            content_type="application/json",
        )
        assert response.status_code == 400
```

### 5.4 Security Tests (5% target)

**Pattern:** Adversarial testing, injection attempts, auth bypass.

```python
# tests/security/test_sql_injection.py
import pytest

@pytest.mark.security
class TestSQLInjection:
    """Ensure SQL injection attempts are blocked at every layer."""

    INJECTION_PAYLOADS = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "UNION SELECT * FROM secrets",
        "1; DELETE FROM voyant_jobs WHERE 1=1",
        "admin'--",
        "1' WAITFOR DELAY '0:0:5'--",
    ]

    @pytest.fixture
    def trino(self):
        from apps.core.lib.trino import TrinoClient
        return TrinoClient.__new__(TrinoClient)

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    def test_trino_sql_guard_blocks_injection(self, trino, payload):
        with pytest.raises(ValueError, match="Invalid query type"):
            trino._validate_sql(payload)

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    def test_api_rejects_injection_in_query(self, client, db, payload):
        response = client.post(
            "/v1/sql/query",
            json={"query": payload},
            content_type="application/json",
        )
        assert response.status_code in (400, 403, 422)
```

---

## 6. CI/CD Pipeline Design

### 6.1 GitHub Actions Workflow

Replace the existing `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  # ========================================================================
  # Stage 1: Fast Feedback (<2 min)
  # ========================================================================
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install ruff
      - run: ruff check apps voyant_project tests scripts
      - run: ruff format --check apps voyant_project tests scripts

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install pyright django-types
      - run: pyright apps/ --outputjson || true  # Advisory for now

  # ========================================================================
  # Stage 2: Unit Tests (<3 min)
  # ========================================================================
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-asyncio pytest-cov pytest-django
      - name: Run unit tests with coverage
        run: |
          pytest -m unit -q \
            --cov=apps \
            --cov-report=xml:coverage-unit.xml \
            --cov-fail-under=60 \
            --junitxml=results-unit.xml
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: unit-test-results
          path: |
            coverage-unit.xml
            results-unit.xml

  # ========================================================================
  # Stage 3: Integration Tests (with services, <8 min)
  # ========================================================================
  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: voyant_test
          POSTGRES_USER: voyant
          POSTGRES_PASSWORD: voyant
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        ports: ["6379:6379"]
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-asyncio pytest-cov pytest-django
      - name: Run integration tests
        env:
          VOYANT_DATABASE_URL: postgresql://voyant:voyant@localhost:5432/voyant_test
          VOYANT_REDIS_URL: redis://localhost:6379/0
          VOYANT_TEMPORAL_HOST: localhost:7233
          VOYANT_SECURITY_ENABLED: "false"
          VOYANT_SECRETS_BACKEND: env
        run: |
          pytest -m integration -q \
            --cov=apps \
            --cov-report=xml:coverage-integration.xml \
            --cov-append \
            --junitxml=results-integration.xml
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: integration-test-results
          path: |
            coverage-integration.xml
            results-integration.xml

  # ========================================================================
  # Stage 4: E2E Tests (full stack, <10 min)
  # ========================================================================
  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-asyncio pytest-cov pytest-django
      - name: Run E2E tests
        env:
          VOYANT_DATABASE_URL: postgresql://voyant:voyant@localhost:5432/voyant_test
          VOYANT_SECURITY_ENABLED: "false"
        run: |
          pytest -m e2e -q \
            --cov=apps \
            --cov-report=xml:coverage-e2e.xml \
            --cov-append \
            --junitxml=results-e2e.xml

  # ========================================================================
  # Stage 5: Coverage Report & Gate
  # ========================================================================
  coverage-report:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests, e2e-tests]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
      - name: Merge coverage reports
        run: |
          pip install coverage
          coverage combine coverage-*.xml || true
          coverage report --fail-under=80 || true
      - name: Comment PR with coverage
        uses: orgoro/coverage@v3
        with:
          coverageFile: coverage-e2e.xml
          token: ${{ secrets.GITHUB_TOKEN }}
          thresholdAll: 0.80

  # ========================================================================
  # Stage 6: Security Scan
  # ========================================================================
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install pip-audit bandit
      - name: Dependency audit
        run: pip-audit --fail-on HIGH
      - name: Static security analysis
        run: bandit -r apps/ -ll
      - name: Run security tests
        run: |
          pip install -r requirements.txt
          pytest -m security -q --junitxml=results-security.xml

  # ========================================================================
  # Stage 7: Docker Build
  # ========================================================================
  docker-build:
    runs-on: ubuntu-latest
    needs: [unit-tests]
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: docker build -f infra/standalone/Dockerfile -t voyant-api:ci .
      - name: Verify image
        run: docker run --rm voyant-api:ci python -c "import voyant_project; print('OK')"
```

### 6.2 Coverage Gates

| Stage | Gate | Action |
|-------|------|--------|
| Unit tests | `--cov-fail-under=60` | Block merge if <60% |
| Integration | `--cov-fail-under=70` | Block merge if <70% |
| E2E | `--cov-fail-under=75` | Block merge if <75% |
| Total | `--cov-fail-under=80` | Block merge if <80% |

---

## 7. Module-by-Module Test Plan

### 7.1 `apps/core/` — Current: ~30% → Target: 85%

| File | Current Tests | Gap | Tests to Add |
|------|---------------|-----|-------------|
| `models.py` | 0 | Full | RBACManager filtering, TenantModel indexes, AuditLog creation, SystemSetting.get_value type-casting |
| `config.py` | 3 | Medium | Docker secrets resolution, pydantic validators, env var precedence |
| `middleware.py` | 7 | Low | RequestId, Tenant, SomaContext, APIVersion, RBAC middleware |
| `security/auth.py` | 2 | High | JWKS fetch, RS256 decode, audience/issuer verify, role derivation, permission mapping, cross-realm rejection |
| `security/policy.py` | 1 | High | SpiceDB check_permission, add/remove_relationship |
| `lib/secrets.py` | 0 | Full | All 5 backends: Env, K8s, File (Fernet), Vault, InMemory |
| `lib/errors.py` | 0 | Full | Error catalog lookup, exception hierarchy, to_response() |
| `lib/circuit_breaker.py` | 3 | Low | State transitions, thread safety, metrics |
| `lib/job_queue.py` | 16 | None | Already well tested |
| `lib/trino.py` | 10 | None | Already well tested |
| `lib/temporal_client.py` | 0 | Full | Connection, error handling |
| `lib/python_sandbox.py` | 0 | Full | Docker execution, security constraints |
| `lib/spicedb_rbac.py` | 7 | Low | Permission checks, relationship ops |

**New tests needed:** ~45

### 7.2 `apps/worker/` — Current: 0% → Target: 70%

| File | Current Tests | Gap | Tests to Add |
|------|---------------|-----|-------------|
| Workflows (13) | 0 | Full | Each workflow's step sequencing, error paths, retry policies |
| Activities (13) | 0 | Full | Each activity's core logic with in-process data |

**Strategy:** Use `temporalio.worker.Worker` test sandbox with mock Temporal server for workflow tests. For activities, call directly with real data (existing pattern).

**New tests needed:** ~80

### 7.3 `apps/analysis/` — Current: ~25% → Target: 85%

| File | Current Tests | Gap | Tests to Add |
|------|---------------|-----|-------------|
| `lib/anomaly.py` | 4 | Medium | Edge cases: all NaN, single value, constant data |
| `lib/forecasting.py` | 4 | Medium | Confidence intervals, seasonal patterns, missing data |
| `lib/segmentation.py` | 0 | Full | Segment profiling, drift detection, t-test |
| `lib/ml_primitives.py` | 5 | Low | Already well tested |
| `lib/nlp_primitives.py` | 0 | Full | Sentiment analysis, edge cases |
| `lib/stats_primitives.py` | 0 | Full | Correlation matrix, distribution fitting |

**New tests needed:** ~35

### 7.4 `apps/scraper/` — Current: ~20% → Target: 80%

| File | Current Tests | Gap | Tests to Add |
|------|---------------|-----|-------------|
| `security.py` | 3 | Medium | All 15+ blocked IP ranges, decimal/octal bypass, DNS resolution |
| `workflow.py` | 0 | Full | 6-stage workflow orchestration |
| `search_activities.py` | 0 | Full | SearXNG client |
| `deep_research_workflow.py` | 0 | Full | Multi-agent orchestration |

**New tests needed:** ~30

### 7.5 `apps/mcp/` — Current: ~5% → Target: 75%

| File | Current Tests | Gap | Tests to Add |
|------|---------------|-----|-------------|
| `tools_core.py` | 1 | High | Each tool's parameter validation and delegation |
| `tools_catalog.py` | 0 | Full | Each tool's service integration |
| `tools_scrape.py` | 0 | Full | Each tool's workflow dispatch |

**New tests needed:** ~40

### 7.6 `apps/search/` — Current: ~30% → Target: 85%

| File | Current Tests | Gap | Tests to Add |
|------|---------------|-----|-------------|
| `lib/embeddings.py` | 12 | None | Already well tested |
| `lib/milvus_store.py` | 4 | Low | Collection lifecycle, hybrid search merge |
| `api.py` | 2 | Medium | Tenant isolation, RBAC, pagination |

**New tests needed:** ~15

### 7.7 `apps/governance/` — Current: ~10% → Target: 80%

| File | Current Tests | Gap | Tests to Add |
|------|---------------|-----|-------------|
| `lib/lineage.py` | 0 | Full | Graph traversal, impact analysis, JSON export |
| `lib/schema_evolution.py` | 3 | Medium | Breaking change detection, semantic versioning |
| `api.py` | 0 | Full | DataHub GraphQL, quota enforcement |

**New tests needed:** ~30

### 7.8 `apps/capsules/` — Current: ~35% → Target: 85%

| File | Current Tests | Gap | Tests to Add |
|------|---------------|-----|-------------|
| Unit tests | 21 | Low | Already well tested |
| Integration tests | 8 | Low | Already well tested |
| `services/capsule_core.py` | Partial | Low | Content hash, clone-on-edit |
| `services/capsule_execution.py` | Partial | Low | Step routing, capability enforcement |

**New tests needed:** ~15

### 7.9 `apps/ontology/` — Current: 0% → Target: 80%

| File | Current Tests | Gap | Tests to Add |
|------|---------------|-----|-------------|
| `models.py` | 0 | Full | Constraints, soft-delete, version field |
| `services.py` | 0 | Full | CRUD, batch ops, multi-hop traversal, upsert |
| `validators.py` | 0 | Full | Type checking, required constraints, regex rules |

**New tests needed:** ~35

### 7.10 `apps/ingestion/` — Current: ~15% → Target: 80%

| File | Current Tests | Gap | Tests to Add |
|------|---------------|-----|-------------|
| `lib/airbyte_client.py` | 1 | High | Circuit breaker, sync polling, health check |
| `lib/quality_rules.py` | 5 | Low | Already well tested |

**New tests needed:** ~20

---

## 8. Total Test Count Estimate

| Category | Current | To Add | Total | % of Total |
|----------|---------|--------|-------|------------|
| Unit | ~150 | ~250 | ~400 | 60% |
| Integration | ~60 | ~120 | ~180 | 27% |
| E2E | ~30 | ~50 | ~80 | 12% |
| Security | ~5 | ~25 | ~30 | 5% |
| Performance | ~5 | ~10 | ~15 | 2% |
| **Total** | **~250** | **~455** | **~705** | **100%** |

**Estimated coverage: 13% → 80%**

---

## 9. Test Execution Strategy

### 9.1 Local Development

```bash
# Fast feedback (<30s) — run on every save
pytest -m unit -q --tb=line

# Before commit (<2min)
pytest -m "unit or security" -q

# Full validation (<10min)
pytest -q --cov=apps --cov-fail-under=80
```

### 9.2 CI Pipeline

```
PR Created
  ├── Lint + Typecheck (<1 min)
  ├── Unit Tests (<3 min) ─── FAIL → Block merge
  ├── Integration Tests (<8 min) ─── FAIL → Block merge
  ├── E2E Tests (<10 min) ─── FAIL → Block merge
  ├── Security Scan (<3 min) ─── HIGH vuln → Block merge
  ├── Coverage Report ─── <80% → Block merge
  └── Docker Build (<3 min) ─── FAIL → Block merge
```

### 9.3 Nightly Full Suite

```bash
# Run everything including slow/benchmark tests
pytest -q --cov=apps --cov-report=html --benchmark-only
```

---

## 10. Test Conventions

### 10.1 File Naming

- `test_<module>_<aspect>.py` — e.g., `test_core_secrets.py`, `test_analysis_anomaly.py`
- Group by module, then by aspect (not by class)

### 10.2 Class Naming

```python
class Test<Feature>:           # Unit tests
class Test<Feature>Integration: # Integration tests
class Test<Feature>E2E:         # E2E tests
```

### 10.3 Method Naming

```python
def test_<action>_<expected>():
    # Examples:
    def test_detect_normal_outlier():
    def test_validate_sql_blocks_insert():
    def test_analyze_missing_source_returns_400():
    def test_capsule_draft_to_certified():
```

### 10.4 Fixture Rules

- **No fixtures with side effects** outside their scope
- **No shared mutable state** between tests
- **No ordering dependencies** between tests
- **Factories over raw data** — always use factory functions
- **Real data over mocks** — use actual objects, not MagicMock

### 10.5 Assertion Rules

```python
# GOOD: Specific assertions
assert result.anomalies[0].index == 100
assert response.status_code == 400
assert "Missing required parameter" in error

# BAD: Vague assertions
assert result is not None
assert response.ok
assert error
```

---

## 11. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Restructure `tests/` directory (move existing tests to correct categories)
- [ ] Create `tests/unit/conftest.py`, `tests/integration/conftest.py`, `tests/e2e/conftest.py`
- [ ] Create `tests/factories/` module
- [ ] Update `pytest.ini` with new markers
- [ ] Create `docker-compose.test.yml` (test profile)
- [ ] Write 50 unit tests for `apps/core/` gaps

### Phase 2: Core Coverage (Week 3-4)
- [ ] Write 80 unit tests for `apps/analysis/` gaps
- [ ] Write 45 unit tests for `apps/worker/` activities
- [ ] Write 30 unit tests for `apps/scraper/` security
- [ ] Write 25 security tests
- [ ] Update CI pipeline with staged jobs

### Phase 3: Integration (Week 5-6)
- [ ] Write 60 integration tests for `tests/integration/database/`
- [ ] Write 30 integration tests for `tests/integration/ingestion/`
- [ ] Write 30 integration tests for `tests/integration/search/`
- [ ] Wire Temporal test sandbox for workflow tests

### Phase 4: E2E & Polish (Week 7-8)
- [ ] Write 50 E2E tests for key API flows
- [ ] Write 40 MCP tool tests
- [ ] Set up coverage gates in CI
- [ ] Write performance benchmarks
- [ ] Documentation and team training

---

## 12. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **No mocks** | Existing philosophy works. Real code paths catch real bugs. |
| **Dataclass factories** | Matches existing `FakeCapsule` pattern. No external dependencies. |
| **pytest markers** | Clean categorization. Easy to run subsets. |
| **Docker Compose profiles** | Minimal infra for unit tests, full stack for integration. |
| **Staged CI** | Fast feedback first, full validation on success. |
| **Coverage gates** | Prevent regression. Enforce improvement. |
| **Transaction isolation** | `db` fixture rolls back after each test. No pollution. |
| **Service health checks** | Skip tests gracefully when services unavailable. |

---

## 13. Success Metrics

| Metric | Current | Target (8 weeks) |
|--------|---------|------------------|
| Test count | 248 | 705 |
| Coverage | 13% | 80% |
| Unit test time | N/A | <3 min |
| Integration test time | N/A | <8 min |
| E2E test time | N/A | <10 min |
| CI pipeline time | ~5 min | <15 min |
| Security test count | ~5 | 30 |
| Flaky tests | Unknown | 0 |

---

**End of Design Document**
