# VOYANT ENTERPRISE UPGRADE — FULL ARCHITECTURAL RECOMMENDATIONS

**Document ID:** VOYANT-ARCH-ENTERPRISE-3.1.0
**Status:** APPROVED FOR PLANNING
**Date:** 2026-05-21
**Classification:** Architecture Decision Record + Implementation Roadmap
**Compliance:** ISO/IEC 25010:2011, ISO/IEC 29148:2018, OWASP Top 10 2021

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Current State Gap Analysis](#2-current-state-gap-analysis)
3. [Upgrade Pillars](#3-upgrade-pillars)
   - 3.1 Milvus Vector Database Migration
   - 3.2 Octopus Module (Octoparse Parity)
   - 3.3 Deep Research Module v2
   - 3.4 Enterprise Scraping Stack Expansion
4. [Recommended Open Source Tool Matrix](#4-recommended-open-source-tool-matrix)
5. [Integration Architecture](#5-integration-architecture)
6. [Data Flow Diagrams](#6-data-flow-diagrams)
7. [Deployment & Infrastructure Changes](#7-deployment--infrastructure-changes)
8. [Security & Compliance Hardening](#8-security--compliance-hardening)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [Risk Assessment](#10-risk-assessment)

---

## 1. EXECUTIVE SUMMARY

This document defines the **enterprise-grade upgrade path** for Voyant v3.0.0 → v3.1.0. Three major architectural initiatives are proposed:

| Initiative | Current State | Target State | Business Impact |
|------------|--------------|--------------|-----------------|
| **Vector Search** | In-memory JSON store (128-dim TF-IDF), no persistence, no scale | Milvus 2.4+ (HNSW/GPU), hybrid dense+sparse search, billion-vector scale | Semantic search at enterprise scale, RAG-ready |
| **Web Scraping** | Basic scraper (Playwright/httpx/Scrapy/Selenium) + Octopus schema stubs | **Octopus Module** — full Octoparse feature parity: no-code workflows, AI auto-detection, cloud scheduling, proxy rotation, CAPTCHA solving, 600+ templates | Turn-key data extraction for non-technical users |
| **Deep Research** | Single-loop SearXNG → parallel fetch → aggregation | **Recursive multi-agent research** with breadth/depth parameters, source credibility scoring, cross-reference validation, structured report generation | Production-grade research automation |

**Additional tooling expansion** covers 15+ enterprise open-source packages to complete the data processing toolbox.

---

## 2. CURRENT STATE GAP ANALYSIS

### 2.1 Vector Store (CRITICAL — blocks production scale)

| Gap | Severity | Evidence |
|-----|----------|----------|
| In-memory only with JSON persistence | 🔴 Critical | `apps/search/lib/vector_store.py` line 56: "For large scale, upgrade to FAISS or dedicated vector DB" |
| No ANN indexing — brute-force cosine scan O(n) | 🔴 Critical | Every query iterates all vectors |
| No tenant isolation at index level | 🟠 High | Metadata filtering only |
| 128-dim TF-IDF limit | 🟠 High | Cannot use modern embeddings (768/1024/1536-dim) |
| No hybrid search (dense + sparse) | 🟡 Medium | Cannot combine semantic + keyword search |

### 2.2 Scraper / Octopus (HIGH — schema exists, no dispatcher)

| Gap | Severity | Evidence |
|-----|----------|----------|
| `OctopusDispatcher` does not exist | 🔴 Critical | `apps/scraper/octopus/__init__.py` imports from `dispatcher.py` — **file missing** |
| No visual/no-code workflow builder | 🔴 Critical | Agent must provide all CSS/XPath selectors manually |
| No AI auto-detection of data fields | 🔴 Critical | Octoparse's core differentiator is absent |
| No template library | 🟠 High | Every job starts from scratch |
| No proxy rotation / IP management | 🟠 High | Single-IP scraping easily blocked |
| No CAPTCHA solving integration | 🟠 High | Manual intervention required |
| No cloud scheduling / cron | 🟡 Medium | Jobs are one-shot only |
| No anti-bot evasion (fingerprint randomization) | 🟡 Medium | `curl-cffi` and `camoufox` in pyproject.toml but not wired |

### 2.3 Deep Research (MEDIUM — basic workflow exists)

| Gap | Severity | Evidence |
|-----|----------|----------|
| No recursive depth/breadth control | 🟠 High | Single search → fetch loop only |
| No content synthesis or summarization | 🟠 High | Returns raw aggregation only |
| No source credibility scoring | 🟡 Medium | All sources weighted equally |
| No cross-reference validation | 🟡 Medium | Cannot verify claims across sources |
| No structured report generation | 🟡 Medium | Output is unstructured JSON |

---

## 3. UPGRADE PILLARS

---

### 3.1 PILLAR 1: Milvus Vector Database Migration

#### 3.1.1 Architecture Decision

**Decision:** Replace in-memory `VectorStore` with **Milvus 2.4+** as the primary vector database.

**Rationale:**
- Milvus is Apache 2.0, cloud-native, K8s-native, and handles billions of vectors
- Native hybrid search (dense + sparse/BM25) for semantic + keyword combined ranking
- HNSW indexing with sub-10ms ANN search latency
- Partition-level multi-tenancy maps perfectly to Voyant's `tenant_id` isolation
- GPU acceleration (CAGRA) for high-throughput workloads
- `django-milvus` provides ORM-like interface with Django routing

#### 3.1.2 Proposed Schema (Collection Design)

```python
# apps/search/lib/milvus_store.py
from django_milvus.models import MilvusModel
from django_milvus.fields import (
    PrimaryKeyField, VarCharField, FloatVectorField,
    Int64Field, JSONField, SparseVectorField
)
from django_milvus.indexes import HNSW, InvertedIndex

class VoyantDocument(MilvusModel):
    id = PrimaryKeyField(auto_id=True)
    doc_id = VarCharField(max_length=256)      # External UUID
    tenant_id = VarCharField(max_length=64)     # Partition key
    content = VarCharField(max_length=65535)
    embedding = FloatVectorField(dim=1536)      # OpenAI/text-embedding-3-large
    sparse_embedding = SparseVectorField()      # BM25 / SPLADE for hybrid
    metadata = JSONField(default=dict)
    source_type = VarCharField(max_length=32)   # "scrape" | "ingest" | "upload"
    created_at = Int64Field()                   # Unix timestamp

    class MilvusMeta:
        collection_name = 'voyant_documents'
        database = 'milvus'
        consistency_level = 'Bounded'
        enable_dynamic_field = True
        # Partition by tenant_id for isolation + query pruning
        partition_key_field = 'tenant_id'

    class MilvusIndexes:
        embedding_idx = HNSW(
            field='embedding',
            metric_type='COSINE',
            M=16,
            efConstruction=256,
        )
        sparse_idx = InvertedIndex(field='sparse_embedding')
        source_idx = InvertedIndex(field='source_type')
```

#### 3.1.3 Migration Path

| Phase | Action | Duration |
|-------|--------|----------|
| 1 | Add `django-milvus` + `pymilvus` to dependencies; deploy Milvus standalone in Docker Compose | 1 day |
| 2 | Create `MilvusVectorStore` adapter implementing existing `VectorStore` interface | 2 days |
| 3 | Backfill existing JSON vectors into Milvus collection | 1 day |
| 4 | Update `apps/search/api.py` to use hybrid search (dense + sparse) | 2 days |
| 5 | Update MCP tools (`voyant.vector.search/index`) | 1 day |
| 6 | Add Milvus to K8s manifests + Helm charts | 2 days |
| 7 | Deprecate in-memory `VectorStore` (keep as fallback for offline mode) | 1 day |

#### 3.1.4 Search API Upgrade

```python
# Hybrid search combining dense semantic + sparse keyword
results = VoyantDocument.search(
    query_embedding= dense_vec,           # 1536-dim from OpenAI
    query_sparse= sparse_vec,             # BM25 sparse vector
    top_k=10,
    filter_expr=f'tenant_id == "{tenant_id}" AND source_type == "scrape"',
    ranker=WeightedRanker(0.7, 0.3),      # 70% semantic, 30% keyword
)
```

#### 3.1.5 Infrastructure Addition

```yaml
# infra/standalone/docker-compose.yml addition
  milvus-standalone:
    image: milvusdb/milvus:v2.4.17
    command: ["milvus", "run", "standalone"]
    ports:
      - "19530:19530"
      - "9091:9091"
    volumes:
      - milvus_data:/var/lib/milvus
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    depends_on:
      - etcd
      - minio

  etcd:
    image: quay.io/coreos/etcd:v3.5.14
    # ... etcd config

volumes:
  milvus_data:
```

---

### 3.2 PILLAR 2: Octopus Module — Full Octoparse Parity

#### 3.2.1 Vision

The **Octopus Module** transforms Voyant from a "scraper toolkit" into an **enterprise no-code data extraction platform** comparable to Octoparse, but fully open-source, MCP-native, and integrated into Voyant's multi-tenant workflow engine.

#### 3.2.2 Feature Parity Matrix: Voyant Octopus vs Octoparse

| Octoparse Feature | Octopus Implementation | Module / File |
|-------------------|------------------------|---------------|
| **No-code visual workflow builder** | Agent-provided JSON workflows + auto-detection API | `octopus/workflows/` |
| **AI auto-detection** | LLM-based field detection (agent provides hints, Voyant executes) | `octopus/auto_detect.py` |
| **Cloud extraction / scheduling** | Temporal cron workflows | `apps.worker.workflows.octopus_scheduled_workflow` |
| **IP rotation / proxy management** | Proxy pool with Bright Data / Oxylabs / ScrapingBee | `octopus/proxy_pool.py` |
| **CAPTCHA solving** | 2Captcha / CapSolver / NopeCHA integration | `octopus/captcha_solver.py` |
| **Anti-bot evasion** | curl-cffi + camoufox + playwright-stealth + fingerprint rotation | `octopus/evasion/` |
| **Infinite scroll / AJAX** | Playwright auto-scroll + DOM mutation observer | `octopus/dynamic/` |
| **Template library** | 600+ pre-built JSON templates (e-commerce, maps, social, jobs) | `octopus/templates/` |
| **Data export formats** | JSON, CSV, Parquet, XLSX, Markdown, Google Sheets API | `octopus/exporters/` |
| **Real-time monitoring** | Prometheus metrics per job + Kafka telemetry | `octopus/telemetry.py` |
| **Human-in-the-loop (HITL)** | Dashboard review queue for uncertain extractions | `dashboard/src/views/view-hitl.ts` |
| **Multi-engine orchestration** | 8 ARM dispatch (already defined in schemas) | `octopus/dispatcher.py` |
| **API / MCP access** | Full REST + MCP tool coverage | `apps.mcp.tools_scrape` |

#### 3.2.3 Module Structure

```
apps/scraper/octopus/                    # EXPANDED from schema-only
├── __init__.py                          # Exports (already exists)
├── schemas.py                           # Pydantic models (already exists, enhance)
├── dispatcher.py                        # NEW: Central ARM router
├── arms/
│   ├── __init__.py
│   ├── arm_static.py                    # ARM-1: httpx + parsel
│   ├── arm_dynamic.py                   # ARM-2: Playwright + stealth
│   ├── arm_evasion.py                   # ARM-3: curl-cffi + camoufox
│   ├── arm_crawl.py                     # ARM-4: Scrapy + Crawlee
│   ├── arm_api_intercept.py             # ARM-5: XHR/JSON capture
│   ├── arm_document.py                  # ARM-6: pdfplumber + unstructured
│   ├── arm_ocr.py                       # ARM-7a: Tesseract
│   ├── arm_transcribe.py                # ARM-7b: Whisper
│   └── arm_archive.py                   # ARM-8: Interactive deep archive
├── auto_detect.py                       # NEW: AI field detection engine
├── proxy_pool.py                        # NEW: Rotating proxy management
├── captcha_solver.py                    # NEW: CAPTCHA solving abstraction
├── evasion/
│   ├── fingerprint_rotator.py           # NEW: JA3/JA4, canvas, WebGL spoofing
│   ├── stealth_profile.py               # NEW: Per-session stealth config
│   └── browser_pool.py                  # NEW: Managed browser lifecycle
├── workflows/
│   ├── no_code_builder.py               # NEW: JSON workflow compiler
│   ├── template_engine.py               # NEW: 600+ template registry
│   └── scheduled_task.py                # NEW: Cron-scheduled scraping
├── exporters/
│   ├── csv_exporter.py
│   ├── parquet_exporter.py
│   ├── xlsx_exporter.py
│   ├── markdown_exporter.py
│   └── gsheet_exporter.py               # NEW: Google Sheets API
├── telemetry.py                         # NEW: Metrics + Kafka events
└── tests/                               # E2E tests for each ARM
```

#### 3.2.4 The Dispatcher (Missing Piece)

```python
# apps/scraper/octopus/dispatcher.py
class OctopusDispatcher:
    """Routes OctopusRequest to the correct ARM executor."""

    _ARMS: Dict[OctopusARM, Callable] = {
        OctopusARM.STATIC: ArmStatic.execute,
        OctopusARM.DYNAMIC: ArmDynamic.execute,
        OctopusARM.EVASION: ArmEvasion.execute,
        OctopusARM.CRAWL: ArmCrawl.execute,
        OctopusARM.API_INTERCEPT: ArmApiIntercept.execute,
        OctopusARM.DOCUMENT: ArmDocument.execute,
        OctopusARM.OCR: ArmOcr.execute,
        OctopusARM.TRANSCRIBE: ArmTranscribe.execute,
        OctopusARM.ARCHIVE: ArmArchive.execute,
    }

    async def dispatch(self, request: OctopusRequest) -> OctopusResult:
        # 1. SSRF validation
        validate_url(request.url)
        # 2. Quota check
        await self._check_quota(request.tenant_id)
        # 3. Route to ARM
        arm_executor = self._ARMS[request.arm]
        # 4. Execute with timeout + circuit breaker
        result = await asyncio.wait_for(
            arm_executor(request),
            timeout=request.timeout_seconds,
        )
        # 5. Store artifact + emit telemetry
        await self._store_and_emit(result)
        return result
```

#### 3.2.5 Auto-Detection Engine

```python
# apps/scraper/octopus/auto_detect.py
class AutoDetectEngine:
    """
    Given a URL and a user hint (e.g. "product listings"),
    automatically generates CSS/XPath selectors.
    Uses DOM structure analysis + heuristics + agent-provided hints.
    No LLM inside Voyant — deterministic algorithms only.
    """

    def detect(self, url: str, hint: str, html: str) -> Dict[str, str]:
        # 1. Structural analysis: find repeating DOM patterns
        # 2. Semantic analysis: match hint to class names, IDs, aria-labels
        # 3. Data-type inference: dates, prices, emails, URLs
        # 4. Return ranked selector candidates
        pass
```

#### 3.2.6 Proxy Pool Integration

```python
# apps/scraper/octopus/proxy_pool.py
class ProxyPool:
    """
    Manages rotating proxies from multiple providers.
    Supports: Bright Data, Oxylabs, ScrapingBee, Smartproxy, custom.
    """

    providers: List[ProxyProvider] = [
        BrightDataProvider(),
        OxylabsProvider(),
        ScrapingBeeProvider(),
        CustomProxyProvider(),  # From env / Vault
    ]

    def get_proxy(self, tenant_id: str, target_domain: str) -> Proxy:
        # Round-robin per tenant, with session affinity
        # Health-check failed proxies auto-evicted
        pass
```

#### 3.2.7 CAPTCHA Solver Abstraction

```python
# apps/scraper/octopus/captcha_solver.py
class CaptchaSolver:
    """
    Pluggable CAPTCHA solving.
    Supports: 2Captcha, CapSolver, NopeCHA, Anti-Captcha.
    """

    async def solve_image_captcha(self, image_b64: str, provider: str) -> str: ...
    async def solve_recaptcha_v2(self, site_key: str, page_url: str) -> str: ...
    async def solve_cloudflare_turnstile(self, site_key: str, page_url: str) -> str: ...
    async def solve_hcaptcha(self, site_key: str, page_url: str) -> str: ...
```

#### 3.2.8 Evasion / Anti-Bot Stack

| Technique | Tool | Status |
|-----------|------|--------|
| TLS fingerprint spoofing (JA3/JA4) | `curl-cffi` | In pyproject.toml, wire it |
| Anti-detect browser | `camoufox` | In pyproject.toml, wire it |
| Playwright stealth patches | `playwright-stealth` | **ADD** |
| Fingerprint rotation | Custom `fingerprint_rotator.py` | **BUILD** |
| WebGL/Canvas/Font spoofing | Custom + camoufox | **BUILD** |
| Request fingerprint randomization | Custom | **BUILD** |

---

### 3.3 PILLAR 3: Deep Research Module v2

#### 3.3.1 Vision

Transform the basic `DeepResearchWorkflow` (SearXNG → parallel fetch → aggregation) into a **recursive, multi-agent research engine** comparable to OpenAI Deep Research, Perplexity Deep Research, and Gemini Deep Research.

#### 3.3.2 Architecture: Recursive Search-Reason Loop

```
User Query
    │
    ▼
┌─────────────────┐
│  CLARIFY        │  ← Optional: ask clarifying questions (1 round)
│  (Agent hint)   │
└─────────────────┘
    │
    ▼
┌─────────────────┐     breadth = B (e.g. 5 parallel queries)
│  GENERATE SERP  │     depth = D (e.g. 3 recursive levels)
│  QUERIES        │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  SEARCH         │  ← SearXNG + Brave Search API + Google CSE
│  (Parallel B)   │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  FETCH & PARSE  │  ← Octopus ARM-2/3 (Playwright/camoufox)
│  (Parallel)     │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  EXTRACT        │  ← Readability-lxml / trafilatura / markdownify
│  & STRUCTURE    │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  SOURCE SCORE   │  ← Domain credibility DB + freshness + authority
│  & DEDUPE       │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  SYNTHESIZE     │  ← LLM-agnostic: agent receives structured evidence
│  LEARNINGS      │     Voyant returns: key_findings[], follow_up_questions[]
└─────────────────┘
    │
    ├── depth < D ? ──→ GENERATE FOLLOW-UP QUERIES → loop
    │
    ▼
┌─────────────────┐
│  CROSS-REF      │  ← Verify claims across ≥2 independent sources
│  VALIDATION     │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  GENERATE       │  ← Structured markdown report with citations
│  REPORT         │     Sections: Executive Summary, Findings, Sources, Confidence
└─────────────────┘
    │
    ▼
   Artifact → MinIO
```

#### 3.3.3 Module Structure

```
apps/scraper/deep_research/              # NEW directory
├── __init__.py
├── schemas.py                           # ResearchConfig, ResearchResult, Citation
├── workflow.py                          # DeepResearchWorkflow v2 (Temporal)
├── agents/
│   ├── query_generator.py               # Generate SERP queries from topic
│   ├── source_scorer.py                 # Domain credibility + PageRank proxy
│   ├── content_extractor.py             # trafilatura / readability-lxml
│   ├── synthesizer.py                   # Structured evidence synthesis
│   ├── cross_validator.py               # Cross-reference claim validation
│   └── report_generator.py              # Markdown report with citations
├── sources/
│   ├── searxng_client.py                # Existing
│   ├── brave_search.py                  # NEW: Brave Search API
│   ├── google_cse.py                    # NEW: Google Custom Search
│   └── serper_client.py                 # Existing (Serper.dev)
├── credibility/
│   ├── domain_db.py                     # Static credibility DB (news=.9, blog=.4)
│   └── freshness_scorer.py              # Recency scoring
└── tests/
    └── test_deep_research_e2e.py
```

#### 3.3.4 Source Credibility Database

```python
# apps/scraper/deep_research/credibility/domain_db.py
DOMAIN_CREDIBILITY = {
    # Tier 1: Authoritative
    "gov": 0.95, "edu": 0.95, "ac.uk": 0.95, "nature.com": 0.95,
    "arxiv.org": 0.90, "reuters.com": 0.90, "bloomberg.com": 0.90,
    # Tier 2: Credible
    "wikipedia.org": 0.80, "github.com": 0.80, "medium.com": 0.60,
    # Tier 3: Uncertain
    "blogspot.com": 0.40, "wordpress.com": 0.40,
    # Default
    "default": 0.50,
}
```

#### 3.3.5 Report Schema

```python
class ResearchReport(BaseModel):
    query: str
    generated_at: datetime
    breadth: int
    depth: int
    sources_consulted: int
    sources_cited: List[Citation]
    executive_summary: str
    key_findings: List[Finding]
    confidence_score: float  # 0.0-1.0 based on source quality + cross-validation
    follow_up_questions: List[str]
    raw_evidence: List[EvidenceChunk]  # For agent inspection
```

---

### 3.4 PILLAR 4: Enterprise Scraping Stack Expansion

#### 3.4.1 New Dependencies to Add

| Package | Purpose | License | Current Status |
|---------|---------|---------|----------------|
| `django-milvus` | Django ORM for Milvus | Apache 2.0 | **ADD** |
| `pymilvus` | Milvus Python SDK | Apache 2.0 | **ADD** |
| `playwright-stealth` | Playwright stealth patches | MIT | **ADD** |
| `botasaurus` | Python anti-bot crawler framework | MIT | **ADD** |
| `crawl4ai` | LLM-native crawler (markdown output) | Apache 2.0 | **ADD** |
| `trafilatura` | Content extraction to markdown | Apache 2.0 | In pyproject.toml ✅ |
| `readability-lxml` | Article extraction | Apache 2.0 | In pyproject.toml ✅ |
| `markdownify` | HTML → Markdown conversion | MIT | **ADD** |
| `adblockparser` | Ad/tracker blocking | MIT | **ADD** |
| `flaresolverr` | Cloudflare bypass proxy | MIT | **ADD** (Docker sidecar) |
| `zenrows` | Anti-bot API client | Proprietary (API) | **ADD** (optional) |
| `scrapingbee` | Proxy/anti-bot API client | Proprietary (API) | **ADD** (optional) |
| `google-api-python-client` | Google Sheets / CSE export | Apache 2.0 | **ADD** |
| `openpyxl` | XLSX export | MIT | In pyproject.toml ✅ |
| `xlsxwriter` | Advanced XLSX formatting | BSD | **ADD** |
| `polars` | Fast DataFrame for export processing | MIT | **ADD** |
| `pyarrow` | Parquet export | Apache 2.0 | In pyproject.toml ✅ |
| `fsspec` | Unified file system for cloud exports | BSD | **ADD** |
| `s3fs` | S3 export | Apache 2.0 | **ADD** |
| `gcsfs` | GCS export | BSD | **ADD** |

#### 3.4.2 Docker Compose Additions

```yaml
  # Anti-bot bypass sidecar
  flaresolverr:
    image: ghcr.io/flaresolverr/flaresolverr:latest
    environment:
      - LOG_LEVEL=info
    ports:
      - "8191:8191"

  # Milvus (already defined in 3.1.5)
  milvus-standalone:
    ...

  # Optional: Browserless managed browser pool
  browserless:
    image: ghcr.io/browserless/chromium:latest
    ports:
      - "3000:3000"
    environment:
      - MAX_CONCURRENT_SESSIONS=10
      - CONNECTION_TIMEOUT=60000
```

---

## 4. RECOMMENDED OPEN SOURCE TOOL MATRIX

### 4.1 Data Processing & Export

| Tool | Role | Integration Point |
|------|------|-------------------|
| **Polars** | High-performance DataFrame for transform/export | `octopus/exporters/` |
| **FSSpec** | Unified filesystem abstraction (S3, GCS, Azure, local) | `octopus/exporters/` |
| **XlsxWriter** | Rich Excel formatting (charts, formulas, conditional formatting) | `octopus/exporters/xlsx_exporter.py` |
| **Markdownify** | HTML → clean Markdown | `deep_research/content_extractor.py` |

### 4.2 Scraping & Evasion

| Tool | Role | Integration Point |
|------|------|-------------------|
| **Playwright-Stealth** | Patches to hide automation fingerprints | `octopus/evasion/stealth_profile.py` |
| **Botasaurus** | Python framework with built-in stealth + parallelization | Alternative to Scrapy for ARM-4 |
| **Crawl4AI** | AI-native crawler returning LLM-ready markdown | `deep_research/content_extractor.py` |
| **FlareSolverr** | Cloudflare bypass proxy (Docker sidecar) | `octopus/evasion/` |
| **AdBlockParser** | Block ads/trackers to reduce load + noise | `octopus/dynamic/` |

### 4.3 Search & Research

| Tool | Role | Integration Point |
|------|------|-------------------|
| **Brave Search API** | Privacy-focused search results | `deep_research/sources/brave_search.py` |
| **Google CSE** | Programmable search engine | `deep_research/sources/google_cse.py` |
| **Trafilatura** | Content extraction (already in deps) | `deep_research/content_extractor.py` |
| **Readability-lxml** | Article extraction (already in deps) | `deep_research/content_extractor.py` |

---

## 5. INTEGRATION ARCHITECTURE

### 5.1 Octopus + UPTP Integration

The UPTP engine (`apps.uptp_core/engine.py`) must route to Octopus:

```python
# In UPTPExecutionEngine.dispatch_execution
elif category == TemplateCategory.SCRAPE:
    if template_id == "scrape.octopus.auto":
        return OctopusDispatcher().dispatch(
            OctopusRequest(url=params["url"], arm=OctopusARM.AUTO, ...)
        )
    elif template_id == "scrape.octopus.crawl":
        return OctopusDispatcher().dispatch(
            OctopusRequest(url=params["url"], arm=OctopusARM.CRAWL, ...)
        )
    elif template_id == "scrape.octopus.template":
        template = TemplateRegistry.get(params["template_name"])
        return OctopusDispatcher().dispatch(template.to_request())
```

### 5.2 Octopus + MCP Integration

```python
# apps/mcp/tools_scrape.py additions
@mcp_app.tool()
def scrape_auto_detect(url: str, hint: str, tenant_id: str) -> Dict:
    """Auto-detect and extract structured data from a URL."""
    request = OctopusRequest(
        url=url,
        arm=OctopusARM.DYNAMIC,
        tenant_id=tenant_id,
        auto_detect_hint=hint,
    )
    result = asyncio.run(OctopusDispatcher().dispatch(request))
    return result.model_dump()

@mcp_app.tool()
def scrape_template(template_name: str, params: Dict, tenant_id: str) -> Dict:
    """Run a pre-built scraping template."""
    template = TemplateRegistry.get(template_name)
    request = template.render(params, tenant_id=tenant_id)
    result = asyncio.run(OctopusDispatcher().dispatch(request))
    return result.model_dump()

@mcp_app.tool()
def deep_research_v2(query: str, breadth: int, depth: int, tenant_id: str) -> Dict:
    """Execute recursive deep research with structured report output."""
    workflow_id = f"deep-research-{uuid4()}"
    asyncio.run(_start_workflow(
        DeepResearchWorkflowV2,
        workflow_id,
        {"query": query, "breadth": breadth, "depth": depth, "tenant_id": tenant_id}
    ))
    return {"job_id": workflow_id, "status": "started"}
```

### 5.3 Milvus + Search Integration

```python
# apps/search/api.py — upgrade endpoints
@search_router.post("/index")
def index_document(request: IndexRequest):
    tenant_id = get_tenant_id()
    embedding = get_embedding(request.text)          # 1536-dim
    sparse = get_sparse_embedding(request.text)      # BM25 sparse vector
    doc = VoyantDocument(
        doc_id=str(uuid4()),
        tenant_id=tenant_id,
        content=request.text,
        embedding=embedding,
        sparse_embedding=sparse,
        metadata=request.metadata,
        source_type=request.source_type,
        created_at=int(time.time()),
    )
    doc.save()
    return {"id": doc.doc_id}

@search_router.post("/query")
def query_documents(request: QueryRequest):
    tenant_id = get_tenant_id()
    dense_vec = get_embedding(request.query)
    sparse_vec = get_sparse_embedding(request.query)
    results = VoyantDocument.hybrid_search(
        query_embedding=dense_vec,
        query_sparse=sparse_vec,
        top_k=request.top_k,
        filter_expr=f'tenant_id == "{tenant_id}"',
        ranker=WeightedRanker(0.7, 0.3),
    )
    return results
```

---

## 6. DATA FLOW DIAGRAMS

### 6.1 Octopus No-Code Workflow

```
Agent → MCP scrape_auto_detect(url, hint)
    │
    ▼
OctopusDispatcher
    │
    ├── arm == AUTO ? ──→ AutoDetectEngine.analyze(url, hint)
    │                         │
    │                         ▼
    │                     DOM structure analysis
    │                     Repeating pattern detection
    │                     Data-type inference
    │                         │
    │                         ▼
    │                     Selector candidates (ranked)
    │
    ▼
ArmDynamic.execute(selectors)
    │
    ▼
Playwright + stealth_profile
    │
    ▼
Structured extraction → OctopusResult
    │
    ▼
Exporter (JSON/CSV/XLSX/Parquet/Markdown)
    │
    ▼
MinIO artifact store
```

### 6.2 Deep Research v2 Flow

```
Agent → MCP deep_research_v2(query, breadth=5, depth=3)
    │
    ▼
Temporal DeepResearchWorkflowV2
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  RECURSION LEVEL 1 (depth=1)                            │
│  QueryGenerator → 5 SERP queries (breadth=5)            │
│  SearchAgent → parallel search (SearXNG + Brave + CSE)  │
│  FetchAgent → parallel Octopus fetch (ARM-2/3)          │
│  ExtractAgent → trafilatura / readability               │
│  SourceScorer → credibility + freshness                 │
│  Synthesizer → key_findings[1], follow_up_questions[1]  │
└─────────────────────────────────────────────────────────┘
    │
    ▼ (loop while depth < 3)
┌─────────────────────────────────────────────────────────┐
│  RECURSION LEVEL 2 (depth=2)                            │
│  QueryGenerator → follow_up_questions[1] → 5 queries    │
│  ... (same pipeline)                                    │
│  Synthesizer → key_findings[2]                          │
└─────────────────────────────────────────────────────────┘
    │
    ▼
CrossValidator → verify claims across ≥2 sources
    │
    ▼
ReportGenerator → Markdown report with citations
    │
    ▼
ArtifactStore → MinIO (report.md + evidence.json)
```

---

## 7. DEPLOYMENT & INFRASTRUCTURE CHANGES

### 7.1 Docker Compose (Standalone)

Add 3 new services:
1. `milvus-standalone` (with etcd + minio dependencies)
2. `flaresolverr` (Cloudflare bypass sidecar)
3. `browserless` (managed browser pool, optional)

Memory budget increases from 8GB → **10GB**:
- Milvus standalone: 1GB
- FlareSolverr: 256MB
- Browserless: 512MB

### 7.2 Kubernetes

Add to `voyant-core.yaml`:
- Milvus StatefulSet with persistent volume
- FlareSolverr Deployment
- ConfigMap for proxy provider credentials

### 7.3 Helm Charts

Update `voyant-udb/values.yaml`:
```yaml
milvus:
  enabled: true
  mode: standalone  # or cluster
  persistence:
    size: 10Gi
  resources:
    limits:
      memory: 1Gi
      cpu: 1000m

flaresolverr:
  enabled: true

proxyProviders:
  brightData:
    enabled: false
    username: ""
    password: ""
  oxylabs:
    enabled: false
    apiKey: ""
```

---

## 8. SECURITY & COMPLIANCE HARDENING

### 8.1 Scraping Ethics & Compliance

| Control | Implementation |
|---------|---------------|
| robots.txt enforcement | `ArmCrawl` respects `obey_robots=True` |
| Rate limiting per domain | `download_delay` + domain-level token bucket |
| User-Agent rotation | `fake-useragent` + per-provider custom strings |
| GDPR data minimization | PII classifier (`sensitivity_classifier.py`) strips personal data |
| CAPTCHA legal compliance | Only third-party solving services (agent-configured) |
| Audit trail | Every scrape logged to `AuditLog` with actor + URL + selectors |

### 8.2 Milvus Security

| Control | Implementation |
|---------|---------------|
| TLS encryption | Milvus server TLS via cert-manager in K8s |
| RBAC | Milvus user/role per tenant (optional) |
| Partition isolation | `tenant_id` as partition key |
| Data encryption at rest | MinIO SSE for Milvus object storage |

### 8.3 Deep Research Source Ethics

| Control | Implementation |
|---------|---------------|
| Source attribution | Every finding cites URL + accessed_at |
| Confidence scoring | Low-confidence findings flagged |
| Misinformation detection | Cross-reference validation rejects singleton claims |
| Copyright respect | Extraction limited to fair-use snippets (configurable max chars) |

---

## 9. IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Weeks 1-2)
- [ ] Add `django-milvus`, `pymilvus`, `playwright-stealth`, `botasaurus`, `crawl4ai`, `markdownify`, `polars`, `fsspec` to dependencies
- [ ] Deploy Milvus in standalone Docker Compose
- [ ] Build `MilvusVectorStore` adapter
- [ ] Migrate search API to Milvus hybrid search
- [ ] Write Milvus integration tests

### Phase 2: Octopus Core (Weeks 3-5)
- [ ] Implement `OctopusDispatcher` with all 8 ARM executors
- [ ] Wire `curl-cffi` and `camoufox` (already in deps)
- [ ] Build `AutoDetectEngine` with DOM pattern analysis
- [ ] Build `ProxyPool` with provider abstraction
- [ ] Build `CaptchaSolver` with pluggable providers
- [ ] Build `TemplateRegistry` with 50 MVP templates
- [ ] Add exporters: CSV, Parquet, XLSX, Markdown
- [ ] Write E2E tests for each ARM

### Phase 3: Octopus Enterprise (Weeks 6-8)
- [ ] Add 600+ template library (JSON definitions)
- [ ] Build cloud scheduling (Temporal cron workflows)
- [ ] Add Google Sheets export integration
- [ ] Build HITL review queue in dashboard
- [ ] Add real-time telemetry (Prometheus + Kafka)
- [ ] Add anti-bot evasion stack (JA3/JA4, fingerprint rotation)

### Phase 4: Deep Research v2 (Weeks 9-11)
- [ ] Build `DeepResearchWorkflowV2` with recursive loop
- [ ] Implement `QueryGenerator`, `SourceScorer`, `CrossValidator`
- [ ] Add Brave Search API + Google CSE sources
- [ ] Build structured `ResearchReport` generation
- [ ] Integrate with Octopus for fetching
- [ ] Write E2E research tests

### Phase 5: Hardening (Weeks 12-13)
- [ ] Load testing: 10K vectors, 100 concurrent scrapes
- [ ] Security audit: SSRF, CAPTCHA ethics, proxy leak checks
- [ ] Documentation: API docs, MCP tool docs, template authoring guide
- [ ] Compliance review: ISO 25010 gap closure

---

## 10. RBAC & SECURITY ARCHITECTURE

### 10.1 Three-Layer Authorization

| Layer | Technology | Scope |
|-------|-----------|-------|
| **Layer 1: Keycloak JWT + Roles** | Keycloak RS256 | Realm + Role authentication |
| **Layer 2: Tenant Isolation** | Django ORM + RBACManager | Row-level filtering by tenant_id + realm |
| **Layer 3: SpiceDB ReBAC** | Authzed gRPC | Resource-level permissions (view/edit/delete on specific objects) |

### 10.2 Role Definitions

| Role | Data Access | Operations |
|------|-------------|------------|
| **voyant-admin** | All tenants, all realms, all data | CRUD + execute + manage + delete |
| **voyant-engineer** | Own tenant, own realm | Read all + write sources/jobs + execute SQL/presets + scrape |
| **voyant-analyst** | Own tenant, own realm | Read all + execute SQL/presets + research (capped) |
| **voyant-viewer** | Own tenant, own realm | Read dashboards, reports, artifacts ONLY |

### 10.3 Realm Isolation

- Each Keycloak realm is a **security boundary**
- Users from `realm-a` **CANNOT** access `realm-b` endpoints
- Admin in `realm-a` **CANNOT** see data from `realm-b`
- Cross-realm access requires explicit `manage:realms` permission

### 10.4 RBAC in New Modules

| Module | RBAC Enforcement |
|--------|-----------------|
| **Milvus** | Tenant + realm + owner filtering on all search/index/delete |
| **Octopus** | `execute:scrape` required; analysts template-only; viewers blocked |
| **Deep Research** | `execute:research` required; analyst caps on breadth/depth |
| **SQL** | `execute:sql` required; admin override audited |
| **Governance** | `read:quotas` for engineers; `write:quotas` admin-only |

### 10.5 Audit Logging

Every RBAC decision logged to immutable `AuditLog`:
- `auth.denied.role` — Wrong role
- `auth.denied.realm` — Cross-realm attempt
- `auth.denied.tenant` — Cross-tenant attempt
- `auth.admin_override` — Admin bypass (heavily audited)

---

## 11. RISK ASSESSMENT

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Milvus adds infra complexity | Medium | Medium | Start with standalone; cluster only when >10M vectors |
| Anti-bot arms race | High | Medium | Pluggable provider model; swap providers without code changes |
| CAPTCHA solving costs | Medium | Medium | Agent-configurable; disabled by default |
| Template maintenance | Medium | Low | Community template registry; versioning |
| Deep Research hallucinations | Medium | High | Zero LLM inside Voyant; agent receives evidence only |
| Proxy credential leaks | Low | High | Vault integration; never log credentials |
| Cross-tenant data leak | Low | Critical | Three-layer RBAC + penetration testing |
| Cross-realm privilege escalation | Low | Critical | Realm validation in JWT + SpiceDB checks |

---

## APPENDIX A: Octopus ARM Detailed Specifications

### ARM-1: Static (`arm_static.py`)
- **Engine:** httpx + parsel (XPath/CSS)
- **Use case:** Simple HTML pages, APIs, sitemaps
- **Performance:** >1000 req/sec per worker
- **Stealth:** Minimal; relies on proxy rotation

### ARM-2: Dynamic (`arm_dynamic.py`)
- **Engine:** Playwright + Chromium
- **Use case:** SPA, JavaScript-rendered content, infinite scroll
- **Performance:** 5-20 pages/sec per browser context
- **Stealth:** Playwright-stealth patches, user-agent rotation

### ARM-3: Evasion (`arm_evasion.py`)
- **Engine:** curl-cffi (JA3 spoofing) OR camoufox (anti-detect Firefox)
- **Use case:** Protected sites with WAF/bot detection
- **Performance:** curl-cffi: >100 req/sec; camoufox: 5-10/sec
- **Stealth:** Maximum — TLS fingerprint spoofing, browser fingerprint randomization

### ARM-4: Crawl (`arm_crawl.py`)
- **Engine:** Scrapy + Crawlee (Python) OR Botasaurus
- **Use case:** Full-site crawls, link discovery, sitemap extraction
- **Performance:** 100-1000 pages/sec depending on site
- **Stealth:** Proxy rotation, random delays, robots.txt respect

### ARM-5: API Intercept (`arm_api_intercept.py`)
- **Engine:** Playwright network interception
- **Use case:** SPA sites that load data via XHR/fetch
- **Performance:** 10-50 API captures per page
- **Stealth:** Same as ARM-2

### ARM-6: Document (`arm_document.py`)
- **Engine:** pdfplumber + unstructured + tika
- **Use case:** PDF, DOCX, XLSX extraction
- **Performance:** 1-10 docs/sec
- **Stealth:** N/A (local files)

### ARM-7a: OCR (`arm_ocr.py`)
- **Engine:** Tesseract + Pillow preprocessing
- **Use case:** Image-based text extraction
- **Performance:** 1-5 images/sec
- **Stealth:** N/A

### ARM-7b: Transcribe (`arm_transcribe.py`)
- **Engine:** Whisper (OpenAI)
- **Use case:** Audio/video transcription
- **Performance:** 0.5-2x real-time
- **Stealth:** N/A

### ARM-8: Archive (`arm_archive.py`)
- **Engine:** Playwright interactive automation
- **Use case:** Deep archival of tabbed interfaces, download portals
- **Performance:** 1-5 interactions/minute
- **Stealth:** Same as ARM-2 + download tracking

---

## APPENDIX B: Template Library Categories (MVP 50 → Target 600+)

| Category | Count | Examples |
|----------|-------|----------|
| E-commerce | 80 | Amazon, eBay, Shopify, Walmart, Target |
| Real Estate | 40 | Zillow, Realtor.com, Redfin |
| Social Media | 60 | Twitter/X, LinkedIn, Instagram, TikTok |
| Maps / Local | 40 | Google Maps, Yelp, Foursquare |
| Jobs | 30 | LinkedIn Jobs, Indeed, Glassdoor |
| Finance | 50 | Yahoo Finance, SEC EDGAR, CoinMarketCap |
| News | 40 | CNN, BBC, Reuters, Bloomberg |
| Academic | 30 | Google Scholar, arXiv, PubMed |
| Government | 30 | USASpending, data.gov, SERCOP |
| Travel | 30 | Booking.com, Airbnb, TripAdvisor |
| Automotive | 20 | Cars.com, Autotrader, Patiotuerca |
| Generic | 150 | Product pages, directories, contact lists |

---

*End of Document*
