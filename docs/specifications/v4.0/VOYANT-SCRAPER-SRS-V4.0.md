# Voyant v4.0 Scraper Module — Software Requirements Specification

**Document ID:** VOYANT-SRS-SCRAPER-4.0.0
**Version:** 4.0.0-draft
**Date:** 2026-09-05
**Status:** Draft for Review
**Classification:** Internal
**Standard:** ISO/IEC/IEEE 29148:2018
**Author:** Voyant Engineering

---

## 1. Introduction

### 1.1 Purpose

This SRS specifies the requirements for the Voyant v4.0 Scraper Module ("Octopus") — an Octoparse-grade web data extraction engine integrated into the Voyant Data Intelligence Platform.

### 1.2 Scope

The Scraper Module provides enterprise-grade web data extraction: no-code visual building, template library, anti-bot evasion, CAPTCHA solving, IP rotation, scheduling, multi-format export, and AI agent integration via MCP.

### 1.3 Definitions

| Term | Definition |
|------|-----------|
| Task | A configured scraping workflow (URL + selectors + actions + schedule) |
| Template | Pre-built, reusable task for a specific website or use case |
| Workflow | Sequence of scraping actions (navigate, click, scroll, extract, paginate) |
| Selector | CSS/XPath expression identifying elements to extract |
| Anti-Bot | Techniques to bypass website anti-scraping measures |
| Incremental Extraction | Only extracting new/changed data since last run |
| Parent-Child Task | Task that triggers another task with extracted data |

---

## 2. Current State — Voyant Scraper v3.0

### 2.1 Measured Metrics

| Metric | Value |
|--------|-------|
| Python files | 54 |
| Lines of code | 8,471 |
| API endpoints | 11 |
| MCP tools | 7 |
| Temporal workflows | 3 |
| Activity classes | 6 |
| Test files | 16 |

### 2.2 Architecture Components

| Component | File | Status |
|-----------|------|--------|
| API Layer | `api.py` (11 endpoints) | Production |
| Models | `ScrapeJob`, `ScrapeArtifact` | Production |
| Browser Arms | `arm_static`, `arm_dynamic`, `arm_crawl`, `arm_document`, `arm_ocr`, `arm_transcribe`, `arm_evasion`, `arm_archive` | Production |
| Content Extraction | `content_extractor.py` (trafilatura → readability → newspaper → crawl4ai → fallback) | Production |
| HTML Parser | `html_parser.py` (BeautifulSoup/lxml) | Production |
| PDF Parser | `pdf_parser.py` (pdfplumber) | Production |
| OCR Processor | `ocr_processor.py` (Tesseract) | Production |
| Deep Research | `deep_research_workflow.py`, `deep_research/` (V2 with query generation, multi-source, synthesis) | Production |
| Search Integration | `brave_search.py`, `google_cse.py`, `searxng_client.py` | Production |
| Security | `security.py` (SSRF protection, URL validation) | Production |
| Workflow Engine | `workflow.py` (Temporal orchestration) | Production |
| Dispatcher | `dispatcher.py` (routes to arms) | Production |
| Evasion | `arm_evasion.py` (user-agent rotation, fingerprint randomization, curl-cffi, camoufox) | Production |
| Octopus Dispatcher | `octopus/dispatcher.py` (circuit breaker integration) | Production |

### 2.3 Existing MCP Tools

| Tool | Description |
|------|-------------|
| `scrape.fetch` | Fetch web page with browser options |
| `scrape.extract` | Extract data from HTML using CSS/XPath selectors |
| `scrape.ocr` | OCR on images via Tesseract |
| `scrape.parse_pdf` | Parse PDF documents |
| `scrape.transcribe` | Transcribe audio/video |
| `scrape.deep_archive` | Deep archival scraping |
| `voyant.research.run/status` | Deep research workflow |

### 2.4 Existing REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/scrape/start` | Start scrape job |
| POST | `/v1/scrape/extract` | Extract from HTML |
| POST | `/v1/scrape/fetch` | Fetch page |
| POST | `/v1/scrape/deep_archive` | Deep archive |
| POST | `/v1/scrape/ocr` | OCR processing |
| POST | `/v1/scrape/parse_pdf` | PDF parsing |
| POST | `/v1/scrape/transcribe` | Audio transcription |
| GET | `/v1/scrape/status/{id}` | Job status |
| POST | `/v1/scrape/cancel` | Cancel job |
| GET | `/v1/scrape/result/{id}` | Get results |
| GET | `/v1/scrape/metrics/{id}` | Get metrics |

---

## 3. Gap Analysis — Octoparse vs Voyant v3.0

### 3.1 Summary by Category

| Category | Total | Met | Partial | Missing | Gap % |
|----------|-------|-----|---------|---------|-------|
| Core Scraping Engine | 13 | 6 | 3 | 4 | 38% |
| Anti-Bot & Evasion | 8 | 5 | 1 | 2 | 25% |
| Task Management | 11 | 4 | 3 | 4 | 36% |
| Data Export & Integration | 10 | 6 | 1 | 3 | 30% |
| AI & Agent Integration | 6 | 0 | 2 | 4 | 67% |
| Free Web Tools | 6 | 1 | 1 | 4 | 67% |
| Enterprise Features | 6 | 4 | 1 | 1 | 17% |
| **TOTAL** | **60** | **26** | **12** | **22** | **37%** |

### 3.2 Critical Gaps (P0)

| ID | Gap | Octoparse Has | Voyant Has | Effort |
|----|-----|--------------|------------|--------|
| GAP-001 | No-Code Visual Builder | Drag-and-drop workflow builder | Nothing | 12 weeks |
| GAP-002 | Template Library | 600+ pre-built templates | 0 templates | 4 weeks |
| GAP-003 | AI Auto-Detect | AI detects page structure | Manual selectors only | 4 weeks |
| GAP-004 | CAPTCHA Solving | AI-powered bypass (reCAPTCHA, hCaptcha) | Nothing | 4 weeks |
| GAP-005 | IP Rotation (Residential) | 10K+ residential IPs | Basic proxy support | 4 weeks |
| GAP-006 | Pagination Handling | Auto-detect next page/load more | Basic scroll only | 2 weeks |
| GAP-007 | Login Automation | Credential storage, session management | Cookie support only | 2 weeks |

### 3.3 Major Gaps (P1)

| ID | Gap | Effort |
|----|-----|--------|
| GAP-008 | Agent Skills (pre-built multi-step workflows) | 3 weeks |
| GAP-009 | CLI Tool | 2 weeks |
| GAP-010 | JSONL Streaming | 1 week |
| GAP-011 | Parent-Child Task Chaining | 2 weeks |
| GAP-012 | Incremental Extraction | 2 weeks |
| GAP-013 | AI-Generated Scrapers (NL → rules) | 3 weeks |
| GAP-014 | iFrame Content Extraction | 1 week |
| GAP-015 | Dropdown/Select Handling | 1 week |
| GAP-016 | Form Filling & Submission | 1 week |
| GAP-017 | Task Scheduling (cron) | 1 week |
| GAP-018 | Task Import/Export (JSON) | 1 week |
| GAP-019 | Template Matching (AI) | 2 weeks |
| GAP-020 | Webhook Notifications | 1 week |
| GAP-021 | Google Sheets Export | 1 week |
| GAP-022 | CLI Tool | 2 weeks |

### 3.4 Moderate Gaps (P2)

| ID | Gap | Effort |
|----|-----|--------|
| GAP-023 | Screenshot Capture | 1 week |
| GAP-024 | XML Sitemap Generation | 1 week |
| GAP-025 | Email/Image Extractor Tools | 1 week |
| GAP-026 | Video Downloader | 1 week |
| GAP-027 | Task Versioning | 1 week |
| GAP-028 | Local Execution | 2 weeks |
| GAP-029 | Data Retention Policies | 1 week |
| GAP-030 | GDPR Compliance | 2 weeks |

---

## 4. Functional Requirements

### 4.1 Task Engine (P0)

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| SCR-F-001 | System SHALL create scraping tasks with URL, selectors, and workflow steps | Task created via API, stored in DB, retrievable |
| SCR-F-002 | System SHALL list, get, update, and delete tasks | Full CRUD via REST API |
| SCR-F-003 | System SHALL execute tasks via Temporal workflows | Task execution produces artifacts |
| SCR-F-004 | System SHALL monitor task status in real-time | Status updates via polling/SSE |
| SCR-F-005 | System SHALL support cron-based scheduling | Tasks run automatically on schedule |
| SCR-F-006 | System SHALL support concurrent execution (50+ tasks) | No degradation at 50 concurrent tasks |
| SCR-F-007 | System SHALL store task run history with trace_id | Every run is auditable |

### 4.2 Template Engine (P0)

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| SCR-F-010 | System SHALL provide template CRUD operations | Templates stored as JSON, editable |
| SCR-F-011 | System SHALL ship 50 templates at Phase 1 | Templates for Amazon, Google Maps, Twitter, etc. |
| SCR-F-012 | System SHALL execute templates with parameter substitution | User provides URL/params, template runs |
| SCR-F-013 | System SHALL categorize templates (E-Commerce, Maps, Social, etc.) | Filterable by category |

### 4.3 Anti-Bot Engine (P0)

#### 4.3.1 CAPTCHA Solving — Hybrid AI-Native + Human Fallback

The system SHALL implement a 4-tier CAPTCHA solving strategy with cascading fallback:

| Tier | Method | CAPTCHA Types | Accuracy Target | Latency | Cost |
|------|--------|--------------|-----------------|---------|------|
| 1 | Behavioral Simulation | reCAPTCHA v3 | 70% | <1s | Free |
| 2 | Audio Bypass (Whisper STT) | reCAPTCHA v2 (audio) | 90% | 2-3s | Free |
| 3 | Vision LLM (GPT-4V/Claude) | hCaptcha, text CAPTCHAs, image grids | 70-85% | 3-5s | ~$0.01 |
| 4 | Human Solving Farm | All types (fallback) | 95% | 10-60s | $1-3/1K |

**Design Principles:**
- Tiers are attempted in order (1→2→3→4); first success wins
- Each tier is optional (graceful degradation if not configured)
- Tier 1 and 2 are self-hosted (zero external dependencies)
- Tier 3 requires any configured LLM provider (7 already configured)
- Tier 4 requires commercial API key (2Captcha/AntiCaptcha/CapSolver)
- All tiers log solve method, latency, and success/failure for monitoring

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| SCR-F-020 | System SHALL solve reCAPTCHA v2/v3 automatically | >90% solve rate (hybrid) |
| SCR-F-020a | System SHALL simulate human behavioral signals for reCAPTCHA v3 | Score >= 0.7 on 70% of attempts |
| SCR-F-020b | System SHALL solve reCAPTCHA v2 audio challenges via speech-to-text | >90% accuracy on audio CAPTCHAs |
| SCR-F-020c | System SHALL solve image CAPTCHAs via vision LLM | >70% accuracy on text/image CAPTCHAs |
| SCR-F-020d | System SHALL fall back to human solving farm when AI methods fail | 100% fallback coverage |
| SCR-F-021 | System SHALL solve hCaptcha automatically | >85% solve rate (hybrid) |
| SCR-F-022 | System SHALL solve Cloudflare Turnstile | >85% solve rate (hybrid) |
| SCR-F-023 | System SHALL rotate IP addresses across proxy pools | No IP reuse within configurable window |
| SCR-F-024 | System SHALL randomize browser fingerprints | WebGL, Canvas, Audio, Navigator spoofing |
| SCR-F-025 | System SHALL support residential proxy providers | Integration with BrightData/SmartProxy/Oxylabs |

#### 4.3.2 AI-Native CAPTCHA Solver Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  HybridCaptchaSolver                         │
│                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │ BehavioralSim│   │ AudioSolver │   │ VisionSolver│       │
│  │ (Tier 1)    │   │ (Tier 2)    │   │ (Tier 3)    │       │
│  │             │   │             │   │             │       │
│  │ Mouse move  │   │ Click audio │   │ Screenshot  │       │
│  │ Scroll sim  │   │ Download mp3│   │ Send to LLM │       │
│  │ Type timing │   │ Whisper STT │   │ Parse answer│       │
│  │ Canvas/WebGL│   │ Submit text │   │ Submit      │       │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘       │
│         │ fail             │ fail             │ fail         │
│         ▼                  ▼                  ▼              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │              HumanFarmSolver (Tier 4)                │     │
│  │  2Captcha → AntiCaptcha → CapSolver (chain)         │     │
│  └─────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

**Tier 1 — Behavioral Simulation (reCAPTCHA v3 only):**
- Simulate realistic mouse movements using Bezier curves
- Simulate scroll events with natural timing
- Simulate keyboard events with variable delay (50-150ms per keystroke)
- Canvas fingerprint: inject realistic noise (already in fingerprint.py)
- WebGL fingerprint: randomized vendor/renderer (already in fingerprint.py)
- Page dwell time: minimum 3 seconds before interaction
- Navigator properties: hardwareConcurrency, deviceMemory, plugins

**Tier 2 — Audio Bypass (reCAPTCHA v2):**
- Click the audio challenge button in the CAPTCHA iframe
- Download the audio challenge MP3
- Transcribe using Whisper (faster-whisper for speed, or OpenAI Whisper API)
- Submit transcribed text as answer
- Retry once if transcription confidence is low

**Tier 3 — Vision LLM (hCaptcha, text CAPTCHAs):**
- Screenshot the CAPTCHA element
- Send image to configured LLM with vision capability
- Prompt: "What text/characters are shown in this CAPTCHA image? Answer with only the characters."
- Parse LLM response, extract answer
- For hCaptcha image grids: "Which images contain [object]? List the positions (1-9)."

**Tier 4 — Human Farm (fallback):**
- Existing MultiProviderCaptchaSolver (2Captcha → AntiCaptcha → CapSolver)
- Guaranteed solve for all CAPTCHA types
- Used only when Tiers 1-3 fail

### 4.4 Browser Automation (P0)

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| SCR-F-030 | System SHALL handle infinite scroll | Auto-scroll until no new content |
| SCR-F-031 | System SHALL follow pagination (next button, load more) | Auto-detect and click next |
| SCR-F-032 | System SHALL automate login with stored credentials | Encrypted credential storage |
| SCR-F-033 | System SHALL interact with dropdowns/selects | Select by value/text/index |
| SCR-F-034 | System SHALL fill and submit forms | Field mapping + submit |
| SCR-F-035 | System SHALL extract from iframes | Switch context and extract |
| SCR-F-036 | System SHALL capture screenshots | Full page or element screenshots |

### 4.5 Export Engine (P0)

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| SCR-F-040 | System SHALL export to JSON | Valid JSON array output |
| SCR-F-041 | System SHALL export to JSONL (streaming) | Row-by-row streaming |
| SCR-F-042 | System SHALL export to CSV | RFC 4180 compliant |
| SCR-F-043 | System SHALL export to XLSX | Excel-compatible |
| SCR-F-044 | System SHALL export to XML | Well-formed XML |
| SCR-F-045 | System SHALL export to PostgreSQL | Direct INSERT |
| SCR-F-046 | System SHALL export to MySQL | Direct INSERT |
| SCR-F-047 | System SHALL auto-export on task completion | Configurable per task |

### 4.6 AI Integration (P1)

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| SCR-F-050 | System SHALL generate scrapers from NL descriptions | "Scrape Amazon product prices" → working task |
| SCR-F-051 | System SHALL match URLs to best-fit templates | AI selects template from library |
| SCR-F-052 | System SHALL auto-detect page structure | AI identifies data fields without selectors |
| SCR-F-053 | System SHALL provide agent skills for multi-step workflows | Skills as MCP-callable units |
| SCR-F-054 | System SHALL provide 13 MCP tools | All tools registered and callable |

### 4.7 Visual Builder (P0)

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| SCR-F-060 | System SHALL provide drag-and-drop workflow builder | Browser-based visual editor |
| SCR-F-061 | System SHALL support point-and-click element selection | Click element → selector auto-generated |
| SCR-F-062 | System SHALL support live preview of extraction | See extracted data in real-time |
| SCR-F-063 | System SHALL export/import workflows as JSON | Portable workflow definitions |

---

## 5. Non-Functional Requirements

| ID | Requirement | Target | Priority |
|----|-------------|--------|----------|
| SCR-NF-001 | Task execution latency (simple page) | <5 seconds | P0 |
| SCR-NF-002 | Task execution latency (complex SPA) | <30 seconds | P0 |
| SCR-NF-003 | Concurrent task execution | 50+ simultaneous | P0 |
| SCR-NF-004 | Template library at launch | 50 templates (Phase 1), 200+ (Phase 5) | P0 |
| SCR-NF-005 | CAPTCHA solve rate | >90% | P0 |
| SCR-NF-006 | Data extraction accuracy | >99% field accuracy | P0 |
| SCR-NF-007 | System availability | 99.9% uptime | P0 |
| SCR-NF-008 | Export latency (10K rows) | <10 seconds | P0 |
| SCR-NF-009 | IP pool size | 10,000+ residential IPs | P1 |
| SCR-NF-010 | Concurrent users | 1,000+ | P1 |

---

## 6. Target Architecture — v4.0

### 6.1 New Models

| Model | Description | Key Fields |
|-------|-------------|------------|
| `ScrapeTemplate` | Pre-built template | name, site_pattern, selectors, workflow, category, language |
| `ScrapeWorkflow` | Visual workflow definition | name, steps (JSON), input_schema, output_schema |
| `ScrapeStep` | Individual workflow step | step_type, selector, action, wait_condition, options |
| `ScrapeSchedule` | Cron scheduling | task_id, cron_expr, timezone, enabled |
| `ScrapeExport` | Export config | task_id, format, destination, auto_export |
| `ScrapeProxy` | Proxy pool config | proxy_type, provider, endpoints, rotation_strategy |
| `ScrapeFingerprint` | Browser fingerprint | user_agent, viewport, webgl, canvas, audio |
| `AgentSkill` | Pre-built agent workflow | name, description, steps, tools, parameters |
| `ScrapeRun` | Execution record | task_id, status, rows_extracted, duration_ms, trace_id |

### 6.2 New API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/scraper/templates` | List templates |
| GET | `/v1/scraper/templates/{id}` | Get template |
| POST | `/v1/scraper/templates/{id}/run` | Run template |
| POST | `/v1/scraper/tasks` | Create task |
| GET | `/v1/scraper/tasks` | List tasks |
| GET | `/v1/scraper/tasks/{id}` | Get task |
| PUT | `/v1/scraper/tasks/{id}` | Update task |
| DELETE | `/v1/scraper/tasks/{id}` | Delete task |
| POST | `/v1/scraper/tasks/{id}/run` | Execute task |
| GET | `/v1/scraper/tasks/{id}/runs` | List runs |
| POST | `/v1/scraper/tasks/{id}/schedule` | Set schedule |
| POST | `/v1/scraper/tasks/{id}/export` | Configure export |
| POST | `/v1/scraper/workflows` | Create workflow |
| POST | `/v1/scraper/workflows/{id}/run` | Run workflow |
| POST | `/v1/scraper/ai/generate` | NL → scraper |
| POST | `/v1/scraper/ai/match` | URL → template |
| GET | `/v1/scraper/agent-skills` | List skills |
| POST | `/v1/scraper/agent-skills/{id}/execute` | Execute skill |
| GET | `/v1/scraper/proxies` | List proxies |
| GET | `/v1/scraper/fingerprints` | List fingerprints |
| GET | `/v1/scraper/runs/{id}/stream` | JSONL stream |

### 6.3 New MCP Tools

| Tool | Description |
|------|-------------|
| `voyant.scraper.template.list` | List available templates |
| `voyant.scraper.template.run` | Run template with params |
| `voyant.scraper.task.create` | Create task |
| `voyant.scraper.task.run` | Execute task |
| `voyant.scraper.task.status` | Check run status |
| `voyant.scraper.workflow.create` | Create visual workflow |
| `voyant.scraper.workflow.run` | Run workflow |
| `voyant.scraper.ai.generate` | NL → scraper |
| `voyant.scraper.ai.match` | URL → template |
| `voyant.scraper.export` | Export results |
| `voyant.scraper.stream` | JSONL streaming |
| `voyant.scraper.skill.list` | List agent skills |
| `voyant.scraper.skill.execute` | Execute skill |

---

## 7. Implementation Roadmap

| Phase | Weeks | Deliverables | Priority | Effort |
|-------|-------|-------------|----------|--------|
| **Foundation** | 1–4 | Template engine, task CRUD, scheduling, export engine, 50 templates | P0 | 4 dev-weeks |
| **Anti-Bot** | 5–8 | CAPTCHA solver, IP rotation, fingerprint randomizer, residential proxy | P0 | 4 dev-weeks |
| **Visual Builder** | 9–12 | React drag-and-drop builder, step types, live preview | P0 | 4 dev-weeks |
| **AI Integration** | 13–16 | NL-to-scraper, template matching, agent skills, JSONL streaming | P1 | 4 dev-weeks |
| **CLI & Polish** | 17–20 | CLI tool, Google Sheets export, parent-child tasks, incremental extraction | P1 | 4 dev-weeks |
| **Enterprise** | 21–24 | GDPR, SOC 2 prep, performance optimization, 200+ templates | P2 | 4 dev-weeks |

---

## 8. Template Library — Phase 1 (50 Templates)

| # | Category | Template | Site |
|---|----------|----------|------|
| 1 | E-Commerce | Product Search | Amazon |
| 2 | E-Commerce | Product Details | Amazon |
| 3 | E-Commerce | Product Reviews | Amazon |
| 4 | E-Commerce | Product Search | eBay |
| 5 | E-Commerce | Product Listings | Walmart |
| 6 | Maps | Business Listings | Google Maps |
| 7 | Maps | Business Reviews | Google Maps |
| 8 | Maps | Business Details | Google Maps |
| 9 | Social Media | Post Search | Twitter/X |
| 10 | Social Media | User Profile | Twitter/X |
| 11 | Social Media | Video Search | YouTube |
| 12 | Social Media | Video Details | YouTube |
| 13 | Social Media | Post Search | Reddit |
| 14 | Social Media | Subreddit Posts | Reddit |
| 15 | Social Media | Profile Data | LinkedIn |
| 16 | Social Media | Company Data | LinkedIn |
| 17 | Social Media | Video Search | TikTok |
| 18 | Social Media | Profile Data | TikTok |
| 19 | Social Media | Post Search | Instagram |
| 20 | Lead Gen | Email Extraction | Any Website |
| 21 | Lead Gen | Contact Info | Yellow Pages |
| 22 | Lead Gen | Business Directory | Yelp |
| 23 | Jobs | Job Search | Indeed |
| 24 | Jobs | Job Details | Indeed |
| 25 | Jobs | Job Search | LinkedIn Jobs |
| 26 | Real Estate | Property Listings | Zillow |
| 27 | Real Estate | Property Details | Zillow |
| 28 | Real Estate | Property Listings | Realtor.com |
| 29 | News | Article Search | Google News |
| 30 | News | Article Content | Any News Site |
| 31 | Finance | Stock Data | Yahoo Finance |
| 32 | Finance | Company Data | Crunchbase |
| 33 | Travel | Hotel Search | Booking.com |
| 34 | Travel | Flight Search | Google Flights |
| 35 | Travel | Restaurant Reviews | TripAdvisor |
| 36 | Education | Course Search | Coursera |
| 37 | Education | Research Papers | Google Scholar |
| 38 | Directories | Business Directory | Yellow Pages |
| 39 | Directories | Professional Directory | Clutch.co |
| 40 | Search Engine | Search Results | Google |
| 41 | Search Engine | Search Results | Bing |
| 42 | E-Commerce | Product Search | Alibaba |
| 43 | E-Commerce | Product Search | AliExpress |
| 44 | Social Media | Post Search | Facebook |
| 45 | Social Media | Group Posts | Facebook |
| 46 | News | Hacker News | Hacker News |
| 47 | Developer | Repository Search | GitHub |
| 48 | Developer | Package Search | npm |
| 49 | Developer | Questions | Stack Overflow |
| 50 | Universal | Any Page → Markdown | Universal |

---

## 9. Test Plan

| ID | Test Case | Type | Priority |
|----|-----------|------|----------|
| SCR-T-001 | Create task with valid URL and selectors | Unit | P0 |
| SCR-T-002 | Run task on static HTML page | Integration | P0 |
| SCR-T-003 | Run task on JavaScript-rendered SPA | Integration | P0 |
| SCR-T-004 | Run task with pagination | Integration | P0 |
| SCR-T-005 | Run task with infinite scroll | Integration | P0 |
| SCR-T-006 | Run task with login automation | Integration | P0 |
| SCR-T-007 | Solve reCAPTCHA v2 | Integration | P0 |
| SCR-T-008 | Solve hCaptcha | Integration | P0 |
| SCR-T-009 | IP rotation during execution | Integration | P1 |
| SCR-T-010 | Browser fingerprint randomization | Unit | P1 |
| SCR-T-011 | Template execution (Amazon) | Integration | P0 |
| SCR-T-012 | Template execution (Google Maps) | Integration | P0 |
| SCR-T-013 | Visual builder create workflow | UI | P0 |
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

---

## 10. ISO Compliance Matrix

### 10.1 ISO/IEC 25010:2011 — Quality Model

| Characteristic | Sub-Characteristic | v4.0 Implementation |
|---------------|-------------------|-------------------|
| Functional Suitability | Completeness | All 30 requirements (SCR-F-*) |
| Functional Suitability | Correctness | Selector validation, data type coercion |
| Functional Suitability | Appropriateness | Template-first design, visual builder |
| Performance Efficiency | Time behaviour | <5s simple, <30s SPA, p95 <60s |
| Performance Efficiency | Resource utilization | Browser pool, connection reuse |
| Performance Efficiency | Capacity | 50+ concurrent, 10K+ rows/export |
| Compatibility | Interoperability | REST + MCP + CLI + JSONL + webhook |
| Usability | Learnability | Templates, visual builder, AI auto-detect |
| Usability | Operability | 4 access modes (UI + API + CLI + MCP) |
| Reliability | Maturity | Circuit breakers, retry logic |
| Reliability | Fault tolerance | Browser crash recovery, proxy failover |
| Security | Confidentiality | Encrypted credentials, SSRF protection |
| Security | Integrity | Input validation, URL sanitization |
| Security | Non-repudiation | Audit logging with trace_id |
| Maintainability | Modularity | Separate arms per domain |
| Portability | Adaptability | Docker + K8s, self-hosted + cloud |

### 10.2 ISO/IEC 27001:2022 — Security Controls

| Control | Implementation |
|---------|---------------|
| A.9 Access Control | RBAC, tenant isolation |
| A.10 Cryptography | AES-256 credentials, TLS 1.3 |
| A.12 Operations | SSRF protection, rate limiting |
| A.14 Secure Development | SAST, dependency checks |
| A.16 Incident Management | Alerting on failures |
| A.18 Compliance | GDPR handling, configurable retention |

### 10.3 ISO 9001:2015 — Quality Management

| Requirement | Implementation |
|-------------|---------------|
| §8.3 Design | This SRS as design input |
| §8.5 Production | CI/CD with automated testing |
| §9.1 Monitoring | Prometheus + Grafana |
| §10.2 Nonconformity | Defect tracking, root cause analysis |

---

## Appendix A: Octoparse Feature Parity

| Feature | Octoparse | v3.0 | v4.0 Target |
|---------|-----------|------|-------------|
| No-Code Builder | Full | None | Visual Builder |
| AI Auto-Detect | Yes | None | AI-powered |
| Templates | 600+ | 0 | 200+ |
| Browser Automation | Full | Full | Full |
| Anti-Bot | Full | Partial | Full |
| CAPTCHA Solving | AI | None | AI |
| IP Rotation | Residential | Basic | Residential |
| Scheduling | Cron | Temporal | Cron + Temporal |
| Export Formats | 5+ | 3 | 6+ |
| Database Export | 4 DBs | 2 DBs | 4+ DBs |
| REST API | 23 endpoints | 11 endpoints | 21+ endpoints |
| MCP Tools | 6 | 7 | 13+ |
| CLI | Yes | None | Yes |
| JSONL Streaming | Yes | None | Yes |
| Agent Skills | Soon | None | Yes |
| NL-to-Scraper | Soon | None | Yes |
| Parent-Child | Yes | None | Yes |
| Incremental | Yes | None | Yes |
| Open Source | No | Yes (Apache 2.0) | Yes |
| Self-Hosted | No | Docker | Docker + K8s |
| Ontology Integration | No | No | Yes |

---

**Document Control:**
- Created: 2026-09-05
- Author: Voyant Engineering
- Review cycle: Every sprint

### Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 4.0.0-draft | 2026-09-05 | Voyant Engineering | Initial SRS |
| 4.0.1 | 2026-09-09 | MiMoCode Agent | §4.3 expanded: AI-native CAPTCHA solver design (4-tier hybrid: behavioral simulation → audio bypass → vision LLM → human farm fallback). Added SCR-F-020a through SCR-F-020d. Architecture diagram added. |
- Next review: 2026-09-19
