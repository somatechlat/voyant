# SOFTWARE REQUIREMENTS SPECIFICATION
# VOYANT v3.1.0 ENTERPRISE UPGRADE

**Document ID:** VOYANT-SRS-3.1.0-ENTERPRISE
**Status:** APPROVED
**Version:** 1.0.0
**Date:** 2026-05-21
**Classification:** Canonical SRS
**Compliance:** ISO/IEC 29148:2018, ISO/IEC 25010:2011, ISO/IEC 27001:2022, OWASP Top 10 2021

---

## REVISION HISTORY

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0.0 | 2026-05-21 | Voyant Architecture Team | Initial enterprise upgrade SRS |

---

## TABLE OF CONTENTS

1. [Introduction](#1-introduction)
2. [References](#2-references)
3. [Definitions and Acronyms](#3-definitions-and-acronyms)
4. [System Overview](#4-system-overview)
5. [Functional Requirements](#5-functional-requirements)
   - 5.1 Milvus Vector Database (FR-MIL-001 to FR-MIL-012)
   - 5.2 Octopus Scraping Module (FR-OCT-001 to FR-OCT-035)
   - 5.3 Deep Research Module (FR-DRS-001 to FR-DRS-018)
   - 5.4 Enterprise Export & Integration (FR-EXP-001 to FR-EXP-010)
6. [Non-Functional Requirements](#6-non-functional-requirements)
   - 6.1 Performance Efficiency (NFR-PER-001 to NFR-PER-010)
   - 6.2 Reliability (NFR-REL-001 to NFR-REL-008)
   - 6.3 Security (NFR-SEC-001 to NFR-SEC-015)
   - 6.4 Maintainability (NFR-MNT-001 to NFR-MNT-006)
   - 6.5 Portability (NFR-PRT-001 to NFR-PRT-004)
   - 6.6 Compatibility (NFR-CMP-001 to NFR-CMP-005)
   - 6.7 Usability (NFR-USB-001 to NFR-USB-005)
7. [Interface Requirements](#7-interface-requirements)
8. [Data Requirements](#8-data-requirements)
9. [Quality Requirements](#9-quality-requirements)
10. [Compliance Requirements](#10-compliance-requirements)
11. [Risk and Assumptions](#11-risk-and-assumptions)
12. [Appendices](#12-appendices)

---

## 1. INTRODUCTION

### 1.1 Purpose

This Software Requirements Specification (SRS) defines the functional and non-functional requirements for the Voyant v3.1.0 Enterprise Upgrade. It covers three major architectural initiatives:

1. **Milvus Vector Database Migration** — Replacing the in-memory vector store with a production-grade vector database
2. **Octopus Scraping Module** — Enterprise no-code data extraction platform with Octoparse feature parity
3. **Deep Research Module v2** — Recursive multi-agent research engine with structured report generation

### 1.2 Scope

**In Scope:**
- Vector search infrastructure upgrade to Milvus 2.4+
- Hybrid dense + sparse vector search
- Octopus 8-ARM scraping dispatcher implementation
- AI auto-detection of data fields
- Proxy rotation and CAPTCHA solving
- Template library (50 MVP → 600+ target)
- No-code workflow builder
- Scheduled / cloud scraping
- Deep research recursive loop with breadth/depth control
- Source credibility scoring and cross-reference validation
- Structured report generation with citations
- Enterprise export formats (Parquet, XLSX, Markdown, Google Sheets)

**Out of Scope:**
- LLM integration inside Voyant ("Zero Intelligence" principle maintained)
- Native mobile applications
- Real-time collaborative editing

### 1.3 Intended Audience

- Software architects and lead developers
- DevOps / SRE engineers
- QA / compliance engineers
- Product managers
- AI agent integrators (MCP consumers)

---

## 2. REFERENCES

| ID | Document | Version | Organization |
|----|----------|---------|--------------|
| REF-1 | ISO/IEC 29148:2018 — Systems and software engineering — Life cycle processes — Requirements engineering | 2018 | ISO |
| REF-2 | ISO/IEC 25010:2011 — Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — System and software quality models | 2011 | ISO |
| REF-3 | ISO/IEC 27001:2022 — Information security, cybersecurity and privacy protection — Information security management systems — Requirements | 2022 | ISO |
| REF-4 | OWASP Top 10 — 2021 | 2021 | OWASP |
| REF-5 | Voyant SRS v3.0.0 (Canonical) | 3.0.0 | SomaTech |
| REF-6 | Voyant Scraper SRS v1.0.0 | 1.0.0 | SomaTech |
| REF-7 | Milvus Documentation v2.4 | 2.4 | Zilliz / LF AI |
| REF-8 | Octoparse Feature Documentation | 2025 | Octoparse Inc. |

---

## 3. DEFINITIONS AND ACRONYMS

| Term | Definition |
|------|------------|
| **ANN** | Approximate Nearest Neighbor — algorithm for fast vector similarity search |
| **ARM** | Autonomous Retrieval Mechanism — one of 8 scraping strategies in Octopus |
| **CAPTCHA** | Completely Automated Public Turing test to tell Computers and Humans Apart |
| **HNSW** | Hierarchical Navigable Small World — graph-based ANN index |
| **HITL** | Human In The Loop — manual review step for uncertain extractions |
| **JA3/JA4** | TLS fingerprinting hashes used for bot detection |
| **MCP** | Model Context Protocol — agent-facing tool interface |
| **OCR** | Optical Character Recognition |
| **PII** | Personally Identifiable Information |
| **SERP** | Search Engine Results Page |
| **SSRF** | Server-Side Request Forgery |
| **UPTP** | Universal Parametric Template Pattern — Voyant's generic execution router |
| **WAF** | Web Application Firewall |

---

## 4. SYSTEM OVERVIEW

### 4.1 Current System Context

Voyant v3.0.0 is a Django 5 + Ninja REST API platform with Temporal.io workflow orchestration, DuckDB analytics, Trino SQL federation, and in-memory vector search. It exposes 35+ MCP tools and supports multi-tenant data operations.

### 4.2 Upgrade Context

The v3.1.0 upgrade addresses three critical production gaps:

1. **Vector search cannot scale** — In-memory JSON storage with O(n) brute-force search
2. **Scraping is manual** — Agent must provide all selectors; no auto-detection, no templates
3. **Research is shallow** — Single search-fetch loop without synthesis or validation

### 4.3 System Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL SYSTEMS                         │
│  Milvus Cluster  │  Proxy Providers  │  CAPTCHA Services   │
│  (Zilliz Cloud   │  (Bright Data,    │  (2Captcha,         │
│   or Self-Host)  │   Oxylabs, etc.)  │   CapSolver)        │
└─────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────────┐
│                      VOYANT v3.1.0                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Milvus    │  │   Octopus   │  │   Deep Research v2  │ │
│  │   Store     │  │   Module    │  │   Module            │ │
│  │             │  │  8 ARMs     │  │  Recursive Loop     │ │
│  │ Hybrid      │  │  Templates  │  │  Source Scoring     │ │
│  │ Search      │  │  Auto-Detect│  │  Cross-Validation   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           EXISTING v3.0.0 CORE                      │   │
│  │  Django / Ninja / Temporal / DuckDB / Trino / Kafka │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. FUNCTIONAL REQUIREMENTS

---

### 5.1 MILVUS VECTOR DATABASE

#### FR-MIL-001: Milvus Deployment
**Priority:** MUST
**Description:** The system shall deploy Milvus 2.4+ in standalone mode for development and cluster mode for production.
**Verification:** Docker Compose contains `milvus-standalone` service; K8s manifests contain Milvus StatefulSet.

#### FR-MIL-002: Collection Schema
**Priority:** MUST
**Description:** The system shall define a `voyant_documents` collection with fields: `id`, `doc_id`, `tenant_id`, `content`, `embedding` (FloatVector), `sparse_embedding` (SparseVector), `metadata` (JSON), `source_type`, `created_at`.
**Verification:** Unit test creates collection and validates schema.

#### FR-MIL-003: Tenant Partition Isolation
**Priority:** MUST
**Description:** The system shall use `tenant_id` as the partition key to enforce physical data isolation between tenants.
**Verification:** Query with `tenant_id == "A"` returns only tenant A documents; tenant B documents are inaccessible.

#### FR-MIL-004: HNSW Index Creation
**Priority:** MUST
**Description:** The system shall create an HNSW index on the `embedding` field with `metric_type=COSINE`, `M=16`, `efConstruction=256`.
**Verification:** `utility.index_building_progress("voyant_documents", "embedding")` returns 100%.

#### FR-MIL-005: Dense Vector Search
**Priority:** MUST
**Description:** The system shall perform approximate nearest neighbor (ANN) search on dense embeddings with latency < 50ms p99 for 1M vectors.
**Verification:** Load test with 1M vectors; measure query latency.

#### FR-MIL-006: Sparse Vector Search
**Priority:** MUST
**Description:** The system shall support sparse vector search (BM25) for keyword-based retrieval.
**Verification:** Insert documents with sparse vectors; query returns keyword-relevant results.

#### FR-MIL-007: Hybrid Search
**Priority:** MUST
**Description:** The system shall support hybrid search combining dense and sparse vectors with configurable weights (e.g., 70% dense + 30% sparse).
**Verification:** Hybrid query returns results ranked by weighted combination; unit test validates ranker behavior.

#### FR-MIL-008: Metadata Filtering
**Priority:** MUST
**Description:** The system shall support filtering by metadata fields during vector search using Milvus expression syntax.
**Verification:** Search with `filter_expr='tenant_id == "t1" AND source_type == "scrape"'` returns correct subset.

#### FR-MIL-009: Backward Compatibility
**Priority:** SHOULD
**Description:** The system shall maintain the existing `VectorStore` Python interface; Milvus implementation shall be a drop-in replacement.
**Verification:** All existing search tests pass with Milvus backend.

#### FR-MIL-010: Django-Milvus ORM
**Priority:** SHOULD
**Description:** The system shall use `django-milvus` to provide Django ORM-like model classes for Milvus collections.
**Verification:** `Document.objects.filter(tenant_id="t1").search(query_vector)` works.

#### FR-MIL-011: Connection Pooling
**Priority:** SHOULD
**Description:** The system shall implement thread-safe Milvus connection pooling with retry logic for transient failures.
**Verification:** Concurrent search from 100 threads succeeds without connection errors.

#### FR-MIL-012: Monitoring
**Priority:** SHOULD
**Description:** The system shall expose Milvus collection statistics (entity count, index status, load state) via Prometheus metrics.
**Verification:** `voyant_milvus_entities_total` and `voyant_milvus_index_ready` metrics are scrapable.

---

### 5.2 OCTOPUS SCRAPING MODULE

#### FR-OCT-001: OctopusDispatcher Implementation
**Priority:** MUST
**Description:** The system shall implement `OctopusDispatcher` to route `OctopusRequest` objects to the correct ARM executor based on the `arm` field.
**Verification:** Unit test dispatches requests to all 8 ARM types and receives `OctopusResult`.

#### FR-OCT-002: ARM-1 Static Execution
**Priority:** MUST
**Description:** ARM-1 shall fetch static HTML using httpx + parsel, extract fields via CSS/XPath selectors, and return structured data.
**Verification:** E2E test fetches `example.com` and extracts `<h1>` text.

#### FR-OCT-003: ARM-2 Dynamic Execution
**Priority:** MUST
**Description:** ARM-2 shall render JavaScript using Playwright, execute browser actions (click, scroll, wait), and extract data from dynamic DOM.
**Verification:** E2E test renders React SPA and extracts dynamically loaded content.

#### FR-OCT-004: ARM-3 Evasion Execution
**Priority:** MUST
**Description:** ARM-3 shall bypass bot detection using curl-cffi (JA3 spoofing) or camoufox (anti-detect Firefox) based on `evasion_mode`.
**Verification:** E2E test fetches Cloudflare-protected site successfully; fingerprint test shows non-automation signature.

#### FR-OCT-005: ARM-4 Crawl Execution
**Priority:** MUST
**Description:** ARM-4 shall crawl websites using Scrapy with configurable depth, concurrency, robots.txt respect, and sitemap parsing.
**Verification:** E2E test crawls 3 levels deep on internal test site; respects robots.txt.

#### FR-OCT-006: ARM-5 API Interception
**Priority:** MUST
**Description:** ARM-5 shall intercept XHR/fetch network requests during Playwright rendering and capture JSON responses.
**Verification:** E2E test intercepts API calls on SPA and returns captured JSON payloads.

#### FR-OCT-007: ARM-6 Document Execution
**Priority:** MUST
**Description:** ARM-6 shall extract text, tables, and metadata from PDF, DOCX, and XLSX files using pdfplumber + unstructured.
**Verification:** E2E test extracts tables from sample PDF with >95% accuracy.

#### FR-OCT-008: ARM-7a OCR Execution
**Priority:** MUST
**Description:** ARM-7a shall extract text from images using Tesseract with preprocessing (contrast, sharpen) and confidence thresholds.
**Verification:** E2E test OCRs sample image; accuracy >85%.

#### FR-OCT-009: ARM-7b Transcription Execution
**Priority:** MUST
**Description:** ARM-7b shall transcribe audio/video files using Whisper with configurable model size.
**Verification:** E2E test transcribes sample MP3; WER <12%.

#### FR-OCT-010: ARM-8 Archive Execution
**Priority:** MUST
**Description:** ARM-8 shall perform interactive deep archival: click selectors, wait for DOM settle, scan for download links, download files, write manifest.
**Verification:** E2E test archives tabbed interface with 3 tabs and 2 downloads.

#### FR-OCT-011: Auto-Detection Engine
**Priority:** MUST
**Description:** The system shall provide `AutoDetectEngine` that analyzes DOM structure and generates CSS/XPath selector candidates without manual configuration.
**Verification:** Input: e-commerce product page without selectors. Output: ranked selectors for title, price, image with >80% precision.

#### FR-OCT-012: Proxy Pool Management
**Priority:** MUST
**Description:** The system shall manage a rotating proxy pool supporting Bright Data, Oxylabs, ScrapingBee, and custom proxies with health checks and session affinity.
**Verification:** 100 sequential requests use ≥10 different IPs; failed proxies auto-evicted.

#### FR-OCT-013: CAPTCHA Solving
**Priority:** SHOULD
**Description:** The system shall integrate with 2Captcha, CapSolver, and NopeCHA for image CAPTCHA, reCAPTCHA v2, hCaptcha, and Cloudflare Turnstile.
**Verification:** E2E test solves reCAPTCHA v2 demo page via CapSolver.

#### FR-OCT-014: Template Registry
**Priority:** MUST
**Description:** The system shall maintain a template registry with pre-built scraping configurations for common websites. MVP: 50 templates. Target: 600+.
**Verification:** `TemplateRegistry.list()` returns ≥50 templates; `TemplateRegistry.get("amazon_product")` returns valid config.

#### FR-OCT-015: Template Execution
**Priority:** MUST
**Description:** The system shall execute templates by rendering parameters into `OctopusRequest` and dispatching to the correct ARM.
**Verification:** Execute `google_maps_reviews` template with `location="New York"`; returns structured reviews.

#### FR-OCT-016: No-Code Workflow Builder
**Priority:** SHOULD
**Description:** The system shall accept JSON workflow definitions that chain multiple ARM steps (e.g., login → navigate → extract → paginate).
**Verification:** JSON workflow with 4 steps executes successfully via Temporal.

#### FR-OCT-017: Cloud Scheduling
**Priority:** SHOULD
**Description:** The system shall support cron-based scheduled scraping via Temporal cron workflows.
**Verification:** Schedule daily job at 9 AM UTC; verify execution at correct time.

#### FR-OCT-018: Export Formats
**Priority:** MUST
**Description:** The system shall export scraped data as JSON, CSV, Parquet, XLSX, and Markdown.
**Verification:** Same dataset exports to all 5 formats with schema preservation.

#### FR-OCT-019: Google Sheets Export
**Priority:** SHOULD
**Description:** The system shall export data directly to Google Sheets via API.
**Verification:** OAuth2 flow completes; data appears in specified sheet.

#### FR-OCT-020: SSRF Protection
**Priority:** MUST
**Description:** All Octopus ARMs shall enforce SSRF protection blocking private IPs, metadata endpoints, and non-HTTP schemes.
**Verification:** Security test blocks 169.254.169.254, localhost, RFC 1918 addresses.

#### FR-OCT-021: Tenant Quota Enforcement
**Priority:** MUST
**Description:** Octopus execution shall check tenant quotas (concurrent jobs, monthly pages) before dispatch.
**Verification:** Quota-exceeded tenant receives `QuotaExceededError`.

#### FR-OCT-022: Circuit Breaker
**Priority:** MUST
**Description:** Each ARM shall use circuit breaker pattern for external dependencies (proxies, CAPTCHA solvers).
**Verification:** 5 consecutive proxy failures open circuit; 6th request fails fast.

#### FR-OCT-023: Telemetry
**Priority:** SHOULD
**Description:** Octopus shall emit Kafka events for every job: start, page fetched, success, failure.
**Verification:** Consumer receives `voyant.octopus.job.started` event with job_id.

#### FR-OCT-024: Human-in-the-Loop
**Priority:** SHOULD
**Description:** The system shall queue uncertain extractions (low confidence or CAPTCHA detected) for human review in the dashboard.
**Verification:** Low-confidence job status = `pending_review`; appears in dashboard queue.

#### FR-OCT-025: Fingerprint Rotation
**Priority:** SHOULD
**Description:** ARM-2 and ARM-3 shall rotate browser fingerprints (canvas, WebGL, fonts, user-agent) per session.
**Verification:** Fingerprinting test shows unique fingerprints across 10 sessions.

#### FR-OCT-026: Ad Blocking
**Priority:** SHOULD
**Description:** ARM-2 and ARM-3 shall block ads and tracking scripts to reduce load and noise.
**Verification:** Page load time reduced by >30% with ad blocking enabled.

#### FR-OCT-027: robots.txt Compliance
**Priority:** MUST
**Description:** ARM-4 shall respect robots.txt directives when `obey_robots=True`.
**Verification:** Crawl of site with `Disallow: /admin/` does not fetch `/admin/`.

#### FR-OCT-028: Concurrent Request Limiting
**Priority:** MUST
**Description:** ARM-4 shall limit concurrent requests per domain to prevent overload.
**Verification:** Crawl with `concurrent_requests=16` never exceeds 16 simultaneous connections to same domain.

#### FR-OCT-029: Retry Logic
**Priority:** MUST
**Description:** All ARMs shall implement exponential backoff retry for transient failures (5xx, timeout).
**Verification:** Simulated 503 response retried 3 times before final failure.

#### FR-OCT-030: Artifact Storage
**Priority:** MUST
**Description:** Octopus results shall be stored as artifacts in MinIO with content-addressable keys.
**Verification:** Artifact URI returned in `OctopusResult.artifact_uri`; retrievable from MinIO.

#### FR-OCT-031: MCP Tool Surface
**Priority:** MUST
**Description:** All Octopus capabilities shall be exposed as MCP tools: `scrape.auto_detect`, `scrape.template`, `scrape.workflow`.
**Verification:** MCP client discovers and invokes tools successfully.

#### FR-OCT-032: Temporal Workflow Integration
**Priority:** MUST
**Description:** Multi-step and scheduled Octopus jobs shall execute as Temporal workflows with full history and replay.
**Verification:** Temporal UI shows workflow history with ARM execution steps.

#### FR-OCT-033: UPTP Integration
**Priority:** MUST
**Description:** Octopus shall be routable via UPTP with templates: `scrape.octopus.auto`, `scrape.octopus.template`, `scrape.octopus.crawl`.
**Verification:** UPTP dispatch returns job URN; Temporal workflow executes.

#### FR-OCT-034: Playwright-Stealth Integration
**Priority:** SHOULD
**Description:** ARM-2 shall apply playwright-stealth patches to evade basic bot detection.
**Verification:** Bot detection test page (e.g., bot.sannysoft.com) shows green checkmarks.

#### FR-OCT-035: Rate Limiting Per Domain
**Priority:** MUST
**Description:** The system shall enforce per-domain rate limits with token bucket algorithm.
**Verification:** 100 requests to same domain with `rate_limit=10/min` complete at ~10/min.

---

### 5.3 DEEP RESEARCH MODULE v2

#### FR-DRS-001: Recursive Research Loop
**Priority:** MUST
**Description:** The system shall execute a recursive research loop with configurable `breadth` (parallel queries per level) and `depth` (recursive levels).
**Verification:** `breadth=5, depth=3` generates 5 + 25 + 125 = 155 queries total.

#### FR-DRS-002: Query Generation
**Priority:** MUST
**Description:** The system shall generate search-optimized sub-queries from the initial research question and from follow-up questions discovered at each recursion level.
**Verification:** Input "AI code editors 2025" generates ≥3 distinct sub-queries.

#### FR-DRS-003: Multi-Source Search
**Priority:** MUST
**Description:** The system shall query multiple search providers in parallel: SearXNG, Brave Search API, and Google Custom Search Engine.
**Verification:** Research job queries ≥2 providers; deduplicates overlapping results.

#### FR-DRS-004: Parallel Content Fetching
**Priority:** MUST
**Description:** The system shall fetch content from discovered URLs in parallel using Octopus ARM-2/3.
**Verification:** 20 URLs fetched concurrently; results aggregated.

#### FR-DRS-005: Content Extraction
**Priority:** MUST
**Description:** The system shall extract clean article content from fetched HTML using trafilatura, readability-lxml, or crawl4ai.
**Verification:** Extraction removes navigation, ads, footers; returns main article text.

#### FR-DRS-006: Source Credibility Scoring
**Priority:** MUST
**Description:** The system shall score each source by domain credibility (authoritative > credible > uncertain) and content freshness.
**Verification:** `arxiv.org` scores ≥0.90; `blogspot.com` scores ≤0.50.

#### FR-DRS-007: Content Deduplication
**Priority:** MUST
**Description:** The system shall deduplicate content using text similarity (MinHash/LSH) to avoid processing identical pages.
**Verification:** 10 identical copies of same press release counted as 1 unique source.

#### FR-DRS-008: Evidence Synthesis
**Priority:** MUST
**Description:** The system shall synthesize extracted content into structured "learnings" — key facts with source attribution.
**Verification:** Output contains `learnings: [{"claim": "...", "sources": ["url1", "url2"]}]`.

#### FR-DRS-009: Cross-Reference Validation
**Priority:** MUST
**Description:** The system shall flag claims that appear in only one source (unverified) and confirm claims supported by ≥2 independent sources.
**Verification:** Singleton claim has `verified=false`; multi-source claim has `verified=true`.

#### FR-DRS-010: Follow-Up Question Generation
**Priority:** MUST
**Description:** The system shall generate follow-up questions based on gaps in current evidence to guide next recursion level.
**Verification:** After level 1, output contains ≥2 follow-up questions.

#### FR-DRS-011: Structured Report Generation
**Priority:** MUST
**Description:** The system shall generate a Markdown report with: title, executive summary, key findings (with citations), methodology, confidence score, and source list.
**Verification:** Report passes JSON schema validation; contains ≥1 citation per finding.

#### FR-DRS-012: Confidence Scoring
**Priority:** MUST
**Description:** The report shall include an overall confidence score (0.0-1.0) based on source quality, cross-validation coverage, and evidence density.
**Verification:** Research with only blog sources scores <0.5; research with peer-reviewed sources scores >0.8.

#### FR-DRS-013: Temporal Workflow
**Priority:** MUST
**Description:** Deep research shall execute as a Temporal workflow with each recursion level as a child workflow.
**Verification:** Temporal UI shows parent workflow + depth child workflows.

#### FR-DRS-014: Artifact Storage
**Priority:** MUST
**Description:** Final report and raw evidence shall be stored as MinIO artifacts.
**Verification:** `artifact_uri` returned; report.md and evidence.json retrievable.

#### FR-DRS-015: MCP Tool Surface
**Priority:** MUST
**Description:** Deep research shall expose MCP tool: `deep_research(query, breadth, depth)`.
**Verification:** MCP client invokes tool; receives job_id for polling.

#### FR-DRS-016: UPTP Integration
**Priority:** MUST
**Description:** Deep research shall be routable via UPTP template: `research.deep`.
**Verification:** UPTP dispatch starts Temporal workflow.

#### FR-DRS-017: Source Freshness Scoring
**Priority:** SHOULD
**Description:** The system shall penalize outdated sources (>2 years) and boost recent sources (<6 months).
**Verification:** 2026 article scores higher than 2022 article on same topic.

#### FR-DRS-018: Max Content Length Limit
**Priority:** MUST
**Description:** The system shall enforce configurable maximum content extraction length (default 10,000 chars) to respect copyright fair use.
**Verification:** Extracted content never exceeds limit; truncated with ellipsis.

---

### 5.5 RBAC & SECURITY

#### FR-RBAC-001: Keycloak Realm Validation
**Priority:** MUST
**Description:** The system shall validate that the JWT token's realm matches the configured service realm; tokens from other realms shall be rejected with 403.
**Verification:** Token from `realm-a` accessing `realm-b` endpoint returns 403.

#### FR-RBAC-002: Role-Based Permission Derivation
**Priority:** MUST
**Description:** The system shall derive granular permissions from Keycloak realm roles: `voyant-admin` → wildcard; `voyant-engineer` → read/write/execute; `voyant-analyst` → read/execute; `voyant-viewer` → read-only dashboards/reports.
**Verification:** User with `voyant-viewer` role cannot access `/v1/sources`.

#### FR-RBAC-003: Tenant Isolation
**Priority:** MUST
**Description:** The system shall enforce that non-admin users can only access data belonging to their own tenant; cross-tenant access attempts shall return 403.
**Verification:** Engineer in Tenant A attempts to read Tenant B source; receives 403.

#### FR-RBAC-004: Realm Isolation
**Priority:** MUST
**Description:** The system shall enforce that users can only access data within their own realm; cross-realm access requires `manage:realms` permission.
**Verification:** Admin in Realm X attempts to read Realm Y without permission; receives 403.

#### FR-RBAC-005: Permission-Based API Access
**Priority:** MUST
**Description:** Every API endpoint shall require a specific permission; unauthorized access shall return 403.
**Verification:** All endpoints tested with each role; only permitted roles succeed.

#### FR-RBAC-006: MCP Tool Permission Enforcement
**Priority:** MUST
**Description:** Every MCP tool shall check user permissions before execution; tools shall return error for unauthorized users.
**Verification:** Viewer attempts `scrape.fetch`; receives permission error.

#### FR-RBAC-007: Admin Override Auditing
**Priority:** MUST
**Description:** Admin actions that bypass normal restrictions (e.g., SQL write) shall be logged to immutable audit log with full context.
**Verification:** Admin executes INSERT via SQL endpoint; audit log contains query, admin user_id, timestamp.

#### FR-RBAC-008: SpiceDB Resource Permissions
**Priority:** SHOULD
**Description:** The system shall check SpiceDB for resource-level permissions (view/edit/delete) on specific objects.
**Verification:** User A (owner) can delete source; User B (viewer) receives 403 on same source.

#### FR-RBAC-009: Role-Based Data Filtering
**Priority:** MUST
**Description:** API responses shall filter fields based on role; viewers shall not see internal fields (e.g., proxy credentials, API keys).
**Verification:** Response JSON for viewer lacks `proxy_url`, `api_key` fields.

#### FR-RBAC-010: Milvus RBAC Filtering
**Priority:** MUST
**Description:** Milvus vector search shall filter by `tenant_id + realm + owner_id`; users cannot search vectors outside their tenant.
**Verification:** Search returns only vectors matching user's tenant and realm.

#### FR-RBAC-011: Octopus RBAC
**Priority:** MUST
**Description:** Octopus dispatch shall require `execute:scrape` permission; viewers blocked; analysts limited to templates only.
**Verification:** Viewer dispatch returns 403; analyst custom workflow returns 403; engineer succeeds.

#### FR-RBAC-012: Deep Research RBAC
**Priority:** MUST
**Description:** Deep research shall require `execute:research` permission; analysts have breadth/depth caps; viewers blocked.
**Verification:** Analyst breadth=10 capped to 3; viewer receives 403.

#### FR-RBAC-013: Immutable Audit Log
**Priority:** MUST
**Description:** All access control decisions (granted/denied) shall be written to append-only audit log with actor, resource, action, outcome, realm, tenant.
**Verification:** Audit log contains denied entries; no update/delete endpoints exist.

#### FR-RBAC-014: Realm-Aware Models
**Priority:** MUST
**Description:** All models shall include `realm` field; queries shall filter by `realm + tenant_id`.
**Verification:** Database query inspection shows `WHERE realm = 'x' AND tenant_id = 'y'`.

---

### 5.4 ENTERPRISE EXPORT & INTEGRATION

#### FR-EXP-001: Parquet Export
**Priority:** MUST
**Description:** The system shall export datasets to Apache Parquet format with schema preservation.
**Verification:** Parquet file readable by pandas/pyarrow; schema matches source.

#### FR-EXP-002: XLSX Export
**Priority:** MUST
**Description:** The system shall export datasets to XLSX with formatting: headers, column widths, date formatting.
**Verification:** Excel opens file; formatting correct.

#### FR-EXP-003: Markdown Export
**Priority:** MUST
**Description:** The system shall export extracted web content to clean Markdown.
**Verification:** Markdown renders correctly; no HTML artifacts.

#### FR-EXP-004: CSV Export
**Priority:** MUST
**Description:** The system shall export datasets to RFC 4180 compliant CSV.
**Verification:** pandas.read_csv() succeeds; special chars escaped.

#### FR-EXP-005: JSON Export
**Priority:** MUST
**Description:** The system shall export datasets to JSON (array of objects).
**Verification:** json.loads() succeeds; schema valid.

#### FR-EXP-006: Google Sheets Export
**Priority:** SHOULD
**Description:** The system shall export datasets directly to Google Sheets via API with OAuth2.
**Verification:** Data appears in specified Google Sheet within 60 seconds.

#### FR-EXP-007: S3 Export
**Priority:** SHOULD
**Description:** The system shall export artifacts to S3 using fsspec.
**Verification:** Object appears in S3 bucket; presigned URL accessible.

#### FR-EXP-008: GCS Export
**Priority:** SHOULD
**Description:** The system shall export artifacts to Google Cloud Storage.
**Verification:** Object appears in GCS bucket.

#### FR-EXP-009: Polars Integration
**Priority:** SHOULD
**Description:** The system shall use Polars for high-performance DataFrame operations during export transformation.
**Verification:** 100K row transform completes in <1 second.

#### FR-EXP-010: FSSpec Integration
**Priority:** SHOULD
**Description:** The system shall use fsspec for unified filesystem abstraction across local, S3, GCS, and Azure.
**Verification:** Same code writes to local, S3, and GCS without modification.

---

## 6. NON-FUNCTIONAL REQUIREMENTS

### 6.1 PERFORMANCE EFFICIENCY

#### NFR-PER-001: Vector Search Latency
**Category:** Time Behaviour
**Requirement:** Milvus ANN search latency shall be < 50ms p99 for collections with ≤10M vectors.
**Verification:** Load test with 10M vectors; measure p99 latency.

#### NFR-PER-002: Vector Search Throughput
**Category:** Capacity
**Requirement:** Milvus shall sustain ≥1000 QPS per query node.
**Verification:** Load test with concurrent clients.

#### NFR-PER-003: Scraping Throughput
**Category:** Capacity
**Requirement:** ARM-1 (static) shall sustain ≥1000 pages/sec per worker. ARM-2 (dynamic) shall sustain ≥10 pages/sec per browser context.
**Verification:** Benchmark with test server.

#### NFR-PER-004: Deep Research Speed
**Category:** Time Behaviour
**Requirement:** Deep research with breadth=5, depth=3 shall complete in < 10 minutes.
**Verification:** E2E timing test.

#### NFR-PER-005: Export Speed
**Category:** Time Behaviour
**Requirement:** Export of 100K rows to Parquet shall complete in < 5 seconds.
**Verification:** Benchmark with synthetic data.

#### NFR-PER-006: Memory Efficiency
**Category:** Resource Utilization
**Requirement:** Milvus standalone shall operate within 1GB RAM for ≤1M vectors.
**Verification:** Docker stats monitoring.

#### NFR-PER-007: Index Build Time
**Category:** Time Behaviour
**Requirement:** HNSW index build for 1M vectors shall complete in < 10 minutes.
**Verification:** Measure index build time.

#### NFR-PER-008: Concurrent Scraping Jobs
**Category:** Capacity
**Requirement:** The system shall support ≥100 concurrent Octopus jobs per tenant.
**Verification:** Load test with 100 simultaneous workflows.

#### NFR-PER-009: Proxy Pool Size
**Category:** Capacity
**Requirement:** Proxy pool shall support ≥100 concurrent connections with <1% failure rate.
**Verification:** Proxy health check monitoring.

#### NFR-PER-010: Dashboard Load Time
**Category:** Time Behaviour
**Requirement:** Dashboard pages shall load in < 2 seconds.
**Verification:** Lighthouse performance audit.

---

### 6.2 RELIABILITY

#### NFR-REL-001: Vector Store Availability
**Category:** Availability
**Requirement:** Milvus shall achieve 99.9% uptime in production cluster mode.
**Verification:** Uptime monitoring over 30 days.

#### NFR-REL-002: Data Durability
**Category:** Fault Tolerance
**Requirement:** Vector data shall be replicated across ≥3 nodes in cluster mode; zero data loss on single-node failure.
**Verification:** Chaos engineering: kill one Milvus node; verify data integrity.

#### NFR-REL-003: Scraping Resilience
**Category:** Fault Tolerance
**Requirement:** Octopus jobs shall survive transient failures (5xx, timeout, proxy failure) via retry with exponential backoff.
**Verification:** Simulate failures; verify retry and eventual success.

#### NFR-REL-004: Circuit Breaker Recovery
**Category:** Recoverability
**Requirement:** Circuit breakers shall transition from OPEN to HALF_OPEN after 30 seconds and to CLOSED after 2 successes.
**Verification:** Unit test state machine transitions.

#### NFR-REL-005: Graceful Degradation
**Category:** Fault Tolerance
**Requirement:** If Milvus is unavailable, search API shall return 503 with fallback message; ingestion continues.
**Verification:** Milvus downtime simulation.

#### NFR-REL-006: Workflow Recovery
**Category:** Recoverability
**Requirement:** Temporal workflows shall resume from last completed activity after worker restart.
**Verification:** Kill worker mid-workflow; restart; verify continuation.

#### NFR-REL-007: Proxy Failover
**Category:** Fault Tolerance
**Requirement:** Proxy pool shall evict failed proxies within 5 seconds and redistribute load.
**Verification:** Block proxy IP; verify eviction and continued operation.

#### NFR-REL-008: Backup and Restore
**Category:** Recoverability
**Requirement:** Milvus collections shall support snapshot backup and point-in-time restore.
**Verification:** Create snapshot; delete data; restore; verify.

---

### 6.3 SECURITY

#### NFR-SEC-001: TLS Encryption
**Category:** Confidentiality
**Requirement:** All Milvus connections shall use TLS 1.3 in production.
**Verification:** SSL Labs scan; verify TLS 1.3 only.

#### NFR-SEC-002: Authentication
**Category:** Confidentiality
**Requirement:** Milvus shall enforce username/password authentication; no anonymous access.
**Verification:** Attempt unauthenticated connection; verify rejection.

#### NFR-SEC-003: Tenant Isolation
**Category:** Confidentiality
**Requirement:** Tenant A shall never access Tenant B vectors via search, get, or delete operations.
**Verification:** Security penetration test.

#### NFR-SEC-004: Proxy Credential Protection
**Category:** Confidentiality
**Requirement:** Proxy credentials shall be stored in Vault/K8s secrets; never logged or exposed in API responses.
**Verification:** Code audit + grep for credential patterns in logs.

#### NFR-SEC-005: CAPTCHA Key Protection
**Category:** Confidentiality
**Requirement:** CAPTCHA solver API keys shall be stored in Vault; rotated every 90 days.
**Verification:** Vault audit + key rotation test.

#### NFR-SEC-006: SSRF Prevention
**Category:** Integrity
**Requirement:** All Octopus requests shall pass SSRF validation blocking private IPs, metadata endpoints, and file:// URLs.
**Verification:** Security test with 50 SSRF payloads.

#### NFR-SEC-007: PII Stripping
**Category:** Privacy
**Requirement:** Scraped data shall pass through `SensitivityClassifier`; PII fields redacted before storage.
**Verification:** Input HTML with email/phone; verify redaction in output.

#### NFR-SEC-008: Audit Logging
**Category:** Accountability
**Requirement:** Every scrape and research request shall log actor, URL, timestamp, and outcome to immutable audit log.
**Verification:** Audit log inspection.

#### NFR-SEC-009: Rate Limiting
**Category:** Integrity
**Requirement:** API endpoints shall enforce rate limiting: 60 req/min per tenant, burst 10.
**Verification:** Load test; verify 429 responses.

#### NFR-SEC-010: Content Security Policy
**Category:** Integrity
**Requirement:** Dashboard shall enforce CSP headers preventing XSS.
**Verification:** CSP evaluator scan.

#### NFR-SEC-011: Input Validation
**Category:** Integrity
**Requirement:** All Octopus request parameters shall be validated via Pydantic with `extra="forbid"`.
**Verification:** Fuzzing test with invalid parameters.

#### NFR-SEC-012: robots.txt Compliance
**Category:** Compliance
**Requirement:** Crawl operations shall respect robots.txt; violations logged and alerted.
**Verification:** Crawl test with restrictive robots.txt.

#### NFR-SEC-013: Fair Use Limits
**Category:** Compliance
**Requirement:** Content extraction limited to 10,000 characters per source for copyright fair use.
**Verification:** Extract long article; verify truncation.

#### NFR-SEC-014: Source Attribution
**Category:** Accountability
**Requirement:** Deep research reports shall attribute every claim to source URL.
**Verification:** Report inspection; verify citations.

#### NFR-SEC-015: Misinformation Flagging
**Category:** Integrity
**Requirement:** Claims from low-credibility sources (<0.5) or singleton sources shall be flagged.
**Verification:** Report inspection; verify confidence warnings.

#### NFR-SEC-016: Realm Validation
**Category:** Confidentiality
**Requirement:** The system shall reject JWT tokens from unauthorized realms with 403.
**Verification:** Cross-realm token test returns 403.

#### NFR-SEC-017: Tenant Isolation Enforcement
**Category:** Confidentiality
**Requirement:** Non-admin users shall be unable to access data outside their tenant; IDOR attacks prevented.
**Verification:** Penetration test modifies URL param to other tenant; receives 403.

#### NFR-SEC-018: Role Escalation Prevention
**Category:** Integrity
**Requirement:** Users shall be unable to elevate privileges by modifying JWT claims.
**Verification:** RS256 signature prevents forged roles.

#### NFR-SEC-019: Field-Level Filtering
**Category:** Confidentiality
**Requirement:** API responses shall exclude sensitive fields for lower-privilege roles.
**Verification:** Viewer response lacks proxy credentials, API keys, internal configs.

#### NFR-SEC-020: Immutable Audit Log
**Category:** Accountability
**Requirement:** Audit log shall be append-only; no update or delete operations permitted.
**Verification:** Attempt to modify audit log entry fails.

#### NFR-SEC-021: Cross-Realm Admin Protection
**Category:** Confidentiality
**Requirement:** Cross-realm admin access shall require explicit `manage:realms` permission AND explicit `?realm=` parameter.
**Verification:** Admin without `manage:realms` accessing other realm receives 403.

---

### 6.4 MAINTAINABILITY

#### NFR-MNT-001: Modular ARM Design
**Category:** Modularity
**Requirement:** Each Octopus ARM shall be independently replaceable without affecting others.
**Verification:** Remove ARM-4; verify ARM-1 still functions.

#### NFR-MNT-002: Proxy Provider Plugin
**Category:** Modularity
**Requirement:** Adding a new proxy provider shall require only implementing a single interface class.
**Verification:** Add mock provider in <50 lines.

#### NFR-MNT-003: Template Versioning
**Category:** Modularity
**Requirement:** Templates shall support versioning; old versions remain executable.
**Verification:** Create v2 of template; verify v1 still works.

#### NFR-MNT-004: Test Coverage
**Category:** Testability
**Requirement:** New code shall achieve ≥80% test coverage; integration tests for every ARM.
**Verification:** pytest-cov report.

#### NFR-MNT-005: Documentation
**Category:** Analyzability
**Requirement:** Every public API and MCP tool shall have OpenAPI + docstring documentation.
**Verification:** Automated doc generation; 100% coverage check.

#### NFR-MNT-006: Code Quality
**Category:** Analyzability
**Requirement:** All code shall pass ruff linting and pyright type checking with zero errors.
**Verification:** CI gate.

---

### 6.5 PORTABILITY

#### NFR-PRT-001: Docker Deployment
**Category:** Adaptability
**Requirement:** All new services shall deploy via Docker Compose with single-command startup.
**Verification:** `docker compose up` succeeds on clean machine.

#### NFR-PRT-002: Kubernetes Deployment
**Category:** Adaptability
**Requirement:** All new services shall include K8s manifests and Helm charts.
**Verification:** `helm install` succeeds on test cluster.

#### NFR-PRT-003: Cloud Provider Agnostic
**Category:** Installability
**Requirement:** Milvus deployment shall work on AWS, GCP, Azure, and on-premise.
**Verification:** Deploy on minikube, EKS, and GKE.

#### NFR-PRT-004: OS Compatibility
**Category:** Installability
**Requirement:** Octopus shall run on Linux (primary), macOS (development), and Windows (via WSL).
**Verification:** CI matrix across OS versions.

---

### 6.6 COMPATIBILITY

#### NFR-CMP-001: Backward Compatibility
**Category:** Co-existence
**Requirement:** v3.1.0 APIs shall be backward-compatible with v3.0.0 clients.
**Verification:** v3.0.0 client test suite passes against v3.1.0 server.

#### NFR-CMP-002: Milvus Version Compatibility
**Category:** Interoperability
**Requirement:** Code shall support Milvus 2.4.x and 2.5.x.
**Verification:** Test against both versions.

#### NFR-CMP-003: Browser Compatibility
**Category:** Interoperability
**Requirement:** ARM-2/3 shall support Chromium, Firefox, and WebKit.
**Verification:** E2E tests on all three engines.

#### NFR-CMP-004: Export Format Compatibility
**Category:** Interoperability
**Requirement:** Exported files shall open correctly in Excel 2016+, Google Sheets, pandas, and LibreOffice.
**Verification:** Manual validation.

#### NFR-CMP-005: MCP Protocol Compatibility
**Category:** Interoperability
**Requirement:** MCP tools shall conform to Model Context Protocol 2025-03-26 specification.
**Verification:** MCP inspector validation.

---

### 6.7 USABILITY

#### NFR-USB-001: Template Discoverability
**Category:** Appropriateness Recognizability
**Requirement:** Template registry shall be searchable by category, website name, and data type.
**Verification:** User test: find "Amazon reviews" template in <3 clicks.

#### NFR-USB-002: Error Messages
**Category:** User Error Protection
**Requirement:** Octopus errors shall include actionable remediation (e.g., "CAPTCHA detected; enable solver in settings").
**Verification:** Review error message catalog.

#### NFR-USB-003: Dashboard HITL Queue
**Category:** Operability
**Requirement:** Dashboard shall display pending review items with preview and approve/reject actions.
**Verification:** UI test with simulated pending items.

#### NFR-USB-004: MCP Tool Descriptions
**Category:** Learnability
**Requirement:** MCP tool descriptions shall clearly explain parameters, expected output, and example usage.
**Verification:** Documentation review.

#### NFR-USB-005: Report Readability
**Category:** Appropriateness Recognizability
**Requirement:** Deep research reports shall be readable by non-technical stakeholders; include executive summary.
**Verification:** User test with business stakeholder.

---

## 7. INTERFACE REQUIREMENTS

### 7.1 User Interfaces

| Interface | Technology | Purpose |
|-----------|-----------|---------|
| Dashboard — HITL Queue | Lit 3 + Tailwind | Review uncertain extractions |
| Dashboard — Template Browser | Lit 3 + Tailwind | Search and preview templates |
| Dashboard — Research Viewer | Lit 3 + Tailwind | View deep research reports |

### 7.2 Hardware Interfaces

| Interface | Specification |
|-----------|--------------|
| GPU (optional) | NVIDIA GPU for Milvus CAGRA indexing; Whisper transcription |
| SSD | Milvus data nodes require NVMe SSD for index storage |

### 7.3 Software Interfaces

| Interface | Protocol | Purpose |
|-----------|----------|---------|
| Milvus | gRPC (port 19530) | Vector storage and search |
| Milvus (HTTP) | REST (port 9091) | Monitoring and admin |
| FlareSolverr | HTTP (port 8191) | Cloudflare bypass |
| Browserless | WebSocket (port 3000) | Managed browser pool |
| CAPTCHA Solvers | REST API | Image/text CAPTCHA solving |
| Proxy Providers | HTTP/SOCKS5 | Rotating proxies |
| Google Sheets | REST API (OAuth2) | Export destination |
| S3 / GCS | REST API (fsspec) | Export destination |

### 7.4 Communication Interfaces

| Interface | Protocol | Purpose |
|-----------|----------|---------|
| Kafka | TCP (port 9092) | Octopus telemetry events |
| Temporal | gRPC (port 7233) | Workflow orchestration |

---

## 8. DATA REQUIREMENTS

### 8.1 Data Models

#### Milvus Collection: `voyant_documents`

| Field | Type | Constraints |
|-------|------|-------------|
| id | INT64 | Primary key, auto_id |
| doc_id | VARCHAR(256) | Unique per tenant |
| tenant_id | VARCHAR(64) | Partition key |
| content | VARCHAR(65535) | Full text |
| embedding | FLOAT_VECTOR(1536) | HNSW index, COSINE |
| sparse_embedding | SPARSE_VECTOR | Inverted index |
| metadata | JSON | Dynamic fields |
| source_type | VARCHAR(32) | Indexed |
| created_at | INT64 | Unix timestamp |

#### Octopus Template Registry

| Field | Type | Constraints |
|-------|------|-------------|
| template_id | VARCHAR(64) | Primary key |
| name | VARCHAR(256) | Human-readable |
| category | VARCHAR(64) | E-commerce, Maps, etc. |
| arm | VARCHAR(32) | ARM type |
| config | JSON | Full OctopusRequest |
| version | INT | Semantic versioning |
| author | VARCHAR(128) | Creator |
| verified | BOOL | Officially tested |

#### Deep Research Report

| Field | Type | Constraints |
|-------|------|-------------|
| report_id | UUID | Primary key |
| tenant_id | VARCHAR(64) | Tenant scoping |
| query | TEXT | Original question |
| breadth | INT | Configured breadth |
| depth | INT | Configured depth |
| confidence_score | FLOAT | 0.0-1.0 |
| sources_consulted | INT | Total URLs fetched |
| report_markdown | TEXT | Generated report |
| evidence_json | JSON | Raw evidence chunks |
| created_at | TIMESTAMP | Generation time |

### 8.2 Data Retention

| Data Type | Retention Period | Action |
|-----------|-----------------|--------|
| Vector embeddings | 365 days | Auto-prune by `created_at` |
| Octopus artifacts | 90 days | Move to cold storage |
| Deep research reports | 365 days | Archive after 90 days |
| Audit logs | 2555 days (7 years) | Immutable append-only |
| Proxy logs | 30 days | Anonymize IP addresses |

---

## 9. QUALITY REQUIREMENTS

### 9.1 ISO/IEC 25010 Quality Characteristics

| Characteristic | Target | Measurement |
|----------------|--------|-------------|
| Functional Suitability | 100% of MUST requirements | Requirement traceability matrix |
| Performance Efficiency | p99 latency < 50ms (vectors), < 2s (scrape) | Load testing |
| Compatibility | Backward compatible with v3.0.0 | Integration tests |
| Usability | Dashboard tasks completable in <5 clicks | User testing |
| Reliability | 99.9% uptime | Uptime monitoring |
| Security | Zero critical vulnerabilities | Penetration test + SAST |
| Maintainability | 80% test coverage | pytest-cov |
| Portability | Deployable on Docker, K8s, AWS, GCP, Azure | Deployment tests |

---

## 10. COMPLIANCE REQUIREMENTS

### 10.1 Regulatory Compliance

| Regulation | Requirement | Verification |
|------------|-------------|--------------|
| GDPR | PII stripping, data minimization, right to erasure | Audit + legal review |
| CCPA | Data retention limits, consumer access | Audit + legal review |
| SOC 2 Type II | Access controls, audit trails, change management | Auditor assessment |
| ISO 27001 | Risk assessment, security controls | Internal audit |

### 10.2 Ethical Compliance

| Principle | Requirement |
|-----------|-------------|
| robots.txt | Always respected unless explicitly overridden by agent |
| Rate limiting | Never exceed reasonable request frequency |
| Attribution | All research findings cite original sources |
| Fair use | Content extraction limited to 10,000 chars |
| Transparency | Agent is informed when CAPTCHA solving is used |

---

## 11. RISK AND ASSUMPTIONS

### 11.1 Assumptions

| ID | Assumption |
|----|-----------|
| ASM-1 | Milvus 2.4+ will remain actively maintained by LF AI |
| ASM-2 | Proxy providers (Bright Data, Oxylabs) will maintain API stability |
| ASM-3 | CAPTCHA solving services will remain commercially available |
| ASM-4 | Target websites will not implement AI-undetectable anti-bot measures |
| ASM-5 | SearXNG/Brave Search will remain accessible without authentication |

### 11.2 Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| RSK-1 | Milvus cluster complexity exceeds team capacity | Medium | High | Start with standalone; hire Milus SRE if scaling |
| RSK-2 | Anti-bot measures make scraping unreliable | High | Medium | Pluggable provider model; rapid provider switching |
| RSK-3 | CAPTCHA solving costs exceed budget | Medium | Medium | Per-tenant billing; agent-configurable limits |
| RSK-4 | Template maintenance burden | Medium | Low | Community registry; automated health checks |
| RSK-5 | Deep research generates false information | Medium | High | Cross-validation; confidence scoring; human review |
| RSK-6 | Proxy credential compromise | Low | High | Vault integration; regular rotation; audit logging |

---

## 12. APPENDICES

### Appendix A: Requirement Traceability Matrix

| Requirement | Module | Test Case | Status |
|-------------|--------|-----------|--------|
| FR-MIL-001 | infra/standalone/docker-compose.yml | test_milvus_deploy | Planned |
| FR-MIL-002 | apps/search/lib/milvus_store.py | test_milvus_schema | Planned |
| FR-MIL-003 | apps/search/lib/milvus_store.py | test_tenant_isolation | Planned |
| FR-MIL-004 | apps/search/lib/milvus_store.py | test_hnsw_index | Planned |
| FR-MIL-005 | tests/search/ | test_search_latency | Planned |
| FR-OCT-001 | apps/scraper/octopus/dispatcher.py | test_dispatcher_routing | Planned |
| FR-OCT-002 | apps/scraper/octopus/arms/arm_static.py | test_arm_static | Planned |
| FR-OCT-003 | apps/scraper/octopus/arms/arm_dynamic.py | test_arm_dynamic | Planned |
| FR-OCT-004 | apps/scraper/octopus/arms/arm_evasion.py | test_arm_evasion | Planned |
| FR-OCT-011 | apps/scraper/octopus/auto_detect.py | test_auto_detect | Planned |
| FR-OCT-012 | apps/scraper/octopus/proxy_pool.py | test_proxy_rotation | Planned |
| FR-DRS-001 | apps/scraper/deep_research/workflow.py | test_recursive_loop | Planned |
| FR-DRS-006 | apps/scraper/deep_research/credibility/ | test_source_score | Planned |

### Appendix B: MCP Tool Registry (New Tools)

| Tool | Category | Description |
|------|----------|-------------|
| `scrape.auto_detect` | Octopus | Auto-detect and extract data from URL |
| `scrape.template` | Octopus | Run pre-built scraping template |
| `scrape.workflow` | Octopus | Execute multi-step scraping workflow |
| `scrape.template.list` | Octopus | List available templates |
| `deep_research` | Research | Execute recursive deep research |
| `deep_research.status` | Research | Check research job status |
| `deep_research.report` | Research | Retrieve completed report |
| `vector.hybrid_search` | Search | Hybrid dense + sparse search |
| `vector.index_batch` | Search | Batch index documents |
| `export.gsheet` | Export | Export data to Google Sheets |
| `export.s3` | Export | Export data to S3 |

### Appendix C: ISO 25010 Compliance Checklist

| Characteristic | Status | Evidence |
|----------------|--------|----------|
| Functional Suitability | ☐ | Traceability matrix |
| Performance Efficiency | ☐ | Load test results |
| Compatibility | ☐ | Integration test results |
| Usability | ☐ | User test results |
| Reliability | ☐ | Uptime metrics |
| Security | ☐ | Penetration test report |
| Maintainability | ☐ | Test coverage report |
| Portability | ☐ | Deployment test results |

---

*End of Document*
