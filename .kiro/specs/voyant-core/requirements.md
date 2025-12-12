# VOYANT Software Requirements Specification (SRS)
## Autonomous Data Intelligence Tool for SomaStack

**Document ID:** VOYANT-SRS-002  
**Version:** 2.0  
**Date:** December 8, 2025  
**Status:** Draft for Review  
**Classification:** Technical Specification  
**Compliance:** ISO/IEC/IEEE 29148:2018 (Systems and Software Engineering - Life Cycle Processes - Requirements Engineering)

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) defines the complete functional and non-functional requirements for **VOYANT**, an autonomous data intelligence tool designed to operate as a first-class component within the **SomaStack** ecosystem. VOYANT provides AI agents with comprehensive data discovery, ingestion, analysis, and visualization capabilities.

### 1.2 Scope

VOYANT is a **Tool** registered in **SomaAgentHub** that:
- Receives analysis requests from AI agents via SomaAgentHub's Tool Runner
- Autonomously discovers, connects to, and ingests data from heterogeneous sources
- Applies statistical analysis, machine learning, and visualization processes
- Stores analysis artifacts and returns actionable results
- Integrates with **SomaBrain** for memory persistence (no separate memory layer)
- Respects **Capsule** constraints and **Constitution** safety policies

### 1.3 Product Perspective

VOYANT operates within the SomaStack architecture:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SOMASTACK ECOSYSTEM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │ SomaAgent01  │───►│SomaAgentHub  │───►│   VOYANT     │                   │
│  │ (Runtime)    │    │(Orchestrator)│    │   (Tool)     │                   │
│  └──────────────┘    └──────┬───────┘    └──────┬───────┘                   │
│                             │                   │                           │
│                             ▼                   ▼                           │
│                      ┌──────────────┐    ┌──────────────┐                   │
│                      │  SomaBrain   │◄───│  Data Sources│                   │
│                      │  (Memory)    │    │  (External)  │                   │
│                      └──────────────┘    └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.4 Intended Audience

- Software Architects designing SomaStack integrations
- Development Teams implementing VOYANT components
- QA Engineers validating integration points
- DevOps Engineers deploying the SomaStack
- Security Officers auditing data access patterns


### 1.5 Document Conventions

- **SHALL**: Mandatory requirement (MUST be implemented)
- **SHOULD**: Recommended requirement (STRONGLY recommended)
- **MAY**: Optional requirement (implementation discretion)
- **EARS Pattern**: All requirements follow Easy Approach to Requirements Syntax
- **INCOSE Compliance**: All requirements follow INCOSE quality rules

### 1.6 References

| Document | Version | Description |
|----------|---------|-------------|
| SRS-SomaAgentHub | 4.0.0 | SomaAgentHub orchestration platform specification |
| SomaBrain Technical Overview | 1.0 | Cognitive memory service specification |
| SomaAgent01 Roadmap | 1.0 | Agent runtime component specification |
| ISO/IEC/IEEE 29148:2018 | 2018 | Requirements engineering standard |

---

## 2. Glossary

### 2.1 SomaStack Terms

| Term | Definition |
|------|------------|
| **SomaAgentHub** | Graph-based workflow orchestration platform that manages agents, crews, and tools |
| **SomaBrain** | Multi-tenant cognitive memory service providing semantic, vector, and episodic storage |
| **SomaAgent01** | Concrete agent runtime (fork of Agent Zero) with gateway, Web UI, and conversation worker |
| **AgentSpec** | JSON schema defining an agent's instructions, tools, memory bindings, and constraints |
| **CrewSpec** | Collection of agents coordinated by a supervisor or classifier |
| **GraphWorkflow** | Declarative DAG describing orchestration of agents, tools, and conditional branches |
| **Capsule** | Immutable YAML document defining execution constraints, resources, and security policy |
| **Constitution** | Cryptographically signed policy document guaranteeing safety and compliance |
| **Tool Runner** | SomaAgentHub component that executes registered tools with OPA policy enforcement |
| **HITL** | Human-In-The-Loop - pause points awaiting human review |

### 2.2 VOYANT Terms

| Term | Definition |
|------|------------|
| **VOYANT** | Autonomous data intelligence tool (French: "seer, clairvoyant") |
| **Preset** | Pre-configured analysis workflow (e.g., BENCHMARK_MY_BRAND) |
| **Job** | A single execution of an analysis request within VOYANT |
| **Artifact** | Generated output file (chart, report, data export) |
| **DQS** | Data Quality Score (0.0 to 1.0) indicating analysis reliability |
| **Connector** | Integration module for a specific data source type |

### 2.3 Technical Terms

| Term | Definition |
|------|------------|
| **OPA** | Open Policy Agent - policy decision point for security and governance |
| **Temporal** | Durable workflow engine used by SomaAgentHub for execution |
| **MCP** | Model Context Protocol - standard interface for AI agent tool communication |
| **OTEL** | OpenTelemetry - observability framework for traces and metrics |

---

## 3. System Overview

### 3.1 System Context

VOYANT is registered as a **Tool** in SomaAgentHub's Agent Registry. It is invoked through GraphWorkflow nodes and respects Capsule constraints.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VOYANT INTEGRATION CONTEXT                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐         GraphWorkflow          ┌─────────────────┐    │
│  │   AI Agent      │◄──────────────────────────────►│  SomaAgentHub   │    │
│  │ (via Agent01)   │                                │  Tool Runner    │    │
│  └─────────────────┘                                └────────┬────────┘    │
│                                                              │             │
│                                                              │ invokes     │
│                                                              ▼             │
│  ┌─────────────────┐         Memory API             ┌─────────────────┐    │
│  │   SomaBrain     │◄──────────────────────────────►│     VOYANT      │    │
│  │   (Memory)      │                                │     (Tool)      │    │
│  └─────────────────┘                                └────────┬────────┘    │
│                                                              │             │
│                    ┌─────────────────────────────────────────┼─────────┐   │
│                    │                             │           │         │   │
│              ┌─────▼─────┐               ┌───────▼───────┐  ▼         │   │
│              │   Data    │               │  Statistical  │ Artifacts  │   │
│              │  Sources  │               │    Engine     │ (MinIO)    │   │
│              └───────────┘               └───────────────┘            │   │
└─────────────────────────────────────────────────────────────────────────────┘
```


### 3.2 Integration Points

| Integration Point | SomaStack Component | Protocol | Description |
|-------------------|---------------------|----------|-------------|
| **Tool Registration** | SomaAgentHub Agent Registry | REST/gRPC | VOYANT registers as a Tool with JSON manifest |
| **Tool Invocation** | SomaAgentHub Tool Runner | HTTP/gRPC | Tool Runner calls VOYANT endpoints |
| **Memory Storage** | SomaBrain | HTTP REST | VOYANT stores/recalls analysis context via SomaBrain API |
| **Policy Enforcement** | OPA (via SomaAgentHub) | HTTP | All tool invocations pass OPA policy checks |
| **Capsule Constraints** | SomaAgentHub | YAML | VOYANT respects resource limits, tool whitelist, network egress |
| **Constitution** | SomaBrain | JSON | VOYANT respects signed safety policies |
| **Observability** | OTEL Collector | OTLP | Traces and metrics exported to SomaStack observability |
| **Events** | Kafka | Kafka Protocol | Job lifecycle events published to SomaStack event bus |

### 3.3 Major Components

| Component | Responsibility | SomaStack Dependency |
|-----------|----------------|----------------------|
| **Tool Interface Layer** | Exposes VOYANT as a SomaAgentHub Tool | SomaAgentHub Tool Runner |
| **Ingestion Layer** | Data source discovery and ingestion | None (external sources) |
| **Processing Layer** | Data cleaning, validation, transformation | None |
| **Statistical Layer** | Analysis, ML, forecasting | None |
| **Visualization Layer** | Chart and report generation | None |
| **Memory Integration** | Analysis context persistence | SomaBrain |
| **Artifact Storage** | Generated outputs | MinIO (shared with SomaStack) |

---

## 4. Functional Requirements

### Requirement 1: SomaAgentHub Tool Registration

**User Story:** As a SomaAgentHub administrator, I want VOYANT to register as a Tool in the Agent Registry, so that agents can invoke data analysis capabilities through GraphWorkflows.

#### Acceptance Criteria

1. WHEN SomaAgentHub starts, THE VOYANT tool manifest SHALL be discoverable via the Agent Registry API at `GET /v1/tools/voyant`.

2. WHEN the VOYANT tool manifest is retrieved, THE system SHALL return a JSON document containing tool identifier, description, input schema, output schema, security level, timeout configuration, and cost estimate.

3. WHEN a GraphWorkflow node references `toolId: voyant`, THE SomaAgentHub Tool Runner SHALL route the invocation to the VOYANT service endpoint.

4. WHEN VOYANT receives an invocation from Tool Runner, THE system SHALL validate the request against the registered input schema before processing.

5. IF the Tool Runner sends a request that violates the input schema, THEN VOYANT SHALL return a structured error response with validation failure details within 100 milliseconds.

6. WHEN VOYANT completes processing, THE system SHALL return a response conforming to the registered output schema.

7. WHEN VOYANT is deployed, THE system SHALL register with SomaAgentHub using the tool registration endpoint `POST /v1/tools`.

---

### Requirement 2: Capsule Constraint Compliance

**User Story:** As a security officer, I want VOYANT to respect Capsule constraints, so that data analysis operations execute within defined security boundaries.

#### Acceptance Criteria

1. WHEN a GraphWorkflow node invokes VOYANT with a Capsule reference, THE system SHALL retrieve and parse the Capsule YAML before execution.

2. WHEN a Capsule specifies `toolWhitelist`, THE system SHALL verify that all sub-tools VOYANT intends to use are in the whitelist before proceeding.

3. WHEN a Capsule specifies `networkEgress` restrictions, THE system SHALL restrict all outbound connections to the allowed destinations only.

4. WHEN a Capsule specifies `maxRuntimeSeconds`, THE system SHALL terminate execution and return partial results if the timeout is exceeded.

5. WHEN a Capsule specifies `memoryLimitMiB`, THE system SHALL enforce memory limits and spill to disk rather than exceeding the limit.

6. WHEN a Capsule specifies `cpuLimitMillicores`, THE system SHALL throttle CPU usage to respect the limit.

7. IF VOYANT detects a Capsule violation during execution, THEN THE system SHALL abort the operation, log the violation to the audit trail, and return a structured error response.

8. WHEN Capsule constraints are enforced, THE system SHALL record the Capsule ID and constraint evaluation outcome in the job metadata.

---

### Requirement 3: SomaBrain Memory Integration

**User Story:** As an AI agent, I want VOYANT to persist analysis context to SomaBrain, so that I can recall previous analyses and build on prior knowledge.

#### Acceptance Criteria

1. WHEN VOYANT completes an analysis job, THE system SHALL store an analysis summary record in SomaBrain via `POST /memory/remember` with the tenant's namespace.

2. WHEN storing analysis context, THE system SHALL include job identifier, preset name, data source identifiers, key findings, and artifact references in the memory payload.

3. WHEN an agent requests analysis on a topic previously analyzed, THE system SHALL query SomaBrain via `POST /memory/recall` to retrieve relevant prior analyses.

4. WHEN prior analyses are retrieved, THE system SHALL incorporate relevant context into the current analysis to provide continuity.

5. WHEN storing memory records, THE system SHALL propagate the tenant ID and session ID from the originating GraphWorkflow context.

6. IF SomaBrain is unavailable, THEN THE system SHALL proceed with analysis but include a warning in the response indicating memory persistence failed.

7. WHEN memory records are stored, THE system SHALL tag them with `fact: analysis` to enable filtered recall.

8. WHEN VOYANT stores memory, THE system SHALL respect SomaBrain's Constitution by passing payloads through `constitution_engine.check` before storage.


---

### Requirement 4: OPA Policy Enforcement

**User Story:** As a security officer, I want VOYANT to enforce OPA policies, so that data access and tool execution comply with organizational governance rules.

#### Acceptance Criteria

1. WHEN VOYANT receives a tool invocation, THE system SHALL query the OPA policy endpoint before executing any data access operations.

2. WHEN OPA policy evaluation returns `deny`, THE system SHALL abort the operation and return a structured error response with the policy violation details.

3. WHEN connecting to external data sources, THE system SHALL evaluate OPA policies for data egress authorization.

4. WHEN generating artifacts containing potentially sensitive data, THE system SHALL evaluate OPA policies for data classification and apply appropriate redaction.

5. WHEN OPA is unavailable, THE system SHALL apply fail-closed semantics and deny the operation rather than proceeding without policy evaluation.

6. WHEN policy decisions are made, THE system SHALL log the decision to the immutable audit trail with timestamp, actor, resource, and outcome.

7. WHEN a Capsule includes an `opaPolicy` reference, THE system SHALL load and evaluate that specific policy in addition to default policies.

---

### Requirement 5: Preset Workflow Execution

**User Story:** As an AI agent, I want to execute pre-configured analysis workflows, so that I can obtain comprehensive results without specifying individual steps.

#### Acceptance Criteria

1. WHEN an agent invokes the `BENCHMARK_MY_BRAND` preset, THE system SHALL perform market share calculation, competitive positioning, sentiment analysis, and trend forecasting for the specified brand and competitors.

2. WHEN an agent invokes the `PREDICT_SALES` preset, THE system SHALL generate sales forecasts with confidence intervals using time series analysis methods.

3. WHEN an agent invokes the `FORECAST_DEMAND` preset, THE system SHALL decompose time series into trend, seasonal, and residual components and produce demand predictions.

4. WHEN an agent invokes the `DETECT_ANOMALIES` preset, THE system SHALL identify statistical outliers using IQR, Z-score, and Isolation Forest methods and return anomaly scores with explanations.

5. WHEN an agent invokes the `SEGMENT_CUSTOMERS` preset, THE system SHALL perform clustering analysis using K-means or DBSCAN and return customer segments with profile characteristics.

6. WHEN an agent invokes the `FIX_DATA_QUALITY` preset, THE system SHALL detect and remediate data quality issues including missing values, duplicates, and format inconsistencies.

7. WHEN any preset execution completes, THE system SHALL generate a Data Quality Score between 0.0 and 1.0 indicating the reliability of the analysis.

8. WHILE a preset is executing, THE system SHALL emit progress events to Kafka at intervals not exceeding 5 seconds.

---

### Requirement 6: Data Source Discovery and Connection

**User Story:** As an AI agent, I want VOYANT to automatically discover and connect to data sources, so that I do not need to manually configure integrations.

#### Acceptance Criteria

1. WHEN an agent provides a URL hint, THE system SHALL analyze the URL pattern and return detected source type, authentication requirements, and connection confidence score.

2. WHEN the system detects a known API pattern (REST, GraphQL, database connection string), THE system SHALL generate appropriate connector configuration automatically.

3. WHEN a data source requires OAuth authentication, THE system SHALL initiate the OAuth flow and store obtained tokens in SomaAgentHub's secure credential store.

4. WHEN a data source requires API key authentication, THE system SHALL retrieve credentials from SomaAgentHub's credential store using the tenant's namespace.

5. WHEN connecting to a new source, THE system SHALL discover the schema and catalog available tables, fields, and data types.

6. IF a connection attempt fails, THEN THE system SHALL retry with exponential backoff (0.5s → 1s → 2s → 4s → 5s cap) up to 5 attempts before reporting failure.

7. WHEN a previously configured source becomes unavailable, THE system SHALL attempt reconnection and notify via job status if data cannot be retrieved.

8. WHEN discovering data sources, THE system SHALL respect Capsule `networkEgress` restrictions and only probe allowed destinations.

---

### Requirement 7: Data Ingestion

**User Story:** As an AI agent, I want VOYANT to ingest data from multiple source types, so that I can analyze data regardless of its origin or format.

#### Acceptance Criteria

1. WHEN ingesting from structured sources (CSV, Excel, JSON, Parquet), THE system SHALL automatically detect schema, data types, and encoding.

2. WHEN ingesting from databases (PostgreSQL, MySQL, MongoDB), THE system SHALL use connection pooling and execute queries with configurable timeouts.

3. WHEN ingesting from APIs, THE system SHALL handle pagination, rate limiting, and authentication token refresh automatically.

4. WHEN ingesting from documents (PDF, Word, PowerPoint), THE system SHALL extract text content, tables, and metadata using document parsing libraries.

5. WHEN ingesting from web pages, THE system SHALL parse HTML content and extract structured data.

6. WHEN ingesting streaming data, THE system SHALL buffer and batch records for efficient processing.

7. WHILE ingesting large datasets exceeding 1 million rows, THE system SHALL process data in chunks to maintain memory efficiency within Capsule limits.

8. WHEN ingestion completes, THE system SHALL record row counts, byte sizes, and ingestion duration in job metadata.

---

### Requirement 8: Data Processing and Quality

**User Story:** As an AI agent, I want VOYANT to clean and validate data automatically, so that analysis results are reliable and accurate.

#### Acceptance Criteria

1. WHEN processing ingested data, THE system SHALL detect and report missing value percentages per column.

2. WHEN processing ingested data, THE system SHALL identify duplicate records using configurable matching rules.

3. WHEN processing ingested data, THE system SHALL detect outliers using IQR, Z-score, and Modified Z-score methods.

4. WHEN missing values are detected, THE system SHALL apply appropriate imputation strategies (mean, median, mode, or model-based) based on data type and distribution.

5. WHEN outliers are detected, THE system SHALL flag, winsorize, or remove outliers based on preset configuration.

6. WHEN processing completes, THE system SHALL compute a Data Quality Score based on completeness, consistency, validity, and timeliness metrics.

7. IF the Data Quality Score falls below 0.7, THEN THE system SHALL include quality warnings in the analysis results.

8. WHEN data from multiple sources is combined, THE system SHALL perform entity resolution using fuzzy matching with configurable similarity thresholds.


---

### Requirement 9: Statistical Analysis Engine

**User Story:** As an AI agent, I want VOYANT to perform rigorous statistical analysis, so that insights are scientifically valid and actionable.

#### Acceptance Criteria

1. WHEN performing descriptive statistics, THE system SHALL calculate mean, median, mode, standard deviation, variance, skewness, kurtosis, and percentiles (P5, P10, P25, P50, P75, P90, P95).

2. WHEN performing correlation analysis, THE system SHALL compute Pearson, Spearman, and Kendall correlation coefficients with significance tests.

3. WHEN performing hypothesis testing, THE system SHALL execute appropriate tests (t-test, ANOVA, chi-square, Mann-Whitney) based on data characteristics and return p-values with effect sizes.

4. WHEN performing regression analysis, THE system SHALL fit linear, logistic, and regularized models and return coefficients, R-squared, and diagnostic metrics.

5. WHEN performing time series analysis, THE system SHALL decompose series into trend, seasonal, and residual components and test for stationarity.

6. WHEN performing forecasting, THE system SHALL generate predictions using ARIMA, ETS, or Prophet models with confidence intervals.

7. WHEN performing clustering, THE system SHALL determine optimal cluster count using elbow method or silhouette score and return cluster assignments with centroids.

8. WHEN performing classification, THE system SHALL train models, perform cross-validation, and return accuracy, precision, recall, and F1 scores.

9. WHEN statistical methods are selected automatically, THE system SHALL choose appropriate methods based on data types, distributions, and sample sizes.

10. WHEN statistical computations complete, THE system SHALL include methodology documentation in the results for reproducibility.

---

### Requirement 10: Visualization Generation

**User Story:** As an AI agent, I want VOYANT to generate appropriate visualizations automatically, so that analysis results are visually interpretable.

#### Acceptance Criteria

1. WHEN generating charts, THE system SHALL automatically select chart type (bar, line, scatter, histogram, box, heatmap) based on data characteristics.

2. WHEN a categorical variable and numeric variable are present, THE system SHALL generate a bar chart comparing categories.

3. WHEN time series data is present, THE system SHALL generate a line chart showing trends over time.

4. WHEN two numeric variables are analyzed for correlation, THE system SHALL generate a scatter plot with trend line.

5. WHEN distribution analysis is performed, THE system SHALL generate histograms with distribution curve overlay.

6. WHEN multiple variables are correlated, THE system SHALL generate a heatmap showing the correlation matrix.

7. WHEN charts are generated, THE system SHALL produce interactive HTML files using Plotly with zoom, pan, and hover capabilities.

8. WHEN a preset specifies chart requirements, THE system SHALL override automatic selection with specified chart types.

---

### Requirement 11: Report and Artifact Generation

**User Story:** As an AI agent, I want VOYANT to produce comprehensive reports, so that analysis results can be shared and archived.

#### Acceptance Criteria

1. WHEN a job completes, THE system SHALL generate an HTML report containing summary, methodology, results, charts, and data tables.

2. WHEN a job completes, THE system SHALL generate a JSON artifact containing all structured results for programmatic consumption.

3. WHEN requested, THE system SHALL generate PDF reports suitable for executive distribution.

4. WHEN requested, THE system SHALL generate Excel exports containing data tables and embedded charts.

5. WHEN artifacts are generated, THE system SHALL store them in MinIO object storage with unique paths based on job identifier.

6. WHEN artifacts are requested, THE system SHALL return signed URLs with configurable expiration times.

7. WHEN artifact retention period expires, THE system SHALL automatically delete artifacts according to configured retention policy.

8. WHEN generating reports, THE system SHALL apply OPA-enforced PII redaction before including data in outputs.

---

### Requirement 12: Job Orchestration

**User Story:** As an AI agent, I want VOYANT to reliably execute long-running analysis jobs, so that complex analyses complete successfully even under adverse conditions.

#### Acceptance Criteria

1. WHEN a job is created, THE system SHALL persist job state to durable storage before beginning execution.

2. WHILE a job is executing, THE system SHALL checkpoint progress at each major stage to enable recovery.

3. IF a job execution fails due to transient error, THEN THE system SHALL automatically retry the failed activity up to 3 times with exponential backoff.

4. IF the VOYANT service restarts during job execution, THEN THE system SHALL resume incomplete jobs from the last checkpoint.

5. WHEN a job exceeds the Capsule-defined timeout, THE system SHALL terminate execution and mark the job as timed out with partial results if available.

6. WHEN multiple jobs are submitted concurrently, THE system SHALL queue and execute jobs respecting configured concurrency limits.

7. WHEN a job is cancelled by the agent, THE system SHALL terminate execution gracefully and release resources within 30 seconds.

8. WHEN job state changes occur, THE system SHALL publish events to Kafka for SomaAgentHub workflow coordination.

---

### Requirement 13: Observability and Monitoring

**User Story:** As a system operator, I want comprehensive observability into VOYANT operations, so that I can monitor health, diagnose issues, and ensure SLA compliance.

#### Acceptance Criteria

1. WHEN the system operates, THE system SHALL emit structured JSON logs with correlation identifiers linking to SomaAgentHub workflow instance IDs.

2. WHEN jobs execute, THE system SHALL record duration, stage timings, row counts, and error counts as Prometheus metrics.

3. WHEN requests traverse the system, THE system SHALL propagate OpenTelemetry trace context from SomaAgentHub and emit spans for each major operation.

4. WHEN job lifecycle events occur, THE system SHALL publish events to Kafka using the SomaStack event schema.

5. WHEN health checks are requested, THE system SHALL verify connectivity to all dependencies (DuckDB, MinIO, SomaBrain) and return aggregate health status.

6. WHEN metrics are scraped, THE system SHALL expose Prometheus-format metrics on a dedicated endpoint compatible with SomaStack monitoring.

7. WHEN the system starts, THE system SHALL perform startup self-checks and report readiness only after all critical dependencies are verified.

8. WHEN tracing spans are emitted, THE system SHALL include Capsule ID and workflow instance ID as span attributes.


---

### Requirement 14: Security and Access Control

**User Story:** As a security officer, I want VOYANT to enforce security controls consistent with SomaStack policies, so that data and credentials are protected from unauthorized access.

#### Acceptance Criteria

1. WHEN a tool invocation is received, THE system SHALL authenticate the caller by validating the JWT token issued by SomaAgentHub's Auth Service.

2. WHEN credentials are needed for data source connections, THE system SHALL retrieve them from SomaAgentHub's secure credential store (never store credentials locally).

3. WHEN PII patterns (email, SSN, phone) are detected in output data, THE system SHALL mask sensitive values before including them in results.

4. WHEN SQL queries are executed, THE system SHALL validate queries against allowlist of permitted statement types (SELECT, WITH only).

5. WHEN network connections are made, THE system SHALL restrict egress to Capsule-defined allowed domains only.

6. WHEN audit events occur (job creation, data access, credential usage), THE system SHALL log events to the SomaStack immutable audit storage.

7. WHEN multi-tenant mode is enabled, THE system SHALL isolate data and jobs between tenants using namespace separation consistent with SomaAgentHub tenant model.

8. WHEN processing data, THE system SHALL never log raw data values; only metadata and aggregates are permitted in logs.

---

### Requirement 15: Performance and Scalability

**User Story:** As a system architect, I want VOYANT to meet performance targets, so that AI agents receive timely responses for their analysis requests.

#### Acceptance Criteria

1. WHEN ingesting data, THE system SHALL achieve throughput of 100,000 rows per second or higher for structured data sources.

2. WHEN executing standard presets on datasets under 1 million rows, THE system SHALL complete analysis within 5 minutes.

3. WHEN processing large datasets exceeding 10 million rows, THE system SHALL utilize distributed processing frameworks.

4. WHEN multiple jobs execute concurrently, THE system SHALL maintain response times within 20% of single-job baseline for up to 50 concurrent jobs.

5. WHEN DuckDB operations are requested concurrently, THE system SHALL serialize access using async locks to prevent corruption.

6. WHEN memory usage approaches Capsule-defined limits, THE system SHALL spill intermediate results to disk rather than failing.

---

### Requirement 16: Error Handling and Recovery

**User Story:** As an AI agent, I want VOYANT to handle errors gracefully, so that I receive meaningful feedback when issues occur.

#### Acceptance Criteria

1. IF a data source connection fails, THEN THE system SHALL return a structured error with source identifier, error type, and suggested remediation.

2. IF data quality is insufficient for requested analysis, THEN THE system SHALL return partial results with quality warnings rather than failing completely.

3. IF a statistical method fails due to data characteristics, THEN THE system SHALL attempt alternative methods and document the fallback in results.

4. IF SomaBrain is unavailable, THEN THE system SHALL proceed with analysis but include a warning indicating memory persistence failed.

5. IF an unrecoverable error occurs, THEN THE system SHALL mark the job as failed, preserve diagnostic information, and return a structured error response.

6. WHEN errors occur, THE system SHALL never expose internal stack traces or sensitive configuration details in responses to agents.

---

### Requirement 17: Configuration and Deployment

**User Story:** As a DevOps engineer, I want VOYANT to be deployable as part of the SomaStack, so that I can operate it reliably alongside other SomaStack components.

#### Acceptance Criteria

1. WHEN deployed, THE system SHALL read configuration from environment variables with sensible defaults for development environments.

2. WHEN deployed to Kubernetes, THE system SHALL support horizontal scaling of stateless API components.

3. WHEN deployed, THE system SHALL expose liveness, readiness, and startup probe endpoints for orchestrator health management.

4. WHEN configuration changes are applied, THE system SHALL apply non-critical changes without restart where possible.

5. WHEN secrets are required, THE system SHALL integrate with Kubernetes Secrets or HashiCorp Vault consistent with SomaStack secret management.

6. WHEN deployed, THE system SHALL include Helm charts compatible with SomaStack Helm deployment patterns.

7. WHEN deployed alongside SomaAgentHub, THE system SHALL share the same Kafka, Redis, and PostgreSQL instances where appropriate.

8. WHEN deployed, THE system SHALL register itself with SomaAgentHub's service discovery mechanism.

---

## 5. Non-Functional Requirements

### 5.1 Performance Requirements

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Tool Invocation Latency | < 200ms | P99 latency for acknowledgment |
| Ingestion Throughput | > 100K rows/sec | Rows processed per second |
| Analysis Completion | < 5 min for < 1M rows | Job duration metric |
| Concurrent Jobs | 50+ simultaneous | Load test with concurrent requests |
| SomaBrain Memory Latency | < 50ms | P99 latency for remember/recall |

### 5.2 Reliability Requirements

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Job Success Rate | > 99% | Successful jobs / total jobs |
| System Availability | 99.9% | Uptime monitoring |
| Data Durability | 99.999999999% | MinIO replication factor |
| Recovery Time | < 5 min | Time to resume after failure |
| SomaBrain Dependency | Graceful degradation | Memory offline warning |

### 5.3 Security Requirements

| Requirement | Implementation |
|-------------|----------------|
| Encryption in Transit | TLS 1.3 for all connections |
| Encryption at Rest | AES-256 for sensitive data |
| Authentication | JWT validation via SomaAgentHub Auth Service |
| Authorization | OPA policy enforcement |
| Audit Logging | Immutable logs to SomaStack audit storage |
| PII Protection | Automatic detection and masking |

### 5.4 Scalability Requirements

| Dimension | Target |
|-----------|--------|
| Data Volume | 100GB+ per job |
| Concurrent Users | 100+ agents |
| Storage Growth | 1TB+ total capacity |
| Horizontal Scaling | Stateless API to 10+ replicas |


---

## 6. Interface Requirements

### 6.1 SomaAgentHub Tool Interface

VOYANT registers as a Tool in SomaAgentHub using the following manifest:

```json
{
  "id": "voyant",
  "type": "http",
  "name": "VOYANT Data Intelligence",
  "description": "Autonomous data discovery, ingestion, analysis, and visualization",
  "version": "2.0.0",
  "endpoint": "http://voyant:8000/v1/invoke",
  "timeoutSec": 300,
  "securityLevel": "medium",
  "costEstimate": {
    "baseCredits": 10,
    "perRowCredits": 0.001
  },
  "inputSchema": {
    "type": "object",
    "required": ["action"],
    "properties": {
      "action": {
        "type": "string",
        "enum": ["discover", "connect", "analyze", "status", "result", "query"]
      },
      "preset": { "type": "string" },
      "params": { "type": "object" },
      "job_id": { "type": "string" },
      "hint": { "type": "string" },
      "sql": { "type": "string" }
    }
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "job_id": { "type": "string" },
      "status": { "type": "string" },
      "result": { "type": "object" },
      "error": { "type": "object" }
    }
  }
}
```

### 6.2 VOYANT API Endpoints

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| `POST` | `/v1/invoke` | Main tool invocation endpoint (called by Tool Runner) | Action-specific payload | Job ID or result |
| `GET` | `/v1/presets` | List available analysis presets | – | Preset catalog |
| `GET` | `/v1/jobs/{id}` | Get job status and progress | – | Job status object |
| `GET` | `/v1/jobs/{id}/result` | Get completed job results | – | Analysis results |
| `GET` | `/v1/artifacts/{id}/{type}` | Get artifact by type | – | Signed URL |
| `GET` | `/health` | Health check endpoint | – | Health status |
| `GET` | `/ready` | Readiness probe | – | Ready status |
| `GET` | `/metrics` | Prometheus metrics | – | Metrics text |

### 6.3 SomaBrain Memory Interface

VOYANT uses SomaBrain's HTTP API for memory operations:

```
# Store analysis context
POST /memory/remember
{
  "task": "voyant_analysis",
  "content": "Analysis of sales data for Q4 2025...",
  "fact": "analysis",
  "metadata": {
    "job_id": "uuid",
    "preset": "PREDICT_SALES",
    "data_sources": ["postgres://sales_db"],
    "dqs": 0.92
  }
}

# Recall prior analyses
POST /memory/recall
{
  "query": "sales forecast Q4",
  "limit": 5,
  "type": "analysis"
}
```

### 6.4 Kafka Event Interface

VOYANT publishes job lifecycle events to Kafka using the SomaStack event schema:

```json
{
  "event": "voyant.job.state.changed",
  "job_id": "uuid",
  "workflow_instance_id": "uuid",
  "capsule_id": "string",
  "state": "running|succeeded|failed|cancelled",
  "progress": 0.75,
  "stage": "statistical_analysis",
  "timestamp": "ISO8601",
  "tenant_id": "uuid",
  "extra": {
    "preset": "PREDICT_SALES",
    "rows_processed": 150000,
    "dqs": 0.92
  }
}
```

### 6.5 Metrics Interface

Prometheus metrics exposed at `/metrics`:

```
# Job metrics
voyant_jobs_total{preset, state}
voyant_job_duration_seconds{preset, stage}
voyant_job_rows_processed_total{preset}

# Data quality metrics
voyant_data_quality_score{preset}
voyant_missing_values_ratio{source}
voyant_duplicate_records_total{source}

# Integration metrics
voyant_somabrain_latency_seconds{operation}
voyant_somabrain_errors_total{operation}
voyant_tool_invocation_latency_seconds
voyant_capsule_violations_total{constraint}

# Resource metrics
voyant_memory_usage_bytes
voyant_cpu_usage_ratio
voyant_duckdb_query_duration_seconds
```

---

## 7. Constraints

### 7.1 Technical Constraints

1. THE system SHALL use only open-source components with permissive licenses (MIT, Apache 2.0, BSD).
2. THE system SHALL be deployable on Kubernetes 1.27 or later alongside SomaStack components.
3. THE system SHALL support Python 3.11 or later for the core application.
4. THE system SHALL NOT implement its own memory layer; all memory operations go through SomaBrain.
5. THE system SHALL NOT implement its own authentication; all auth is delegated to SomaAgentHub.
6. THE system SHALL NOT bypass OPA policy checks under any circumstances.

### 7.2 Integration Constraints

1. THE system SHALL register as a Tool in SomaAgentHub before accepting invocations.
2. THE system SHALL respect Capsule constraints for all operations.
3. THE system SHALL use SomaStack's shared Kafka instance for event publishing.
4. THE system SHALL use SomaStack's shared MinIO instance for artifact storage.
5. THE system SHALL propagate trace context from SomaAgentHub for distributed tracing.

### 7.3 Business Constraints

1. THE system SHALL not require paid third-party services for core functionality.
2. THE system SHALL operate within a single cloud region for data residency compliance.

---

## 8. Assumptions and Dependencies

### 8.1 Assumptions

1. SomaAgentHub is deployed and operational before VOYANT starts.
2. SomaBrain is deployed and accessible for memory operations.
3. OPA policy server is deployed and accessible for policy evaluation.
4. Kafka is deployed for event publishing.
5. MinIO is deployed for artifact storage.
6. Network connectivity exists between VOYANT and configured data sources.

### 8.2 Dependencies

| Component | Version | Purpose | SomaStack Shared |
|-----------|---------|---------|------------------|
| SomaAgentHub | 4.0.0+ | Tool registration and invocation | Yes |
| SomaBrain | 1.0+ | Memory persistence | Yes |
| OPA | 0.50+ | Policy enforcement | Yes |
| Kafka | 3.0+ | Event publishing | Yes |
| MinIO | Latest | Artifact storage | Yes |
| DuckDB | 0.9+ | Analytical database | No (VOYANT-specific) |
| PostgreSQL | 15+ | Job metadata storage | Yes (shared) |
| Redis | 7+ | Caching | Yes (shared) |


---

## 9. Acceptance Criteria Summary

| Requirement | Criteria Count | Priority | SomaStack Integration |
|-------------|---------------|----------|----------------------|
| Tool Registration | 7 | Critical | SomaAgentHub |
| Capsule Compliance | 8 | Critical | SomaAgentHub |
| SomaBrain Integration | 8 | Critical | SomaBrain |
| OPA Policy | 7 | Critical | OPA |
| Preset Workflows | 8 | Critical | – |
| Data Discovery | 8 | High | – |
| Data Ingestion | 8 | Critical | – |
| Data Processing | 8 | Critical | – |
| Statistical Engine | 10 | Critical | – |
| Visualization | 8 | High | – |
| Reports | 8 | High | MinIO |
| Orchestration | 8 | Critical | Kafka |
| Observability | 8 | High | OTEL, Kafka |
| Security | 8 | Critical | OPA, SomaAgentHub |
| Performance | 6 | High | – |
| Error Handling | 6 | High | – |
| Deployment | 8 | Medium | Kubernetes |

**Total Acceptance Criteria: 130**

---

## 10. Traceability Matrix

### 10.1 SomaStack Integration Traceability

| VOYANT Requirement | SomaAgentHub SRS Reference | SomaBrain Reference |
|--------------------|---------------------------|---------------------|
| Req 1 (Tool Registration) | FR4-AG-04 (Extended Tool Descriptor) | – |
| Req 2 (Capsule Compliance) | Section 12 (Capsule Concept) | – |
| Req 3 (SomaBrain Integration) | FR4-MEM-01, FR4-MEM-02 | Section 3.1 (Memory Service) |
| Req 4 (OPA Policy) | FR4-GOV-01, FR4-GOV-02 | Section 3.3 (Constitution) |
| Req 12 (Job Orchestration) | FR4-WF-01 to FR4-WF-05 | – |
| Req 13 (Observability) | FR4-OBS-01, FR4-OBS-02 | Section 3.5 (Observability) |
| Req 14 (Security) | NFR5-SEC-01 to NFR5-SEC-03 | Section 3.3 (Constitution) |

### 10.2 Capsule Constraint Mapping

| Capsule Field | VOYANT Enforcement |
|---------------|-------------------|
| `toolWhitelist` | Req 2.2 - Verify sub-tools before execution |
| `networkEgress` | Req 2.3, Req 6.8 - Restrict outbound connections |
| `maxRuntimeSeconds` | Req 2.4, Req 12.5 - Enforce timeout |
| `memoryLimitMiB` | Req 2.5, Req 15.6 - Enforce memory limit |
| `cpuLimitMillicores` | Req 2.6 - Throttle CPU usage |
| `opaPolicy` | Req 4.7 - Load and evaluate specific policy |
| `personaId` | Req 3.5 - Propagate to SomaBrain |

---

## 11. Document Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Owner | | | |
| Technical Lead | | | |
| QA Lead | | | |
| Security Lead | | | |
| SomaStack Architect | | | |

---

## 12. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-08 | Kiro | Initial draft (standalone UDB) |
| 2.0 | 2025-12-08 | Kiro | Complete rewrite for SomaStack integration |

---

## Appendix A: Example Capsule for VOYANT

```yaml
apiVersion: soma/v1
kind: Capsule
metadata:
  name: voyant-standard-analysis
  version: "1.0"
  createdAt: "2025-12-08T00:00:00Z"
spec:
  purpose: "Standard data analysis with VOYANT tool"
  personaId: "analyst"
  toolWhitelist:
    - name: "voyant"
      version: ">=2.0"
    - name: "http_client"
      version: ">=1.0"
  imageFlavor: "python:3.12-slim"
  networkEgress:
    - "*.amazonaws.com"
    - "api.openai.com"
  rootPermissions: false
  maxRuntimeSeconds: 300
  memoryLimitMiB: 2048
  cpuLimitMillicores: 1000
  security:
    opaPolicy: "policies/voyant_standard.rego"
  audit:
    logLevel: "info"
    retainDays: 30
```

---

## Appendix B: Example GraphWorkflow with VOYANT

```json
{
  "id": "sales-forecast-workflow",
  "name": "Sales Forecast Analysis",
  "version": 1,
  "nodes": [
    {
      "id": "discover",
      "type": "tool",
      "toolId": "voyant",
      "parameters": {
        "action": "discover",
        "hint": "postgres://sales_db"
      }
    },
    {
      "id": "analyze",
      "type": "tool",
      "toolId": "voyant",
      "parameters": {
        "action": "analyze",
        "preset": "PREDICT_SALES",
        "params": {
          "horizon": 90,
          "confidence": 0.95
        }
      },
      "capsule": "voyant-standard-analysis"
    },
    {
      "id": "review",
      "type": "human_interrupt",
      "interrupt": true,
      "risk": "MEDIUM"
    }
  ],
  "edges": [
    { "source": "discover", "target": "analyze" },
    { "source": "analyze", "target": "review", "condition": "state.dqs < 0.8" }
  ]
}
```

---

*End of VOYANT Software Requirements Specification v2.0*
