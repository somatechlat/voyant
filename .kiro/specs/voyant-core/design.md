# VOYANT Technical Design Document
## Autonomous Data Intelligence Tool for SomaStack

**Document ID:** VOYANT-TDD-002  
**Version:** 2.0  
**Date:** December 8, 2025  
**Status:** Draft for Review  
**Classification:** Technical Design  
**Compliance:** ISO/IEC/IEEE 42010:2022 (Architecture Description)

---

## 1. Overview

### 1.1 Purpose

This Technical Design Document (TDD) defines the architecture, components, interfaces, data models, and implementation approach for **VOYANT**, an autonomous data intelligence tool that operates as a first-class component within the **SomaStack** ecosystem.

### 1.2 Design Philosophy

VOYANT follows the SomaStack design principles:

1. **NO MOCKS** - All integrations use real SomaStack services
2. **NO BYPASS** - All operations go through proper channels (OPA, SomaBrain, etc.)
3. **REAL DATA** - No fake returns, no hardcoded values
4. **FAIL-CLOSED** - Security failures deny access, not permit
5. **OBSERVABLE** - Every operation is traced and metriced

### 1.3 Scope

This document covers:
- System architecture and component design
- SomaStack integration patterns
- Data models and schemas
- API specifications
- Correctness properties for validation
- Error handling strategies
- Testing approach

---

## 2. Architecture

### 2.1 System Context

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SOMASTACK DEPLOYMENT                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │ SomaAgent01 │────►│SomaAgentHub │────►│   VOYANT    │────►│ Data Sources│   │
│  │  (Runtime)  │     │(Orchestrator)│     │   (Tool)    │     │  (External) │   │
│  └─────────────┘     └──────┬──────┘     └──────┬──────┘     └─────────────┘   │
│                             │                   │                               │
│         ┌───────────────────┼───────────────────┼───────────────────┐           │
│         │                   │                   │                   │           │
│         ▼                   ▼                   ▼                   ▼           │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │     OPA     │     │  SomaBrain  │     │    Kafka    │     │    MinIO    │   │
│  │  (Policy)   │     │  (Memory)   │     │  (Events)   │     │ (Artifacts) │   │
│  └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘   │
│                                                                                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                        │
│  │ PostgreSQL  │     │    Redis    │     │   DuckDB    │                        │
│  │ (Metadata)  │     │  (Cache)    │     │ (Analytics) │                        │
│  └─────────────┘     └─────────────┘     └─────────────┘                        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```


### 2.2 Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              VOYANT INTERNAL ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         TOOL INTERFACE LAYER                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │ Tool Runner │  │   Capsule   │  │    Auth     │  │   Health    │    │   │
│  │  │  Endpoint   │  │  Validator  │  │  Validator  │  │   Probes    │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         ORCHESTRATION LAYER                             │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │    Job      │  │   Preset    │  │  Checkpoint │  │   Event     │    │   │
│  │  │  Manager    │  │  Executor   │  │   Manager   │  │  Publisher  │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         PROCESSING LAYER                                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │   Data      │  │    Data     │  │ Statistical │  │    Chart    │    │   │
│  │  │  Ingestion  │  │  Processing │  │   Engine    │  │  Generator  │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         INTEGRATION LAYER                               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │  SomaBrain  │  │     OPA     │  │   Kafka     │  │   MinIO     │    │   │
│  │  │   Client    │  │   Client    │  │   Client    │  │   Client    │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Layer Responsibilities

| Layer | Components | Responsibility |
|-------|------------|----------------|
| **Tool Interface** | Tool Runner Endpoint, Capsule Validator, Auth Validator, Health Probes | Receive invocations from SomaAgentHub, validate requests, enforce Capsule constraints |
| **Orchestration** | Job Manager, Preset Executor, Checkpoint Manager, Event Publisher | Manage job lifecycle, execute presets, checkpoint progress, publish events |
| **Processing** | Data Ingestion, Data Processing, Statistical Engine, Chart Generator | Core data intelligence capabilities |
| **Integration** | SomaBrain Client, OPA Client, Kafka Client, MinIO Client | Communicate with SomaStack services |

---

## 3. Components and Interfaces

### 3.1 Tool Interface Layer

#### 3.1.1 Tool Runner Endpoint

**Purpose:** Receive and route invocations from SomaAgentHub Tool Runner.

**Interface:**
```python
class ToolRunnerEndpoint:
    async def invoke(self, request: ToolInvocationRequest) -> ToolInvocationResponse:
        """
        Main entry point for all VOYANT operations.
        Called by SomaAgentHub Tool Runner.
        """
        pass
```

**Request Flow:**
1. Receive invocation from Tool Runner
2. Validate JWT token via Auth Validator
3. Parse and validate Capsule constraints
4. Route to appropriate action handler
5. Return response or job ID

#### 3.1.2 Capsule Validator

**Purpose:** Enforce Capsule constraints on all operations.

**Interface:**
```python
class CapsuleValidator:
    async def validate(self, capsule_id: str, operation: str) -> CapsuleContext:
        """
        Load Capsule, validate constraints, return execution context.
        Raises CapsuleViolationError if constraints cannot be met.
        """
        pass
    
    async def enforce_network_egress(self, destination: str, context: CapsuleContext) -> bool:
        """Check if destination is allowed by Capsule networkEgress."""
        pass
    
    async def enforce_tool_whitelist(self, tool_name: str, context: CapsuleContext) -> bool:
        """Check if tool is in Capsule toolWhitelist."""
        pass
```

#### 3.1.3 Auth Validator

**Purpose:** Validate JWT tokens issued by SomaAgentHub Auth Service.

**Interface:**
```python
class AuthValidator:
    async def validate_token(self, token: str) -> AuthContext:
        """
        Validate JWT against SomaAgentHub OIDC provider.
        Returns tenant_id, roles, and permissions.
        """
        pass
```

### 3.2 Orchestration Layer

#### 3.2.1 Job Manager

**Purpose:** Manage job lifecycle, state persistence, and recovery.

**Interface:**
```python
class JobManager:
    async def create_job(self, preset: str, params: dict, context: ExecutionContext) -> Job:
        """Create a new job, persist initial state."""
        pass
    
    async def get_job(self, job_id: str) -> Job:
        """Retrieve job by ID."""
        pass
    
    async def update_job_state(self, job_id: str, state: JobState, progress: float) -> None:
        """Update job state and progress."""
        pass
    
    async def resume_job(self, job_id: str, checkpoint_id: str) -> Job:
        """Resume job from checkpoint after failure."""
        pass
```

#### 3.2.2 Preset Executor

**Purpose:** Execute pre-configured analysis workflows.

**Interface:**
```python
class PresetExecutor:
    async def execute(self, preset: str, params: dict, job: Job) -> AnalysisResult:
        """
        Execute a preset workflow.
        Emits progress events, checkpoints at each stage.
        """
        pass
    
    def get_preset_catalog(self) -> list[PresetDefinition]:
        """Return catalog of available presets."""
        pass
```

#### 3.2.3 Event Publisher

**Purpose:** Publish job lifecycle events to Kafka.

**Interface:**
```python
class EventPublisher:
    async def publish_job_event(self, event: JobEvent) -> None:
        """
        Publish job state change to Kafka.
        Uses SomaStack event schema.
        """
        pass
```


### 3.3 Processing Layer

#### 3.3.1 Data Ingestion

**Purpose:** Discover, connect to, and ingest data from heterogeneous sources.

**Interface:**
```python
class DataIngestion:
    async def discover(self, hint: str, context: CapsuleContext) -> DiscoveryResult:
        """
        Analyze hint, detect source type, return connection requirements.
        Respects Capsule networkEgress restrictions.
        """
        pass
    
    async def connect(self, config: SourceConfig, context: CapsuleContext) -> Connection:
        """
        Establish connection to data source.
        Retrieves credentials from SomaAgentHub credential store.
        """
        pass
    
    async def ingest(self, connection: Connection, query: str, context: CapsuleContext) -> DataFrame:
        """
        Ingest data from source into DuckDB.
        Processes in chunks for large datasets.
        """
        pass
```

#### 3.3.2 Data Processing

**Purpose:** Clean, validate, and transform ingested data.

**Interface:**
```python
class DataProcessing:
    async def process(self, data: DataFrame, config: ProcessingConfig) -> ProcessedData:
        """
        Apply data quality checks and transformations.
        Returns processed data with DQS score.
        """
        pass
    
    def compute_dqs(self, data: DataFrame) -> DataQualityScore:
        """
        Compute Data Quality Score based on:
        - Completeness (missing values)
        - Consistency (duplicates)
        - Validity (outliers, format)
        - Timeliness (data freshness)
        """
        pass
```

#### 3.3.3 Statistical Engine

**Purpose:** Perform rigorous statistical analysis.

**Interface:**
```python
class StatisticalEngine:
    async def analyze(self, data: ProcessedData, analysis_type: str, params: dict) -> StatisticalResult:
        """
        Execute statistical analysis based on type.
        Auto-selects appropriate methods based on data characteristics.
        """
        pass
    
    def descriptive_stats(self, data: DataFrame) -> DescriptiveStats:
        """Calculate mean, median, std, percentiles, etc."""
        pass
    
    def correlation_analysis(self, data: DataFrame, method: str) -> CorrelationMatrix:
        """Compute Pearson, Spearman, or Kendall correlations."""
        pass
    
    def time_series_forecast(self, data: DataFrame, horizon: int, confidence: float) -> Forecast:
        """Generate forecasts using ARIMA, ETS, or Prophet."""
        pass
    
    def clustering(self, data: DataFrame, method: str) -> ClusterResult:
        """Perform K-means or DBSCAN clustering."""
        pass
```

#### 3.3.4 Chart Generator

**Purpose:** Generate visualizations automatically.

**Interface:**
```python
class ChartGenerator:
    async def generate(self, data: ProcessedData, result: StatisticalResult) -> list[Chart]:
        """
        Auto-select and generate appropriate charts.
        Returns interactive Plotly HTML files.
        """
        pass
    
    def select_chart_type(self, data: DataFrame, analysis_type: str) -> ChartType:
        """Determine optimal chart type based on data characteristics."""
        pass
```

### 3.4 Integration Layer

#### 3.4.1 SomaBrain Client

**Purpose:** Persist and recall analysis context via SomaBrain.

**Interface:**
```python
class SomaBrainClient:
    async def remember(self, payload: MemoryPayload, tenant_id: str) -> str:
        """
        Store analysis context in SomaBrain.
        POST /memory/remember
        """
        pass
    
    async def recall(self, query: str, tenant_id: str, limit: int = 5) -> list[MemoryRecord]:
        """
        Recall prior analyses from SomaBrain.
        POST /memory/recall
        """
        pass
    
    async def check_constitution(self, payload: dict) -> bool:
        """
        Verify payload against SomaBrain Constitution.
        Returns True if allowed, raises ConstitutionError if denied.
        """
        pass
```

**Integration Pattern:**
```
VOYANT                          SomaBrain
   │                                │
   │  POST /memory/remember         │
   │  {                             │
   │    "task": "voyant_analysis",  │
   │    "content": "...",           │
   │    "fact": "analysis",         │
   │    "metadata": {...}           │
   │  }                             │
   │ ──────────────────────────────►│
   │                                │
   │  { "ok": true, "key": "..." }  │
   │ ◄──────────────────────────────│
   │                                │
```

#### 3.4.2 OPA Client

**Purpose:** Evaluate OPA policies before operations.

**Interface:**
```python
class OPAClient:
    async def evaluate(self, policy: str, input_data: dict) -> PolicyDecision:
        """
        Evaluate OPA policy.
        POST /v1/data/{policy}
        """
        pass
    
    async def check_data_access(self, source: str, tenant_id: str) -> bool:
        """Check if tenant can access data source."""
        pass
    
    async def check_tool_execution(self, tool: str, params: dict, tenant_id: str) -> bool:
        """Check if tool execution is permitted."""
        pass
```

#### 3.4.3 Kafka Client

**Purpose:** Publish events to SomaStack event bus.

**Interface:**
```python
class KafkaClient:
    async def publish(self, topic: str, event: dict) -> None:
        """
        Publish event to Kafka topic.
        Uses SomaStack event schema.
        """
        pass
```

#### 3.4.4 MinIO Client

**Purpose:** Store and retrieve artifacts.

**Interface:**
```python
class MinIOClient:
    async def store_artifact(self, job_id: str, artifact_type: str, content: bytes) -> str:
        """
        Store artifact in MinIO.
        Returns artifact path.
        """
        pass
    
    async def get_signed_url(self, path: str, expiry_seconds: int) -> str:
        """Generate signed URL for artifact access."""
        pass
    
    async def delete_artifacts(self, job_id: str) -> None:
        """Delete all artifacts for a job (retention cleanup)."""
        pass
```

---

## 4. Data Models

### 4.1 Core Models

#### 4.1.1 Job

```python
@dataclass
class Job:
    id: str                          # UUID
    tenant_id: str                   # From SomaAgentHub context
    workflow_instance_id: str        # SomaAgentHub workflow instance
    capsule_id: str                  # Capsule reference
    preset: str                      # Preset name
    params: dict                     # Preset parameters
    state: JobState                  # PENDING, RUNNING, SUCCEEDED, FAILED, CANCELLED
    progress: float                  # 0.0 to 1.0
    stage: str                       # Current execution stage
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error: Optional[JobError]
    result: Optional[AnalysisResult]
    checkpoints: list[Checkpoint]
```

#### 4.1.2 AnalysisResult

```python
@dataclass
class AnalysisResult:
    job_id: str
    preset: str
    summary: str                     # Human-readable summary
    dqs: float                       # Data Quality Score (0.0 to 1.0)
    kpis: dict[str, KPIValue]        # Key performance indicators
    statistics: dict                 # Statistical results
    insights: list[Insight]          # Generated insights
    charts: list[ChartReference]     # References to generated charts
    artifacts: list[ArtifactReference]  # References to stored artifacts
    warnings: list[str]              # Quality or processing warnings
    methodology: str                 # Documentation of methods used
    data_sources: list[str]          # Sources used in analysis
    row_count: int                   # Total rows processed
    duration_seconds: float          # Total execution time
```

#### 4.1.3 Checkpoint

```python
@dataclass
class Checkpoint:
    id: str                          # UUID
    job_id: str
    stage: str                       # Stage name
    state_snapshot: dict             # Serialized state
    created_at: datetime
```


### 4.2 Integration Models

#### 4.2.1 ToolInvocationRequest

```python
@dataclass
class ToolInvocationRequest:
    """Request from SomaAgentHub Tool Runner"""
    action: str                      # discover, connect, analyze, status, result, query
    preset: Optional[str]            # For analyze action
    params: Optional[dict]           # Action-specific parameters
    job_id: Optional[str]            # For status/result actions
    hint: Optional[str]              # For discover action
    sql: Optional[str]               # For query action
    
    # SomaAgentHub context (from headers/JWT)
    tenant_id: str
    workflow_instance_id: str
    capsule_id: Optional[str]
    trace_context: dict              # OTEL trace context
```

#### 4.2.2 MemoryPayload

```python
@dataclass
class MemoryPayload:
    """Payload for SomaBrain memory storage"""
    task: str = "voyant_analysis"
    content: str                     # Analysis summary
    fact: str = "analysis"           # Memory type tag
    metadata: dict                   # Job metadata
    
    # Metadata includes:
    # - job_id: str
    # - preset: str
    # - data_sources: list[str]
    # - dqs: float
    # - key_findings: list[str]
    # - artifact_refs: list[str]
```

#### 4.2.3 JobEvent

```python
@dataclass
class JobEvent:
    """Event for Kafka publication"""
    event: str = "voyant.job.state.changed"
    job_id: str
    workflow_instance_id: str
    capsule_id: str
    state: str                       # running, succeeded, failed, cancelled
    progress: float
    stage: str
    timestamp: str                   # ISO8601
    tenant_id: str
    extra: dict                      # preset, rows_processed, dqs, etc.
```

### 4.3 Database Schema

#### 4.3.1 PostgreSQL Tables

```sql
-- Jobs table (VOYANT-specific, uses shared PostgreSQL)
CREATE TABLE voyant_jobs (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    workflow_instance_id UUID,
    capsule_id TEXT,
    preset TEXT NOT NULL,
    params JSONB NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED')),
    progress FLOAT DEFAULT 0.0,
    stage TEXT,
    error JSONB,
    result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    
    -- Index for tenant queries
    INDEX idx_voyant_jobs_tenant (tenant_id),
    INDEX idx_voyant_jobs_state (state),
    INDEX idx_voyant_jobs_workflow (workflow_instance_id)
);

-- Checkpoints table
CREATE TABLE voyant_checkpoints (
    id UUID PRIMARY KEY,
    job_id UUID REFERENCES voyant_jobs(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    state_snapshot JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    
    INDEX idx_voyant_checkpoints_job (job_id)
);

-- Audit log (uses SomaStack shared audit pattern)
CREATE TABLE voyant_audit_log (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT now(),
    tenant_id UUID NOT NULL,
    actor TEXT,
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    decision TEXT NOT NULL,
    details JSONB,
    
    INDEX idx_voyant_audit_timestamp (timestamp),
    INDEX idx_voyant_audit_tenant (tenant_id)
);
```

---

## 5. Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### 5.1 Tool Registration Properties

**Property 1: Tool manifest schema validity**
*For any* VOYANT tool manifest, serializing to JSON and deserializing back SHALL produce an equivalent manifest object.
**Validates: Requirements 1.2**

**Property 2: Tool invocation routing**
*For any* valid ToolInvocationRequest with action in [discover, connect, analyze, status, result, query], the Tool Runner Endpoint SHALL route to the corresponding handler without error.
**Validates: Requirements 1.3, 1.4**

### 5.2 Capsule Compliance Properties

**Property 3: Network egress enforcement**
*For any* Capsule with networkEgress restrictions and any outbound connection attempt, the connection SHALL succeed only if the destination matches an allowed pattern.
**Validates: Requirements 2.3**

**Property 4: Timeout enforcement**
*For any* Capsule with maxRuntimeSeconds and any job execution, the job SHALL terminate within maxRuntimeSeconds + 30 seconds grace period.
**Validates: Requirements 2.4**

**Property 5: Memory limit enforcement**
*For any* Capsule with memoryLimitMiB and any job execution, memory usage SHALL not exceed memoryLimitMiB (spill to disk instead).
**Validates: Requirements 2.5**

### 5.3 SomaBrain Integration Properties

**Property 6: Memory storage round-trip**
*For any* valid AnalysisResult, storing it via SomaBrain remember and recalling with a matching query SHALL return a record containing the original job_id and preset.
**Validates: Requirements 3.1, 3.2, 3.3**

**Property 7: Tenant isolation**
*For any* two distinct tenant_ids and any memory operation, recall for tenant A SHALL never return records stored by tenant B.
**Validates: Requirements 3.5**

### 5.4 OPA Policy Properties

**Property 8: Policy denial propagation**
*For any* OPA policy that returns deny for a given input, the corresponding VOYANT operation SHALL abort and return a structured error.
**Validates: Requirements 4.2**

**Property 9: Fail-closed semantics**
*For any* OPA unavailability scenario, all policy-gated operations SHALL be denied rather than permitted.
**Validates: Requirements 4.5**

### 5.5 Data Quality Properties

**Property 10: DQS range validity**
*For any* processed dataset, the computed Data Quality Score SHALL be in the range [0.0, 1.0].
**Validates: Requirements 5.7, 8.6**

**Property 11: DQS warning threshold**
*For any* analysis result with DQS < 0.7, the result SHALL contain at least one quality warning.
**Validates: Requirements 8.7**

### 5.6 Job Orchestration Properties

**Property 12: Job state machine validity**
*For any* job, state transitions SHALL follow: PENDING → RUNNING → (SUCCEEDED | FAILED | CANCELLED). No other transitions are valid.
**Validates: Requirements 12.1**

**Property 13: Checkpoint recovery**
*For any* job with at least one checkpoint, resuming from that checkpoint SHALL restore the job to the checkpointed stage.
**Validates: Requirements 12.2, 12.4**

**Property 14: Event publication consistency**
*For any* job state change, a corresponding Kafka event SHALL be published within 5 seconds.
**Validates: Requirements 5.8, 12.8**

### 5.7 Statistical Analysis Properties

**Property 15: Descriptive statistics completeness**
*For any* numeric column, descriptive_stats SHALL return all required metrics: mean, median, mode, std, variance, skewness, kurtosis, and percentiles.
**Validates: Requirements 9.1**

**Property 16: Forecast confidence interval validity**
*For any* time series forecast with confidence level C, the confidence interval SHALL contain approximately C% of actual values when backtested.
**Validates: Requirements 9.6**

### 5.8 Security Properties

**Property 17: PII masking completeness**
*For any* output containing detected PII patterns (email, SSN, phone), the patterns SHALL be masked before inclusion in results.
**Validates: Requirements 14.3**

**Property 18: Audit trail completeness**
*For any* job creation, data access, or credential usage event, an audit log entry SHALL be created with timestamp and actor.
**Validates: Requirements 14.6**
