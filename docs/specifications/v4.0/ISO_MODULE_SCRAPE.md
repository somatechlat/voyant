# ISO Module Specification: Scraper Engine

> **Module:** `apps/scraper` + `dashboard/src/views/view-scraper.ts`  
> **Version:** 4.0 — Scraper Octopus  
> **Status:** Production  
> **Standard:** ISO/IEC/IEEE 29148:2018  

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Actors and Roles](#2-actors-and-roles)
3. [Screen Mockups](#3-screen-mockups)
4. [Functional Requirements](#4-functional-requirements)
5. [Data Models](#5-data-models)
6. [API Endpoints](#6-api-endpoints)
7. [Anti-Bot Engine Architecture](#7-anti-bot-engine-architecture)
8. [MCP Tool Catalog](#8-mcp-tool-catalog)
9. [Integration Points](#9-integration-points)
10. [Quality Attributes](#10-quality-attributes)
11. [Implementation References](#11-implementation-references)

---

## 1. Module Overview

### 1.1 Purpose

The Scraper Engine is Voyant's comprehensive web data extraction platform. It provides visual workflow building, template-based scraping, anti-bot evasion (CAPTCHA solving, fingerprint randomization, proxy rotation), and agent-native MCP tool access. All scraping is **pure execution** — agents provide selectors and URLs; no LLM is used in the scraping path itself.

### 1.2 Key Differentiators

| Differentiator | Description |
|---|---|
| **Scraper Octopus v4.0** | 9-arm architecture covering templates, workflows, builder, jobs, results, CAPTCHA, proxies, fingerprints, and agent skills |
| **4-Tier Hybrid CAPTCHA Solver** | Behavioral simulation → Audio/Whisper bypass → Vision LLM → Commercial human farms |
| **Visual Workflow Builder** | Browser-based point-and-click workflow composition with live preview |
| **Agent-Native** | 13 MCP tools for autonomous agent-driven scraping |
| **Zero-LLM Execution** | Scraping path has no LLM dependency — deterministic, auditable, fast |
| **Temporal Orchestration** | All jobs run as durable Temporal workflows with retry, timeout, and cancellation |

### 1.3 Scope

- Web page fetching (Playwright, httpx, Scrapy engines)
- Structured data extraction (CSS/XPath selectors)
- PDF parsing, OCR (Tesseract), audio transcription (Whisper)
- Template CRUD and execution
- Visual workflow builder with step palette
- Job lifecycle management and result export
- Anti-bot: CAPTCHA solving, fingerprint randomization, proxy rotation
- Agent skill definitions

---

## 2. Actors and Roles

| Actor | Role | Permissions |
|---|---|---|
| **Data Analyst** | Runs templates, views results, exports data | `read:*`, `write:jobs` |
| **Agent (AI)** | Invokes MCP tools for autonomous scraping | Via MCP tool auth |
| **Admin** | Manages templates, proxies, fingerprints, schedules | `write:jobs`, admin |
| **System (Temporal)** | Orchestrates workflow execution | Internal |
| **External CAPTCHA APIs** | 2Captcha, AntiCaptcha, CapSolver | API key auth |

---

## 3. Screen Mockups

### 3.1 Templates Tab

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ☰  Scraper Engine                                      [Templates|Builder|Jobs|Results] │
│──────────────────────────────────────────────────────────────────────────│
│ 📋 Templates    📂 Categories    🐙 Octopus Arms    🔧 MCP Tools    🎭 Playwright │
│    47               14              9                  8              Live    │
│──────────────────────────────────────────────────────────────────────────│
│ 🔍 [Search templates...____________]  [All (47)] [ecommerce (12)] [social (8)] ...│
│──────────────────────────────────────────────────────────────────────────│
│ ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐    │
│ │ 🕷️ Amazon Products  │ │ 🕷️ Twitter Posts   │ │ 🕷️ HN Frontpage   │    │
│ │ amazon.com          │ │ twitter.com        │ │ news.ycombinator..│    │
│ │ E-commerce template │ │ Social media       │ │ News aggregator   │    │
│ │ [ecommerce] 8 fields│ │ [social] 5 fields  │ │ [news] 3 fields   │    │
│ │ 142 runs · 94%      │ │ 89 runs · 87%      │ │ 234 runs · 99%    │    │
│ │ [▶ Run]  [🔧]      │ │ [▶ Run]  [🔧]      │ │ [▶ Run]  [🔧]      │    │
│ └────────────────────┘ └────────────────────┘ └────────────────────┘    │
│ ┌────────────────────┐ ┌────────────────────┐                           │
│ │ 🕷️ Zillow Listings │ │ 🕷️ Reddit Posts    │                           │
│ │ ...                │ │ ...                │                           │
│ └────────────────────┘ └────────────────────┘                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Visual Builder Tab

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [Workflow name: My Workflow___________]          [📋 Export JSON] [📥 Import] │
│──────────────────────────────────────────────────────────────────────────│
│ ┌──────────────┐ ┌─────────────────────────────────┐ ┌──────────────┐   │
│ │ Workflow Steps│ │ Browser Preview                 │ │ Step Config  │   │
│ │              │ │ [Enter URL to preview...] [Load] │ │              │   │
│ │ 🌐 Navigate  │ │ ┌─────────────────────────────┐ │ │ 🖱️ Click     │   │
│ │ 🖱️ Click     │ │ │                             │ │ │ Config       │   │
│ │ 📜 Scroll    │ │ │   Hacker News               │ │ │              │   │
│ │ ⏳ Wait      │ │ │   ┌───────────────────────┐ │ │ │ CSS Selector │   │
│ │ 📊 Extract   │ │ │   │ ▸ .titleline a        │ │ │ │ [.titleline] │   │
│ │ ⌨️ Enter Text│ │ │   │ (click to select)     │ │ │ │              │   │
│ │ 👆 Hover     │ │ │   └───────────────────────┘ │ │ │ Auto-fill by │   │
│ │ 📄 Paginate  │ │ │                             │ │ │ clicking in   │   │
│ │ 🔐 Login     │ │ └─────────────────────────────┘ │ │ preview       │   │
│ │ 📸 Screenshot│ │                                 │ │              │   │
│ │ 🔀 Condition │ │ Steps (4)                       │ │ Output       │   │
│ │ 🔄 Loop      │ │ 1. 🌐 Navigate → https://...   │ │ [JSON ▾]     │   │
│ │              │ │ 2. ⏳ Wait → 2000ms            │ │              │   │
│ │              │ │ 3. 📜 Scroll → 3x down         │ │ Schedule     │   │
│ │              │ │ 4. 📊 Extract → .titleline  [▲▼✕]│ │ [Once ▾]    │   │
│ │              │ │                                 │ │              │   │
│ │              │ │                                 │ │ Anti-Bot     │   │
│ │              │ │                                 │ │ ☑ Playwright │   │
│ │              │ │                                 │ │ ☐ Evasion    │   │
│ │              │ │                                 │ │ ☑ Block res. │   │
│ │              │ │                                 │ │              │   │
│ │              │ │                                 │ │ [▶ Run WF]   │   │
│ └──────────────┘ └─────────────────────────────────┘ └──────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Jobs Tab

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [All statuses ▾]                                        [🔄 Refresh]    │
│──────────────────────────────────────────────────────────────────────────│
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ Job ID       │ Status    │ URLs │ Pages │ Bytes   │ Artifacts │ Created│ │
│ │──────────────│───────────│──────│───────│─────────│───────────│────────│ │
│ │ a3f8...2c1d  │ 🟢 success│ 3    │ 3     │ 245 KB  │ 7         │ 2m ago │ │
│ │ b7e1...9a4f  │ 🔵 running│ 1    │ 1     │ 89 KB   │ 2         │ 5m ago │ │
│ │ c2d9...1b7e  │ 🟡 queued │ 5    │ 0     │ 0 B     │ 0         │ 8m ago │ │
│ │ d4a6...3e2c  │ 🔴 failed │ 2    │ 0     │ 0 B     │ 0         │ 1h ago │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Functional Requirements

### 4.1 Template Management

| FR-ID | Requirement | Priority | Ref |
|---|---|---|---|
| FR-SCR-001 | System shall support CRUD operations on scrape templates with category, site_pattern, engine, selectors, workflow, parameters, and output_fields | P0 | `models.py:123-186` |
| FR-SCR-002 | System shall search templates by name, description, and site_pattern with debounced (400ms) input | P1 | `view-scraper.ts:167-191` |
| FR-SCR-003 | System shall filter templates by 14 predefined categories (ecommerce, social, maps, news, finance, jobs, realestate, travel, education, developer, leadgen, directory, search, universal) | P1 | `models.py:130-145` |
| FR-SCR-004 | System shall track template use_count and success_rate for ranking | P2 | `models.py:169-170` |

### 4.2 Visual Builder

| FR-ID | Requirement | Priority | Ref |
|---|---|---|---|
| FR-SCR-010 | Builder shall provide 12 step types: navigate, click, scroll, wait, extract, enter_text, hover, paginate, login, screenshot, condition, loop | P0 | `view-scraper.ts:627` |
| FR-SCR-011 | Builder shall support a live browser preview with element selection for CSS selector auto-fill | P0 | `view-scraper.ts:668-692` |
| FR-SCR-012 | Builder shall export/import workflows as JSON with `{{param}}` substitution | P1 | `view-scraper.ts:295-333` |
| FR-SCR-013 | Builder shall support reordering steps via drag (▲/▼) and removal (✕) | P1 | `view-scraper.ts:273-287` |
| FR-SCR-014 | Builder shall provide per-step configuration panels with action-specific fields | P1 | `view-scraper.ts:781-849` |

### 4.3 Job Execution

| FR-ID | Requirement | Priority | Ref |
|---|---|---|---|
| FR-SCR-020 | System shall execute scraping jobs via Temporal workflows with automatic retry | P0 | `api.py:144-169` |
| FR-SCR-021 | System shall poll job status every 2 seconds with audit step and live feed | P0 | `view-scraper.ts:219-242` |
| FR-SCR-022 | System shall support job cancellation via Temporal workflow handle | P0 | `api.py:378-400` |
| FR-SCR-023 | System shall validate all URLs against SSRF attacks before execution | P0 | `api.py:200-203` |
| FR-SCR-024 | System shall export results as JSON or CSV via client-side Blob generation | P1 | `view-scraper.ts:387-414` |

### 4.4 CAPTCHA Solving

| FR-ID | Requirement | Priority | Ref |
|---|---|---|---|
| FR-SCR-030 | System shall solve reCAPTCHA v2, v3, hCaptcha, and Cloudflare Turnstile | P0 | `captcha_solver.py:45-100` |
| FR-SCR-031 | System shall chain CAPTCHA providers (2Captcha → AntiCaptcha → CapSolver) with automatic failover | P0 | `captcha_solver.py:609-716` |
| FR-SCR-032 | System shall provide 4-tier hybrid solving: behavioral → audio → vision → human farm | P0 | `captcha_hybrid.py:22-310` |
| FR-SCR-033 | Tier 1 behavioral solver shall simulate mouse movements (Bézier curves), scrolling, and keyboard events | P1 | `captcha_behavioral.py:38-248` |
| FR-SCR-034 | Tier 2 audio solver shall transcribe reCAPTCHA audio challenges via Whisper STT (faster-whisper preferred) | P1 | `captcha_audio.py:24-347` |
| FR-SCR-035 | Tier 3 vision solver shall use a vision LLM to solve image CAPTCHAs and hCaptcha grids | P1 | `captcha_vision.py:37-419` |

### 4.5 Anti-Bot Infrastructure

| FR-ID | Requirement | Priority | Ref |
|---|---|---|---|
| FR-SCR-040 | System shall randomize browser fingerprints (user-agent, viewport, WebGL, canvas, audio, navigator, screen) | P0 | `fingerprint.py:131-533` |
| FR-SCR-041 | System shall rotate proxies via round-robin, random, or least-used strategies with 60s failure cooldown | P0 | `proxy_manager.py:27-395` |
| FR-SCR-042 | System shall support residential, datacenter, mobile, and ISP proxy types from BrightData, SmartProxy, and Oxylabs | P1 | `proxy_manager.py:320-395` |
| FR-SCR-043 | System shall inject fingerprint overrides via Playwright `add_init_script` before navigation | P0 | `fingerprint.py:237-255` |

---

## 5. Data Models

### 5.1 ScrapeJob

**Table:** `voyant_scrape_job` — `models.py:24-80`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `job_id` | UUIDField | PK, auto | Job unique identifier |
| `tenant_id` | CharField(128) | indexed | Multi-tenant isolation |
| `status` | CharField(64) | indexed, choices: queued/running/succeeded/failed/cancelled/partial | Job lifecycle status |
| `urls` | JSONField | required | List of URLs to scrape |
| `selectors` | JSONField | nullable | Agent-provided CSS/XPath selectors |
| `options` | JSONField | default=dict | Execution options (engine, timeout, scroll, ocr, transcribe) |
| `pages_fetched` | IntegerField | default=0 | Progress counter |
| `bytes_processed` | BigIntegerField | default=0 | Data volume counter |
| `artifact_count` | IntegerField | default=0 | Output artifact count |
| `error_count` | IntegerField | default=0 | Error counter |
| `error_message` | TextField | blank | Error details |
| `retry_count` | IntegerField | default=0 | Retry attempt counter |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `started_at` | DateTimeField | nullable | Execution start |
| `finished_at` | DateTimeField | nullable | Execution end |

**Indexes:** `(tenant_id, status)`, `(created_at)`

### 5.2 ScrapeArtifact

**Table:** `voyant_scrape_artifact` — `models.py:83-120`

| Field | Type | Description |
|---|---|---|
| `artifact_id` | CharField(512) | PK |
| `job` | FK → ScrapeJob | Parent job |
| `artifact_type` | CharField(64) | Choices: html/json/csv/image/video/pdf/text/audio/ocr/transcript |
| `format` | CharField(32) | File format |
| `storage_path` | CharField(512) | MinIO/S3 object key |
| `content_hash` | CharField(128) | Content integrity hash |
| `size_bytes` | BigIntegerField | File size |
| `source_url` | URLField(2048) | Origin URL |
| `metadata` | JSONField | Additional metadata |

### 5.3 ScrapeTemplate

**Table:** `scraper_template` — `models.py:123-186`

| Field | Type | Description |
|---|---|---|
| `id` | UUIDField | PK |
| `tenant_id` | CharField(128) | Multi-tenant, default="system" |
| `name` | CharField(255) | Template name |
| `site_pattern` | CharField(500) | URL pattern or domain |
| `category` | CharField(50) | One of 14 categories |
| `description` | TextField | Human-readable description |
| `language` | CharField(10) | Default language code |
| `engine` | CharField(20) | Default="playwright" |
| `selectors` | JSONField | CSS/XPath selector map |
| `workflow` | JSONField | Ordered step definitions |
| `options` | JSONField | Execution options |
| `parameters` | JSONField | Parameterized input definitions |
| `output_fields` | JSONField | Expected output field names |
| `use_count` | PositiveIntegerField | Execution counter |
| `success_rate` | FloatField | 0.0–1.0 success ratio |

### 5.4 ScrapeWorkflow (v4.0)

**Table:** `voyant_scrape_workflow` — `models.py:193-220`

| Field | Type | Description |
|---|---|---|
| `id` | UUIDField | PK |
| `tenant_id` | CharField(128) | Multi-tenant |
| `name` | CharField(255) | Workflow name |
| `description` | TextField | Description |
| `steps` | JSONField | Ordered step list |
| `input_schema` | JSONField | JSON Schema for inputs |
| `output_schema` | JSONField | JSON Schema for outputs |

### 5.5 ScrapeStep

**Table:** `voyant_scrape_step` — `models.py:223-288`

| Field | Type | Description |
|---|---|---|
| `id` | UUIDField | PK |
| `workflow` | FK → ScrapeWorkflow | Parent workflow |
| `order` | PositiveIntegerField | Execution order |
| `step_type` | CharField(32) | 14 types: navigate/click/scroll/wait/extract/enter_text/hover/screenshot/loop/condition/close_popup/back/new_tab/download |
| `selector` | CharField(1024) | CSS selector or XPath |
| `action` | CharField(255) | Action identifier |
| `wait_condition` | CharField(512) | CSS selector or timeout |
| `options` | JSONField | Step-specific config |

### 5.6 ScrapeProxy

**Table:** `voyant_scrape_proxy` — `models.py:435-486`

| Field | Type | Description |
|---|---|---|
| `proxy_type` | CharField(32) | residential/datacenter/mobile/isp |
| `provider` | CharField(128) | brightdata/oxylabs/smartproxy |
| `endpoints` | JSONField | List of proxy gateway URLs |
| `rotation_strategy` | CharField(32) | per_request/session/sticky |
| `is_active` | BooleanField | Active flag |

### 5.7 ScrapeFingerprint

**Table:** `voyant_scrape_fingerprint` — `models.py:489-524`

| Field | Type | Description |
|---|---|---|
| `user_agent` | TextField | User-Agent string |
| `viewport_width` | PositiveIntegerField | Default 1920 |
| `viewport_height` | PositiveIntegerField | Default 1080 |
| `webgl_vendor` | CharField(255) | WebGL vendor string |
| `webgl_renderer` | TextField | WebGL renderer string |

### 5.8 ScrapeSchedule

**Table:** `voyant_scrape_schedule` — `models.py:291-325`

| Field | Type | Description |
|---|---|---|
| `task` | FK → ScrapeJob | Parent job |
| `cron_expr` | CharField(128) | Cron expression |
| `timezone` | CharField(64) | Default "UTC" |
| `enabled` | BooleanField | Active flag |

### 5.9 ScrapeExport

**Table:** `voyant_scrape_export` — `models.py:328-367`

| Field | Type | Description |
|---|---|---|
| `task` | FK → ScrapeJob | Parent job |
| `format` | CharField(16) | json/csv/xlsx/xml/jsonl/parquet |
| `destination` | CharField(1024) | S3 path, webhook URL, file path |
| `auto_export` | BooleanField | Auto-export after each run |

### 5.10 AgentSkill

**Table:** `voyant_agent_skill` — `models.py:527-562`

| Field | Type | Description |
|---|---|---|
| `name` | CharField(255) | Unique skill identifier |
| `description` | TextField | Human-readable description |
| `steps` | JSONField | Ordered step definitions |
| `tools` | JSONField | List of MCP tool names |
| `parameters` | JSONField | JSON Schema for inputs |

---

## 6. API Endpoints

### 6.1 Core Scrape API (`scrape_router`)

| Method | Path | Schema | Auth | Description | Ref |
|---|---|---|---|---|---|
| POST | `/scrape/start` | ScrapeStartSchema → 202 ScrapeJobSchema | write:jobs | Start scraping job | `api.py:177-244` |
| POST | `/scrape/extract` | ScrapeExtractSchema | write:jobs | Extract data from HTML via selectors | `api.py:247-277` |
| POST | `/scrape/fetch` | ScrapeFetchSchema | write:jobs | Fetch single page | `api.py:280-301` |
| POST | `/scrape/deep_archive` | ScrapeDeepArchiveSchema | write:jobs | Deep archival scrape | `api.py:304-319` |
| POST | `/scrape/ocr` | ScrapeOcrSchema | write:jobs | OCR image processing | `api.py:322-330` |
| POST | `/scrape/parse_pdf` | ScrapePdfSchema | write:jobs | PDF text/table extraction | `api.py:333-341` |
| POST | `/scrape/transcribe` | ScrapeTranscribeSchema | write:jobs | Audio transcription | `api.py:344-355` |
| GET | `/scrape/status/{job_id}` | → ScrapeJobSchema | read:* | Job status | `api.py:358-375` |
| POST | `/scrape/cancel` | → {status, job_id} | write:jobs | Cancel job | `api.py:378-400` |
| GET | `/scrape/result/{job_id}` | → ScrapeResultSchema | read:* | Get artifacts | `api.py:403-424` |
| GET | `/scrape/metrics/{job_id}` | → metrics dict | read:* | Job metrics | `api.py:427-440` |
| POST | `/scrape/captcha/test` | CaptchaTestSchema | write:jobs | Test CAPTCHA solver | `api.py:468-524` |
| GET | `/scrape/captcha/status` | → CaptchaStatusSchema | read:* | CAPTCHA config status | `api.py:527-545` |
| GET | `/scrape/health` | → health dict | read:* | Service health check | `api.py:548-583` |

### 6.2 v4.0 Scraper Octopus API (`scraper_v2_router`)

| Method | Path | Auth | Description | Ref |
|---|---|---|---|---|
| POST | `/scraper-v2/workflows` | write:jobs | Create workflow | `api.py:627-654` |
| GET | `/scraper-v2/workflows` | read:* | List workflows | `api.py:657-676` |
| GET | `/scraper-v2/workflows/{id}` | read:* | Get workflow | `api.py:679-695` |
| PUT | `/scraper-v2/workflows/{id}` | write:jobs | Update workflow | `api.py:698-721` |
| DELETE | `/scraper-v2/workflows/{id}` | write:jobs | Delete workflow | `api.py:724-734` |
| POST | `/scraper-v2/steps` | write:jobs | Create step | `api.py:772-799` |
| GET | `/scraper-v2/workflows/{id}/steps` | read:* | List steps | `api.py:802-819` |
| PUT | `/scraper-v2/steps/{id}` | write:jobs | Update step | `api.py:822-843` |
| DELETE | `/scraper-v2/steps/{id}` | write:jobs | Delete step | `api.py:846-855` |
| POST | `/scraper-v2/schedules` | write:jobs | Create schedule | `api.py:886-909` |
| GET | `/scraper-v2/schedules` | read:* | List schedules | `api.py:912-930` |
| POST | `/scraper-v2/exports` | write:jobs | Create export config | `api.py:1012-1035` |
| GET | `/scraper-v2/exports` | read:* | List exports | `api.py:1038-1056` |
| POST | `/scraper-v2/runs` | write:jobs | Create run | `api.py:1133-1157` |
| GET | `/scraper-v2/runs` | read:* | List runs | `api.py:1160-1188` |
| PATCH | `/scraper-v2/runs/{id}` | write:jobs | Update run status | `api.py:1210-1262` |
| POST | `/scraper-v2/proxies` | write:jobs | Create proxy | `api.py:1309-1333` |
| GET | `/scraper-v2/proxies` | read:* | List proxies | `api.py:1336-1365` |
| POST | `/scraper-v2/fingerprints` | write:jobs | Create fingerprint | `api.py:1453-1477` |
| GET | `/scraper-v2/fingerprints` | read:* | List fingerprints | `api.py:1480-1497` |
| POST | `/scraper-v2/fingerprints/generate` | write:jobs | Generate random fingerprint | `api.py:1556-1585` |
| POST | `/scraper-v2/agent-skills` | write:jobs | Create agent skill | `api.py:1620-1644` |
| GET | `/scraper-v2/agent-skills` | read:* | List agent skills | `api.py:1647-1664` |

### 6.3 Request/Response Schemas

**ScrapeStartSchema** (`api.py:29-34`):
```json
{
  "urls": ["https://example.com"],
  "selectors": {"title": "h1", "price": ".price-value"},
  "options": {"engine": "playwright", "timeout": 30, "scroll": true}
}
```

**ScrapeFetchSchema** (`api.py:65-80`):
```json
{
  "url": "https://example.com",
  "engine": "playwright",
  "wait_for": ".content-loaded",
  "scroll": false,
  "timeout": 30,
  "block_resources": true,
  "capture_json": false
}
```

---

## 7. Anti-Bot Engine Architecture

### 7.1 4-Tier Hybrid CAPTCHA Solver Chain

```
┌─────────────────────────────────────────────────────────────────┐
│                    HybridCaptchaSolver                           │
│                   (captcha_hybrid.py:22)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CAPTCHA Type          Chain                                    │
│  ─────────────         ──────────────────────────────           │
│  reCAPTCHA v3  →  Tier 1 (behavioral)  →  Tier 4 (human farm) │
│  reCAPTCHA v2  →  Tier 2 (audio/whisper) → Tier 4 (human farm)│
│  hCaptcha      →  Tier 3 (vision LLM)  →  Tier 4 (human farm) │
│  Turnstile     →  Tier 4 (human farm) directly                 │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ Tier 1: BehavioralCaptchaSolver (captcha_behavioral.py:22)     │
│   - Bézier curve mouse movement simulation                     │
│   - Natural scroll events (2-4 down, 40% scroll-back)          │
│   - Keyboard events (Tab, Arrow keys)                          │
│   - Page dwell time (3-7 seconds)                              │
│   - Target: reCAPTCHA v3 score ≥ 0.7                           │
│   - Cost: $0, Latency: <1s                                     │
├─────────────────────────────────────────────────────────────────┤
│ Tier 2: AudioCaptchaSolver (captcha_audio.py:90)               │
│   - Clicks reCAPTCHA checkbox → finds audio challenge           │
│   - Downloads MP3 from audio source URL                        │
│   - Transcribes via faster-whisper (preferred) or openai-whisper│
│   - Cleans transcript (alphanumeric only)                      │
│   - Types answer, clicks verify                                │
│   - Retries with different Whisper model sizes                 │
│   - Cost: $0, Latency: 2-3s                                    │
├─────────────────────────────────────────────────────────────────┤
│ Tier 3: VisionCaptchaSolver (captcha_vision.py:37)             │
│   - Resolves LLM config: explicit → DB → env settings          │
│   - Text CAPTCHA: screenshot → base64 → vision LLM → parse     │
│   - hCaptcha grid: screenshot → LLM identifies tiles → click   │
│   - OpenAI-compatible /chat/completions with image_url          │
│   - Cost: ~$0.01, Latency: 3-5s                                │
├─────────────────────────────────────────────────────────────────┤
│ Tier 4: MultiProviderCaptchaSolver (captcha_solver.py:609)     │
│   - Chains: 2Captcha → AntiCaptcha → CapSolver                  │
│   - Each provider: submit task → poll result (5s interval)      │
│   - 300s timeout per provider                                  │
│   - Cost: $1-3/1K solves, Latency: 10-60s                      │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Fingerprint Randomizer

The `BrowserFingerprint` class (`fingerprint.py:131-460`) generates realistic fingerprints:

```
┌─────────────────────────────────────────────┐
│           BrowserFingerprint.random()        │
├─────────────────────────────────────────────┤
│ User-Agent    ← Chrome/Firefox/Safari + OS  │
│ Viewport      ← 10 common desktop resolutions│
│ WebGL         ← 15 vendor/renderer combos   │
│ Navigator     ← languages, cores, memory    │
│ Screen        ← color_depth, pixel_ratio    │
│ Canvas Noise  ← deterministic per-fp seed   │
│ Audio Noise   ← frequency perturbation      │
└─────────────────────────────────────────────┘
         ↓ apply_to_page(page)
┌─────────────────────────────────────────────┐
│ page.add_init_script(js_overrides)           │
│ - navigator.userAgent, .platform, .languages │
│ - navigator.hardwareConcurrency, .deviceMemory│
│ - screen.colorDepth, .width, .height         │
│ - WebGLRenderingContext.getParameter override │
│ - Canvas getImageData noise injection        │
│ - AudioContext oscillator perturbation       │
└─────────────────────────────────────────────┘
```

### 7.3 Proxy Manager

The `ProxyManager` (`proxy_manager.py:127-308`) manages proxy rotation:

| Strategy | Algorithm | Description |
|---|---|---|
| `round_robin` | Index-based cycling | Sequential proxy selection |
| `random` | Random choice | Random usable proxy per request |
| `least_used` | Minimum total_uses | Distributes load evenly |

**Health tracking:** Failed proxies enter 60s cooldown. Per-proxy success/fail counters. Provider integrations: BrightData, SmartProxy, Oxylabs (`proxy_manager.py:320-395`).

---

## 8. MCP Tool Catalog

13 agent-accessible tools defined in `apps/mcp/tools_scraper_ops.py`:

| # | Tool Name | Description | Key Params | Ref |
|---|---|---|---|---|
| 1 | `voyant.scraper.template.list` | List templates by category | category, limit | `tools_scraper_ops.py:36-80` |
| 2 | `voyant.scraper.template.run` | Execute template with params | template_id, parameters | `tools_scraper_ops.py:88-180` |
| 3 | `voyant.scraper.task.create` | Create scrape job (no exec) | urls, selectors, options | `tools_scraper_ops.py:188-233` |
| 4 | `voyant.scraper.task.run` | Execute existing job via Temporal | job_id | `tools_scraper_ops.py:241-299` |
| 5 | `voyant.scraper.task.status` | Check job or run status | job_id, run_id | `tools_scraper_ops.py:307-382` |
| 6 | `voyant.scraper.workflow.create` | Create visual workflow | name, steps, schemas | `tools_scraper_ops.py:390-441` |
| 7 | `voyant.scraper.workflow.run` | Execute workflow | workflow_id, input_params | `tools_scraper_ops.py:449-540` |
| 8 | `voyant.scraper.ai.generate` | NL → task config (zero-LLM) | description | `tools_scraper_ops.py:548-664` |
| 9 | `voyant.scraper.ai.match` | URL → best template match | url | `tools_scraper_ops.py:833-936` |
| 10 | `voyant.scraper.export` | Export results (JSON/CSV/XLSX) | job_id, format | `tools_scraper_ops.py:944-1080` |
| 11 | `voyant.scraper.stream` | Stream results as JSONL | job_id, limit, offset | `tools_scraper_ops.py:1088-1151` |
| 12 | `voyant.scraper.skill.list` | List agent skills | limit | `tools_scraper_ops.py:1159-1197` |
| 13 | `voyant.scraper.skill.execute` | Execute agent skill | skill_id, parameters | `tools_scraper_ops.py:1205-1295` |

---

## 9. Integration Points

| System | Integration | Direction | Ref |
|---|---|---|---|
| **Temporal** | Workflow orchestration for all scrape jobs | Outbound | `api.py:144-169` |
| **Playwright** | Browser automation engine | Outbound | `fingerprint.py:237`, `captcha_behavioral.py:170` |
| **MinIO/S3** | Artifact storage | Outbound | `models.py:108` |
| **2Captcha** | Commercial CAPTCHA solving | Outbound | `captcha_solver.py:148-296` |
| **AntiCaptcha** | Commercial CAPTCHA solving | Outbound | `captcha_solver.py:304-449` |
| **CapSolver** | Commercial CAPTCHA solving | Outbound | `captcha_solver.py:457-601` |
| **Whisper (faster/openai)** | Audio transcription for Tier 2 | Outbound | `captcha_audio.py:24-53` |
| **Vision LLM (OpenAI-compat)** | Image CAPTCHA solving for Tier 3 | Outbound | `captcha_vision.py:132-193` |
| **Redis** | Event publishing (scraper events) | Outbound | `api.py:223` |
| **MCP Protocol** | Agent tool invocation | Inbound | `tools_scraper_ops.py` |

---

## 10. Quality Attributes

| Attribute | Target | Evidence |
|---|---|---|
| **CAPTCHA Solve Rate** | >90% hybrid (SRS SCR-F-020) | 4-tier chain with fallback |
| **SSRF Protection** | 100% URL validation | `api.py:200-203` |
| **Template Search Latency** | <500ms with debounce | `view-scraper.ts:171` (400ms debounce) |
| **Job Execution** | Durable via Temporal | Auto-retry, cancellation, timeout |
| **Concurrency** | Thread-safe proxy manager | `proxy_manager.py:157` (threading.Lock) |
| **Fingerprint Uniqueness** | 10^9+ combinations | 7 Chrome versions × 10 viewports × 15 WebGL × ... |
| **Multi-Tenancy** | Full isolation | tenant_id on all queries |

---

## 11. Implementation References

| Component | File | Key Lines |
|---|---|---|
| Template model | `apps/scraper/models.py` | 123–186 |
| Core API | `apps/scraper/api.py` | 1–583 |
| v4.0 API | `apps/scraper/api.py` | 588–1700+ |
| CAPTCHA solver chain | `apps/scraper/services/captcha_solver.py` | 1–777 |
| Behavioral solver | `apps/scraper/services/captcha_behavioral.py` | 1–257 |
| Audio solver | `apps/scraper/services/captcha_audio.py` | 1–347 |
| Vision solver | `apps/scraper/services/captcha_vision.py` | 1–419 |
| Hybrid orchestrator | `apps/scraper/services/captcha_hybrid.py` | 1–323 |
| Proxy manager | `apps/scraper/services/proxy_manager.py` | 1–395 |
| Fingerprint randomizer | `apps/scraper/services/fingerprint.py` | 1–533 |
| MCP scraper tools | `apps/mcp/tools_scraper_ops.py` | 1–1295 |
| Dashboard view | `dashboard/src/views/view-scraper.ts` | 1–1177 |
