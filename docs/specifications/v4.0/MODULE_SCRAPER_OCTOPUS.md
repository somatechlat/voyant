# Scraper Octopus Module — Deep Design Document

**Document ID:** VOYANT-DESIGN-SCRAPER-OCTOPUS-4.0
**Version:** 4.0.0
**Date:** 2026-09-05
**Status:** Draft for Review
**Classification:** Internal

---

## Table of Contents

1. [Current Implementation (Deep)](#1-current-implementation-deep)
2. [Octoparse Comparison](#2-octoparse-comparison)
3. [Bright Data / ScrapingBee Comparison](#3-bright-data--scrapingbee-comparison)
4. [Improvements Over All Competitors](#4-improvements-over-all-competitors)
5. [Anti-Bot Engine Design](#5-anti-bot-engine-design)
6. [Visual Builder Design](#6-visual-builder-design)
7. [Template Engine Design](#7-template-engine-design)
8. [Complete API Design (v4.0)](#8-complete-api-design-v40)
9. [Performance Targets](#9-performance-targets)

---

## 1. Current Implementation (Deep)

### 1.1 OCTOPUS Architecture Overview

The Scraper Octopus is a multi-arm scraping engine modeled after an octopus metaphor: each arm represents a specialized scraping strategy, dispatched by a central coordinator. The system is organized as:

```
OctopusDispatcher
├── ARM-1: Static       (httpx + parsel)
├── ARM-2: Dynamic      (Playwright + stealth)
├── ARM-3: Evasion      (curl-cffi / camoufox)
├── ARM-4: Crawl        (Scrapy)
├── ARM-5: API Intercept(Playwright XHR capture)
├── ARM-6: Document     (pdfplumber + unstructured)
├── ARM-7a: OCR         (Tesseract)
├── ARM-7b: Transcribe  (Whisper)
└── ARM-8: Archive      (Playwright deep archive)
```

**Key Architectural Principle: Agent-Tool Separation.** The Octopus is a pure execution engine. An external agent (LLM or programmatic) provides ALL intelligence — URLs, selectors, options. The Octopus executes mechanically. This separation means the scraper contains zero LLM integration and zero decision logic.

**Dispatcher Pipeline** (`apps/scraper/octopus/dispatcher.py`):

Every request follows this path:
1. **SSRF Validation** — `validate_url()` from `security.py` blocks internal IPs, metadata endpoints, and bypass techniques
2. **Tenant Quota Check** — `require_quota()` enforces per-tenant daily and concurrent job limits
3. **Usage Recording** — `record_usage()` increments counters before execution
4. **Executor Resolution** — Lazy-loaded ARM modules via `_get_arm_executors()`; each ARM is independently importable so missing optional dependencies (e.g., camoufox) degrade gracefully
5. **Circuit Breaker Protection** — `get_circuit_breaker(f"octopus_arm_{arm}")` wraps execution; opens after consecutive failures
6. **Execution with Timeout** — `asyncio.wait_for(executor, timeout=request.timeout_seconds)`
7. **Artifact Storage** — Successful results stored via `store_artifact()` for downstream consumption

**Schemas** (`apps/scraper/octopus/schemas.py`):

- `OctopusARM` — StrEnum of 9 arm identifiers
- `OctopusRequest` — Unified input with 40+ fields covering all arms; uses `extra="forbid"` to prevent silent parameter injection
- `OctopusResult` — Unified output with success/failure, HTML, extracted fields, captured JSON, document text, OCR blocks, transcription segments, crawl pages, archive manifest, and artifact metadata
- `BrowserAction` — Browser automation step (click/fill/scroll/wait/screenshot/hover/select/keyboard)
- `CrawledPage` — Single page result from ARM-4

---

### 1.2 Nine OCTOPUS Arms — Deep Detail

#### ARM-1: Static (`arm_static.py`)

**Technology:** `httpx` (async HTTP) + `parsel` (CSS/XPath extraction)

**When Dispatched:** When the target page is server-rendered HTML with no JavaScript rendering requirements. Fastest arm — no browser overhead.

**Execution Flow:**
1. Creates `httpx.AsyncClient` with configurable TLS verification (certifi CA bundle or `False`)
2. Sends GET request with configurable `User-Agent` and `Accept-Language` headers
3. Extracts named fields via CSS selectors (`sel.css(selector).getall()`) and XPath selectors (`sel.xpath(selector).getall()`)
4. Extracts metadata: `<title>`, OpenGraph tags (og:title, og:description, og:image), canonical link, Schema.org JSON-LD (`<script type="application/ld+json">`)
5. Optionally extracts all `<a href>` links if `extract_links=True`

**Returns:** `OctopusResult` with `html`, `status_code`, `response_headers`, `extracted_fields`, `page_metadata`, `discovered_links`.

**Latency:** ~0.5–2s for most pages (single HTTP request).

---

#### ARM-2: Dynamic (`arm_dynamic.py`)

**Technology:** `playwright.async_api` + `playwright-stealth` (optional)

**When Dispatched:** For JavaScript-rendered SPAs, React/Vue/Angular apps, or pages requiring interaction before data is available.

**Execution Flow:**
1. Launches headless Chromium via Playwright
2. Applies stealth patches (`stealth_async`) to evade bot detection (navigator.webdriver removal, plugin spoofing, etc.)
3. Optionally blocks image/media/font resources via `page.route("**/*", ...)` for speed
4. Navigates to URL with configurable `wait_until` (domcontentloaded, networkidle, load, commit)
5. Optionally waits for a specific CSS selector via `wait_for_selector()`
6. Optionally scrolls to bottom via `window.scrollTo(0, document.body.scrollHeight)`
7. Applies settle delay (`settle_ms`)
8. Executes browser action sequence (click, fill, scroll, wait, screenshot, hover, select, keyboard)
9. Extracts fields using `HTMLParser` (lxml-based CSS/XPath)
10. Extracts metadata and links

**Browser Actions** support 8 types: `click`, `fill`, `scroll`, `wait`, `screenshot`, `hover`, `select`, `keyboard`.

**Latency:** ~3–15s depending on JS complexity and wait times.

---

#### ARM-3: Evasion (`arm_evasion.py`)

**Technology:** Two sub-modes:
- **curl-cffi** — HTTP client with TLS fingerprint impersonation (mimics Chrome, Safari, Edge TLS handshakes)
- **Camoufox** — Firefox-based stealth browser with anti-fingerprinting

**When Dispatched:** When the target site has anti-bot protection (Cloudflare, Akamai, DataDome, etc.) and ARM-2 would be detected.

**curl-cffi Mode:**
1. Uses `curl_cffi.requests.AsyncSession` with `impersonate="chrome124"` (configurable)
2. Supports proxy passthrough: `proxies = {"http": proxy_url, "https": proxy_url}`
3. TLS fingerprint matches real browser, bypassing JA3/JA4 fingerprint checks
4. After fetch, extracts fields via `HTMLParser`

**Camoufox Mode:**
1. Uses `AsyncCamoufox` — a hardened Firefox fork with random Canvas/WebGL/AudioContext fingerprints
2. Supports proxy configuration via `proxy={"server": proxy_url}`
3. Renders JavaScript like a real browser while appearing as a genuine user

**Latency:** curl-cffi ~1–3s (HTTP-only, no JS); Camoufox ~5–20s (full browser).

---

#### ARM-4: Crawl (`arm_crawl.py`)

**Technology:** `Scrapy` via a custom `ScrapyClient` wrapper

**When Dispatched:** For large-scale site crawling — following links, respecting robots.txt, depth control.

**Execution Flow:**
1. Validates all `start_urls` against SSRF rules
2. Runs Scrapy in a background thread (`asyncio.to_thread`) since `CrawlerProcess.start()` is blocking
3. Supports sitemap crawling via `crawl_sitemap()`
4. Configurable: `concurrent_requests` (default 16), `download_delay` (0.5s), `obey_robots`, `max_depth`, `follow_links`

**Returns:** `OctopusResult` with `crawled_pages` (list of `CrawledPage`) and `total_pages` count.

**Latency:** Minutes for large sites; seconds for small crawls.

---

#### ARM-5: API Intercept (`arm_api_intercept.py`)

**Technology:** Playwright with network response monitoring

**When Dispatched:** When the target loads data via XHR/Fetch API calls and the user wants the raw JSON rather than rendered HTML.

**Execution Flow:**
1. Launches Playwright with `page.on("response", _on_response)` listener
2. For every XHR/Fetch response:
   - Checks `resource_type` is `xhr` or `fetch`
   - Filters by `capture_url_contains` patterns
   - Checks `content-type` header for `json`
   - Enforces `capture_max_bytes` (default 512KB) and `capture_max_items` (default 25)
   - Parses JSON and appends to `captured_json` list
3. After page load + settle, awaits all pending capture tasks
4. Returns both `html` (page content) and `captured_json` (list of intercepted API responses)

**Returns:** `OctopusResult` with `captured_json` — each entry has `url`, `status`, `content_type`, `body`.

**Use Case:** Reverse-engineering hidden APIs, capturing search results loaded via AJAX, extracting data from SPAs that fetch JSON endpoints.

---

#### ARM-6: Document (`arm_document.py`)

**Technology:** `pdfplumber` + `unstructured` (auto-partition)

**When Dispatched:** When the URL points to a PDF or Office document.

**Execution Flow:**
1. Downloads remote documents to a temp file via httpx (with SSRF validation)
2. Parses with `PDFParser` (Tika → pdfplumber fallback chain)
3. Attempts `unstructured.partition.auto.partition()` for broader format support
4. Extracts: text, metadata, tables (via pdfplumber)
5. Cleans up temp files

**Returns:** `OctopusResult` with `document_text`, `document_tables`, `document_metadata`.

---

#### ARM-7a: OCR (`arm_ocr.py`)

**Technology:** Tesseract via `pytesseract` + Pillow preprocessing

**When Dispatched:** When the target contains images with text that needs extraction (screenshots, scanned documents, infographics).

**Execution Flow:**
1. Fetches image bytes from URL (or reads local file)
2. Loads with Pillow, applies preprocessing (contrast enhancement ×1.5, sharpen filter)
3. Runs `pytesseract.image_to_data()` for structured extraction with bounding boxes
4. Filters word blocks by `ocr_confidence_threshold` (default 60%)
5. Returns full text + individual word blocks with coordinates and confidence

**Returns:** `OctopusResult` with `ocr_text` (full text) and `ocr_blocks` (list of word dicts with text, left, top, width, height, confidence).

---

#### ARM-7b: Transcribe (`arm_transcribe.py`)

**Technology:** OpenAI Whisper (local model)

**When Dispatched:** When the target contains audio/video that needs transcription (podcasts, lectures, interviews).

**Execution Flow:**
1. Downloads media file to temp (supports mp3, mp4, wav, webm)
2. Loads Whisper model (`tiny`/`base`/`small`/`medium`/`large`)
3. Runs `model.transcribe(temp_path, language=request.language)`
4. Formats output as plain text, JSON, or SRT subtitles
5. Cleans up temp files

**Returns:** `OctopusResult` with `transcription`, `transcription_language`, `transcription_segments`.

---

#### ARM-8: Archive (`arm_archive.py`)

**Technology:** Playwright + httpx

**When Dispatched:** For deep archival scraping of interactive sites — clicking through tabs, downloading linked files.

**Execution Flow:**
1. Navigates to URL, captures baseline HTML
2. Iterates through `interaction_selectors` — clicks each, waits for DOM to settle, captures HTML state
3. Finds all `<a>` links matching `download_patterns`
4. Downloads matching files to `target_dir/files/`
5. Handles JavaScript-based download links (e.g., `javascript:download('file.pdf')`)
6. Writes `deep_archive_manifest.json` with all states and downloads

**Returns:** `OctopusResult` with `archive_manifest`, `files_downloaded`, `interaction_states`.

---

### 1.3 Deep Research v2 Pipeline

**Location:** `apps/scraper/deep_research/`

**Key Principle: Zero LLM usage.** All algorithms are deterministic and reproducible. The pipeline uses TF-IDF sentence salience, MinHash deduplication, and domain credibility databases instead of language models.

**10-Step Pipeline:**

#### Step 1: Query Expansion
**Agent:** `QueryGenerator`
**Algorithm:**
1. Tokenize input query, remove stopwords (English + Spanish, 300+ words)
2. Select templates from 13 predefined patterns: `"{query}"`, `"{query} overview"`, `"{query} latest research"`, `"{query} statistics"`, `site:gov {query}`, `filetype:pdf "{query}"`, etc.
3. Return `breadth` unique sub-queries

#### Step 2: Multi-Engine Search
**Activity:** `dr_search_all_engines`
**Engines (parallel):**
- **SearXNG** — Sovereign, zero-cost, zero-tracking self-hosted meta-search engine (Docker)
- **Brave Search** — Commercial API (requires `serper_api_key`)
- **Google CSE** — Custom Search Engine (requires `google_cse_api_key` + `google_cse_cx`)

Results are normalized to `SearchResultItem(url, title, snippet, engine, rank)` and deduplicated by URL.

#### Step 3: Parallel Content Fetch
**Activity:** `dr_fetch_octopus`
**Dispatches:** Octopus ARM-2 (dynamic) or ARM-3 (evasion) based on `arm="auto"` preference (defaults to evasion for higher bypass rate).
**Fallback:** Legacy `ScrapeActivities.fetch_page` if Octopus is unavailable.

#### Step 4: Content Extraction
**Agent:** `ContentExtractor`
**Fallback chain (priority order):**
1. **trafilatura** — Best for article/main content extraction; returns clean text
2. **readability-lxml** — Mozilla Readability algorithm port; returns HTML summary
3. **newspaper3k** — Article extraction library; good for news content
4. **crawl4ai** — WebCrawler-based extraction with markdown output
5. **Fallback** — Strip HTML tags via regex, return raw text (capped at 50KB)

Each method is independently importable with availability flags. If a library is missing, it's silently skipped.

#### Step 5: Source Scoring
**Agent:** `SourceScorer`
**Algorithm:**
- **Credibility** — Lookup in `DomainCredibilityDB`: tiers from 0.95 (academic: arxiv.org, nature.com) to 0.10 (low quality). Covers ~100 explicit domains + rule-based classification (.gov → 0.90, .edu → 0.85, etc.)
- **Freshness** — Regex-based year extraction from text; linear decay over 5 years (1.0 = today, 0.0 = 5+ years old)
- **Total score** — `credibility × (0.6 + 0.4 × freshness)`

Sources below `min_source_score` (default 0.15) are filtered out.

#### Step 6: Deduplication
**Algorithm:** MinHash/LSH
1. Convert each document to character 5-shingles
2. Compute 64-hash MinHash signatures using MD5
3. Estimate Jaccard similarity between signatures
4. Group documents with similarity ≥ `dedup_threshold` (default 0.85)
5. Keep one representative per group, remove near-duplicates

#### Step 7: Synthesis
**Agent:** `Synthesizer`
**Algorithm (deterministic TF-IDF):**
1. Tokenize all sentences across all sources
2. Compute inverse document frequency (IDF) over the corpus
3. Score each sentence by TF-IDF keyword density + uniqueness
4. Cluster top-scoring sentences by Jaccard token overlap (threshold 0.25)
5. Emit `Finding` objects with `EvidenceChunk` attribution and confidence scores
6. Generate follow-up queries from novel keywords in top findings

#### Step 8: Recursive Follow-up
If `depth > 1`, follow-up queries from Step 7 are used as inputs for another iteration of Steps 2–7. This enables deeper exploration of sub-topics discovered in initial research.

#### Step 9: Cross-Reference Validation
**Agent:** `CrossValidator`
**Algorithm:**
1. For each finding, compute character 4-grams
2. Check n-gram overlap against all source texts (Jaccard threshold 0.15)
3. Count unique domains supporting each claim
4. Mark as `cross_validated=True` if ≥2 independent domains support the claim
5. Compute confidence: `min(1.0, domains × 0.25 + avg_overlap × 0.5)`

#### Step 10: Report Generation
**Agent:** `ReportGenerator`
Produces a deterministic Markdown report with:
- Executive summary (URLs processed, duplicates removed, findings count, validation rate)
- Findings section (each with claim, confidence, evidence chunks, supporting sources)
- Citations table (domain, title, URL, credibility score)
- Methodology section (10-step pipeline description)

**Pydantic Schemas:**
- `ResearchConfig` — Input config (query, breadth 1–10, depth 1–5, tenant_id, max_urls_per_query, min_source_score, dedup_threshold, require_cross_validation)
- `Finding` — claim, evidence_chunks, supporting_sources, confidence_score, cross_validated
- `Citation` — url, title, domain, credibility_score, freshness_score
- `ResearchReport` — markdown, executive_summary, findings, citations, confidence_score
- `SynthesisOutput` — findings, citations, follow_up_queries

---

### 1.4 Template System

**51 pre-built templates** across **14 categories**:

| Category | Count | Examples |
|----------|-------|---------|
| E-Commerce | 10 | Amazon (search/details/reviews), eBay, Walmart, Alibaba, AliExpress, Shopify, Etsy, Best Buy |
| Social Media | 11 | Twitter/X (search/profile), YouTube (search/details), Reddit (search/subreddit), LinkedIn (profile/company), TikTok, Instagram, Facebook |
| Maps | 3 | Google Maps (listings/reviews/details) |
| News | 3 | Google News, any news site article, Hacker News |
| Finance | 2 | Yahoo Finance stock data, Crunchbase company data |
| Jobs | 3 | Indeed (search/details), LinkedIn Jobs |
| Real Estate | 3 | Zillow (listings/details), Realtor.com |
| Travel | 3 | Booking.com, Google Flights, TripAdvisor |
| Education | 2 | Coursera, Google Scholar |
| Developer | 3 | GitHub repos, npm packages, Stack Overflow |
| Lead Generation | 3 | Email extraction, Yellow Pages, Yelp |
| Directory | 2 | Yellow Pages directory, Clutch.co |
| Search Engine | 2 | Google search, Bing search |
| Universal | 1 | Any page to Markdown |

**Template Format:**
```json
{
  "name": "Amazon Product Search",
  "category": "ecommerce",
  "site_pattern": "amazon.com",
  "engine": "playwright",
  "selectors": {"title": "h2 a span", "price": ".a-price .a-offscreen"},
  "workflow": [
    {"action": "navigate", "url": "https://amazon.com/s?k={{search_query}}"},
    {"action": "scroll", "times": 3},
    {"action": "extract"}
  ],
  "parameters": [{"name": "search_query", "type": "string", "required": true}],
  "output_fields": ["title", "price", "rating", "url", "image"]
}
```

**Parameter Substitution:** `{{param_name}}` placeholders in workflow URLs and selectors are replaced at runtime via `_substitute_workflow()` — JSON serialize → string replace → JSON deserialize.

**Template SDK** (`apps/scraper/template_sdk.py`):
- `TEMPLATE_SCHEMA` — Full JSON Schema for validation
- `TemplateBuilder` — Fluent builder pattern: `.category()`, `.site()`, `.navigate()`, `.scroll()`, `.extract()`, `.paginate()`, `.anti_bot()`, `.output_field()`, `.tag()`, `.build()`
- `validate_template()` — Validates against schema, returns error list
- `load_template()` / `load_templates_from_dir()` — JSON file loading
- `template_to_mcp_params()` — Converts template parameters to MCP tool format

**14 Supported Workflow Actions:** `navigate`, `click`, `scroll`, `wait`, `extract`, `enter_text`, `hover`, `loop`, `condition`, `back`, `new_tab`, `close_popup`, `screenshot`, `download`

**5 Pagination Types:** `next_button`, `page_numbers`, `load_more`, `infinite_scroll`, `url_pattern`

---

### 1.5 Content Extraction Chain

**Deep Research uses:** trafilatura → readability → newspaper → crawl4ai → regex fallback

**Template-based scraping uses:** Playwright page.query_selector_all() → inner_text()

**Document parsing uses:** Apache Tika → pdfplumber (fallback)

**OCR uses:** Tesseract with Pillow preprocessing (contrast ×1.5, sharpen)

**Transcription uses:** OpenAI Whisper (local model: tiny/base/small/medium/large)

---

### 1.6 Security: SSRF Protection

**Location:** `apps/scraper/security.py`

**Protection Layers:**

1. **Scheme Validation** — Only `http` and `https` allowed (blocks `file://`, `ftp://`, `gopher://`)
2. **Hostname Blocklist** — `localhost`, `127.0.0.1`, `::1`, `0.0.0.0`, AWS metadata (`169.254.169.254`), GCP metadata (`metadata.google.internal`), Azure metadata
3. **IP Range Blocklist** — 16 CIDR ranges: loopback (127.0.0.0/8), private (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), link-local (169.254.0.0/16), carrier-grade NAT (100.64.0.0/10), multicast, reserved, IPv6 equivalents
4. **DNS Resolution** — `resolve_hostname()` resolves hostnames to IPs and checks against blocked ranges
5. **Extension Blocklist** — Blocks `.exe`, `.dll`, `.bat`, `.sh`, `.js`, `.php`, `.jsp`, `.asp`, etc.
6. **Credential Bypass Detection** — Detects `http://evil.com@169.254.169.254` patterns
7. **Decimal/Octal/Hex IP Detection** — Detects `http://2130706433/` (decimal for 127.0.0.1)
8. **URL Length Limit** — Max 2048 characters
9. **Batch Limit** — Max 1000 URLs per request
10. **Selector Sanitization** — Removes `javascript:` and `data:` URIs; max 1000 chars

**Rate Limiting:**
- Default tier: 100 requests/hour, 1000 URLs/request, 10 concurrent jobs
- Premium tier: 1000 requests/hour, 10000 URLs/request, 50 concurrent jobs

---

### 1.7 MCP Tools (7 Existing)

| Tool | Name | Description |
|------|------|-------------|
| 1 | `scrape.fetch` | Fetch web page with engine selection, scroll, wait, JSON capture |
| 2 | `scrape.extract` | Extract structured data from HTML via CSS/XPath selectors |
| 3 | `scrape.ocr` | Run Tesseract OCR on image URLs |
| 4 | `scrape.parse_pdf` | Parse PDF with optional table extraction |
| 5 | `scrape.transcribe` | Transcribe audio/video via Whisper |
| 6 | `scrape.deep_archive` | Interactive deep archival with click-through and download |
| 7 | `voyant.templates.execute` | UPTP Core Router — dispatches any template execution |

All MCP tools are thin bridges to activity classes — zero intelligence, pure mechanical delegation.

---

### 1.8 Visual Scraping System

**Location:** `apps/scraper/visual/`

**Components:**

#### `auto_detect.py` — AutoDetectEngine
Deterministic DOM analysis (no ML) that identifies:
- **Lists** — Repeating DOM patterns (3+ children with same tag+class); extracts field definitions from first item; returns sample data
- **Tables** — `<table>` structures with headers and rows
- **Pagination** — Next buttons (10 XPath patterns), page numbers, load-more buttons (7 patterns), infinite scroll indicators
- **Forms** — `<form>` elements with text/search/email inputs and submit buttons
- **Load More** — Infinite scroll containers and load-more buttons

Returns `DetectResult` with detected structures, selectors, sample data, and field definitions.

#### `browser_manager.py` — BrowserManager + BrowserSession
Server-side Playwright browser management:
- **BrowserSession** — Wraps a Playwright page with navigate, click (coordinates and selectors), scroll, hover, enter_text, extract_data, evaluate JS
- **PageState** — Captures URL, title, base64 PNG screenshot, viewport dimensions, scroll position, all interactive elements
- **Element Detection** — JavaScript-based detection of all interactive elements (`a`, `button`, `input`, `select`, `textarea`, `[onclick]`, `[role="button"]`, `[tabindex]`) with CSS selectors, XPath, bounding boxes, and attributes
- **BrowserManager** — Singleton session manager with create/get/close operations

#### `consumer.py` — ScraperConsumer (WebSocket)
Django Channels WebSocket consumer connecting frontend to Playwright:
- Actions: `start`, `navigate`, `screenshot`, `click`, `click_element`, `scroll`, `hover`, `enter_text`, `extract`, `detect`, `back`, `forward`, `close`
- Auto-detect runs after every navigation
- Returns `page_state` with full element list on every action

---

### 1.9 Parsing Modules

#### `html_parser.py`
lxml-based HTML parser supporting CSS selectors (including pseudo-elements `::text`, `::attr(href)`, `::html`), XPath selectors, and nested extraction (repeating item patterns with field mapping).

#### `pdf_parser.py`
Dual-engine: Apache Tika first (broad format support), pdfplumber fallback (native text extraction). Table extraction via pdfplumber.

#### `ocr_processor.py`
Tesseract OCR with image preprocessing (RGB conversion, contrast ×1.5, sharpen). Supports plain text and structured extraction (bounding boxes + confidence per word). Batch processing.

#### `tika_client.py`
Apache Tika REST API client for universal document extraction (1000+ formats). Supports text extraction, metadata, language detection, and MIME type listing.

---

### 1.10 Temporal Workflow Orchestration

**`workflow.py`** — `ScrapeWorkflow`:
1. Fetch page activity (5min timeout)
2. Extract data activity (1min timeout)
3. Optional OCR activity (5min timeout)
4. Optional transcription activity (10min timeout)
5. Store artifact activity (2min timeout)
6. Finalize job activity (1min timeout)

**`deep_research/workflow.py`** — `DeepResearchWorkflowV2`:
Orchestrates the full 10-step deep research pipeline with retry policies (3 attempts, exponential backoff).

---

## 2. Octoparse Comparison

### 2.1 Feature-by-Feature Matrix (60 Features)

| # | Feature | Octoparse | Voyant v3.0 | Voyant v4.0 | Notes |
|---|---------|-----------|-------------|-------------|-------|
| 1 | No-Code Visual Builder | ✅ Full | ❌ | 🔄 Planned | Octoparse drag-and-drop is polished |
| 2 | Point-and-Click Selection | ✅ | 🔄 Partial (WebSocket consumer) | 🔄 Planned | Voyant has backend, needs frontend |
| 3 | Template Library | ✅ 600+ | ✅ 51 | ✅ 200+ target | Octoparse has 10× more templates |
| 4 | AI Auto-Detect | ✅ ML-based | ✅ Deterministic DOM | ✅ Enhanced | Voyant's is faster, more reliable |
| 5 | Static Page Scraping | ✅ | ✅ ARM-1 | ✅ | Parity |
| 6 | JavaScript Rendering | ✅ Chromium | ✅ Playwright | ✅ | Parity |
| 7 | Anti-Bot Evasion | ✅ | ✅ ARM-3 (curl-cffi + camoufox) | ✅ Enhanced | Voyant has dual-mode evasion |
| 8 | CAPTCHA Solving | ✅ AI-powered | ❌ | 🔄 Multi-provider | Octoparse advantage |
| 9 | IP Rotation | ✅ 10K+ residential | 🔄 Basic proxy | 🔄 Planned pool | Octoparse advantage |
| 10 | Browser Fingerprinting | ✅ | ✅ curl-cffi impersonation + camoufox | ✅ Enhanced | Voyant has two approaches |
| 11 | Pagination (Next Button) | ✅ Auto-detect | ✅ Auto-detect (10 patterns) | ✅ | Parity |
| 12 | Infinite Scroll | ✅ | ✅ scroll action | ✅ | Parity |
| 13 | Load More Button | ✅ Auto-detect | ✅ Auto-detect | ✅ | Parity |
| 14 | Login Automation | ✅ Credential storage | 🔄 Cookie support | 🔄 Planned | Octoparse advantage |
| 15 | Form Filling | ✅ | ✅ enter_text action | ✅ | Parity |
| 16 | Dropdown/Select | ✅ | ✅ select action | ✅ | Parity |
| 17 | iFrame Extraction | ✅ | ❌ | 🔄 Planned | Octoparse advantage |
| 18 | Screenshot Capture | ✅ | ✅ ARM-2 screenshot action | ✅ | Parity |
| 19 | Data Export: JSON | ✅ | ✅ | ✅ | Parity |
| 20 | Data Export: CSV | ✅ | ✅ | ✅ | Parity |
| 21 | Data Export: XLSX | ✅ | ❌ | 🔄 Planned | Gap |
| 22 | Data Export: XML | ✅ | ❌ | 🔄 Planned | Gap |
| 23 | Data Export: Database | ✅ PostgreSQL, MySQL, SQL Server, Oracle | ✅ PostgreSQL, MySQL | ✅ | Octoparse has more DB targets |
| 24 | Data Export: Google Sheets | ✅ | ❌ | 🔄 Planned | Gap |
| 25 | JSONL Streaming | ✅ | ❌ | 🔄 Planned | Gap |
| 26 | REST API | ✅ 23 endpoints | ✅ 11 endpoints | ✅ 21+ endpoints | Approaching parity |
| 27 | Scheduling (Cron) | ✅ Built-in | ✅ Temporal | ✅ Cron + Temporal | Voyant has more robust scheduling |
| 28 | Task CRUD | ✅ | ✅ ScrapeJob | ✅ Full CRUD | Parity |
| 29 | Run History | ✅ | ✅ ScrapeJob status | ✅ ScrapeRun model | Parity |
| 30 | Incremental Extraction | ✅ | ❌ | 🔄 Planned | Gap |
| 31 | Parent-Child Tasks | ✅ | ❌ | 🔄 Planned | Gap |
| 32 | Workflow Import/Export | ✅ JSON | ✅ Template JSON | ✅ | Parity |
| 33 | Cloud Execution | ✅ Cloud | ✅ Docker/K8s | ✅ | Parity |
| 34 | Desktop App | ✅ Windows/Mac | ❌ | ❌ | Octoparse advantage |
| 35 | Local Execution | ✅ | ✅ Docker | ✅ | Parity |
| 36 | Concurrent Tasks | ✅ High | ✅ 50+ | ✅ 50+ | Parity |
| 37 | Webhook Notifications | ✅ | ❌ | 🔄 Planned | Gap |
| 38 | Email Notifications | ✅ | ❌ | 🔄 Planned | Gap |
| 39 | API Rate Limiting | ✅ | ✅ Tier-based | ✅ | Parity |
| 40 | Proxy Support | ✅ Residential | ✅ Basic | ✅ Planned pool | Octoparse has larger pool |
| 41 | Custom User-Agent | ✅ | ✅ Configurable | ✅ | Parity |
| 42 | Cookie Management | ✅ | ✅ Browser context | ✅ | Parity |
| 43 | XHR/API Capture | ✅ | ✅ ARM-5 | ✅ | Parity |
| 44 | Document Parsing (PDF) | ✅ | ✅ ARM-6 | ✅ | Parity |
| 45 | OCR | ✅ | ✅ ARM-7a (Tesseract) | ✅ | Parity |
| 46 | Audio/Video Transcription | ❌ | ✅ ARM-7b (Whisper) | ✅ | **Voyant advantage** |
| 47 | Deep Archive | ❌ | ✅ ARM-8 | ✅ | **Voyant advantage** |
| 48 | MCP Agent Tools | ❌ | ✅ 7 tools | ✅ 13+ tools | **Voyant exclusive** |
| 49 | Deep Research Pipeline | ❌ | ✅ 10-step pipeline | ✅ | **Voyant exclusive** |
| 50 | Ontology Integration | ❌ | ❌ | ✅ Auto-detect types | **Voyant exclusive** |
| 51 | Intent Engine Integration | ❌ | ❌ | ✅ NL→scraper | **Voyant exclusive** |
| 52 | Capsule Integration | ❌ | ❌ | ✅ Portable recipes | **Voyant exclusive** |
| 53 | Self-Hosted | ❌ Cloud-only | ✅ Apache 2.0 | ✅ | **Voyant advantage** |
| 54 | Open Source | ❌ | ✅ Apache 2.0 | ✅ | **Voyant advantage** |
| 55 | Multi-Tenant | ❌ | ✅ tenant_id isolation | ✅ | **Voyant advantage** |
| 56 | Circuit Breakers | ❌ | ✅ Per-arm breakers | ✅ | **Voyant advantage** |
| 57 | Temporal Orchestration | ❌ | ✅ Durable workflows | ✅ | **Voyant advantage** |
| 58 | Artifact Store | ❌ | ✅ Content-addressed | ✅ | **Voyant advantage** |
| 59 | Audit Trail | ❌ | ✅ Step-by-step logging | ✅ | **Voyant advantage** |
| 60 | SSRF Protection | ❌ | ✅ 10-layer defense | ✅ | **Voyant advantage** |

### 2.2 What Octoparse Does Better

1. **Visual Builder Polish** — Octoparse's drag-and-drop builder is the industry benchmark. Years of UX refinement make it the easiest tool for non-technical users.

2. **CAPTCHA Solving** — Built-in AI-powered CAPTCHA solving for reCAPTCHA v2/v3, hCaptcha, and Cloudflare Turnstile. Voyant has zero CAPTCHA solving.

3. **Template Library Scale** — 600+ pre-built templates vs Voyant's 51. Covers more edge cases and niche sites.

4. **Desktop Application** — Native Windows/Mac app for local execution without Docker. Voyant is container-only.

5. **IP Pool Size** — 10,000+ residential IPs in their managed pool. Voyant has basic proxy passthrough.

6. **Login Automation** — Encrypted credential storage with session management. Voyant has cookie support only.

7. **Export Breadth** — Google Sheets, XML, JSONL streaming, and 4 database targets vs Voyant's 2 DB targets.

### 2.3 What Voyant Does Better

1. **MCP Agent Integration** — 7 tools (13+ planned) that allow AI agents to orchestrate scraping programmatically. Octoparse has zero agent integration.

2. **Deep Research Pipeline** — 10-step autonomous multi-source research pipeline with source scoring, deduplication, cross-validation, and report generation. No competitor has anything comparable.

3. **Ontology Integration** — Scraping results can automatically create ontology types. Octoparse has no knowledge graph integration.

4. **Self-Hosted with Full Control** — Apache 2.0 license, Docker/K8s deployment, full data sovereignty. Octoparse is cloud-only.

5. **Temporal Orchestration** — Durable, retryable workflow execution with circuit breakers. More robust than Octoparse's execution engine.

6. **Audio/Video Transcription** — Whisper-based transcription of media files. Octoparse cannot transcribe.

7. **Deep Archiving** — Interactive tab-clicking + file downloading for deep archival. Octoparse has no equivalent.

8. **Multi-Tenant Security** — Tenant isolation, SSRF protection, rate limiting, circuit breakers. Octoparse is single-tenant.

---

## 3. Bright Data / ScrapingBee Comparison

### 3.1 Proxy Infrastructure

| Aspect | Bright Data | ScrapingBee | Voyant (Planned) |
|--------|-------------|-------------|-------------------|
| IP Pool Size | 72M+ residential | 10M+ residential | 10K+ (via integrations) |
| Proxy Types | Residential, datacenter, mobile, ISP | Residential, datacenter | Residential (Bright Data/Oxylabs/SmartProxy) |
| Geographic Coverage | 195 countries | 50+ countries | Configurable per provider |
| Rotation Strategy | Per-request, session-based | Per-request | Configurable: per-request, per-session, sticky |
| Management | Bright Data dashboard | ScrapingBee API | Planned: `ScrapeProxy` model with provider, endpoints, rotation_strategy |

**Voyant's Approach:** Rather than building our own proxy network (impractical at scale), Voyant integrates with existing residential proxy providers through a unified `ScrapeProxy` configuration model. The proxy manager will support failover between providers.

### 3.2 CAPTCHA Solving

| Aspect | Bright Data | ScrapingBee | Voyant (Planned) |
|--------|-------------|-------------|-------------------|
| reCAPTCHA v2 | ✅ | ✅ | 🔄 Multi-provider chain |
| reCAPTCHA v3 | ✅ | ✅ | 🔄 |
| hCaptcha | ✅ | ✅ | 🔄 |
| Cloudflare Turnstile | ✅ | ✅ | 🔄 |
| Solve Rate | >95% | >90% | Target: >90% |
| Solving Method | Built-in | Built-in | Planned: 2Captcha → CapSolver → Anti-Captcha chain |

**Voyant's Approach:** A multi-provider CAPTCHA solving chain with automatic fallback. The chain tries the cheapest/fastest provider first and escalates on failure. This provides higher effective solve rates than any single provider.

### 3.3 API Comparison

| Aspect | Bright Data | ScrapingBee | Voyant |
|--------|-------------|-------------|--------|
| API Style | REST + proxy | REST | REST + MCP tools |
| Agent Integration | ❌ | ❌ | ✅ 7 MCP tools (13+ planned) |
| Deep Research | ❌ | ❌ | ✅ 10-step pipeline |
| Template Library | ❌ | ❌ | ✅ 51 templates |
| Visual Builder | ❌ | ❌ | 🔄 Planned |
| Self-Hosted | ❌ | ❌ | ✅ Apache 2.0 |
| Data Storage | ❌ (returns data) | ❌ (returns data) | ✅ ArtifactStore |
| Workflow Orchestration | ❌ | ❌ | ✅ Temporal |
| Multi-Tenant | ❌ | ❌ | ✅ |

**Voyant's Key Differentiator:** Bright Data and ScrapingBee are *infrastructure* — they provide proxy networks and CAPTCHA solving as a service. Voyant is an *application platform* — it provides end-to-end data extraction with agent integration, research pipelines, and knowledge graph connectivity. Voyant can *use* Bright Data as a proxy provider, but Bright Data cannot replace Voyant's application-layer capabilities.

---

## 4. Improvements Over All Competitors

### 4.1 Deep Research Pipeline (Unique to Voyant)

**No competitor has this.** The 10-step deterministic research pipeline:
- Expands queries into multiple parallel sub-queries
- Searches across 3 engines simultaneously (SearXNG + Brave + Google CSE)
- Fetches content via Octopus evasion arms
- Extracts content with 5-library fallback chain
- Scores sources by domain credibility and freshness
- Deduplicates with MinHash/LSH
- Synthesizes findings with TF-IDF sentence salience
- Cross-validates claims against ≥2 independent sources
- Generates structured Markdown reports with citations

**Competitive Impact:** While Octoparse, Bright Data, and ScrapingBee can scrape individual pages, none can autonomously research a topic across dozens of sources, validate findings, and produce a structured report.

### 4.2 MCP Agent Integration (Unique to Voyant)

7 MCP tools allow AI agents to:
- Fetch any web page with browser options
- Extract structured data via CSS/XPath
- Run OCR on images
- Parse PDF documents
- Transcribe audio/video
- Deep-archive interactive sites
- Execute templates with parameters

**Competitive Impact:** Voyant is the only scraping platform with native AI agent integration. Competitors require custom API wrappers.

### 4.3 Ontology Auto-Detect (Unique to Voyant)

When scraping data, Voyant can automatically create ontology types from the extracted structure. Scraping Amazon products → auto-create `Product` type with `title`, `price`, `rating` fields. This feeds directly into the knowledge graph.

**Competitive Impact:** Competitors return raw data. Voyant creates semantic types that integrate with the broader data intelligence platform.

### 4.4 Intent Engine Integration (Unique to Voyant)

Natural language → scraper configuration. "Scrape Amazon product prices for gaming laptops" → generates a complete task with URL template, selectors, and workflow steps.

**Competitive Impact:** While Octoparse has some AI assistance, Voyant's Intent Engine provides full natural language to executable scraper translation.

### 4.5 Capsule Integration (Unique to Voyant)

Scraping recipes can be packaged as portable Capsules — self-contained, version-controlled data extraction configurations that can be shared, versioned, and deployed across environments.

**Competitive Impact:** No competitor offers portable, version-controlled scraping recipes.

### 4.6 Self-Hosted with Full Control

Apache 2.0 license. Docker/K8s deployment. Full data sovereignty. No data leaves your infrastructure.

**Competitive Impact:** Octoparse, Bright Data, and ScrapingBee are all cloud-only. Voyant is the only option for organizations with strict data residency requirements.

---

## 5. Anti-Bot Engine Design

### 5.1 CAPTCHA Solving — Multi-Provider Chain

```
CAPTCHA Detection
    ↓
Provider Chain (ordered by cost/speed):
    1. 2Captcha    — Cheapest, ~$1–3/1000 solves
    2. CapSolver    — Fast, AI-powered
    3. Anti-Captcha — High reliability
    ↓
Solve Result → Inject into page → Continue workflow
```

**Design:**
```python
class CaptchaSolverChain:
    """Multi-provider CAPTCHA solving with automatic fallback."""
    
    providers = [
        TwoCaptchaProvider(api_key=...),
        CapSolverProvider(api_key=...),
        AntiCaptchaProvider(api_key=...),
    ]
    
    async def solve(self, captcha_type, site_key, page_url) -> str:
        for provider in self.providers:
            try:
                token = await provider.solve(captcha_type, site_key, page_url)
                if token:
                    return token
            except Exception:
                continue
        raise CaptchaSolveFailed("All providers exhausted")
```

**Supported Types:** reCAPTCHA v2, reCAPTCHA v3, hCaptcha, Cloudflare Turnstile, FunCAPTCHA.

**Target:** >90% solve rate across all types.

### 5.2 IP Rotation — Proxy Pool Architecture

```
ProxyPoolManager
├── Provider: BrightData    (residential, 72M+ IPs)
├── Provider: Oxylabs       (residential, 100M+ IPs)
├── Provider: SmartProxy    (residential, 40M+ IPs)
└── Provider: Datacenter    (self-hosted, unlimited)
    ↓
Rotation Strategies:
├── Per-Request    — New IP per request
├── Session-Based  — Same IP per session (login flows)
└── Sticky         — Same IP for configurable duration
    ↓
Health Checks:
├── Latency monitoring
├── Success rate tracking
└── Automatic failover
```

**Design:**
```python
class ProxyPoolManager:
    """Manages proxy pools across multiple providers."""
    
    async def get_proxy(self, strategy="per_request", geo="us") -> str:
        provider = self._select_provider(geo)
        proxy = await provider.get_proxy(strategy)
        self._record_usage(proxy)
        return proxy
    
    async def report_failure(self, proxy: str) -> None:
        self._failure_counts[proxy] += 1
        if self._failure_counts[proxy] > 3:
            self._blacklist(proxy)
```

### 5.3 Browser Fingerprinting — Randomization Strategy

**Canvas Fingerprint:** Inject random noise into `CanvasRenderingContext2D.getImageData()` output.

**WebGL Fingerprint:** Randomize `WEBGL_debug_renderer_info` values (vendor, renderer strings).

**AudioContext Fingerprint:** Add random perturbation to `AudioContext.createOscillator()` output.

**Navigator Properties:** Randomize `navigator.hardwareConcurrency` (4–16), `navigator.deviceMemory` (4–32), `navigator.languages`.

**Font Fingerprint:** Randomize available font enumeration order.

**Screen Properties:** Randomize `screen.colorDepth`, `screen.pixelDepth`, `devicePixelRatio` within realistic ranges.

**Implementation:** Camoufox already provides comprehensive fingerprint randomization. For Playwright-based arms, a `FingerprintManager` injects randomized JavaScript overrides at context creation time.

### 5.4 Residential Proxy Integration

**Architecture:**
```
ScrapeRequest
    ↓
OctopusDispatcher
    ↓
ARM-3 (Evasion)
    ↓
ProxyPoolManager.get_proxy(strategy="per_request", geo="us")
    ↓
curl-cffi / camoufox with proxy={"server": "http://user:pass@gate.smartproxy.com:7777"}
```

**Provider Configuration:**
```python
class ScrapeProxy(Model):
    proxy_type = CharField(choices=["residential", "datacenter", "mobile"])
    provider = CharField(choices=["brightdata", "oxylabs", "smartproxy", "custom"])
    endpoints = JSONField()  # List of proxy gateway URLs
    rotation_strategy = CharField(choices=["per_request", "session", "sticky"])
    credentials = EncryptedJSONField()  # AES-256 encrypted
    geo_targeting = JSONField(default=dict)  # {"country": "us", "city": "new_york"}
```

---

## 6. Visual Builder Design

### 6.1 Browser Canvas Architecture

```
┌─────────────────────────────────────────────────┐
│  voyant-browser-canvas (React Component)         │
│                                                  │
│  ┌──────────────────────┐  ┌──────────────────┐ │
│  │  Page Preview        │  │  Workflow Panel  │ │
│  │  (base64 PNG from    │  │  Step 1: Navigate│ │
│  │   BrowserSession)    │  │  Step 2: Click   │ │
│  │                      │  │  Step 3: Scroll  │ │
│  │  [Click overlay for  │  │  Step 4: Extract │ │
│  │   element selection] │  │                  │ │
│  │                      │  │  [Add Step]      │ │
│  └──────────────────────┘  └──────────────────┘ │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  Auto-Detect Results                     │   │
│  │  Lists: Product List (24 items)          │   │
│  │  Tables: Pricing Table (5 rows)          │   │
│  │  Pagination: Next Button (.pagination a) │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**Data Flow:**
1. Frontend connects to `ScraperConsumer` WebSocket
2. User enters URL → `navigate` action → server launches Playwright, returns `PageState` with base64 screenshot + interactive elements
3. User clicks on screenshot → frontend maps click coordinates → sends `click` action → server executes click, returns new `PageState`
4. Auto-detect runs after each navigation → returns detected lists, tables, pagination, forms
5. User builds workflow by adding steps → each step is a `BrowserAction` or workflow step
6. Live preview: user can run extraction at any point to see extracted data

### 6.2 Point-and-Click Element Selection

When the user hovers over the page preview:
1. Frontend sends `hover` action with (x, y) coordinates
2. Server runs `_get_element_at(x, y)` — uses `document.elementFromPoint()` in JavaScript
3. Returns `ElementInfo` with tag, text, CSS selector, XPath, bounding box, attributes
4. Frontend highlights the element with a colored overlay
5. On click, the element's selector is added to the workflow's extraction step

### 6.3 Workflow Step Types

| Step Type | Description | Parameters |
|-----------|-------------|------------|
| `navigate` | Go to URL | url, wait_until |
| `click` | Click element | selector |
| `scroll` | Scroll page | direction, times, wait_ms |
| `wait` | Wait for duration | wait_ms |
| `enter_text` | Type into field | selector, text |
| `hover` | Hover element | selector |
| `extract` | Extract data | selectors map |
| `close_popup` | Close modal/popup | selector (optional) |
| `screenshot` | Capture screenshot | path |
| `loop` | Loop over elements | selector, variable |
| `condition` | Conditional step | field, operator, value |
| `back` | Navigate back | — |
| `new_tab` | Open new tab | — |
| `download` | Download file | url, path |

### 6.4 Live Preview

At any point in workflow building, the user can:
1. Click "Preview" → executes the workflow up to the current step
2. Sees the page state (screenshot) at that point
3. Sees extracted data in a table preview
4. Can adjust selectors and re-preview

**Implementation:** The visual builder sends the workflow as a sequence of actions to `ScraperConsumer`, which executes them against the `BrowserSession` and streams back `PageState` snapshots.

---

## 7. Template Engine Design

### 7.1 Template Schema

```json
{
  "id": "amazon-product-search",
  "name": "Amazon Product Search",
  "version": "1.0.0",
  "category": "ecommerce",
  "site_pattern": "amazon.com",
  "description": "Search Amazon products by keyword",
  "engine": "playwright",
  "language": "en",
  "parameters": [
    {
      "name": "search_query",
      "type": "string",
      "required": true,
      "description": "Search term"
    }
  ],
  "workflow": [
    {"action": "navigate", "url": "https://amazon.com/s?k={{search_query}}"},
    {"action": "scroll", "times": 3, "wait_ms": 1000},
    {"action": "extract", "selectors": {"title": "h2 a span", "price": ".a-price"}}
  ],
  "output_schema": {
    "title": {"type": "string", "description": "Product title"},
    "price": {"type": "string", "description": "Product price"}
  },
  "pagination": {
    "type": "next_button",
    "selector": ".s-pagination-next",
    "max_pages": 10
  },
  "anti_bot": {
    "rotate_ua": true,
    "block_resources": true,
    "evasion_mode": false,
    "stealth": false,
    "proxy": ""
  },
  "schedule": {
    "frequency": "daily",
    "cron": "0 8 * * *"
  },
  "export": {
    "format": "json",
    "destination": ""
  },
  "success_rate": 0.95,
  "last_verified": "2026-09-01",
  "author": "voyant",
  "tags": ["product", "search", "ecommerce"]
}
```

### 7.2 Parameter Substitution

**Mechanism:** Double-brace `{{param_name}}` placeholders in any string field.

**Implementation:**
```python
def _substitute_workflow(workflow: list[dict], params: dict) -> list[dict]:
    """Substitute {{param}} placeholders in workflow steps."""
    workflow_str = json.dumps(workflow)
    for key, value in params.items():
        workflow_str = workflow_str.replace(f"{{{{{key}}}}}", str(value))
    return json.loads(workflow_str)
```

**Supported types:** `string`, `number`, `boolean`, `url`

### 7.3 Creating New Templates

**Method 1: TemplateBuilder (Python)**
```python
template = (
    TemplateBuilder("My Custom Template")
    .category("ecommerce")
    .site("example.com")
    .description("Scrape product listings")
    .engine("playwright")
    .param("search_query", type="string", required=True, description="Search term")
    .navigate("https://example.com/search?q={{search_query}}")
    .scroll(times=3, wait_ms=1000)
    .extract(title="h2", price=".price", url="a[href]")
    .paginate(type="next_button", selector=".next", max_pages=10)
    .anti_bot(rotate_ua=True, block_resources=True)
    .output_field("title", type="string", description="Product title")
    .output_field("price", type="string", description="Product price")
    .tag("product")
    .build()
)
```

**Method 2: JSON File**
```json
{
  "name": "My Custom Template",
  "category": "universal",
  "workflow": [...],
  "parameters": [...]
}
```

Load with `load_template("path/to/template.json")` or `load_templates_from_dir("templates/")`.

**Method 3: Visual Builder**
Use the visual builder to interactively create a workflow, then export as JSON template.

### 7.4 Template SDK

**Location:** `apps/scraper/template_sdk.py`

**Key Classes:**
- `TemplateBuilder` — Fluent builder with 20+ chainable methods
- `TEMPLATE_SCHEMA` — JSON Schema for validation (covers all template fields)
- `validate_template()` — Returns list of validation errors
- `template_to_mcp_params()` — Converts template parameters to MCP tool parameter format

**Validation Rules:**
- Must have `id`, `name`, `category`, and at least one workflow step
- Category must be one of 14 valid categories
- Each workflow step must have a valid `action` (14 valid actions)

---

## 8. Complete API Design (v4.0)

### 8.1 REST Endpoints — Current (v3.0)

| Method | Path | Request Schema | Response Schema | Auth |
|--------|------|---------------|-----------------|------|
| POST | `/v1/scrape/start` | `ScrapeStartSchema` (urls, selectors, options) | 202 `ScrapeJobSchema` | `write:jobs` |
| POST | `/v1/scrape/extract` | `ScrapeExtractSchema` (html, selectors) | Dict of field→values | `write:jobs` |
| POST | `/v1/scrape/fetch` | `ScrapeFetchSchema` (url, engine, wait_for, scroll, timeout, ...) | HTML + metadata | `write:jobs` |
| POST | `/v1/scrape/deep_archive` | `ScrapeDeepArchiveSchema` (url, interaction_selectors, download_patterns, target_dir, ...) | Manifest dict | `write:jobs` |
| POST | `/v1/scrape/ocr` | `ScrapeOcrSchema` (image_url, language) | OCR results | `write:jobs` |
| POST | `/v1/scrape/parse_pdf` | `ScrapePdfSchema` (pdf_url, extract_tables) | PDF content | `write:jobs` |
| POST | `/v1/scrape/transcribe` | `ScrapeTranscribeSchema` (media_url, language) | Transcript | `write:jobs` |
| GET | `/v1/scrape/status/{job_id}` | — | `ScrapeJobSchema` | `read:*` |
| POST | `/v1/scrape/cancel` | job_id | Status | `write:jobs` |
| GET | `/v1/scrape/result/{job_id}` | — | `ScrapeResultSchema` (job_id, status, artifacts) | `read:*` |
| GET | `/v1/scrape/metrics/{job_id}` | — | Metrics dict | `read:*` |

### 8.2 Template Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/scraper/templates` | List templates (filter by category, status, limit) |
| GET | `/v1/scraper/templates/categories` | List categories with counts |
| GET | `/v1/scraper/templates/{id}` | Get template details (selectors, workflow, options) |
| POST | `/v1/scraper/templates/{id}/run` | Execute template with parameters → starts Temporal workflow |
| GET | `/v1/scraper/templates/{id}/preview` | Preview resolved workflow without execution |
| GET | `/v1/scraper/jobs/{id}/audit` | Full audit trail (every step, timing, details) |
| GET | `/v1/scraper/jobs/{id}/audit/live` | Live audit feed (human-readable progress) |

### 8.3 Planned v4.0 Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/scraper/tasks` | Create task |
| GET | `/v1/scraper/tasks` | List tasks |
| GET | `/v1/scraper/tasks/{id}` | Get task |
| PUT | `/v1/scraper/tasks/{id}` | Update task |
| DELETE | `/v1/scraper/tasks/{id}` | Delete task |
| POST | `/v1/scraper/tasks/{id}/run` | Execute task |
| GET | `/v1/scraper/tasks/{id}/runs` | List runs |
| POST | `/v1/scraper/tasks/{id}/schedule` | Set schedule |
| POST | `/v1/scraper/tasks/{id}/export` | Configure export |
| POST | `/v1/scraper/workflows` | Create visual workflow |
| POST | `/v1/scraper/workflows/{id}/run` | Run workflow |
| POST | `/v1/scraper/ai/generate` | NL → scraper |
| POST | `/v1/scraper/ai/match` | URL → template |
| GET | `/v1/scraper/agent-skills` | List agent skills |
| POST | `/v1/scraper/agent-skills/{id}/execute` | Execute skill |
| GET | `/v1/scraper/proxies` | List proxies |
| GET | `/v1/scraper/fingerprints` | List fingerprints |
| GET | `/v1/scraper/runs/{id}/stream` | JSONL stream |

### 8.4 MCP Tool Mapping

| MCP Tool | Maps To | Description |
|----------|---------|-------------|
| `scrape.fetch` | POST `/v1/scrape/fetch` | Fetch page |
| `scrape.extract` | POST `/v1/scrape/extract` | Extract from HTML |
| `scrape.ocr` | POST `/v1/scrape/ocr` | OCR images |
| `scrape.parse_pdf` | POST `/v1/scrape/parse_pdf` | Parse PDF |
| `scrape.transcribe` | POST `/v1/scrape/transcribe` | Transcribe media |
| `scrape.deep_archive` | POST `/v1/scrape/deep_archive` | Deep archive |
| `voyant.templates.execute` | POST `/v1/scraper/templates/{id}/run` | Run template |
| `voyant.scraper.template.list` | GET `/v1/scraper/templates` | (Planned) List templates |
| `voyant.scraper.template.run` | POST `/v1/scraper/templates/{id}/run` | (Planned) Run template |
| `voyant.scraper.task.create` | POST `/v1/scraper/tasks` | (Planned) Create task |
| `voyant.scraper.task.run` | POST `/v1/scraper/tasks/{id}/run` | (Planned) Execute task |
| `voyant.scraper.task.status` | GET `/v1/scraper/tasks/{id}/runs` | (Planned) Check status |
| `voyant.scraper.ai.generate` | POST `/v1/scraper/ai/generate` | (Planned) NL → scraper |

---

## 9. Performance Targets

### 9.1 Latency Targets

| Scenario | Target | Current | Strategy |
|----------|--------|---------|----------|
| Simple static page (ARM-1) | <5s | ~1–2s | httpx + parsel, no browser |
| JavaScript SPA (ARM-2) | <30s | ~5–15s | Playwright + resource blocking |
| Anti-bot page (ARM-3) | <30s | ~3–20s | curl-cffi or camoufox |
| Large crawl (ARM-4, 100 pages) | <5min | ~2–5min | Scrapy concurrent_requests=16 |
| API intercept (ARM-5) | <15s | ~5–10s | Playwright + network monitoring |
| PDF parsing (ARM-6) | <10s | ~2–5s | Tika → pdfplumber fallback |
| OCR processing (ARM-7a) | <10s | ~3–8s | Tesseract with preprocessing |
| Audio transcription (ARM-7b) | <60s | ~20–45s | Whisper base model |
| Deep archive (ARM-8) | <60s | ~15–45s | Playwright + file downloads |
| Template execution | <30s | ~5–15s | Pre-configured selectors |
| Deep research (full pipeline) | <5min | ~2–4min | Parallel fetch + synthesis |

### 9.2 Concurrency Targets

| Metric | Target | Strategy |
|--------|--------|----------|
| Concurrent scrape tasks | 50+ | Temporal workflow parallelism + browser pool |
| Concurrent browser sessions | 20+ | BrowserManager session pool with LRU eviction |
| Concurrent API requests | 100+ | httpx async client pool |
| URLs per batch | 1000 | Sequential within workflow, parallel across workflows |

### 9.3 Accuracy Targets

| Metric | Target | Strategy |
|--------|--------|----------|
| Field extraction accuracy | >99% | Validated selectors, fallback chains |
| CAPTCHA solve rate | >90% | Multi-provider chain with fallback |
| Content extraction quality | >95% | 5-library fallback chain |
| Deduplication precision | >95% | MinHash/LSH with 0.85 threshold |
| Cross-validation accuracy | >90% | 4-gram overlap with ≥2 source requirement |

### 9.4 Reliability Targets

| Metric | Target | Strategy |
|--------|--------|----------|
| System uptime | 99.9% | Circuit breakers, retry logic, fallback executors |
| Task completion rate | >98% | Temporal retries (3 attempts, exponential backoff) |
| Browser crash recovery | <5s | BrowserManager auto-restart on session failure |
| Proxy failover | <2s | Automatic provider switching on failure |
| Export latency (10K rows) | <10s | Streaming JSONL, batch inserts |

### 9.5 Scalability Architecture

```
┌─────────────────────────────────────────────────┐
│  Load Balancer (nginx / K8s ingress)             │
├─────────────────────────────────────────────────┤
│  Django API Servers (N replicas)                 │
├─────────────────────────────────────────────────┤
│  Temporal Workers (M replicas)                   │
│  ├── ScrapeWorker (browser pool per node)        │
│  ├── DeepResearchWorker                          │
│  └── ExportWorker                                │
├─────────────────────────────────────────────────┤
│  Shared State                                    │
│  ├── PostgreSQL (jobs, templates, artifacts)     │
│  ├── Redis (rate limits, circuit breakers)       │
│  ├── MinIO/S3 (artifact storage)                 │
│  └── SearXNG (search engine)                     │
└─────────────────────────────────────────────────┘
```

---

## Appendix A: Data Model Summary

| Model | Table | Key Fields |
|-------|-------|------------|
| `ScrapeJob` | `voyant_scrape_job` | job_id (UUID PK), tenant_id, status, urls, selectors, options, pages_fetched, bytes_processed, artifact_count, error_count, created_at, started_at, finished_at, error_message, retry_count |
| `ScrapeArtifact` | `voyant_scrape_artifact` | artifact_id (PK), job (FK), artifact_type, format, storage_path, content_hash, size_bytes, source_url, metadata |
| `ScrapeTemplate` | `scraper_template` | id (UUID PK), tenant_id, name, site_pattern, category, description, language, status, engine, selectors, workflow, options, parameters, output_fields, use_count, success_rate |

## Appendix B: OctopusARM Enum Reference

| ARM | Value | Technology | Use Case |
|-----|-------|------------|----------|
| STATIC | `static` | httpx + parsel | Fast static HTML pages |
| DYNAMIC | `dynamic` | Playwright + stealth | JavaScript-rendered SPAs |
| EVASION | `evasion` | curl-cffi / camoufox | Anti-bot protected sites |
| CRAWL | `crawl` | Scrapy | Large-scale site crawling |
| API_INTERCEPT | `api_intercept` | Playwright XHR capture | Hidden API reverse-engineering |
| DOCUMENT | `document` | pdfplumber + unstructured | PDF/Office document parsing |
| OCR | `ocr` | Tesseract | Image text extraction |
| TRANSCRIBE | `transcribe` | Whisper | Audio/video transcription |
| ARCHIVE | `archive` | Playwright deep archive | Interactive site archiving |

## Appendix C: Source Code File Map

| Component | File Path | Lines |
|-----------|-----------|-------|
| Models | `apps/scraper/models.py` | 173 |
| REST API | `apps/scraper/api.py` | 431 |
| Template API | `apps/scraper/template_api.py` | 492 |
| Template SDK | `apps/scraper/template_sdk.py` | 529 |
| Template Definitions | `apps/scraper/templates/definitions.py` | 1038 |
| Temporal Workflow | `apps/scraper/workflow.py` | 179 |
| SSRF Security | `apps/scraper/security.py` | 436 |
| Octopus Schemas | `apps/scraper/octopus/schemas.py` | 197 |
| Octopus Dispatcher | `apps/scraper/octopus/dispatcher.py` | 252 |
| ARM-1 Static | `apps/scraper/octopus/arms/arm_static.py` | 164 |
| ARM-2 Dynamic | `apps/scraper/octopus/arms/arm_dynamic.py` | 177 |
| ARM-3 Evasion | `apps/scraper/octopus/arms/arm_evasion.py` | 186 |
| ARM-4 Crawl | `apps/scraper/octopus/arms/arm_crawl.py` | 115 |
| ARM-5 API Intercept | `apps/scraper/octopus/arms/arm_api_intercept.py` | 150 |
| ARM-6 Document | `apps/scraper/octopus/arms/arm_document.py` | 117 |
| ARM-7a OCR | `apps/scraper/octopus/arms/arm_ocr.py` | 104 |
| ARM-7b Transcribe | `apps/scraper/octopus/arms/arm_transcribe.py` | 156 |
| ARM-8 Archive | `apps/scraper/octopus/arms/arm_archive.py` | 187 |
| Deep Research Workflow | `apps/scraper/deep_research/workflow.py` | 371 |
| Deep Research Activities | `apps/scraper/deep_research/activities.py` | 444 |
| Deep Research Schemas | `apps/scraper/deep_research/schemas.py` | 144 |
| Query Generator | `apps/scraper/deep_research/agents/query_generator.py` | 415 |
| Content Extractor | `apps/scraper/deep_research/agents/content_extractor.py` | 190 |
| Source Scorer | `apps/scraper/deep_research/agents/source_scorer.py` | 179 |
| Synthesizer | `apps/scraper/deep_research/agents/synthesizer.py` | 334 |
| Cross Validator | `apps/scraper/deep_research/agents/cross_validator.py` | 147 |
| Report Generator | `apps/scraper/deep_research/agents/report_generator.py` | 168 |
| HTML Parser | `apps/scraper/parsing/html_parser.py` | 122 |
| PDF Parser | `apps/scraper/parsing/pdf_parser.py` | 198 |
| OCR Processor | `apps/scraper/parsing/ocr_processor.py` | 191 |
| Tika Client | `apps/scraper/parsing/tika_client.py` | 125 |
| Auto-Detect Engine | `apps/scraper/visual/auto_detect.py` | 464 |
| Browser Manager | `apps/scraper/visual/browser_manager.py` | 352 |
| WebSocket Consumer | `apps/scraper/visual/consumer.py` | 246 |
| MCP Scrape Tools | `apps/mcp/tools_scrape.py` | 192 |

---

**Document Control:**
- Created: 2026-09-05
- Author: Voyant Engineering
- Review cycle: Every sprint
- Next review: 2026-09-19
- Related specs: `VOYANT_SCRAPER_SRS_V4.md`, `VOYANT_SAD_V4.md`
