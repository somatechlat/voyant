# Voyant v3.0.0 - Production Readiness Tasks

**Document ID:** VOYANT-TASKS-3.0.0  
**Version:** 3.0  
**Date:** 2026-02-03  
**Status:** In Progress  
**Based on:** requirements.md v2.0, design.md v2.0  
**Compliance:** ISO/IEC/IEEE 29148:2018, VIBE Coding Rules

---

## 0. Task Conventions

- `[ ]` Not started
- `[-]` In progress  
- `[x]` Complete
- `[ ]*` Optional task

---

## 0.1 VOYANT Vision & Current Status

### **THE VISION**
**Autonomous Data Intelligence Tool for AI Agents**
- Agent discovers VOYANT via MCP tools
- Agent says "scrape www.patiotuerca.com" → VOYANT handles everything autonomously
- Complete data science toolkit: scraping, ingestion, profiling, statistics, ML, forecasting, visualization, reporting
- Django-first architecture with ALL Apache tools integrated
- BOTH MCP and REST API interfaces
- ALL secrets in Vault (governed by Temporal)

### **CURRENT STATUS: ~60% Complete**

**✅ IMPLEMENTED (What Works):**
- Django 5 + Django Ninja REST API (40+ endpoints)
- MCP Server with 17 tools (12 Voyant + 5 DataScraper)
- Temporal workflows (ingest, profile, quality, analyze)
- Django ORM models (Source, Job, PresetJob, Artifact)
- SomaStack integration framework (SomaBrain, OPA, Kafka, MinIO clients)
- DataScraper module (Playwright, Selenium, Scrapy, OCR, PDF, transcription)
- Statistical analysis primitives
- Visualization generation (Plotly)

**❌ CRITICAL GAPS (Blocking Production):**
- Test infrastructure BROKEN (V-001, V-002): 13% coverage, collection fails
- Code quality SEVERE (V-003): 746 errors (433 ruff + 313 pyright)
- Tool registration INCOMPLETE: Agents cannot discover VOYANT
- Security NOT enforced: Auth bypassed, no Vault integration
- Apache platform MISSING: No Iceberg, Flink, Ranger, Atlas, NiFi, Superset, Druid, Tika, SkyWalking

**🎯 CRITICAL PATH TO VISION:**
1. **Fix Tests** (V-001, V-002) → Validate everything works
2. **Fix Code Quality** (V-003) → Make maintainable  
3. **Register as Tool** → Enable agent discovery
4. **Enforce Security** → Production-ready (Vault, fail-closed)
5. **Integrate Apache** → Complete data science toolkit

---

## 1. CRITICAL: Fix Test Infrastructure (V-001, V-002)

**Priority:** P0 - BLOCKING  
**Estimated Effort:** 2-3 days  
**Validates:** All requirements indirectly

### 1.1 Fix Test Collection Failures
- [ ] 1.1.1 Fix ModuleNotFoundError for temporalio imports
  - Files: `tests/activities/test_analysis_activities.py`, `tests/activities/test_generation_activities.py`
  - Root cause: Missing or incorrect temporalio test dependencies
  - Resolution: Add proper test fixtures and mocks for Temporal activities

- [ ] 1.1.2 Fix TypeError in analysis_activities.py
  - Files: `voyant/activities/analysis_activities.py`
  - Root cause: Type mismatch in activity definitions
  - Resolution: Correct type annotations and parameter handling

- [ ] 1.1.3 Verify all test files can be collected
  - Command: `pytest --collect-only`
  - Expected: 0 collection errors

### 1.2 Increase Test Coverage to 80%+
- [ ] 1.2.1 Add unit tests for core modules (target: 90% coverage)
  - `voyant/core/config.py`
  - `voyant/core/errors.py`
  - `voyant/core/events.py`
  - `voyant/core/circuit_breaker.py`

- [ ] 1.2.2 Add integration tests for SomaStack integrations (target: 80% coverage)
  - `voyant/integrations/soma.py` - Policy, Memory, Orchestrator clients
  - Test against real SomaStack local stack


- [ ] 1.2.3 Add workflow tests (target: 85% coverage)
  - `voyant/workflows/analyze_workflow.py`
  - `voyant/workflows/ingest_workflow.py`
  - `voyant/workflows/quality_workflow.py`
  - Use Temporal test framework

- [ ] 1.2.4 Add API endpoint tests (target: 95% coverage)
  - `voyant_app/api.py` - All REST endpoints
  - Test auth, validation, error handling
  - Test tenant isolation

- [ ] 1.2.5 Add property-based tests for correctness properties
  - Implement PBT for Properties 1-18 from design.md Section 5
  - Use Hypothesis library
  - Focus on: Capsule compliance, DQS validity, job state machine

**Definition of Done:**
- All tests pass: `pytest -v`
- Coverage ≥ 80%: `pytest --cov=voyant --cov-report=term-missing`
- No collection errors
- CI pipeline green

---

## 2. CRITICAL: Fix Code Quality Issues (V-003)

**Priority:** P0 - BLOCKING  
**Estimated Effort:** 3-4 days  
**Validates:** Code maintainability, security

### 2.1 Fix Ruff Errors (433 errors)
- [ ] 2.1.1 Fix bare except clauses
  - Replace `except:` with specific exception types
  - Add proper error logging

- [ ] 2.1.2 Fix undefined names
  - Example: `List` in `voyant/ingestion/airbyte_utils.py`
  - Add missing imports: `from typing import List`

- [ ] 2.1.3 Fix import order and unused imports
  - Run: `ruff check --fix voyant/`
  - Verify: `ruff check voyant/`

### 2.2 Fix Pyright Type Errors (313 errors)
- [ ] 2.2.1 Fix type mismatches in core modules
  - Add proper type annotations
  - Fix Optional/None handling

- [ ] 2.2.2 Fix missing return type annotations
  - All public functions must have return types
  - Use `-> None` for procedures

- [ ] 2.2.3 Enable strict type checking
  - Update `pyproject.toml`: `typeCheckingMode = "strict"`
  - Fix all new errors

**Definition of Done:**
- `ruff check voyant/` returns 0 errors
- `pyright voyant/` returns 0 errors
- `make lint` passes (after fixing Makefile)
- Pre-commit hooks configured

---

## 3. SomaStack Tool Registration (Requirement 1)

**Priority:** P1 - HIGH  
**Estimated Effort:** 2 days  
**Validates:** Requirements 1.1-1.7

### 3.1 Implement Tool Manifest
- [ ] 3.1.1 Create tool manifest JSON schema
  - File: `voyant/integrations/soma_tool_manifest.py`
  - Include: toolId, description, input/output schemas, security level, timeout, cost

- [ ] 3.1.2 Implement manifest endpoint
  - Endpoint: `GET /v1/tools/voyant`
  - Returns: Tool manifest JSON
  - Test: Validate against SomaAgentHub schema

### 3.2 Implement Tool Registration
- [ ] 3.2.1 Add registration on startup
  - File: `voyant_app/apps.py` - ready() hook
  - Call: `POST /v1/tools` to SomaAgentHub
  - Handle: Registration failures gracefully

- [ ] 3.2.2 Implement tool invocation endpoint
  - Endpoint: `POST /v1/invoke`
  - Validate: Request against input schema
  - Route: To appropriate action handler
  - Return: Response conforming to output schema

### 3.3 Add Property-Based Tests
- [ ] 3.3.1 Property 1: Tool manifest schema validity
  - Test: Serialize/deserialize manifest produces equivalent object
  - Library: Hypothesis

- [ ] 3.3.2 Property 2: Tool invocation routing
  - Test: All valid actions route to correct handlers
  - Actions: discover, connect, analyze, status, result, query

**Definition of Done:**
- Tool manifest endpoint returns valid JSON
- SomaAgentHub can discover and invoke VOYANT
- All property tests pass
- Integration test with SomaAgentHub local stack passes

---

## 4. Capsule Constraint Compliance (Requirement 2)

**Priority:** P1 - HIGH  
**Estimated Effort:** 3 days  
**Validates:** Requirements 2.1-2.8

### 4.1 Implement Capsule Validator
- [ ] 4.1.1 Create CapsuleValidator class
  - File: `voyant/core/capsule.py`
  - Methods: validate(), enforce_network_egress(), enforce_tool_whitelist()
  - Parse: YAML Capsule documents

- [ ] 4.1.2 Implement network egress enforcement
  - Intercept: All outbound HTTP/TCP connections
  - Check: Against Capsule networkEgress whitelist
  - Deny: Connections to non-whitelisted destinations

- [ ] 4.1.3 Implement timeout enforcement
  - Monitor: Job execution time
  - Terminate: Jobs exceeding maxRuntimeSeconds
  - Return: Partial results if available

- [ ] 4.1.4 Implement memory limit enforcement
  - Monitor: Process memory usage
  - Spill: To disk when approaching memoryLimitMiB
  - Prevent: OOM crashes


### 4.2 Add Property-Based Tests
- [ ] 4.2.1 Property 3: Network egress enforcement
  - Test: Connections only succeed for whitelisted destinations
  - Generate: Random Capsule configs and connection attempts

- [ ] 4.2.2 Property 4: Timeout enforcement
  - Test: Jobs terminate within maxRuntimeSeconds + 30s grace
  - Generate: Random timeout values and job durations

- [ ] 4.2.3 Property 5: Memory limit enforcement
  - Test: Memory usage never exceeds memoryLimitMiB
  - Generate: Random memory limits and workload sizes

**Definition of Done:**
- All Capsule constraints enforced
- Violations logged to audit trail
- All property tests pass
- Integration tests with real Capsule documents pass

---

## 5. SomaBrain Memory Integration (Requirement 3)

**Priority:** P1 - HIGH  
**Estimated Effort:** 2 days  
**Validates:** Requirements 3.1-3.8

### 5.1 Implement Memory Storage
- [ ] 5.1.1 Enhance SomaBrain client remember() method
  - File: `voyant/integrations/soma.py`
  - Store: Analysis summary, job metadata, artifact refs
  - Tag: With `fact: analysis`
  - Propagate: Tenant ID, session ID

- [ ] 5.1.2 Implement memory recall
  - Method: recall() in SomaBrain client
  - Query: Prior analyses by topic
  - Incorporate: Context into current analysis

- [ ] 5.1.3 Add Constitution compliance check
  - Method: check_constitution() before storage
  - Validate: Payloads against Constitution policies
  - Handle: Denials gracefully

### 5.2 Add Property-Based Tests
- [ ] 5.2.1 Property 6: Memory storage round-trip
  - Test: Store and recall returns original job_id and preset
  - Generate: Random AnalysisResult objects

- [ ] 5.2.2 Property 7: Tenant isolation
  - Test: Tenant A never recalls Tenant B's records
  - Generate: Random tenant IDs and memory operations

**Definition of Done:**
- Memory storage and recall working
- Constitution checks enforced
- Graceful degradation if SomaBrain unavailable
- All property tests pass
- Integration test with SomaBrain local stack passes

---

## 6. OPA Policy Enforcement (Requirement 4)

**Priority:** P1 - HIGH  
**Estimated Effort:** 2 days  
**Validates:** Requirements 4.1-4.7

### 6.1 Implement Policy Enforcement
- [ ] 6.1.1 Add OPA client policy evaluation
  - File: `voyant/core/opa.py`
  - Method: evaluate_policy()
  - Endpoint: `POST /v1/data/{policy}`

- [ ] 6.1.2 Add policy checks before operations
  - Data access: Check before connecting to sources
  - Tool execution: Check before running presets
  - Artifact generation: Check before creating outputs


- [ ] 6.1.3 Implement fail-closed semantics
  - If OPA unavailable: Deny all operations
  - Log: Policy unavailability to audit trail
  - Return: Structured error with VYNT-6003 code

- [ ] 6.1.4 Add audit logging for policy decisions
  - Log: Timestamp, actor, resource, decision, outcome
  - Store: In immutable audit trail
  - Include: Policy violation details

### 6.2 Add Property-Based Tests
- [ ] 6.2.1 Property 8: Policy denial propagation
  - Test: OPA deny always aborts operation
  - Generate: Random policy decisions

- [ ] 6.2.2 Property 9: Fail-closed semantics
  - Test: OPA unavailable always denies operations
  - Simulate: OPA service failures

**Definition of Done:**
- All operations gated by OPA policies
- Fail-closed behavior verified
- Audit trail complete
- All property tests pass
- Integration test with OPA local stack passes

---

## 7. Preset Workflow Execution (Requirement 5)

**Priority:** P2 - MEDIUM  
**Estimated Effort:** 4 days  
**Validates:** Requirements 5.1-5.8

### 7.1 Implement Preset Workflows
- [ ] 7.1.1 BENCHMARK_MY_BRAND preset
  - Market share calculation
  - Competitive positioning
  - Sentiment analysis
  - Trend forecasting

- [ ] 7.1.2 PREDICT_SALES preset
  - Time series forecasting
  - Confidence intervals
  - ARIMA/ETS/Prophet models

- [ ] 7.1.3 FORECAST_DEMAND preset
  - Seasonal decomposition
  - Trend/seasonal/residual components
  - Demand predictions

- [ ] 7.1.4 DETECT_ANOMALIES preset
  - IQR, Z-score, Isolation Forest methods
  - Anomaly scores with explanations

- [ ] 7.1.5 SEGMENT_CUSTOMERS preset
  - K-means or DBSCAN clustering
  - Customer segments with profiles

- [ ] 7.1.6 FIX_DATA_QUALITY preset
  - Missing value detection and imputation
  - Duplicate detection and removal
  - Format consistency checks

### 7.2 Add Data Quality Score (DQS)
- [ ] 7.2.1 Implement DQS calculation
  - File: `voyant/core/data_quality.py`
  - Metrics: Completeness, consistency, validity, timeliness
  - Range: 0.0 to 1.0

- [ ] 7.2.2 Add DQS to all preset results
  - Include: In AnalysisResult
  - Warn: If DQS < 0.7

### 7.3 Add Progress Events
- [ ] 7.3.1 Emit progress events to Kafka
  - Interval: ≤ 5 seconds
  - Include: Job ID, stage, progress percentage

### 7.4 Add Property-Based Tests
- [ ] 7.4.1 Property 10: DQS range validity
  - Test: DQS always in [0.0, 1.0]
  - Generate: Random datasets

- [ ] 7.4.2 Property 11: DQS warning threshold
  - Test: DQS < 0.7 always includes warning
  - Generate: Random quality scores

**Definition of Done:**
- All 6 presets implemented and tested
- DQS calculated for all analyses
- Progress events emitted
- All property tests pass
- End-to-end tests for each preset pass

---

## 8. Data Source Discovery and Connection (Requirement 6)

**Priority:** P2 - MEDIUM  
**Estimated Effort:** 3 days  
**Validates:** Requirements 6.1-6.8

### 8.1 Implement Source Discovery
- [ ] 8.1.1 Add URL pattern analysis
  - File: `voyant/ingestion/discovery.py`
  - Detect: REST, GraphQL, database connection strings
  - Return: Source type, auth requirements, confidence score

- [ ] 8.1.2 Add schema discovery
  - Discover: Tables, fields, data types
  - Catalog: Available data structures

### 8.2 Implement Connection Management
- [ ] 8.2.1 Add OAuth flow support
  - Initiate: OAuth flow for OAuth-required sources
  - Store: Tokens in SomaAgentHub credential store

- [ ] 8.2.2 Add API key authentication
  - Retrieve: Credentials from credential store
  - Use: Tenant namespace for isolation

- [ ] 8.2.3 Add retry logic
  - Exponential backoff: 0.5s → 1s → 2s → 4s → 5s cap
  - Max attempts: 5
  - Log: Retry attempts

### 8.3 Add Capsule Compliance
- [ ] 8.3.1 Respect networkEgress restrictions
  - Only probe: Allowed destinations
  - Deny: Connections to non-whitelisted hosts

**Definition of Done:**
- Source discovery working for common patterns
- OAuth and API key auth supported
- Retry logic implemented
- Capsule compliance enforced
- Integration tests with real data sources pass

---

## 9. Data Ingestion (Requirement 7)

**Priority:** P2 - MEDIUM  
**Estimated Effort:** 3 days  
**Validates:** Requirements 7.1-7.8

### 9.1 Implement Ingestion for Multiple Source Types
- [ ] 9.1.1 Structured sources (CSV, Excel, JSON, Parquet)
  - Auto-detect: Schema, data types, encoding
  - Handle: Large files with chunking

- [ ] 9.1.2 Databases (PostgreSQL, MySQL, MongoDB)
  - Connection pooling
  - Configurable timeouts
  - Query optimization

- [ ] 9.1.3 APIs
  - Pagination handling
  - Rate limiting
  - Token refresh

- [ ] 9.1.4 Documents (PDF, Word, PowerPoint)
  - Text extraction
  - Table extraction
  - Metadata extraction

- [ ] 9.1.5 Web pages
  - HTML parsing
  - Structured data extraction

- [ ] 9.1.6 Streaming data
  - Buffering and batching
  - Backpressure handling

### 9.2 Add Memory Efficiency
- [ ] 9.2.1 Implement chunked processing
  - Chunk size: Configurable (default 100K rows)
  - Memory limit: Respect Capsule memoryLimitMiB

### 9.3 Add Ingestion Metadata
- [ ] 9.3.1 Record ingestion metrics
  - Row counts
  - Byte sizes
  - Duration
  - Store: In job metadata

**Definition of Done:**
- All source types supported
- Chunked processing for large datasets
- Ingestion metadata recorded
- Integration tests for each source type pass

---

## 10. Data Processing and Quality (Requirement 8)

**Priority:** P2 - MEDIUM  
**Estimated Effort:** 3 days  
**Validates:** Requirements 8.1-8.8

### 10.1 Implement Data Quality Checks
- [ ] 10.1.1 Missing value detection
  - Calculate: Percentage per column
  - Report: In quality summary

- [ ] 10.1.2 Duplicate detection
  - Configurable: Matching rules
  - Report: Duplicate count and examples

- [ ] 10.1.3 Outlier detection
  - Methods: IQR, Z-score, Modified Z-score
  - Report: Outlier count and values

### 10.2 Implement Data Cleaning
- [ ] 10.2.1 Missing value imputation
  - Strategies: Mean, median, mode, model-based
  - Auto-select: Based on data type and distribution

- [ ] 10.2.2 Outlier handling
  - Options: Flag, winsorize, remove
  - Configurable: Based on preset

- [ ] 10.2.3 Entity resolution
  - Fuzzy matching: For multi-source data
  - Configurable: Similarity thresholds

### 10.3 Implement Data Quality Score
- [ ] 10.3.1 Calculate DQS
  - Metrics: Completeness, consistency, validity, timeliness
  - Formula: Weighted average
  - Range: 0.0 to 1.0

- [ ] 10.3.2 Add quality warnings
  - Threshold: DQS < 0.7
  - Include: Specific issues in warning

**Definition of Done:**
- All quality checks implemented
- Data cleaning strategies working
- DQS calculation accurate
- Quality warnings generated
- Unit tests for all quality functions pass

---

## 11. Statistical Analysis Engine (Requirement 9)

**Priority:** P2 - MEDIUM  
**Estimated Effort:** 5 days  
**Validates:** Requirements 9.1-9.10

### 11.1 Implement Descriptive Statistics
- [ ] 11.1.1 Basic statistics
  - Mean, median, mode
  - Standard deviation, variance
  - Skewness, kurtosis
  - Percentiles: P5, P10, P25, P50, P75, P90, P95

### 11.2 Implement Correlation Analysis
- [ ] 11.2.1 Correlation coefficients
  - Pearson, Spearman, Kendall
  - Significance tests
  - P-values and effect sizes

### 11.3 Implement Hypothesis Testing
- [ ] 11.3.1 Statistical tests
  - T-test, ANOVA
  - Chi-square, Mann-Whitney
  - Auto-select: Based on data characteristics

### 11.4 Implement Regression Analysis
- [ ] 11.4.1 Regression models
  - Linear, logistic
  - Regularized models (Ridge, Lasso)
  - Return: Coefficients, R-squared, diagnostics

### 11.5 Implement Time Series Analysis
- [ ] 11.5.1 Decomposition
  - Trend, seasonal, residual components
  - Stationarity tests

- [ ] 11.5.2 Forecasting
  - Models: ARIMA, ETS, Prophet
  - Confidence intervals
  - Backtesting

### 11.6 Implement Clustering
- [ ] 11.6.1 Clustering algorithms
  - K-means, DBSCAN
  - Optimal cluster count: Elbow method, silhouette score
  - Return: Cluster assignments, centroids

### 11.7 Implement Classification
- [ ] 11.7.1 Classification models
  - Train models
  - Cross-validation
  - Return: Accuracy, precision, recall, F1 scores

### 11.8 Add Methodology Documentation
- [ ] 11.8.1 Document methods used
  - Include: In analysis results
  - Purpose: Reproducibility

### 11.9 Add Property-Based Tests
- [ ] 11.9.1 Property 15: Descriptive statistics completeness
  - Test: All required metrics returned
  - Generate: Random numeric columns

- [ ] 11.9.2 Property 16: Forecast confidence interval validity
  - Test: Confidence interval contains ~C% of actual values
  - Generate: Random time series

**Definition of Done:**
- All statistical methods implemented
- Auto-selection logic working
- Methodology documentation included
- All property tests pass
- Unit tests for all statistical functions pass

---

## 12. Visualization Generation (Requirement 10)

**Priority:** P2 - MEDIUM  
**Estimated Effort:** 2 days  
**Validates:** Requirements 10.1-10.8

### 12.1 Implement Chart Generation
- [ ] 12.1.1 Auto-select chart types
  - Bar: Categorical vs numeric
  - Line: Time series
  - Scatter: Two numeric variables
  - Histogram: Distribution analysis
  - Box: Distribution comparison
  - Heatmap: Correlation matrix

- [ ] 12.1.2 Generate interactive charts
  - Library: Plotly
  - Features: Zoom, pan, hover
  - Format: HTML files

- [ ] 12.1.3 Allow preset overrides
  - Respect: Chart type specifications in presets

**Definition of Done:**
- All chart types implemented
- Auto-selection logic working
- Interactive features functional
- Charts stored as artifacts
- Unit tests for chart generation pass

---

## 13. Report and Artifact Generation (Requirement 11)

**Priority:** P2 - MEDIUM  
**Estimated Effort:** 3 days  
**Validates:** Requirements 11.1-11.8

### 13.1 Implement Report Generation
- [ ] 13.1.1 HTML reports
  - Include: Summary, methodology, results, charts, tables
  - Template: Professional, branded

- [ ] 13.1.2 JSON artifacts
  - Include: All structured results
  - Purpose: Programmatic consumption

- [ ] 13.1.3 PDF reports
  - Include: Executive summary, key findings
  - Purpose: Distribution

- [ ] 13.1.4 Excel exports
  - Include: Data tables, embedded charts
  - Purpose: Further analysis

### 13.2 Implement Artifact Storage
- [ ] 13.2.1 Store artifacts in MinIO
  - Path: `{tenant_id}/{job_id}/{artifact_type}`
  - Metadata: Job ID, type, size, timestamp

- [ ] 13.2.2 Generate signed URLs
  - Expiration: Configurable (default 1 hour)
  - Return: In artifact references

- [ ] 13.2.3 Implement retention policy
  - Auto-delete: After configured period
  - Default: 30 days

### 13.3 Add PII Redaction
- [ ] 13.3.1 Apply OPA-enforced redaction
  - Detect: PII patterns (email, SSN, phone)
  - Mask: Before including in outputs

### 13.4 Add Property-Based Tests
- [ ] 13.4.1 Property 17: PII masking completeness
  - Test: All PII patterns masked
  - Generate: Random data with PII

**Definition of Done:**
- All report formats implemented
- Artifacts stored in MinIO
- Signed URLs working
- Retention policy enforced
- PII redaction working
- All property tests pass

---

## 14. Job Orchestration (Requirement 12)

**Priority:** P1 - HIGH  
**Estimated Effort:** 3 days  
**Validates:** Requirements 12.1-12.8

### 14.1 Implement Job State Management
- [ ] 14.1.1 Persist job state to PostgreSQL
  - Table: voyant_jobs
  - Fields: id, tenant_id, workflow_instance_id, capsule_id, preset, params, state, progress, stage, error, result, timestamps

- [ ] 14.1.2 Implement checkpointing
  - Checkpoint: At each major stage
  - Store: State snapshot in voyant_checkpoints table
  - Purpose: Recovery after failures

### 14.2 Implement Retry Logic
- [ ] 14.2.1 Add automatic retries
  - Transient errors: Retry up to 3 times
  - Backoff: Exponential (1s, 2s, 4s)
  - Log: Retry attempts

### 14.3 Implement Job Recovery
- [ ] 14.3.1 Resume incomplete jobs on restart
  - Detect: Jobs in RUNNING state
  - Resume: From last checkpoint
  - Log: Recovery attempts

### 14.4 Implement Timeout Handling
- [ ] 14.4.1 Enforce Capsule timeout
  - Monitor: Job execution time
  - Terminate: If exceeds maxRuntimeSeconds
  - Return: Partial results if available

### 14.5 Implement Concurrency Control
- [ ] 14.5.1 Add job queue
  - Queue: Jobs respecting concurrency limits
  - Limit: Configurable (default 50)

- [ ] 14.5.2 Add graceful cancellation
  - Terminate: Within 30 seconds
  - Release: Resources
  - Update: Job state to CANCELLED

### 14.6 Implement Event Publishing
- [ ] 14.6.1 Publish job lifecycle events
  - Events: job.started, job.progress, job.completed, job.failed, job.cancelled
  - Topic: voyant.jobs
  - Schema: SomaStack event schema

### 14.7 Add Property-Based Tests
- [ ] 14.7.1 Property 12: Job state machine validity
  - Test: Only valid transitions allowed
  - Valid: PENDING → RUNNING → (SUCCEEDED | FAILED | CANCELLED)
  - Generate: Random state transition sequences

- [ ] 14.7.2 Property 13: Checkpoint recovery
  - Test: Resume from checkpoint restores correct stage
  - Generate: Random job states and checkpoints

- [ ] 14.7.3 Property 14: Event publication consistency
  - Test: State change publishes event within 5s
  - Generate: Random state changes

### 14.8 Add Property-Based Tests
- [ ] 14.8.1 Property 18: Audit trail completeness
  - Test: All critical events logged
  - Generate: Random job operations

**Definition of Done:**
- Job state persisted and recoverable
- Checkpointing working
- Retry logic implemented
- Timeout enforcement working
- Concurrency control working
- Events published to Kafka
- All property tests pass

---

## 15. Observability and Monitoring (Requirement 13)

**Priority:** P1 - HIGH  
**Estimated Effort:** 2 days  
**Validates:** Requirements 13.1-13.8

### 15.1 Implement Structured Logging
- [ ] 15.1.1 Add correlation IDs
  - Propagate: From SomaAgentHub workflow instance IDs
  - Include: In all log entries

- [ ] 15.1.2 Use structured JSON logs
  - Format: JSON with standard fields
  - Include: Timestamp, level, message, context

### 15.2 Implement Metrics
- [ ] 15.2.1 Add Prometheus metrics
  - Job metrics: total, duration, rows_processed
  - Quality metrics: dqs, missing_values_ratio, duplicate_records
  - Integration metrics: somabrain_latency, somabrain_errors, tool_invocation_latency, capsule_violations
  - Resource metrics: memory_usage, cpu_usage, duckdb_query_duration

- [ ] 15.2.2 Expose metrics endpoint
  - Endpoint: `GET /metrics`
  - Format: Prometheus text format

### 15.3 Implement Distributed Tracing
- [ ] 15.3.1 Add OpenTelemetry spans
  - Propagate: Trace context from SomaAgentHub
  - Emit: Spans for API → workflow → activity
  - Include: Capsule ID, workflow instance ID as attributes

### 15.4 Implement Health Checks
- [ ] 15.4.1 Add health endpoints
  - Liveness: `GET /health`
  - Readiness: `GET /ready`
  - Startup: `GET /startup`

- [ ] 15.4.2 Verify dependencies
  - Check: DuckDB, MinIO, SomaBrain connectivity
  - Return: Aggregate health status

**Definition of Done:**
- Structured logging implemented
- Prometheus metrics exposed
- OpenTelemetry tracing working
- Health checks functional
- Integration with SomaStack observability stack verified

---

## 16. Security and Access Control (Requirement 14)

**Priority:** P0 - CRITICAL  
**Estimated Effort:** 3 days  
**Validates:** Requirements 14.1-14.8

### 16.1 Implement Authentication
- [ ] 16.1.1 Validate JWT tokens
  - File: `voyant/security/auth.py` (already exists)
  - Validate: Against Keycloak OIDC provider
  - Extract: Tenant ID, roles, permissions

- [ ] 16.1.2 Enforce auth on protected routes
  - Apply: KeycloakBearer to all sensitive endpoints
  - Exclude: Health checks, metrics (public)

### 16.2 Implement Authorization
- [ ] 16.2.1 Add role-based access control
  - Roles: voyant-admin, voyant-engineer, voyant-analyst, voyant-viewer
  - Permissions: Derived from roles

- [ ] 16.2.2 Add permission checks
  - Use: require_permission() decorator
  - Check: Before executing operations

### 16.3 Implement Credential Management
- [ ] 16.3.1 Retrieve credentials from SomaAgentHub
  - Never: Store credentials locally
  - Use: Tenant namespace for isolation

### 16.4 Implement PII Protection
- [ ] 16.4.1 Detect PII patterns
  - Patterns: Email, SSN, phone
  - Mask: Before including in outputs

- [ ] 16.4.2 Validate SQL queries
  - Allowlist: SELECT, WITH only
  - Deny: INSERT, UPDATE, DELETE, DROP

### 16.5 Implement Network Security
- [ ] 16.5.1 Restrict egress
  - Enforce: Capsule-defined allowed domains
  - Deny: Connections to non-whitelisted hosts

### 16.6 Implement Audit Logging
- [ ] 16.6.1 Log security events
  - Events: Job creation, data access, credential usage
  - Store: In immutable audit trail
  - Include: Timestamp, actor, resource, outcome

### 16.7 Implement Multi-Tenancy
- [ ] 16.7.1 Isolate data and jobs
  - Use: Namespace separation
  - Consistent: With SomaAgentHub tenant model

- [ ] 16.7.2 Never log raw data
  - Log: Only metadata and aggregates
  - Protect: Sensitive data from logs

**Definition of Done:**
- Auth enforced on all protected routes
- RBAC/ABAC working
- Credentials retrieved from credential store
- PII protection working
- SQL validation working
- Network egress restricted
- Audit logging complete
- Multi-tenancy enforced
- Security audit passes

---

## 17. Performance and Scalability (Requirement 15)

**Priority:** P2 - MEDIUM  
**Estimated Effort:** 3 days  
**Validates:** Requirements 15.1-15.6

### 17.1 Optimize Ingestion Performance
- [ ] 17.1.1 Achieve 100K rows/sec throughput
  - Optimize: DuckDB bulk loading
  - Use: Parallel processing where possible

### 17.2 Optimize Analysis Performance
- [ ] 17.2.1 Complete standard presets in < 5 min
  - For: Datasets < 1M rows
  - Optimize: Statistical computations

### 17.3 Implement Distributed Processing
- [ ] 17.3.1 Add distributed processing for large datasets
  - For: Datasets > 10M rows
  - Use: Temporal parallel activities

### 17.4 Optimize Concurrent Job Performance
- [ ] 17.4.1 Maintain performance with 50 concurrent jobs
  - Target: Response times within 20% of baseline
  - Optimize: Resource allocation

### 17.5 Implement DuckDB Concurrency Control
- [ ] 17.5.1 Serialize DuckDB access
  - Use: Async locks
  - Prevent: Database corruption

### 17.6 Implement Memory Management
- [ ] 17.6.1 Spill to disk when approaching limits
  - Monitor: Memory usage
  - Spill: Intermediate results to disk
  - Prevent: OOM crashes

**Definition of Done:**
- Ingestion throughput ≥ 100K rows/sec
- Standard presets complete in < 5 min for < 1M rows
- Distributed processing working for large datasets
- Concurrent job performance acceptable
- DuckDB concurrency control working
- Memory management preventing OOM
- Performance benchmarks pass

---

## 18. Error Handling and Recovery (Requirement 16)

**Priority:** P2 - MEDIUM  
**Estimated Effort:** 2 days  
**Validates:** Requirements 16.1-16.6

### 18.1 Implement Structured Error Responses
- [ ] 18.1.1 Return structured errors
  - Include: Error code (VYNT-XXXX), message, details
  - Suggest: Remediation steps

### 18.2 Implement Graceful Degradation
- [ ] 18.2.1 Handle data source failures
  - Return: Structured error with source ID, error type, remediation

- [ ] 18.2.2 Handle insufficient data quality
  - Return: Partial results with quality warnings
  - Don't: Fail completely

- [ ] 18.2.3 Handle statistical method failures
  - Attempt: Alternative methods
  - Document: Fallback in results

- [ ] 18.2.4 Handle SomaBrain unavailability
  - Proceed: With analysis
  - Include: Warning about memory persistence failure

### 18.3 Implement Error Security
- [ ] 18.3.1 Never expose internal details
  - Sanitize: Stack traces
  - Hide: Sensitive configuration

**Definition of Done:**
- All errors return structured responses
- Graceful degradation working
- Error security enforced
- Error handling tests pass

---

## 19. Configuration and Deployment (Requirement 17)

**Priority:** P2 - MEDIUM  
**Estimated Effort:** 2 days  
**Validates:** Requirements 17.1-17.8

### 19.1 Implement Configuration Management
- [ ] 19.1.1 Read config from environment variables
  - File: `voyant/core/config.py` (already exists)
  - Provide: Sensible defaults for development

- [ ] 19.1.2 Support hot-reload for non-critical config
  - Reload: Without restart where possible

### 19.2 Implement Kubernetes Support
- [ ] 19.2.1 Support horizontal scaling
  - Stateless: API components
  - Shared: State in PostgreSQL, Redis

- [ ] 19.2.2 Add health probes
  - Liveness: `GET /health`
  - Readiness: `GET /ready`
  - Startup: `GET /startup`

### 19.3 Implement Secret Management
- [ ] 19.3.1 Integrate with Kubernetes Secrets
  - Read: Secrets from K8s Secret objects

- [ ] 19.3.2 Integrate with HashiCorp Vault
  - Read: Secrets from Vault
  - Consistent: With SomaStack secret management

### 19.4 Create Helm Charts
- [ ] 19.4.1 Create Voyant Helm chart
  - Compatible: With SomaStack Helm patterns
  - Include: All necessary resources

### 19.5 Implement Service Discovery
- [ ] 19.5.1 Register with SomaAgentHub
  - On startup: Register as Tool
  - Include: Service endpoint, health check URL

**Definition of Done:**
- Configuration from environment variables working
- Kubernetes deployment working
- Health probes functional
- Secret management integrated
- Helm charts created and tested
- Service discovery working

---

## 20. DataScraper Module Integration (V-006)

**Priority:** P2 - MEDIUM  
**Estimated Effort:** 2 days  
**Validates:** DataScraper module completeness

### 20.1 Consolidate OCR Implementations
- [ ] 20.1.1 Merge OCR modules
  - Primary: `voyant/scraper/media/ocr.py`
  - Remove: `voyant/scraper/parsing/ocr_processor.py`
  - Consolidate: Tesseract-specific logic into primary module

### 20.2 Complete DataScraper Integration
- [ ] 20.2.1 Add to INSTALLED_APPS
  - File: `voyant_project/settings.py`
  - Add: `voyant.scraper`

- [ ] 20.2.2 Run migrations
  - Command: `python manage.py makemigrations voyant.scraper`
  - Command: `python manage.py migrate`

- [ ] 20.2.3 Register workflow in worker
  - File: `voyant/worker/worker_main.py`
  - Register: ScrapeWorkflow

### 20.3 Add DataScraper Tests
- [ ] 20.3.1 Unit tests for security module
  - File: `tests/scraper/test_security.py`
  - Test: SSRF protection, URL validation

- [ ] 20.3.2 Integration tests for workflow
  - File: `tests/scraper/test_workflow.py`
  - Test: End-to-end scraping workflow

**Definition of Done:**
- OCR implementations consolidated
- DataScraper fully integrated
- Migrations applied
- Workflow registered
- Tests passing

---

## 21. Apache Platform Integration

**Priority:** P3 - LOW  
**Estimated Effort:** 10 days  
**Validates:** Apache ecosystem integration

### 21.1 Apache Iceberg Integration
- [ ] 21.1.1 Implement Iceberg lakehouse layer
  - File: `voyant/core/iceberg.py`
  - Replace: DuckDB with Iceberg for data lake
  - Support: ACID transactions, time travel

### 21.2 Apache Flink Integration (Partial - Complete)
- [~] 21.2.1 Complete Flink streaming pipelines
  - Files: `voyant/streaming/*`
  - Implement: Continuous KPIs, real-time anomalies
  - Deploy: Via Temporal StreamingJobWorkflow

### 21.3 Apache Ranger Integration
- [ ] 21.3.1 Enforce Ranger policies
  - File: `voyant/security/ranger.py`
  - Enforce: At query and artifact access
  - Replace: OPA with Ranger for data governance

### 21.4 Apache Atlas Integration
- [ ] 21.4.1 Publish metadata to Atlas
  - File: `voyant/governance/atlas.py`
  - Publish: Lineage, schema, quality metrics
  - Replace: DataHub with Atlas

### 21.5 Apache SkyWalking Integration
- [ ] 21.5.1 Export traces to SkyWalking
  - File: `voyant/observability/skywalking.py`
  - Export: API and workflow traces
  - Replace: OTEL with SkyWalking

### 21.6 Apache NiFi Integration
- [ ] 21.6.1 Add NiFi ingestion adapters
  - File: `voyant/ingestion/nifi.py`
  - Register: Flows with NiFi
  - Support: Complex data pipelines

### 21.7 Apache Superset Integration
- [ ] 21.7.1 Integrate with Superset
  - File: `voyant/bi/superset.py`
  - Export: Curated datasets
  - Create: Dashboards for artifacts

### 21.8 Apache Druid/Pinot Integration
- [ ] 21.8.1 Export to Druid
  - File: `voyant/olap/druid.py`
  - Export: For OLAP workloads

- [ ] 21.8.2 Export to Pinot
  - File: `voyant/olap/pinot.py`
  - Export: For real-time analytics

### 21.9 Apache Tika Integration
- [ ] 21.9.1 Add Tika document extraction
  - File: `voyant/ingestion/tika.py`
  - Use: For unstructured document ingestion
  - Enhance: `voyant/ingestion/unstructured_utils.py`

**Definition of Done:**
- All Apache integrations configured
- Integration tests passing
- Documentation updated
- Deployment guides created

---

## 22. Production Hardening

**Priority:** P1 - HIGH  
**Estimated Effort:** 3 days  
**Validates:** Production readiness

### 22.1 Security Hardening
- [ ] 22.1.1 Remove default secrets
  - Force: Environment variables for all secrets
  - Fail: On startup if secrets not provided in production

- [ ] 22.1.2 Enable security headers
  - CSP, HSTS, X-Frame-Options
  - Configure: In security_settings.py

- [ ] 22.1.3 Enable SSL/TLS
  - Database: SSL connections
  - API: HTTPS only in production

### 22.2 Performance Optimization
- [ ] 22.2.1 Add connection pooling
  - Database: PostgreSQL connection pool
  - Redis: Connection pool

- [ ] 22.2.2 Add caching
  - Cache: Frequently accessed data
  - Use: Redis for distributed caching

### 22.3 Reliability Improvements
- [ ] 22.3.1 Add circuit breakers
  - Wrap: All external service calls
  - Prevent: Cascading failures

- [ ] 22.3.2 Add rate limiting
  - Limit: API requests per tenant
  - Prevent: Abuse

### 22.4 Deployment Validation
- [ ] 22.4.1 Validate docker-compose
  - Check: Healthchecks
  - Check: Dependency order

- [ ] 22.4.2 Update Helm charts
  - Update: For new endpoints and services
  - Test: Deployment to K8s

**Definition of Done:**
- Security hardening complete
- Performance optimized
- Reliability improved
- Deployment validated
- Production deployment successful

---

## 23. Documentation

**Priority:** P2 - MEDIUM  
**Estimated Effort:** 3 days  
**Validates:** Documentation completeness

### 23.1 API Documentation
- [ ] 23.1.1 Generate OpenAPI spec
  - Use: Django Ninja auto-generation
  - Publish: At `/api/docs`

- [ ] 23.1.2 Add API examples
  - Include: Request/response examples
  - Include: Error examples

### 23.2 Architecture Documentation
- [ ] 23.2.1 Update architecture diagrams
  - Reflect: Current implementation
  - Include: All integrations

- [ ] 23.2.2 Document design decisions
  - Create: ADRs for major decisions
  - Store: In `docs/adr/`

### 23.3 Deployment Documentation
- [ ] 23.3.1 Create deployment guide
  - Include: Prerequisites
  - Include: Step-by-step instructions
  - Include: Troubleshooting

- [ ] 23.3.2 Create operations guide
  - Include: Monitoring
  - Include: Alerting
  - Include: Incident response

### 23.4 Developer Documentation
- [ ] 23.4.1 Create developer guide
  - Include: Setup instructions
  - Include: Testing guide
  - Include: Contributing guide

**Definition of Done:**
- API documentation complete
- Architecture documentation updated
- Deployment guide created
- Operations guide created
- Developer guide created

---

## 24. Compliance and Audit

**Priority:** P2 - MEDIUM  
**Estimated Effort:** 2 days  
**Validates:** Compliance requirements

### 24.1 ISO/IEC 25010 Compliance
- [ ] 24.1.1 Verify functional suitability
  - Check: All requirements implemented
  - Check: All acceptance criteria met

- [ ] 24.1.2 Verify performance efficiency
  - Check: Performance targets met
  - Check: Resource usage acceptable

- [ ] 24.1.3 Verify compatibility
  - Check: SomaStack integration working
  - Check: All dependencies compatible

- [ ] 24.1.4 Verify usability
  - Check: API usability
  - Check: Error messages clear

- [ ] 24.1.5 Verify reliability
  - Check: Fault tolerance working
  - Check: Recovery mechanisms working

- [ ] 24.1.6 Verify security
  - Check: Auth/authz working
  - Check: Data protection working

- [ ] 24.1.7 Verify maintainability
  - Check: Code quality acceptable
  - Check: Documentation complete

- [ ] 24.1.8 Verify portability
  - Check: Deployment to different environments working

### 24.2 Security Audit
- [ ] 24.2.1 Conduct security audit
  - Check: OWASP Top 10 compliance
  - Check: Secrets management
  - Check: Network security

- [ ] 24.2.2 Penetration testing
  - Test: API security
  - Test: Auth bypass attempts
  - Test: Injection attacks

### 24.3 Compliance Documentation
- [ ] 24.3.1 Update COMPLIANCE.md
  - Document: Compliance status
  - Document: Remaining gaps

**Definition of Done:**
- ISO/IEC 25010 compliance verified
- Security audit complete
- Penetration testing complete
- Compliance documentation updated

---

## 25. Milestones and Roadmap

### Milestone 1: Foundation (Weeks 1-2) - CRITICAL
**Goal:** Fix critical blockers and establish solid foundation

**Tasks:**
- Section 1: Fix Test Infrastructure (V-001, V-002)
- Section 2: Fix Code Quality Issues (V-003)
- Section 16: Security and Access Control (partial - auth enforcement)

**Success Criteria:**
- All tests pass
- Test coverage ≥ 80%
- Zero ruff/pyright errors
- Auth enforced on all protected routes

---

### Milestone 2: SomaStack Integration (Weeks 3-4) - HIGH PRIORITY
**Goal:** Complete SomaStack integration for Tool registration and core services

**Tasks:**
- Section 3: SomaStack Tool Registration
- Section 4: Capsule Constraint Compliance
- Section 5: SomaBrain Memory Integration
- Section 6: OPA Policy Enforcement
- Section 14: Job Orchestration
- Section 15: Observability and Monitoring

**Success Criteria:**
- VOYANT registered as Tool in SomaAgentHub
- All Capsule constraints enforced
- Memory storage/recall working
- OPA policies enforced
- Job orchestration complete
- Observability stack integrated

---

### Milestone 3: Core Analysis Capabilities (Weeks 5-7) - HIGH PRIORITY
**Goal:** Implement complete analysis pipeline

**Tasks:**
- Section 7: Preset Workflow Execution
- Section 8: Data Source Discovery and Connection
- Section 9: Data Ingestion
- Section 10: Data Processing and Quality
- Section 11: Statistical Analysis Engine
- Section 12: Visualization Generation
- Section 13: Report and Artifact Generation

**Success Criteria:**
- All 6 presets implemented
- Data ingestion working for all source types
- Statistical analysis complete
- Visualizations generated
- Reports and artifacts created

---

### Milestone 4: Production Readiness (Weeks 8-9) - MEDIUM PRIORITY
**Goal:** Harden for production deployment

**Tasks:**
- Section 17: Performance and Scalability
- Section 18: Error Handling and Recovery
- Section 19: Configuration and Deployment
- Section 20: DataScraper Module Integration
- Section 22: Production Hardening

**Success Criteria:**
- Performance targets met
- Error handling complete
- Deployment working
- DataScraper integrated
- Production hardening complete

---

### Milestone 5: Documentation and Compliance (Week 10) - MEDIUM PRIORITY
**Goal:** Complete documentation and compliance verification

**Tasks:**
- Section 23: Documentation
- Section 24: Compliance and Audit

**Success Criteria:**
- All documentation complete
- Compliance verified
- Security audit passed

---

### Milestone 6: Apache Platform Integration (Weeks 11-12) - LOW PRIORITY
**Goal:** Integrate with Apache ecosystem (optional)

**Tasks:**
- Section 21: Apache Platform Integration

**Success Criteria:**
- All Apache integrations working
- Integration tests passing

---

## 26. Risk Management

### High-Risk Items
1. **Test Infrastructure Failures (V-001)**
   - Risk: Cannot validate any functionality
   - Mitigation: Prioritize as P0, allocate dedicated resources

2. **SomaStack Integration Complexity**
   - Risk: Integration failures block deployment
   - Mitigation: Test against local SomaStack early, maintain fallback modes

3. **Performance Targets**
   - Risk: Cannot meet 100K rows/sec ingestion
   - Mitigation: Profile early, optimize incrementally

4. **Security Vulnerabilities**
   - Risk: Production deployment with security gaps
   - Mitigation: Security audit before production, penetration testing

### Medium-Risk Items
1. **Code Quality Issues (V-003)**
   - Risk: Technical debt accumulation
   - Mitigation: Fix incrementally, enforce pre-commit hooks

2. **DataScraper Integration (V-006)**
   - Risk: Redundant implementations cause confusion
   - Mitigation: Consolidate early, document clearly

3. **Apache Platform Integration**
   - Risk: Complex integrations delay delivery
   - Mitigation: Mark as optional (Milestone 6), defer if needed

---

## 27. Success Metrics

### Code Quality Metrics
- Test coverage: ≥ 80%
- Ruff errors: 0
- Pyright errors: 0
- Code review approval: 100%

### Performance Metrics
- Ingestion throughput: ≥ 100K rows/sec
- Analysis completion: < 5 min for < 1M rows
- API latency: < 200ms P99
- Concurrent jobs: 50+ simultaneous

### Reliability Metrics
- Job success rate: > 99%
- System availability: 99.9%
- Recovery time: < 5 min

### Security Metrics
- Auth enforcement: 100% of protected routes
- PII masking: 100% of detected patterns
- Audit logging: 100% of critical events
- Security audit: Pass

### Compliance Metrics
- ISO/IEC 25010: 100% compliance
- OWASP Top 10: 100% compliance
- Requirements coverage: 100%

---

## 28. Notes and Assumptions

### Assumptions
1. SomaStack local stack available for integration testing
2. Keycloak configured with voyant realm
3. PostgreSQL, Redis, Kafka, MinIO available
4. Temporal server running
5. Development environment has Python 3.11+

### Dependencies
1. SomaAgentHub v4.0.0+
2. SomaBrain v1.0+
3. OPA v0.50+
4. Kafka v3.0+
5. MinIO (latest)
6. DuckDB v0.9+
7. PostgreSQL v15+
8. Redis v7+
9. Temporal (latest)

### Out of Scope
1. Custom UI development (use SomaAgent01 Web UI)
2. Mobile app development
3. Real-time streaming analytics (partial - Flink integration optional)
4. Machine learning model training (use pre-trained models)

---

**END OF TASKS DOCUMENT**

