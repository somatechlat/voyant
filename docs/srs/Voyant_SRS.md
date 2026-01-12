# Software Requirements Specification (SRS)
**Project**: Voyant  
**Version**: 3.0.0  
**Date**: 2026-01-05  
**Standard**: ISO/IEC 29148:2018  
**Authors**: SOMA Engineering Team

---

## 1. Introduction

### 1.1 Purpose
This SRS specifies the complete software requirements for **Voyant**, an autonomous data platform that orchestrates web scraping, data ingestion, transformation, and analytics pipelines. This document provides an exhaustive description of all backend modules, scraper engine, Temporal workflows, MCP tools, frontend components, and operational requirements.

### 1.2 Scope
Voyant is a **"Brain vs Muscle"** architecture where:
- **Agent Zero** (Brain) provides intelligence, planning, and decision-making
- **Voyant DataScraper** (Muscle) executes mechanical scraping and data extraction

**Backend Stack**:
- Django 5 + Django Ninja REST API
- Python 3.11 microservices
- Temporal for workflow orchestration
- Spark 3.5 for distributed data processing
- Trino for federated SQL queries
- Kafka for event streaming
- PostgreSQL for metadata
- MinIO/S3 for data lake storage
- Playwright for headless browser automation

**Frontend Stack**:
- Lit 3 Web Components
- Bun 1.3.5 runtime
- Vite for development
- Universal "Clean Light Theme"

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|------|------------|
| Scraper | Automated web data extraction bot |
| Temporal | Durable workflow orchestration engine |
| Activity | Atomic unit of work in Temporal |
| Workflow | Durable, recoverable business process |
| MCP | Model Context Protocol - AI assistant integration |
| Spark | Distributed data processing engine |
| Trino | Federated SQL query engine |
| Data Lake | Raw data storage (Parquet/JSON on S3) |

### 1.4 References
- ISO/IEC 29148:2018 - Requirements Engineering
- Temporal Documentation
- Apache Spark Documentation
- Trino Documentation
- MCP Protocol Specification

---

## 2. Overall Description

### 2.1 Product Perspective
Voyant is the **Data Platform pillar** of the SOMA ecosystem, providing the raw data foundation for:
- **AgentVoiceBox**: Voice training datasets
- **GPUBroker**: Market intelligence and competitor analysis
- **YACHAQ**: Ecuadorian public procurement data
- **External customers**: Data-driven applications

**System Integration**:
- **Keycloak**: OAuth2 identity provider
- **PostgreSQL**: Workflow state and metadata
- **Temporal**: Durable workflow execution
- **Spark**: Large-scale ETL processing
- **Trino**: Multi-source SQL federation
- **Kafka**: Event streaming
- **MinIO/S3**: Data lake storage
- **Prometheus/Grafana**: Observability

### 2.2 Product Functions

#### Core Data Pipelines
1. **Web Scraping**: Headless browser automation (Playwright/Selenium)
2. **Data Ingestion**: Multi-format parsing (HTML, JSON, XML, PDF)
3. **ETL Processing**: Spark-based transformation pipelines
4. **Data Cataloging**: Metadata management and lineage tracking
5. **Query Federation**: Trino-based multi-source queries

#### Autonomous Operation
1. **Self-Healing**: Automatic retry and recovery on failures
2. **Schema Evolution**: Dynamic adaptation to website changes
3. **Rate Limiting**: Intelligent throttling to avoid blocking
4. **Job Scheduling**: Temporal-based cron and event triggers

#### AI Integration
1. **MCP Server**: 29 tools for Agent Zero integration
2. **Policy Enforcement**: Dynamic governance rules
3. **Cost Optimization**: Resource allocation decisions

### 2.3 User Classes

| User Class | Description | Technical Proficiency |
|------------|-------------|----------------------|
| **Platform Admin** | Manages infrastructure, workflows, policies | High |
| **Data Engineer** | Configures pipelines, monitors jobs | High |
| **Data Scientist** | Queries data via Trino, exports datasets | Medium |
| **AI Agent** | Agent Zero invoking MCP tools | N/A (programmatic) |

### 2.4 Operating Environment

**Backend**:
- **OS**: Linux (Docker containers)
- **Runtime**: Python 3.11
- **Database**: PostgreSQL 15
- **Object Storage**: MinIO (S3-compatible)
- **Orchestration**: Docker Compose / Kubernetes
- **CI/CD**: Tilt for local development

**Frontend**:
- **Browser**: Chrome/Firefox/Safari (latest 2 versions)
- **Runtime**: Bun 1.3.5

### 2.5 Constraints

1. **Browser Automation**: Requires headless Chrome/Firefox
2. **Rate Limiting**: Must respect robots.txt and rate limits
3. **Data Retention**: Legal compliance for scraped data storage
4. **Memory**: Spark jobs limited by cluster resources
5. **Latency**: Scraping jobs can take minutes to hours

---

## 3. Backend System Architecture

### 3.1 Core Modules

#### 3.1.1 **voyant/core**
**Purpose**: Foundation layer providing shared utilities and base models.

**Modules** (57 files):
- `models/`: Base data models
  - `base.py`: BaseModel, TimeStampedModel
  - `tenant.py`: TenantAwareModel
  - `workflow.py`: WorkflowExecution model
- `services/`: Core services
  - `temporal_client.py`: Temporal connection management
  - `spark_client.py`: Spark session management
  - `storage_client.py`: S3/MinIO client
- `utils/`: Utility functions
  - `validators.py`: Data validation
  - `serializers.py`: Custom serializers
  - `exceptions.py`: Custom exceptions
  - `logging.py`: Structured logging
- `config/`: Configuration management
  - `settings.py`: Django settings
  - `temporal_config.py`: Temporal worker configuration
  - `spark_config.py`: Spark cluster configuration

**Key Responsibilities**:
- Centralized configuration management
- Database connection pooling
- Temporal client initialization
- Spark session lifecycle
- Error handling framework
- Logging and observability

**API Endpoints**: None (utility module)

**Dependencies**:
- Django ORM
- Temporal Python SDK
- PySpark
- Boto3 (S3 client)

---

#### 3.1.2 **voyant/scraper**
**Purpose**: Web scraping engine with Playwright/Selenium automation.

**Modules** (21 files):
- `engine.py`: Core scraper orchestration
- `browser.py`: Headless browser management
- `parser.py`: HTML/JSON parsing logic
- `extractor.py`: CSS/XPath extraction rules
- `models.py`: ScraperJob, ScraperConfig, ScrapedData
- `api.py`: Scraper management endpoints
- `drivers/`: Browser driver implementations
  - `playwright_driver.py`: Playwright automation
  - `selenium_driver.py`: Selenium fallback
- `strategies/`: Scraping strategies
  - `static_scraper.py`: Static HTML scraping
  - `dynamic_scraper.py`: JavaScript-heavy sites
  - `pagination_handler.py`: Multi-page scraping
- `anti_detection/`: Bot detection evasion
  - `user_agent_rotator.py`: Random user agents
  - `proxy_manager.py`: Proxy pool management
  - `captcha_solver.py`: CAPTCHA handling (manual intervention)

**Key Responsibilities**:
- Headless browser automation
- Dynamic content rendering (JavaScript sites)
- Multi-page pagination handling
- Data extraction via CSS/XPath selectors
- Anti-bot detection measures
- Rate limiting and throttling
- Error recovery and retry logic

**API Endpoints**:
- `POST /v1/scrape/start` - Start scraper job
- `GET /v1/scrape/{job_id}` - Get job status
- `POST /v1/scrape/{job_id}/cancel` - Cancel job
- `GET /v1/scrape/{job_id}/results` - Get scraped data

**Database Tables**:
- `scraper_scraperjob`
- `scraper_scraperconfig`
- `scraper_scrapeddata`
- `scraper_extractionrule`

**Scraper Configuration Schema**:
```python
{
  "target_url": "https://example.com",
  "strategy": "dynamic",  # "static" | "dynamic"
  "extraction_rules": [
    {
      "name": "title",
      "selector": "h1.title",
      "type": "css",
      "extract": "text"
    },
    {
      "name": "price",
      "selector": "//span[@class='price']",
      "type": "xpath",
      "extract": "text",
      "transform": "float"
    }
  ],
  "pagination": {
    "enabled": true,
    "next_button_selector": "a.next",
    "max_pages": 100
  },
  "rate_limit": {
    "requests_per_minute": 10,
    "delay_seconds": 2
  }
}
```

**Execution Flow**:
```
1. Load configuration
2. Initialize browser (Playwright/Selenium)
3. Navigate to target URL
4. Wait for page load (network idle)
5. Execute JavaScript if needed
6. Extract data using rules
7. Handle pagination (if configured)
8. Store results in PostgreSQL + S3
9. Close browser
10. Emit Kafka event (scraper.completed)
```

---

#### 3.1.3 **voyant/workflows**
**Purpose**: Temporal workflow definitions for durable data pipelines.

**Modules** (9 files):
- `definitions/`: Workflow definitions
  - `scrape_workflow.py`: End-to-end scraping workflow
  - `etl_workflow.py`: Spark ETL pipeline workflow
  - `export_workflow.py`: Data export workflow
- `activities/`: Temporal activities (see voyant/activities)
- `signals.py`: Workflow signal handlers
- `queries.py`: Workflow query implementations

**Key Workflows**:

**1. scrape_workflow.py**:
```python
@workflow.defn
class ScrapeWorkflow:
    """
    Durable scraping workflow with automatic retry and recovery.
    
    Steps:
    1. Validate scraper configuration
    2. Initialize browser session
    3. Execute scraping activities
    4. Transform and validate data
    5. Store to data lake
    6. Update catalog metadata
    """
    
    @workflow.run
    async def run(self, config: ScraperConfig) -> ScrapeResult:
        # Step 1: Validate configuration
        validation = await workflow.execute_activity(
            validate_scraper_config,
            config,
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        if not validation.valid:
            raise InvalidConfigError(validation.errors)
        
        # Step 2: Execute scraping (with retry policy)
        scrape_result = await workflow.execute_activity(
            execute_scrape,
            config,
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=RetryPolicy(
                max_attempts=3,
                backoff_coefficient=2.0,
                initial_interval=timedelta(seconds=10)
            )
        )
        
        # Step 3: Transform data
        transformed = await workflow.execute_activity(
            transform_scraped_data,
            scrape_result,
            start_to_close_timeout=timedelta(minutes=10)
        )
        
        # Step 4: Store to S3
        storage_path = await workflow.execute_activity(
            store_to_data_lake,
            transformed,
            start_to_close_timeout=timedelta(minutes=5)
        )
        
        # Step 5: Update catalog
        await workflow.execute_activity(
            update_data_catalog,
            storage_path,
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        return ScrapeResult(
            status="completed",
            rows_scraped=len(transformed.rows),
            storage_path=storage_path
        )
```

**2. etl_workflow.py**:
```python
@workflow.defn
class ETLWorkflow:
    """
    Spark-based ETL pipeline workflow.
    
    Steps:
    1. Load raw data from data lake
    2. Apply transformations (Spark jobs)
    3. Validate output schema
    4. Write to target (Parquet/Trino table)
    5. Update catalog metadata
    """
    
    @workflow.run
    async def run(self, etl_config: ETLConfig) -> ETLResult:
        # Execute Spark job activity
        result = await workflow.execute_activity(
            execute_spark_job,
            etl_config,
            start_to_close_timeout=timedelta(hours=2)
        )
        
        return result
```

**Workflow Features**:
- **Durability**: Workflows survive restarts and failures
- **Retries**: Configurable retry policies per activity
- **Signals**: External events can modify running workflows
- **Queries**: Query workflow state without side effects
- **Versioning**: Support for workflow code updates

---

#### 3.1.4 **voyant/activities**
**Purpose**: Temporal activity implementations (atomic units of work).

**Modules** (10 files):
- `scrape_activities.py`: Browser automation activities
- `transform_activities.py`: Data transformation logic
- `storage_activities.py`: S3/MinIO operations
- `spark_activities.py`: Spark job execution
- `validation_activities.py`: Data quality checks
- `notification_activities.py`: Alert delivery

**Key Activities**:

**execute_scrape**:
```python
@activity.defn
async def execute_scrape(config: ScraperConfig) -> ScrapeResult:
    """
    Execute scraping using configured strategy.
    
    This activity is idempotent - can be safely retried.
    """
    activity.logger.info(f"Starting scrape for {config.target_url}")
    
    # Initialize browser
    browser = await get_browser_instance(
        browser_type=config.browser or "chromium",
        headless=True
    )
    
    try:
        # Execute scraping strategy
        if config.strategy == "dynamic":
            scraper = DynamicScraper(browser, config)
        else:
            scraper = StaticScraper(browser, config)
        
        results = await scraper.scrape()
        
        activity.logger.info(f"Scraped {len(results)} items")
        
        return ScrapeResult(
            status="success",
            rows=results,
            metadata={
                "url": config.target_url,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    except Exception as e:
        activity.logger.error(f"Scraping failed: {e}")
        raise  # Temporal will retry based on policy
    
    finally:
        await browser.close()
```

**execute_spark_job**:
```python
@activity.defn
async def execute_spark_job(etl_config: ETLConfig) -> ETLResult:
    """
    Execute Spark ETL job.
    
    Handles Spark session lifecycle and error recovery.
    """
    activity.logger.info(f"Starting Spark job: {etl_config.job_name}")
    
    spark = get_spark_session(
        app_name=etl_config.job_name,
        config=etl_config.spark_config
    )
    
    try:
        # Load source data
        df = spark.read.parquet(etl_config.input_path)
        
        # Apply transformations
        for transform in etl_config.transformations:
            df = apply_transformation(df, transform)
        
        # Validate schema
        validate_schema(df, etl_config.output_schema)
        
        # Write output
        df.write.mode("overwrite").parquet(etl_config.output_path)
        
        return ETLResult(
            status="success",
            rows_processed=df.count(),
            output_path=etl_config.output_path
        )
    
    finally:
        spark.stop()
```

**store_to_data_lake**:
```python
@activity.defn
async def store_to_data_lake(data: ScrapedData) -> str:
    """
    Store scraped data to S3/MinIO data lake.
    
    Storage format: Parquet with Snappy compression
    Partitioning: /year/month/day/hour/
    """
    s3_client = get_s3_client()
    
    # Convert to Parquet
    df = pd.DataFrame(data.rows)
    buffer = BytesIO()
    df.to_parquet(buffer, compression="snappy")
    
    # Generate storage path
    now = datetime.now()
    path = f"data-lake/scraped/{data.source}/{now.year}/{now.month:02d}/{now.day:02d}/{now.hour:02d}/{uuid.uuid4()}.parquet"
    
    # Upload to S3
    s3_client.put_object(
        Bucket=config.S3_BUCKET,
        Key=path,
        Body=buffer.getvalue()
    )
    
    activity.logger.info(f"Stored data to s3://{config.S3_BUCKET}/{path}")
    
    return f"s3://{config.S3_BUCKET}/{path}"
```

---

#### 3.1.5 **voyant/mcp**
**Purpose**: Model Context Protocol server for AI agent integration.

**Modules** (2 files):
- `server.py`: MCP server implementation
- `tools.py`: Tool definitions (29 tools)

**Available MCP Tools** (29 total):

**Data Discovery**:
1. `list_scrapers` - Get all registered scrapers
2. `get_scraper_config` - Retrieve scraper configuration
3. `search_data_catalog` - Query data catalog by keywords
4. `get_dataset_schema` - Get schema for dataset
5. `get_dataset_sample` - Preview sample rows

**Scraper Operations**:
6. `create_scraper` - Register new scraper configuration
7. `update_scraper` - Modify existing scraper
8. `start_scrape_job` - Trigger scraping workflow
9. `get_job_status` - Check workflow status
10. `cancel_job` - Cancel running job

**Data Querying**:
11. `execute_sql_query` - Run SQL via Trino
12. `export_dataset` - Export data to CSV/JSON/Parquet
13. `get_query_plan` - Explain Trino query execution plan

**Workflow Management**:
14. `list_workflows` - Get active workflows
15. `get_workflow_history` - Retrieve workflow execution history
16. `signal_workflow` - Send signal to running workflow
17. `query_workflow_state` - Query workflow variables

**ETL Operations**:
18. `submit_spark_job` - Start Spark ETL job
19. `get_spark_job_status` - Check Spark job progress
20. `kill_spark_job` - Terminate Spark job

**Data Quality**:
21. `run_data_validation` - Execute data quality checks
22. `get_validation_report` - Retrieve validation results

**Governance**:
23. `create_policy` - Define data access policy
24. `enforce_policy` - Apply policy to dataset
25. `audit_data_access` - Query access logs

**Monitoring**:
26. `get_scraper_metrics` - Scraper performance metrics
27. `get_pipeline_health` - Overall pipeline status
28. `list_recent_errors` - Recent system errors
29. `trigger_alert` - Send alert notification

**MCP Tool Example**:
```python
@mcp.tool()
async def start_scrape_job(
    scraper_id: str,
    params: dict | None = None
) -> dict:
    """
    Start a scraping job for the specified scraper.
    
    Args:
        scraper_id: UUID of registered scraper
        params: Optional override parameters
    
    Returns:
        {
            "job_id": "uuid",
            "workflow_id": "temporal-workflow-id",
            "status": "started",
            "estimated_duration_minutes": 15
        }
    """
    # Load scraper config
    scraper = await Scraper.objects.aget(id=scraper_id)
    config = scraper.config
    
    # Apply parameter overrides
    if params:
        config.update(params)
    
    # Start Temporal workflow
    temporal_client = get_temporal_client()
    workflow_handle = await temporal_client.start_workflow(
        ScrapeWorkflow.run,
        config,
        id=f"scrape-{scraper_id}-{uuid.uuid4()}",
        task_queue="scraper-queue"
    )
    
    return {
        "job_id": str(uuid.uuid4()),
        "workflow_id": workflow_handle.id,
        "status": "started",
        "estimated_duration_minutes": estimate_duration(config)
    }
```

---

#### 3.1.6 **voyant/api**
**Purpose**: REST API endpoints for external clients and dashboard.

**Modules** (2 files):
- `v1.py`: API v1 endpoints
- `schemas.py`: Pydantic request/response schemas

**API Endpoints**:

**Scraper Management**:
- `POST /v1/scrapers` - Create scraper
- `GET /v1/scrapers` - List scrapers
- `GET /v1/scrapers/{id}` - Get scraper details
- `PUT /v1/scrapers/{id}` - Update scraper
- `DELETE /v1/scrapers/{id}` - Delete scraper

**Job Execution**:
- `POST /v1/scrape/start` - Start scrape job
- `GET /v1/scrape/{job_id}` - Get job status
- `POST /v1/scrape/{job_id}/cancel` - Cancel job
- `GET /v1/scrape/{job_id}/results` - Download results

**Data Catalog**:
- `GET /v1/catalog/datasets` - List datasets
- `GET /v1/catalog/datasets/{id}` - Get dataset metadata
- `GET /v1/catalog/datasets/{id}/sample` - Preview data

**Analytics**:
- `POST /v1/query` - Execute Trino SQL query
- `POST /v1/export` - Export dataset
- `GET /v1/metrics` - Platform metrics

---

#### 3.1.7 **voyant/worker**
**Purpose**: Temporal worker process for executing workflows and activities.

**Modules** (8 files):
- `main.py`: Worker entry point
- `config.py`: Worker configuration
- `registry.py`: Workflow/activity registration
- `health_check.py`: Worker health endpoint

**Worker Configuration**:
```python
# config.py
TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "temporal:7233")
TEMPORAL_NAMESPACE = "voyant"
TASK_QUEUE = "scraper-queue"
MAX_CONCURRENT_ACTIVITIES = 10
MAX_CONCURRENT_WORKFLOWS = 50
WORKER_IDENTITY = f"voyant-worker-{socket.gethostname()}"
```

**Worker Startup**:
```python
# main.py
async def main():
    logger.info(f"Starting Voyant worker: {config.WORKER_IDENTITY}")
    
    # Connect to Temporal
    client = await Client.connect(
        config.TEMPORAL_HOST,
        namespace=config.TEMPORAL_NAMESPACE
    )
    
    # Register workflows and activities
    worker = Worker(
        client,
        task_queue=config.TASK_QUEUE,
        workflows=[ScrapeWorkflow, ETLWorkflow, ExportWorkflow],
        activities=[
            execute_scrape,
            execute_spark_job,
            store_to_data_lake,
            update_data_catalog,
            send_notification
        ],
        max_concurrent_activities=config.MAX_CONCURRENT_ACTIVITIES,
        max_concurrent_workflows=config.MAX_CONCURRENT_WORKFLOWS
    )
    
    # Run worker
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
```

---

#### 3.1.8 **voyant/ingestion**
**Purpose**: Multi-format data ingestion pipelines.

**Modules** (4 files):
- `parsers.py`: Format-specific parsers (JSON, XML, CSV, PDF)
- `validators.py`: Schema validation
- `transformers.py`: Data normalization
- `loaders.py`: Bulk data loading

**Supported Formats**:
- JSON (including nested structures)
- XML (with XPath extraction)
- CSV/TSV (with auto-detection)
- Excel (XLSX)
- PDF (text extraction via pdfplumber)
- HTML (structured data extraction)

---

#### 3.1.9 **voyant/governance**
**Purpose**: Data governance and policy enforcement.

**Modules** (2 files):
- `policies.py`: Policy engine
- `audit.py`: Audit logging

**Features**:
- Role-based access control for datasets
- Data retention policies
- PII detection and masking
- Compliance reporting (GDPR, CCPA)

---

#### 3.1.10 **voyant/security**
**Purpose**: Security controls and authentication.

**Modules** (3 files):
- `auth.py`: Authentication middleware
- `encryption.py`: Data encryption utilities
- `secrets.py`: Secrets management

**Features**:
- API key authentication
- OAuth2 via Keycloak
- Data-at-rest encryption (S3 server-side)
- Secrets stored in Vault

---

#### 3.1.11 **voyant/billing**
**Purpose**: Usage tracking and billing integration.

**Modules** (2 files):
- `metering.py`: Usage event recording
- `lago_integration.py`: Lago billing client

**Billable Metrics**:
- Scraper executions (count)
- Data scraped (MB)
- Spark compute time (seconds)
- Trino query execution (bytes scanned)
- Storage usage (GB-months)

---

#### 3.1.12 **voyant/discovery**
**Purpose**: Automatic data source discovery and schema inference.

**Modules** (4 files):
- `crawler.py`: Website structure crawler
- `schema_inference.py`: Automatic schema detection
- `recommender.py`: Scraper configuration suggestions

**Features**:
- Sitemap parsing
- Link discovery (BFS/DFS crawling)
- Schema inference from sample data
- Scraper template recommendation

---

#### 3.1.13 **voyant/generators**
**Purpose**: Synthetic data generation and testing utilities.

**Modules** (2 files):
- `faker_gen.py`: Fake data generation
- `test_data.py`: Test dataset creation

**Use Cases**:
- Testing scraper configurations
- Populating dev/staging environments
- Data privacy (generate synthetic PII)

---

#### 3.1.14 **voyant/integrations**
**Purpose**: Third-party service integrations.

**Modules** (2 files):
- `datahub.py`: DataHub lineage integration
- `superset.py`: Apache Superset dashboard integration

---

## 4. Frontend System Architecture

### 4.1 Directory Structure

```
dashboard/src/
├── components/          # 4 Lit components
│   ├── saas-layout.ts
│   ├── saas-glass-modal.ts
│   ├── saas-status-dot.ts
│   └── saas-infra-card.ts
├── views/               # 2 page views
│   ├── view-login.ts
│   └── view-voyant-setup.ts
├── lib/                 # Utilities
│   ├── api-client.ts
│   ├── formatters.ts
│   └── validators.ts
└── styles/
    └── globals.css
```

### 4.2 Core View: view-voyant-setup.ts

**Purpose**: "Data Platform Management" dashboard - Mother Screen for data engineers.

**Layout**:
- **Top Panel**: Platform KPIs (active jobs, data scraped today, pipeline health)
- **Left Panel**: Scraper registry and configurations
- **Right Panel**: Active workflows and job queue
- **Modals**: Scraper configuration, Spark job submission

**Features**:
1. Scraper configuration editor (JSON schema)
2. Workflow execution visualization
3. Data catalog browser
4. Spark job monitoring
5. Trino query console

**API Calls**:
- `GET /v1/scrapers` - List all scrapers
- `GET /v1/catalog/datasets` - Data catalog
- `GET /v1/workflows` - Active workflows
- `WS /ws/jobs` - Real-time job updates

---

## 5. API Specification

### 5.1 Core Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/v1/scrape/start` | Start scrape job | `{scraper_id, params?}` | `{job_id, workflow_id}` |
| GET | `/v1/scrape/{job_id}` | Get job status | - | `{status, progress, results_url}` |
| POST | `/v1/query` | Execute SQL query | `{sql, limit?}` | `{columns[], rows[]}` |
| POST | `/v1/export` | Export dataset | `{dataset_id, format}` | `{export_url, expires_at}` |

---

## 6. Non-Functional Requirements

### 6.1 Performance

| Metric | Requirement | Notes |
|--------|-------------|-------|
| Scraping Throughput | 1,000 pages/hour | Per worker instance |
| Spark Job Latency | < 5 minutes | For datasets < 10GB |
| API Response Time | < 200ms (p95) | All REST endpoints |
| Temporal Workflow Start | < 100ms | From API call to workflow start |

### 6.2 Scalability

| Dimension | Target | Implementation |
|-----------|--------|----------------|
| Concurrent Scraper Jobs | 100+ | Horizontal worker scaling |
| Data Lake Size | Petabyte-scale | S3 unlimited storage |
| Daily Data Ingestion | 1TB+ | Partitioned Parquet writes |
| Trino Query Concurrency | 50+ | Trino cluster scaling |

### 6.3 Reliability

**Uptime SLA**: 99.9% for API and workflows  
**Data Durability**: 99.999999999% (S3 standard storage)  
**Workflow Recovery**: Automatic retry on transient failures  

**Fault Tolerance**:
- Temporal: Automatic workflow recovery on worker crashes
- Spark: Job resubmission on executor failures
- Scraper: Retry with exponential backoff

### 6.4 Security

**Authentication**:
- API key for programmatic access
- OAuth2 for dashboard users
- Service-to-service mTLS

**Data Protection**:
- S3 server-side encryption (AES-256)
- TLS 1.3 for all connections
- PII detection and redaction
- Access audit logs (365-day retention)

---

## 7. Data Models

### 7.1 Core Entities

#### ScraperConfig
```python
class ScraperConfig:
    id: UUID
    name: str
    target_url: str
    strategy: str  # "static" | "dynamic"
    extraction_rules: List[ExtractionRule]
    pagination: PaginationConfig | None
    rate_limit: RateLimitConfig
    created_at: datetime
    updated_at: datetime
```

#### ScraperJob
```python
class ScraperJob:
    id: UUID
    scraper_id: UUID
    workflow_id: str  # Temporal workflow ID
    status: str  # "pending" | "running" | "completed" | "failed"
    progress: int  # 0-100
    rows_scraped: int
    errors: List[str]
    started_at: datetime
    completed_at: datetime | None
```

#### Dataset
```python
class Dataset:
    id: UUID
    name: str
    description: str
    storage_path: str  # S3 path
    schema: dict  # JSON schema
    row_count: int
    size_bytes: int
    created_at: datetime
    updated_at: datetime
```

---

## 8. Deployment Architecture

### 8.1 Docker Compose Services

**Production Stack**:
1. `postgres` - PostgreSQL 15
2. `temporal` - Temporal server
3. `voyant-api` - Django REST API
4. `voyant-worker` - Temporal worker
5. `spark-master` - Spark master node
6. `spark-worker` - Spark worker node(s)
7. `trino` - Trino coordinator
8. `minio` - S3-compatible object storage
9. `keycloak` - Identity provider
10. `prometheus` - Metrics
11. `grafana` - Visualization
12. `frontend` - Lit dev server (dev only)

### 8.2 Tilt Orchestration

**Tiltfile** orchestrates:
- Backend services via `docker-compose.yml`
- Frontend via `docker-compose.frontend.yml`
- Live code sync for `voyant/` and `dashboard/src/`
- Automatic rebuild on changes

---

## 9. Testing Requirements

### 9.1 Backend Tests

**Unit Tests** (pytest):
- 80%+ coverage
- All scraper strategies
- Temporal activities (mocked)
- Data validation logic

**Integration Tests**:
- Temporal workflow execution
- Spark job submission
- S3 storage operations
- Trino queries

**E2E Tests** (Playwright):
- Full scraping workflow
- Dashboard interactions
- MCP tool invocations

---

## 10. Verification & Validation

### 10.1 Acceptance Criteria

**Scraping**:
- ✅ Successfully scrape 100-page site in < 1 hour
- ✅ Handle pagination correctly
- ✅ Survive rate limiting and retries

**Workflows**:
- ✅ Workflows recover after worker restart
- ✅ Failed activities retry automatically
- ✅ Workflow history persists indefinitely

**MCP Integration**:
- ✅ Agent Zero can invoke all 29 tools
- ✅ Tool responses conform to schema

### 10.2 Manual Verification

1. Run `tilt up` in `voyant/`
2. Verify all services healthy
3. Navigate to `http://localhost:3000`
4. Complete login flow
5. Create test scraper configuration
6. Start scrape job
7. Verify Temporal workflow in UI
8. Check scraped data in S3

---

**END OF VOYANT SRS v3.0.0**
