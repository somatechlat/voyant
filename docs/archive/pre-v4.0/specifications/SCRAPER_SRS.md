# Voyant Scraper v3.0.0 - Software Requirements Specification

**Document ID:** VOYANT-SCRAPER-SRS-3.0.0  
**Version:** 3.0.0  
**Status:** Draft  
**Date:** 2026-02-18  
**Compliance:** ISO/IEC 25010, ISO/IEC/IEEE 29148:2018  
**Module:** Voyant DataScraper  

---

## 1. Introduction

### 1.1 Purpose

This document defines the comprehensive software requirements for the Voyant DataScraper v3.0.0 module. The DataScraper is an enterprise-grade, autonomous web scraping service designed specifically for AI agents, providing end-to-end data extraction capabilities with human-in-the-loop (HITL) support for complex scenarios.

The primary objectives are:
- **Performance:** Surpass commercial scraping APIs (ZenRows, Scrape.do) with response times < 2s and success rates > 99%
- **Reliability:** Enterprise-proven architecture using Apache ecosystem tools
- **Scalability:** Distributed architecture supporting 100K+ URLs per job
- **Intelligence:** HITL integration for CAPTCHA solving and anti-bot bypass
- **Compliance:** ISO 25010 software quality standards

### 1.2 Scope

The DataScraper module encompasses:

**Core Capabilities:**
- Multi-engine web scraping (Playwright, httpx, Scrapy, Selenium)
- JavaScript rendering and SPA support
- Anti-detection and fingerprinting management
- CAPTCHA detection and HITL resolution
- Document extraction (PDF, DOCX, images)
- OCR and media transcription
- Distributed job processing

**Enterprise Integration:**
- Apache NiFi for dataflow orchestration
- Apache Tika for document processing
- Apache PDFBox for PDF extraction
- Redis for job queue management
- Temporal for workflow orchestration
- Kafka for event streaming

**Agent Interface:**
- REST API endpoints
- MCP tool integration
- Pure execution model (no LLM dependency)
- Real-time progress monitoring

### 1.3 Definitions and Abbreviations

| Term | Definition |
|------|------------|
| HITL | Human In The Loop - Manual intervention for complex cases |
| SSRF | Server-Side Request Forgery - Security vulnerability |
| CAPTCHA | Completely Automated Public Turing test to tell Computers and Humans Apart |
| TLS | Transport Layer Security |
| JA3 | TLS client fingerprinting technique |
| CDP | Chrome DevTools Protocol |
| RPA | Robotic Process Automation |
| SOCKS5 | SOCKet Secure protocol version 5 |
| UA | User-Agent string |

### 1.4 Document Conventions

- **"Shall"** denotes a mandatory requirement
- **"Should"** denotes a recommended requirement
- **"May"** denotes an optional requirement
- Present tense describes current implementation behavior
- All requirements are traceable to test cases

---

## 2. Product Perspective

### 2.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Voyant DataScraper v3.0.0                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   REST API      │  │   MCP Tools     │  │   HITL Interface           │  │
│  │   (Django)      │  │   (django-mcp)  │  │   (Web Dashboard)          │  │
│  └────────┬────────┘  └────────┬────────┘  └─────────────┬───────────────┘  │
│           │                    │                          │                   │
│  ┌────────▼────────────────────▼──────────────────────────▼───────────────┐  │
│  │                    Agent-Tool Orchestration Layer                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │  │
│  │  │ Job Manager │  │ Rate Limiter│  │ Auth Guard  │  │ Policy Enf. │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                          │
│  ┌─────────────────────────────────▼────────────────────────────────────────┐ │
│  │                    Execution Engine Layer                                │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │ │
│  │  │ Playwright  │  │   httpx     │  │   Scrapy    │  │  Selenium   │   │ │
│  │  │  (Browser)  │  │  (Static)   │  │  (Spider)   │  │  (Legacy)   │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │ │
│  │                                                                      │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │ │
│  │  │ Anti-Detect │  │ CAPTCHA     │  │ HITL Queue  │  │ Proxy Mgr   │   │ │
│  │  │ Fingerprint │  │ Resolver    │  │ (Redis)     │  │ (Rotation)  │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                          │
│  ┌─────────────────────────────────▼────────────────────────────────────────┐ │
│  │                    Processing & Storage Layer                            │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │ │
│  │  │ Apache NiFi │  │ Apache Tika │  │ OCR Engine  │  │ Transcription│   │ │
│  │  │ Dataflows   │  │ Documents   │  │ (Tesseract) │  │  (Whisper)  │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │ │
│  │                                                                      │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │ │
│  │  │  MinIO      │  │  PostgreSQL │  │   Kafka     │  │  Temporal   │   │ │
│  │  │  (Artifacts)│  │  (Metadata) │  │  (Events)   │  │  (Workflows)│   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 External Interfaces

**User Interfaces:**
- REST API (Django Ninja)
- MCP Tools (JSON-RPC 2.0)
- HITL Dashboard (Web UI)
- CLI Commands

**Hardware Interfaces:**
- CPU: x86_64, ARM64 (multi-architecture)
- Memory: Minimum 4GB RAM (16GB recommended)
- Storage: 100GB SSD minimum
- Network: 1Gbps connectivity

**Software Interfaces:**
- PostgreSQL 16+ (metadata storage)
- Redis 7+ (job queue, caching)
- Apache Kafka 3.7+ (event streaming)
- Temporal (workflow orchestration)
- MinIO/S3 (artifact storage)

---

## 3. Functional Requirements

### 3.1 Core Scraping Engine (FR-SCR-001)

#### 3.1.1 Multi-Engine Support

**FR-SCR-001.1** The system shall support multiple scraping engines:
- Playwright for JavaScript-rendered pages
- httpx for fast static HTML retrieval
- Scrapy for large-scale crawling
- Selenium for broad browser support

**FR-SCR-001.2** The system shall automatically select the optimal engine based on:
- URL characteristics (static vs. dynamic)
- Required features (JavaScript rendering, form interaction)
- Performance requirements
- Resource constraints

**FR-SCR-001.3** The system shall allow explicit engine selection via API parameters.

#### 3.1.2 Browser Automation

**FR-SCR-001.4** The system shall provide browser automation capabilities:
- Page navigation with configurable wait conditions
- Element interaction (click, fill, hover, drag)
- Form submission and authentication flows
- Scroll and navigation handling
- Screenshot and PDF capture

**FR-SCR-001.5** The system shall support Chrome DevTools Protocol (CDP) for:
- Network request/response interception
- JavaScript injection and execution
- Console log capture
- Performance profiling

### 3.2 Anti-Detection System (FR-SCR-002)

#### 3.2.1 Fingerprint Management

**FR-SCR-002.1** The system shall implement browser fingerprint randomization:
- User-Agent rotation from curated list
- Canvas fingerprint noise injection
- WebGL vendor/renderer spoofing
- AudioContext fingerprint modification
- Screen resolution and color depth randomization
- Timezone and locale spoofing
- Navigator properties randomization

**FR-SCR-002.2** The system shall implement TLS fingerprinting (JA3/JA4):
- Custom TLS client hello generation
- Cipher suite randomization
- Extension ordering randomization
- Elliptic curve randomization

#### 3.2.2 Proxy Management

**FR-SCR-002.3** The system shall support multiple proxy protocols:
- HTTP/HTTPS proxies
- SOCKS5 proxies
- SSH tunnels
- Residential proxies
- Datacenter proxies
- Mobile proxies

**FR-SCR-002.4** The system shall implement intelligent proxy rotation:
- Round-robin distribution
- Geographic targeting
- Failure-based rotation
- Performance-based selection
- Sticky sessions for authentication flows

**FR-SCR-002.5** The system shall validate proxy connectivity before use:
- Latency measurement
- Bandwidth testing
- IP leak detection
- Anonymity verification

### 3.3 CAPTCHA Handling (FR-SCR-003)

#### 3.3.1 CAPTCHA Detection

**FR-SCR-003.1** The system shall detect common CAPTCHA types:
- reCAPTCHA v2/v3/Enterprise
- hCAPTCHA
- Cloudflare Turnstile
- Image-based CAPTCHAs
- Text-based CAPTCHAs
- Math CAPTCHAs
- Slider/jigsaw CAPTCHAs
- Biometric CAPTCHAs

**FR-SCR-003.2** The system shall analyze page content for CAPTCHA indicators:
- Iframe detection
- Challenge page patterns
- JavaScript challenge detection
- Behavioral detection

#### 3.3.2 Automated Solving

**FR-SCR-003.3** The system shall integrate with CAPTCHA solving services:
- 2Captcha API
- Anti-Captcha API
- DeathByCaptcha API
- Custom ML-based solver (optional)

**FR-SCR-003.4** The system shall implement ML-based CAPTCHA solving:
- Image preprocessing and enhancement
- Character recognition
- Audio captcha transcription
- Slider trajectory prediction

**FR-SCR-003.5** The system shall track CAPTCHA solving metrics:
- Success rate per CAPTCHA type
- Average solve time
- Cost per solve
- Provider performance

### 3.4 Human In The Loop (FR-SCR-004)

#### 3.4.1 HITL Trigger Conditions

**FR-SCR-004.1** The system shall automatically trigger HITL when:
- CAPTCHA cannot be solved automatically (3 attempts)
- Anti-bot challenge detected (Cloudflare, PerimeterX)
- Login/authentication required with unknown credentials
- Payment gateway or sensitive data access
- Rate limiting triggered with exponential backoff exhausted
- JavaScript errors in critical page rendering
- Form validation requires human judgment
- Custom trigger rules defined by user

**FR-SCR-004.2** The system shall allow configurable HITL triggers:
- Per-job HITL enable/disable
- Per-URL HITL rules
- CAPTCHA type-specific handling
- Domain-specific workflows

#### 3.4.2 HITL Interface

**FR-SCR-004.3** The system shall provide a web-based HITL interface:
- Real-time job status display
- Page screenshot preview
- Interactive browser console
- Manual form filling
- CAPTCHA image/audio display
- Solution input fields
- Continue/cancel job controls

**FR-SCR-004.4** The system shall support asynchronous HITL resolution:
- Job pause on human intervention request
- Notification system (email, webhook, Slack)
- Timeout handling (configurable per job)
- Auto-cancel after timeout

**FR-SCR-004.5** The system shall record HITL interactions:
- Human operator ID
- Timestamp and duration
- Actions taken
- Solution provided
- Success/failure outcome

### 3.5 Document Processing (FR-SCR-005)

#### 3.5.1 Apache Tika Integration

**FR-SCR-005.1** The system shall integrate Apache Tika for document extraction:
- PDF text and metadata extraction
- Microsoft Office documents (DOCX, XLSX, PPTX)
- OpenDocument formats
- HTML and XML parsing
- EPub and MOBI e-books
- Image metadata (EXIF, IPTC)
- Audio/video metadata

**FR-SCR-005.2** The system shall extract structured data from documents:
- Table detection and extraction
- Header/footer identification
- Footnote and endnote extraction
- Hyperlink extraction
- Embedded image extraction

#### 3.5.2 PDF Processing

**FR-SCR-005.3** The system shall provide advanced PDF processing:
- Text extraction with layout preservation
- Table extraction (using pdfplumber)
- Form field extraction
- Signature detection
- Watermark identification
- Digital certificate extraction
- Multi-language support (Unicode)

#### 3.5.3 OCR Processing

**FR-SCR-005.4** The system shall provide OCR capabilities:
- Tesseract integration for image text extraction
- Multi-language support (100+ languages)
- Layout analysis (columns, tables)
- Handwriting recognition (English, Latin scripts)
- Confidence scoring
- Batch processing

### 3.6 Media Processing (FR-SCR-006)

#### 3.6.1 Audio Transcription

**FR-SCR-006.1** The system shall integrate OpenAI Whisper for transcription:
- Multiple model sizes (tiny, base, small, medium, large)
- Language detection and transcription
- Timestamp generation
- Speaker diarization (multi-speaker)
- Punctuation restoration
- Word-level timestamps

**FR-SCR-006.2** The system shall support audio preprocessing:
- Noise reduction
- Normalization
- Format conversion (MP3, WAV, OGG, M4A)
- Silence trimming

#### 3.6.2 Video Processing

**FR-SCR-006.3** The system shall extract frames from video:
- Keyframe extraction
- Thumbnail generation
- Scene detection
- Subtitle/caption extraction
- Audio track separation

### 3.7 Data Extraction (FR-SCR-007)

#### 3.7.1 Selector-Based Extraction

**FR-SCR-007.1** The system shall support multiple selector types:
- CSS selectors (level 3)
- XPath 1.0/2.0 expressions
- Regular expressions
- JSONPath queries
- Text pattern matching

**FR-SCR-007.2** The system shall provide selector functions:
- Attribute extraction
- Text content extraction
- HTML serialization
- Inner/outer HTML
- Element visibility

#### 3.7.2 Structured Data Extraction

**FR-SCR-007.3** The system shall extract structured data:
- Product information (e-commerce)
- Article metadata (news sites)
- Social media posts
- Financial data tables
- Contact information
- Event listings

**FR-SCR-007.4** The system shall support data validation:
- Type checking (string, number, date)
- Format validation (email, phone, URL)
- Range validation
- Pattern matching
- Cross-field validation

### 3.8 Job Management (FR-SCR-008)

#### 3.8.1 Job Lifecycle

**FR-SCR-008.1** The system shall manage job lifecycle:
- Job creation with parameters
- Queue management with priority
- Progress tracking and updates
- Checkpoint and resume capability
- Job cancellation and retry
- Error handling and recovery

**FR-SCR-008.2** The system shall support batch processing:
- Bulk URL submission (up to 100,000 per job)
- Distributed processing across workers
- Parallel execution with configurable concurrency
- Rate limiting per domain
- Respect for robots.txt

#### 3.8.2 Scheduling

**FR-SCR-008.3** The system shall support job scheduling:
- One-time execution
- Recurring schedules (cron expressions)
- Delayed execution
- Dependency-based execution
- Queue prioritization

### 3.9 Output Management (FR-SCR-009)

#### 3.9.1 Artifact Storage

**FR-SCR-009.1** The system shall store artifacts in MinIO/S3:
- Raw HTML pages
- Extracted data (JSON, CSV, XML)
- Screenshots and PDFs
- Media files
- Metadata and logs

**FR-SCR-009.2** The system shall generate presigned URLs for artifact access:
- Configurable expiration
- Secure signing
- Rate-limited access

#### 3.9.2 Output Formats

**FR-SCR-009.3** The system shall support multiple output formats:
- JSON (structured data)
- CSV (tabular data)
- XML (hierarchical data)
- Parquet (columnar storage)
- HTML (raw pages)
- Markdown (formatted text)

---

## 4. Performance Requirements

### 4.1 Response Time

| Operation | Target | Maximum | Measurement |
|-----------|--------|---------|-------------|
| Simple static page fetch | < 500ms | 2s | First byte to last byte |
| JavaScript-rendered page | < 2s | 5s | Full page load |
| CAPTCHA detection | < 100ms | 500ms | Page analysis |
| HITL trigger | < 200ms | 1s | Decision to pause |
| OCR processing (per image) | < 500ms | 2s | Text extraction |
| Transcription (per minute) | < 3s | 10s | Audio to text |
| PDF text extraction (per page) | < 100ms | 500ms | Page to text |

### 4.2 Throughput

| Metric | Target | Maximum |
|--------|--------|---------|
| Concurrent pages per worker | 10 | 50 |
| URLs per job | 100,000 | 1,000,000 |
| Total throughput (per cluster) | 10,000 pages/min | 100,000 pages/min |
| Data extraction rate | 1M records/hour | 10M records/hour |

### 4.3 Success Rate

| Target | Metric |
|--------|--------|
| > 99% | Overall success rate (excluding CAPTCHAs) |
| > 95% | JavaScript-rendered pages |
| > 99.5% | Static HTML pages |
| > 85% | CAPTCHA solving success rate |
| > 99.9% | Google success rate |
| > 99.8% | Amazon success rate |

### 4.4 Resource Efficiency

| Resource | Target | Maximum |
|----------|--------|---------|
| Memory per concurrent page | < 100MB | 200MB |
| CPU per page fetch | < 50ms | 200ms |
| Storage per 1M pages | < 10GB | 50GB |
| Network bandwidth | < 1MB/page | 5MB/page |

---

## 5. Security Requirements

### 5.1 SSRF Protection

**FR-SEC-001** The system shall prevent Server-Side Request Forgery attacks:
- Blocked IP ranges (RFC 1918, localhost, metadata services)
- DNS resolution validation
- Protocol restrictions (HTTP/HTTPS only)
- File extension blocking
- Credential-based URL validation
- Decimal/octal IP detection

### 5.2 Authentication & Authorization

**FR-SEC-002** The system shall implement authentication:
- API key authentication
- JWT token validation (Keycloak)
- OAuth 2.0 integration
- mTLS for service-to-service

**FR-SEC-003** The system shall implement authorization:
- Role-based access control (RBAC)
- Tenant isolation
- Resource quotas
- Rate limiting per tenant

### 5.3 Data Protection

**FR-SEC-004** The system shall protect sensitive data:
- Encryption at rest (AES-256)
- Encryption in transit (TLS 1.3)
- PII detection and masking
- Secure credential storage (Vault)
- Audit logging

### 5.4 Compliance

**FR-SEC-005** The system shall comply with:
- GDPR data handling
- CCPA privacy requirements
- SOC 2 controls
- PCI-DSS (if handling payment data)

---

## 6. Reliability Requirements

### 6.1 Availability

**FR-REL-001** The system shall maintain:
- 99.9% uptime for API endpoints
- 99.5% uptime for scraping services
- Automatic failover for critical components
- Graceful degradation for non-critical failures

### 6.2 Error Handling

**FR-REL-002** The system shall handle errors:
- Automatic retry with exponential backoff
- Circuit breaker for failing domains
- Dead letter queue for failed jobs
- Comprehensive error categorization
- User-friendly error messages

### 6.3 Recovery

**FR-REL-003** The system shall support recovery:
- Job checkpointing every 100 URLs
- Resume from last checkpoint
- Data persistence across restarts
- Backup and restore procedures

---

## 7. Scalability Requirements

### 7.1 Horizontal Scaling

**FR-SCA-001** The system shall scale horizontally:
- Stateless worker nodes
- Auto-scaling based on queue depth
- Load balancing across workers
- Distributed job processing

### 7.2 Vertical Scaling

**FR-SCA-002** The system shall support vertical scaling:
- Configurable resource allocation
- Memory-efficient processing
- CPU optimization
- Network I/O optimization

---

## 8. Interface Requirements

### 8.1 REST API

**FR-API-001** The system shall provide REST API endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/scrape/start` | POST | Start new scraping job |
| `/v1/scrape/status/{job_id}` | GET | Get job status |
| `/v1/scrape/cancel/{job_id}` | POST | Cancel job |
| `/v1/scrape/result/{job_id}` | GET | Get job results |
| `/v1/scrape/fetch` | POST | Single URL fetch |
| `/v1/scrape/extract` | POST | Extract from HTML |
| `/v1/scrape/ocr` | POST | Process OCR |
| `/v1/scrape/transcribe` | POST | Transcribe media |
| `/v1/scrape/parse_pdf` | POST | Parse PDF document |
| `/v1/scrape/hitl/{job_id}` | GET | Get HITL queue |
| `/v1/scrape/hitl/{job_id}/resolve` | POST | Resolve HITL |
| `/v1/scrape/metrics/{job_id}` | GET | Get job metrics |

### 8.2 MCP Tools

**FR-API-002** The system shall provide MCP tools:

| Tool | Description |
|------|-------------|
| `scrape.fetch` | Fetch a web page |
| `scrape.extract` | Extract data from HTML |
| `scrape.ocr` | Process image with OCR |
| `scrape.parse_pdf` | Extract text from PDF |
| `scrape.transcribe` | Transcribe audio/video |
| `scrape.start_job` | Start batch scraping job |
| `scrape.get_status` | Get job status |
| `scrape.get_results` | Get job results |
| `scrape.cancel_job` | Cancel running job |
| `scrape.request_hitl` | Request human intervention |

### 8.3 HITL Dashboard API

**FR-API-003** The system shall provide HITL dashboard API:
- WebSocket for real-time updates
- REST endpoints for job management
- Screenshot streaming
- Interactive browser console

---

## 9. Data Requirements

### 9.1 Data Models

#### ScrapeJob
```
job_id: UUID (PK)
tenant_id: String (128)
status: Enum (queued, running, succeeded, failed, cancelled, partial, hitl_required)
urls: JSON (array of URLs)
selectors: JSON (optional extraction rules)
options: JSON (engine, timeout, proxy, etc.)
pages_fetched: Integer
bytes_processed: BigInteger
artifact_count: Integer
error_count: Integer
created_at: DateTime
started_at: DateTime (nullable)
finished_at: DateTime (nullable)
error_message: Text
retry_count: Integer
hitl_required: Boolean
hitl_resolved: Boolean
checkpoint_url: String (nullable)
```

#### ScrapeArtifact
```
artifact_id: String (512, PK)
job_id: UUID (FK)
artifact_type: Enum (html, json, csv, image, video, pdf, text, audio, ocr, transcript)
format: String (32)
storage_path: String (512)
content_hash: String (128)
size_bytes: BigInteger
source_url: URL (2048)
metadata: JSON
created_at: DateTime
```

#### HITLRequest
```
request_id: UUID (PK)
job_id: UUID (FK)
tenant_id: String (128)
trigger_type: Enum (captcha, anti_bot, auth_required, rate_limit, manual)
trigger_details: JSON
status: Enum (pending, in_progress, resolved, expired, cancelled)
priority: Integer
assigned_to: String (nullable)
resolution: JSON (nullable)
created_at: DateTime
assigned_at: DateTime (nullable)
resolved_at: DateTime (nullable)
expires_at: DateTime
```

### 9.2 Data Retention

| Data Type | Retention Period | Archive Policy |
|-----------|------------------|----------------|
| Job records | 90 days | Compress after 30 days |
| Artifacts | 30 days | Delete after expiration |
| HITL requests | 180 days | Audit log retention |
| Audit logs | 365 days | Immutable archive |
| Metrics | 30 days | Aggregate to daily |

---

## 10. Quality Requirements (ISO/IEC 25010)

### 10.1 Functional Suitability

- All 29 functional requirements are testable
- Acceptance criteria defined for each requirement
- Traceability matrix maintained (Section 12)

### 10.2 Performance Efficiency

- Response time targets defined (Section 4.1)
- Throughput requirements defined (Section 4.2)
- Resource utilization targets defined (Section 4.4)

### 10.3 Compatibility

- Multi-engine support (Section 3.1)
- Multiple output formats (Section 3.9)
- API versioning strategy

### 10.4 Usability

- HITL dashboard for human operators
- Clear error messages
- Progress visualization
- Documentation and examples

### 10.5 Reliability

- 99.9% availability target (Section 6.1)
- Error handling requirements (Section 6.2)
- Recovery procedures (Section 6.3)

### 10.6 Security

- SSRF protection (Section 5.1)
- Authentication/Authorization (Section 5.2)
- Data protection (Section 5.3)
- Compliance requirements (Section 5.4)

### 10.7 Maintainability

- Modular architecture
- Configuration-driven behavior
- Comprehensive logging
- Health check endpoints

### 10.8 Portability

- Docker containerization
- Kubernetes deployment support
- Multi-architecture support (x86_64, ARM64)

---

## 11. Verification and Acceptance Criteria

### 11.1 Test Types

| Test Type | Coverage Target | Tools |
|-----------|-----------------|-------|
| Unit Tests | 90% | pytest, unittest |
| Integration Tests | 80% | pytest, Django TestCase |
| E2E Tests | 70% | Playwright, Selenium |
| Performance Tests | N/A | Locust, JMeter |
| Security Tests | N/A | OWASP ZAP, Bandit |
| PBT Tests | 50 properties | Hypothesis |

### 11.2 Acceptance Criteria

| Requirement | Acceptance Criteria |
|-------------|---------------------|
| FR-SCR-001 (Multi-engine) | All 4 engines functional, auto-selection works |
| FR-SCR-002 (Anti-detection) | Fingerprint randomization active, 99%+ bypass rate |
| FR-SCR-003 (CAPTCHA) | 85%+ solve rate, all major types supported |
| FR-SCR-004 (HITL) | Dashboard functional, < 5min resolution time |
| FR-SCR-005 (Tika) | All document types extractable |
| FR-SCR-006 (Transcription) | Whisper integration, 95%+ accuracy |
| FR-SCR-007 (Extraction) | All selector types functional |
| FR-SCR-008 (Jobs) | 100K URL batch processing |
| FR-SCR-009 (Output) | All formats supported, presigned URLs work |
| FR-SEC (Security) | SSRF blocked, auth enforced, audit logged |

---

## 12. Requirements Traceability

| Req ID | Description | Priority | Test Cases |
|--------|-------------|----------|------------|
| FR-SCR-001.1 | Multi-engine support | P0 | SCR-TEST-001 |
| FR-SCR-001.4 | Browser automation | P0 | SCR-TEST-002 |
| FR-SCR-002.1 | Fingerprint randomization | P0 | SCR-TEST-003 |
| FR-SCR-002.3 | Proxy management | P1 | SCR-TEST-004 |
| FR-SCR-003.1 | CAPTCHA detection | P0 | SCR-TEST-005 |
| FR-SCR-003.3 | CAPTCHA solving | P1 | SCR-TEST-006 |
| FR-SCR-004.1 | HITL triggers | P0 | SCR-TEST-007 |
| FR-SCR-004.3 | HITL interface | P1 | SCR-TEST-008 |
| FR-SCR-005.1 | Tika integration | P1 | SCR-TEST-009 |
| FR-SCR-006.1 | Whisper transcription | P1 | SCR-TEST-010 |
| FR-SCR-007.1 | Selector support | P0 | SCR-TEST-011 |
| FR-SCR-008.1 | Job lifecycle | P0 | SCR-TEST-012 |
| FR-SCR-009.1 | Artifact storage | P0 | SCR-TEST-013 |
| FR-SEC-001 | SSRF protection | P0 | SCR-TEST-014 |
| FR-SEC-002 | Authentication | P0 | SCR-TEST-015 |

---

## 13. Appendices

### 13.1 Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Web Framework | Django Ninja | 5.0+ |
| Browser Automation | Playwright | 1.40+ |
| HTTP Client | httpx | 0.25+ |
| Crawling Framework | Scrapy | 2.11+ |
| Document Processing | Apache Tika | 2.9+ |
| PDF Processing | pdfplumber | 0.11+ |
| OCR | Tesseract | 5.0+ |
| Transcription | OpenAI Whisper | 1.0+ |
| Job Queue | Redis + RQ | 7.0+ |
| Workflow | Temporal | 1.24+ |
| Events | Apache Kafka | 3.7+ |
| Storage | MinIO | Latest |
| Database | PostgreSQL | 16+ |

### 13.2 Performance Benchmarks

| Metric | Voyant Target | ZenRows | Scrape.do |
|--------|---------------|---------|-----------|
| Response Time | < 2s | 4.7s | 10.0s |
| Success Rate | > 99% | 98.19% | 92.64% |
| Google Success | > 99.9% | 100% | 84.11% |
| Amazon Success | > 99.8% | 99.86% | 98.67% |
| Cost per 1K | < $0.50 | $0.80 | $4.48 |

### 13.3 Compliance Checklist

- [ ] ISO/IEC 25010 quality model alignment
- [ ] ISO/IEC/IEEE 29148 requirements engineering
- [ ] GDPR data protection compliance
- [ ] SOC 2 control alignment
- [ ] OWASP security guidelines
- [ ] WCAG 2.1 accessibility (HITL dashboard)

---

**Document Version:** 3.0.0  
**Last Updated:** 2026-02-18  
**Next Review:** 2026-03-18  
**Author:** Voyant Development Team
