# Voyant Scraper Architecture Specification

## 1. Architectural Paradigm: 'Agent-Tool' Pure Execution
The Voyant Scraper module (`apps/scraper`) is designed with a strict **Agent-Tool Architecture**.
* **Zero Intelligence:** The scraper itself contains NO LLM integration and makes NO autonomous decisions.
* **Pure Execution:** It acts purely as a mechanical executor. The intelligence (URLs to scrape, CSS/XPath selectors to extract, whether to run OCR) must be provided by external Agent systems.

## 2. API Framework & Models (Rule 8 & 10 Compliance)
* **API Engine:** The module is strictly built using **Django Ninja** (`apps/scraper/api.py`), fulfilling the API Framework Policy (Rule 8). Fast API / Starlette are NOT present.
* **Database ORM:** Follows the Database ORM Policy (Rule 10) by leveraging strictly Django ORM (`apps/scraper/models.py`).
  * `ScrapeJob`: Tracks the state, URLs, input configurations, parameters, and results of a job.
  * `ScrapeArtifact`: Persists output (HTML, JSON, CSV, text, OCR outputs, media).

## 3. Orchestration: Temporal Workflows
To support long-running UI manipulation and resource-heavy media extraction tasks, the execution orchestration relies heavily on **Temporal**:
* `ScrapeWorkflow` (`apps/scraper/workflow.py`): Loops through provided URLs, mechanically sequences the activities (Fetch page -> Extract Data -> [Process OCR] -> [Transcribe Media] -> Store Artifact).

## 4. Sub-Tools & Supported Activities
The mechanical tasks are broken down into individual Temporal *Activities* inside `apps/scraper/activities.py`:

| Tool / Activity | Execution Technology | Description |
|-----------------|----------------------|-------------|
| **fetch_page** | Playwright / httpx / Scrapy | Mechanically downloads pages. Playwright is used for JavaScript-heavy, dynamic sites where waiting or scrolling is required. `httpx` is used for fast, static rendering. Incorporates internal SSRF protections. |
| **extract_data** | lxml (CSS/XPath) | Accepts Agent-provided selectors to parse the extracted HTML out of the DOM. Can extract texts, attributes, or nested lists. |
| **process_ocr** | Tesseract OCR | Native OCR to read static textual content buried inside images. |
| **parse_pdf** | Native PDF parsers | Extracts tables and text out of complex document formats. |
| **transcribe_media**| Whisper (Speech-To-Text)| Extracts and automatically transcribes audio or video media URLs found during the extraction phase. |

## 5. Security & Isolation
* `apps/scraper/security.py` exists to establish baseline defenses (like Server-Side Request Forgery - SSRF limits) so external agents do not fetch internal AWS endpoints or metadata services through the scraper mechanically.
