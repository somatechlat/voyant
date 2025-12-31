# DataScraper Module - Software Requirements Specification
## Voyant Scraper Module (voyant/scraper)

| Document ID | VOYANT-SCRAPER-SRS-1.0.0 |
|-------------|--------------------------|
| Version | 1.0.0 |
| Date | 2025-12-30 |
| Status | APPROVED |
| Parent | Voyant v3.0.0 |

---

## 1. Introduction

### 1.1 Purpose

This document specifies the requirements for the **DataScraper** module, a web scraping subsystem built as an integral part of the Voyant platform. The module extends Voyant's data intelligence capabilities with browser automation, LLM-driven extraction, OCR, and media transcription.

### 1.2 Scope

| Capability | Description |
|------------|-------------|
| **URL Fetching** | Playwright-based browser automation with anti-bot handling |
| **LLM Extraction** | AI-driven CSS/XPath selector generation |
| **Media Processing** | OCR (images/PDFs), audio/video transcription |
| **Schema Normalization** | Unified JSON output via Voyant contracts |
| **MCP Integration** | `scrape.*` tools for agent workflows |
| **REST API** | Django Ninja endpoints at `/v1/scrape/*` |

### 1.3 Module Location

```
voyant/
├── scraper/                    # THIS MODULE
│   ├── __init__.py
│   ├── models.py               # Django ORM models
│   ├── api.py                  # Django Ninja router
│   ├── tasks.py                # Celery/Temporal tasks
│   ├── browser/
│   │   ├── __init__.py
│   │   └── playwright_client.py
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── selectors.py
│   │   └── llm_selectors.py
│   └── media/
│       ├── __init__.py
│       ├── ocr.py
│       └── transcription.py
├── workflows/
│   └── scrape_workflow.py      # Temporal workflow
├── activities/
│   └── scrape_activities.py    # Temporal activities
└── mcp/
    └── server.py               # UPDATE: Add scrape.* tools
```

### 1.4 Technology Stack (VIBE Compliant + Full Scraping Toolkit)

| Layer | Technology | Purpose |
|-------|------------|---------|
| **API** | Django Ninja | REST endpoints |
| **ORM** | Django ORM | Model persistence |
| **Auth** | Django Auth + Keycloak | Authentication |
| **Sessions** | Django Sessions | Session management |

#### Scraping Toolkit (Multi-Engine)

| Tool | Purpose | Use Case |
|------|---------|----------|
| **Playwright** | Modern browser automation | JavaScript-heavy sites, SPA |
| **Selenium** | Classic browser automation | Legacy sites, form filling |
| **Scrapy** | High-performance crawling | Large-scale crawls, sitemaps |
| **BeautifulSoup** | HTML parsing | Static HTML extraction |
| **lxml** | Fast XML/HTML parsing | XPath queries |
| **requests-html** | Simple HTTP + JS | Quick page fetches |

#### Apache Integrations (Voyant Ecosystem)

| Apache Tool | Purpose | Integration |
|-------------|---------|-------------|
| **Apache Tika** | Document extraction (PDF, DOC, etc.) | `voyant/ingestion/tika.py` |
| **Apache NiFi** | Dataflow routing, ETL pipelines | `voyant/ingestion/nifi.py` |
| **Apache Kafka** | Event streaming | Existing Voyant integration |
| **Apache Iceberg** | Lakehouse storage | Existing Voyant integration |

#### Media Processing

| Library | Purpose | Target |
|---------|---------|--------|
| **pytesseract** | OCR (images) | Image → Text |
| **pdf2image** | PDF rendering | PDF → Images |
| **pdfplumber** | PDF text extraction | PDF → Text (structured) |
| **SpeechRecognition** | Audio transcription | Audio → Text |
| **ffmpeg-python** | Media processing | Video/Audio extraction |
| **Whisper** | AI transcription (optional) | High-quality audio → Text |

---

## 2. Functional Requirements

### FR-SCR-001: Job Creation

| Attribute | Value |
|-----------|-------|
| **Priority** | HIGH |
| **Input** | URLs, LLM prompt, options (OCR, media) |
| **Output** | Job ID (UUID), HTTP 202 Accepted |
| **Storage** | `ScrapeJob` Django model |

**Acceptance Criteria:**
- Payload validated against `ScrapeStartSchema`
- Job created with status `queued`
- Temporal workflow triggered asynchronously

### FR-SCR-002: URL Fetching

| Attribute | Value |
|-----------|-------|
| **Priority** | HIGH |
| **Browser** | Playwright (headless Chromium) |
| **Anti-bot** | robots.txt, rate-limit, proxy rotation |
| **Success Rate** | ≥ 95% on reachable pages |

**Implementation:**
```python
# voyant/scraper/browser/playwright_client.py
from playwright.async_api import async_playwright

class PlaywrightClient:
    async def fetch_page(self, url: str, options: dict) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            html = await page.content()
            await browser.close()
            return html
```

### FR-SCR-003: LLM Selector Generation

| Attribute | Value |
|-----------|-------|
| **Priority** | MEDIUM |
| **LLM Provider** | OpenAI GPT-4 / Claude |
| **Accuracy** | ≥ 90% on benchmark dataset |

**Prompt Template:**
```python
SELECTOR_PROMPT = """
Analyze this HTML and generate CSS/XPath selectors for:
{user_prompt}

HTML:
{html_content}

Output JSON with:
- selectors: list of CSS/XPath
- confidence: 0.0-1.0
- field_mapping: dict of field names to selectors
"""
```

### FR-SCR-004: Media Extraction

| Capability | Library | Accuracy Target |
|------------|---------|-----------------|
| **OCR (images)** | pytesseract | F-score ≥ 0.85 |
| **OCR (PDFs)** | pdf2image + pytesseract | F-score ≥ 0.85 |
| **Transcription** | SpeechRecognition + ffmpeg | WER ≤ 0.12 |

### FR-SCR-005: Schema Normalization

- Use `voyant/core/contracts.py` for schema validation
- All output validates against JSON schema
- Fields: `url`, `title`, `content`, `extracted_data`, `metadata`

### FR-SCR-006: Result Packaging

| Format | Library | Endpoint |
|--------|---------|----------|
| JSON | Native | `/v1/scrape/result/{job_id}?format=json` |
| CSV | csv | `/v1/scrape/result/{job_id}?format=csv` |
| HTML | jinja2 | `/v1/scrape/result/{job_id}?format=html` |

### FR-SCR-007: Job Monitoring

| Metric | Prometheus Name | Labels |
|--------|-----------------|--------|
| Pages fetched | `voyant_scrape_pages_total` | job_id |
| Bytes processed | `voyant_scrape_bytes_total` | job_id |
| OCR success rate | `voyant_scrape_ocr_success` | job_id |
| Job duration | `voyant_scrape_duration_seconds` | job_id |

### FR-SCR-008: Job Cancellation

- Transition job status to `cancelled`
- Cancel Temporal workflow
- Clean up partial artifacts

### FR-SCR-009: Audit Logging

- Use Voyant's `voyant/core/audit_trail.py`
- Log: job_id, timestamp, event_type, actor, details
- Immutable append-only

### FR-SCR-010: Security Checks

| Check | Implementation |
|-------|----------------|
| robots.txt | Parse and respect before fetch |
| Rate limiting | Redis per-domain counters |
| Proxy rotation | Configurable proxy pool |
| CAPTCHA detection | Event hook `scrape.captcha.required` |

---

## 3. Django ORM Models

```python
# voyant/scraper/models.py
import uuid
from django.db import models

class ScrapeJob(models.Model):
    """Web scraping job record."""
    
    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        RUNNING = 'running', 'Running'
        SUCCEEDED = 'succeeded', 'Succeeded'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    job_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tenant_id = models.CharField(max_length=128, db_index=True)
    status = models.CharField(max_length=64, choices=Status.choices, default=Status.QUEUED)
    
    # Input
    urls = models.JSONField()
    llm_prompt = models.TextField(blank=True)
    options = models.JSONField(default=dict)
    
    # Progress
    pages_fetched = models.IntegerField(default=0)
    bytes_processed = models.BigIntegerField(default=0)
    ocr_success_rate = models.FloatField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    
    # Error
    error_message = models.TextField(blank=True)
    
    class Meta:
        db_table = 'voyant_scrape_job'
        indexes = [
            models.Index(fields=['tenant_id', 'status']),
            models.Index(fields=['created_at']),
        ]

class ScrapeArtifact(models.Model):
    """Artifact produced by scraping job."""
    
    class ArtifactType(models.TextChoices):
        HTML = 'html', 'HTML'
        JSON = 'json', 'JSON'
        CSV = 'csv', 'CSV'
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'
        PDF = 'pdf', 'PDF'
    
    artifact_id = models.CharField(max_length=512, primary_key=True)
    job = models.ForeignKey(ScrapeJob, on_delete=models.CASCADE, related_name='artifacts')
    artifact_type = models.CharField(max_length=64, choices=ArtifactType.choices)
    format = models.CharField(max_length=32)
    storage_path = models.CharField(max_length=512)
    size_bytes = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'voyant_scrape_artifact'
```

---

## 4. Django Ninja API

```python
# voyant/scraper/api.py
from ninja import Router, Schema
from typing import List, Dict, Any, Optional
from .models import ScrapeJob, ScrapeArtifact
from .tasks import start_scrape_workflow

scrape_router = Router(tags=["scrape"])

class ScrapeStartSchema(Schema):
    urls: List[str]
    llm_prompt: Optional[str] = None
    options: Optional[Dict[str, Any]] = None

class ScrapeJobSchema(Schema):
    job_id: str
    status: str
    pages_fetched: int
    bytes_processed: int
    created_at: str

@scrape_router.post("/scrape/start", response={202: ScrapeJobSchema})
def start_scrape(request, payload: ScrapeStartSchema):
    """Start a new scraping job."""
    job = ScrapeJob.objects.create(
        tenant_id=request.headers.get('X-Tenant-ID', 'default'),
        urls=payload.urls,
        llm_prompt=payload.llm_prompt or "",
        options=payload.options or {},
    )
    start_scrape_workflow.delay(str(job.job_id))
    return 202, ScrapeJobSchema.from_orm(job)

@scrape_router.get("/scrape/status/{job_id}", response=ScrapeJobSchema)
def get_scrape_status(request, job_id: str):
    """Get job status."""
    job = ScrapeJob.objects.get(job_id=job_id)
    return ScrapeJobSchema.from_orm(job)

@scrape_router.post("/scrape/cancel")
def cancel_scrape(request, job_id: str):
    """Cancel a running job."""
    job = ScrapeJob.objects.get(job_id=job_id)
    job.status = ScrapeJob.Status.CANCELLED
    job.save()
    return {"status": "cancelled", "job_id": job_id}

@scrape_router.get("/scrape/result/{job_id}")
def get_scrape_result(request, job_id: str, format: str = "json"):
    """Get job results."""
    artifacts = ScrapeArtifact.objects.filter(job_id=job_id)
    return {"job_id": job_id, "artifacts": list(artifacts.values())}
```

---

## 5. MCP Tools

| Tool | Description | REST Mapping |
|------|-------------|--------------|
| `scrape.start` | Start scraping job | `POST /v1/scrape/start` |
| `scrape.status` | Get job status | `GET /v1/scrape/status/{job_id}` |
| `scrape.cancel` | Cancel job | `POST /v1/scrape/cancel` |
| `scrape.result` | Get results | `GET /v1/scrape/result/{job_id}` |
| `scrape.metrics` | Get metrics | `GET /v1/scrape/metrics/{job_id}` |

---

## 6. Dependencies

```toml
# pyproject.toml additions

[tool.poetry.dependencies]
# Scraping Engines
playwright = "^1.40"
selenium = "^4.15"
scrapy = "^2.11"
beautifulsoup4 = "^4.12"
lxml = "^5.0"
requests-html = "^0.10"
httpx = "^0.25"

# Apache Integrations
tika = "^2.6"                    # Apache Tika client
# (NiFi via REST API - no Python package needed)

# Media Processing
pytesseract = "^0.3.10"
pdf2image = "^1.16"
pdfplumber = "^0.10"
ffmpeg-python = "^0.2.0"
SpeechRecognition = "^3.10"
openai-whisper = "^20231117"     # Optional: AI transcription

# Utilities
fake-useragent = "^1.4"          # User-Agent rotation
python-magic = "^0.4"            # MIME type detection
```

```bash
# System dependencies (Docker)
apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    poppler-utils \
    ffmpeg \
    chromium \
    libmagic1
```

---

## 7. Verification & Testing

| Test | Criteria |
|------|----------|
| **Unit** | 90% coverage |
| **Integration** | All endpoints functional |
| **E2E** | Scrape real public page |
| **Performance** | 200 concurrent jobs, ≤30s/page |

---

## 8. Traceability Matrix

| Requirement | Model | API | MCP | Workflow |
|-------------|-------|-----|-----|----------|
| FR-SCR-001 | `ScrapeJob` | `/scrape/start` | `scrape.start` | `ScrapeWorkflow` |
| FR-SCR-002 | - | - | - | `FetchActivity` |
| FR-SCR-003 | - | - | - | `LLMSelectorActivity` |
| FR-SCR-004 | `ScrapeArtifact` | - | - | `OCRActivity`, `TranscribeActivity` |
| FR-SCR-005 | - | - | - | `NormalizeActivity` |
| FR-SCR-006 | - | `/scrape/result` | `scrape.result` | - |
| FR-SCR-007 | - | `/scrape/metrics` | `scrape.metrics` | - |
| FR-SCR-008 | `ScrapeJob` | `/scrape/cancel` | `scrape.cancel` | - |

---

**END OF SRS**
