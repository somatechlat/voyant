# VOYANT UDB - CANONICAL ROADMAP
## Autonomous Black Box Data Intelligence System

**Vision**: Voyant is an autonomous data intelligence black box. You give it a high-level request, it discovers, ingests, curates, analyzes, and returns the exact data you need—automatically.

**Status**: 🟡 Foundation Complete → 🟢 Black Box Transformation In Progress

---

## CURRENT STATE (v0.1.0-alpha)

### ✅ What We Have
- **REST API**: FastAPI service with endpoints for ingestion, analysis, status
- **Data Ingestion**: Airbyte integration with 300+ connectors
- **Analytical Engine**: DuckDB for SQL queries and transformations
- **Analysis Stack**: ydata-profiling (EDA), Evidently (quality), KPI engine, Plotly charts
- **Infrastructure**: Kubernetes manifests, Helm charts, Docker Compose
- **Observability**: Prometheus metrics, Kafka events, structured logging
- **Security**: RBAC, OIDC, PII masking, SQL guards
- **Documentation**: Architecture, operations, security, scaling guides

### ❌ What We're Missing (Black Box Requirements)
- **Natural Language Understanding**: Cannot parse "get me Q4 sales data"
- **Autonomous Discovery**: No automatic source scanning/cataloging
- **Intelligent Data Selection**: Cannot map request → relevant sources
- **Dynamic Workflow Generation**: Pre-defined flows only, no runtime orchestration
- **MCP Server Interface**: No agent-to-agent communication protocol
- **Internal Agent System**: No autonomous decision-making agents
- **Self-Contained Orchestration**: Relies on external triggers

---

## TARGET STATE (v1.0.0 - Black Box)

### 🎯 Core Capabilities

**INPUT**: Natural language or structured request
```
"Get me customer revenue analysis for Q4 2024"
"Find all product performance metrics"
"I need sales data from Salesforce and Stripe"
```

**OUTPUT**: Complete, analyzed, validated dataset ready to use
```json
{
  "dataset_id": "customer_revenue_q4_2024",
  "sources_used": ["salesforce_crm", "stripe_payments", "internal_warehouse"],
  "rows": 15420,
  "quality_score": 0.94,
  "artifacts": ["profile.html", "quality_report.json", "revenue_chart.png"],
  "insights": ["Revenue up 23% vs Q3", "Top region: North America"],
  "query_ready": true
}
```

**INTERNAL (Hidden from User)**:
1. Parse request → extract intent, entities, time ranges, metrics
2. Scan data catalog → identify relevant sources
3. Generate ingestion plan → prioritize sources, determine joins
4. Execute workflow → connect, sync, transform, validate
5. Analyze & curate → quality checks, profiling, KPI calculation
6. Return result → final dataset + artifacts + insights

---

## TRANSFORMATION PHASES

### 🔵 PHASE 1: MCP SERVER FOUNDATION (Weeks 1-2)
**Goal**: Enable agent-to-agent communication

#### Deliverables
- [ ] MCP server implementation (SSE/HTTP transport)
- [ ] 5 core MCP tools exposed:
  - `voyant_discover_connect` - Connect to data source
  - `voyant_sync` - Trigger data sync
  - `voyant_analyze` - Run analysis
  - `voyant_sql` - Execute SQL query
  - `voyant_status` - Check job status
- [ ] Tool schema definitions (JSON Schema)
- [ ] MCP client test harness
- [ ] Integration with existing REST endpoints

#### Acceptance Criteria
- Standalone MCP client can discover and call all 5 tools
- Tools return structured responses matching schemas
- Error handling with proper MCP error codes

#### Files to Create/Modify
- `udb_api/mcp_server.py` - MCP server implementation
- `udb_api/mcp_tools.py` - Tool definitions and handlers
- `tests/test_mcp_server.py` - MCP integration tests
- `docs/MCP_INTERFACE.md` - Update with implementation details

---

### 🟢 PHASE 2: DATA CATALOG & DISCOVERY (Weeks 3-4)
**Goal**: Automatic source discovery and cataloging

#### Deliverables
- [ ] Data catalog schema (DuckDB tables):
  - `catalog_sources` - All available data sources
  - `catalog_datasets` - Discovered datasets with metadata
  - `catalog_schemas` - Table schemas and column info
  - `catalog_quality` - Quality scores and freshness
- [ ] Discovery agents (continuous background scanning):
  - `FileSystemWatcher` - Monitor directories for new files
  - `S3BucketPoller` - Poll S3 buckets for new objects
  - `DatabaseSchemaScanner` - Scan database schemas
  - `APIEndpointProber` - Check API endpoints for data
- [ ] Discovery configuration system (`voyant-config.yaml`)
- [ ] Catalog update workflow (Temporal)
- [ ] Semantic search over catalog (keyword + schema matching)

#### Acceptance Criteria
- Discovery agents run continuously in background
- New data sources automatically added to catalog within 60s
- Catalog queryable via SQL and search API
- Quality scores updated on each scan

#### Files to Create
- `udb_api/catalog/` - Catalog management module
- `udb_api/discovery/` - Discovery agents
  - `filesystem_watcher.py`
  - `s3_poller.py`
  - `database_scanner.py`
  - `api_prober.py`
- `udb_api/workflows/catalog_update.py` - Temporal workflow
- `config/voyant-config.yaml` - Discovery configuration
- `tests/test_discovery_agents.py`

---

### 🟡 PHASE 3: REQUEST INTELLIGENCE (Weeks 5-6)
**Goal**: Parse natural language requests and map to data sources

#### Deliverables
- [ ] Request parser:
  - Extract intent (analysis, query, export)
  - Extract entities (customers, products, regions)
  - Extract time ranges (Q4 2024, last month)
  - Extract metrics (revenue, count, growth)
- [ ] Semantic matcher:
  - Map request terms → catalog sources
  - Score relevance of each source
  - Identify required joins
- [ ] Query planner:
  - Generate SQL from request
  - Determine aggregations and filters
  - Optimize query execution
- [ ] LLM integration (optional):
  - Use local LLM for request parsing
  - Fallback to rule-based parser

#### Acceptance Criteria
- Parse "customer revenue Q4" → {entity: customer, metric: revenue, time: Q4}
- Map request → relevant sources with confidence scores
- Generate executable SQL from natural language
- Handle ambiguous requests with clarification prompts

#### Files to Create
- `udb_api/intelligence/` - Request intelligence module
  - `request_parser.py`
  - `semantic_matcher.py`
  - `query_planner.py`
  - `llm_integration.py` (optional)
- `udb_api/intelligence/patterns.yaml` - Pattern library
- `tests/test_request_intelligence.py`

---

### 🟣 PHASE 4: AUTONOMOUS WORKFLOW ENGINE (Weeks 7-9)
**Goal**: Dynamic workflow generation and execution

#### Deliverables
- [ ] Workflow generator:
  - Create Temporal workflow from request
  - Determine activity sequence
  - Set timeouts and retry policies
- [ ] Internal agents (Temporal activities):
  - `ScopeAgent` - Understand request scope
  - `DiscoveryAgent` - Find relevant sources
  - `IngestionAgent` - Pull data from sources
  - `TransformAgent` - Clean, join, normalize
  - `AnalysisAgent` - Profile, validate, compute KPIs
  - `QualityAgent` - Check data quality
- [ ] Workflow orchestrator:
  - Execute workflows durably
  - Handle failures and retries
  - Track progress and emit events
- [ ] Result assembler:
  - Combine outputs from all agents
  - Generate final dataset
  - Create artifacts and insights

#### Acceptance Criteria
- Single request triggers complete workflow automatically
- Workflow adapts to data availability (skip missing sources)
- Failures handled gracefully with partial results
- Progress visible via status API

#### Files to Create
- `udb_api/workflows/` - Workflow definitions
  - `autonomous_ingest.py` - Main workflow
  - `activities/` - Agent activities
    - `scope_activity.py`
    - `discovery_activity.py`
    - `ingestion_activity.py`
    - `transform_activity.py`
    - `analysis_activity.py`
    - `quality_activity.py`
- `udb_api/orchestrator.py` - Workflow orchestrator
- `udb_api/result_assembler.py` - Result assembly
- `tests/test_autonomous_workflow.py`

---

### 🔴 PHASE 5: BLACK BOX INTERFACE (Weeks 10-11)
**Goal**: Single unified interface for all interactions

#### Deliverables
- [ ] Unified request endpoint:
  - `POST /request` - Single entry point
  - Accepts natural language or structured JSON
  - Returns job_id for async tracking
- [ ] Streaming response support:
  - Server-Sent Events for progress updates
  - WebSocket for real-time status
- [ ] Result retrieval:
  - `GET /result/{job_id}` - Get final result
  - `GET /result/{job_id}/stream` - Stream partial results
- [ ] MCP tool consolidation:
  - `voyant_request` - Single MCP tool for all operations
  - Backward compatibility with existing tools
- [ ] CLI tool:
  - `voyant request "get me sales data"`
  - `voyant status <job_id>`
  - `voyant result <job_id>`

#### Acceptance Criteria
- Single request triggers entire pipeline
- Progress visible in real-time
- Results available immediately when ready
- CLI tool works end-to-end

#### Files to Create
- `udb_api/request_handler.py` - Unified request handler
- `udb_api/streaming.py` - SSE/WebSocket support
- `cli/voyant.py` - CLI tool
- `tests/test_black_box_interface.py`

---

### 🟠 PHASE 6: OPTIMIZATION & HARDENING (Weeks 12-14)
**Goal**: Production-ready performance and reliability

#### Deliverables
- [ ] Performance optimization:
  - Parallel source ingestion
  - Incremental sync (only new data)
  - Query result caching
  - Artifact compression
- [ ] Reliability improvements:
  - Circuit breakers for external services
  - Graceful degradation (partial results)
  - Automatic retry with backoff
  - Dead letter queue for failed jobs
- [ ] Observability enhancements:
  - Distributed tracing (OpenTelemetry)
  - Detailed metrics per workflow stage
  - Audit log for all requests
  - Performance profiling
- [ ] Security hardening:
  - Request validation and sanitization
  - Rate limiting per tenant
  - Credential rotation
  - Encrypted artifact storage

#### Acceptance Criteria
- Handle 100 concurrent requests
- P95 latency < 5s for catalog queries
- 99.9% uptime for core services
- Zero credential leaks in logs/metrics

#### Files to Modify
- All workflow files - Add parallelization
- `udb_api/cache.py` - Result caching
- `udb_api/circuit_breaker.py` - Fault tolerance
- `udb_api/security.py` - Enhanced security

---

## ARCHITECTURE EVOLUTION

### Current Architecture (v0.1.0)
```
User → REST API → Airbyte → DuckDB → Analysis → Artifacts
```

### Target Architecture (v1.0.0)
```
User/Agent
    ↓
[MCP Server] ← Agent-to-Agent Communication
    ↓
[Request Intelligence] ← Parse & Understand
    ↓
[Data Catalog] ← Semantic Search
    ↓
[Workflow Generator] ← Dynamic Orchestration
    ↓
[Internal Agents] ← Autonomous Execution
    ├─ Discovery Agent
    ├─ Ingestion Agent
    ├─ Transform Agent
    ├─ Analysis Agent
    └─ Quality Agent
    ↓
[Result Assembler] ← Combine Outputs
    ↓
Final Dataset + Artifacts + Insights
```

---

## INTEGRATION WITH SOMAAGENT HUB

### Voyant as a Tool in the Ecosystem

**SomaAgentHub Agent Flow**:
```python
# Agent receives user request
user: "Analyze our customer churn"

# Agent decides to use Voyant
agent.execute_tool("voyant_request", {
    "query": "Get customer churn analysis with retention metrics"
})

# Voyant autonomously:
# 1. Discovers customer data in Salesforce + internal DB
# 2. Ingests both sources
# 3. Joins on customer_id
# 4. Calculates churn rate, retention cohorts
# 5. Generates quality report + charts
# 6. Returns complete analysis

# Agent receives result and continues workflow
result = voyant.get_result(job_id)
agent.respond(f"Churn rate is {result['kpis']['churn_rate']}%")
```

**Key Integration Points**:
- Voyant exposes MCP server (port 8000/mcp)
- SomaAgentHub agents discover Voyant via service registry
- Agents call Voyant tools via MCP protocol
- Voyant runs autonomously, agents just consume results
- No tight coupling - Voyant works standalone or with agents

---

## MILESTONES & TIMELINE

| Milestone | Target | Status | Deliverables |
|-----------|--------|--------|--------------|
| M0: Foundation | ✅ Complete | Done | REST API, Airbyte, DuckDB, Analysis |
| M1: MCP Server | Week 2 | 🟡 In Progress | MCP tools, agent communication |
| M2: Discovery | Week 4 | 🟢 Planned | Catalog, discovery agents |
| M3: Intelligence | Week 6 | 🟢 Planned | Request parsing, semantic matching |
| M4: Autonomy | Week 9 | 🟢 Planned | Workflow engine, internal agents |
| M5: Black Box | Week 11 | 🟢 Planned | Unified interface, CLI |
| M6: Production | Week 14 | 🟢 Planned | Optimization, hardening |
| **v1.0.0 Release** | **Week 14** | 🎯 Target | **Full Black Box System** |

---

## SUCCESS METRICS

### Technical KPIs
- **Request-to-Result Time**: < 2 minutes for simple queries (< 1M rows)
- **Discovery Latency**: New sources cataloged within 60 seconds
- **Accuracy**: 95%+ correct source selection for requests
- **Reliability**: 99.9% uptime, 99% job success rate
- **Concurrency**: Handle 100+ concurrent requests

### User Experience KPIs
- **Onboarding Time**: < 5 minutes from install to first result
- **Request Clarity**: < 10% requests need clarification
- **Result Quality**: 90%+ users satisfied with data quality
- **Autonomy**: 95%+ requests handled without manual intervention

---

## RISKS & MITIGATIONS

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LLM dependency for parsing | High | Medium | Rule-based fallback parser |
| Catalog grows too large | Medium | High | Partitioning, archival, search optimization |
| Workflow complexity explosion | High | Medium | Template library, workflow simplification |
| Source authentication failures | Medium | High | Credential validation, clear error messages |
| Performance degradation | Medium | Medium | Caching, parallelization, incremental sync |

---

## OPEN QUESTIONS

1. **LLM Integration**: Use local LLM (Ollama) or external API (OpenAI)?
2. **Catalog Storage**: Keep in DuckDB or move to dedicated search engine (Elasticsearch)?
3. **Workflow Engine**: Continue with Temporal or explore alternatives (Prefect, Dagster)?
4. **Multi-Tenancy**: How to isolate data and workflows per tenant?
5. **Pricing Model**: Open source core + paid enterprise features?

---

## CONTRIBUTING

This roadmap is a living document. To propose changes:

1. Open an issue with `[ROADMAP]` prefix
2. Discuss in community meetings (bi-weekly)
3. Submit PR with rationale and impact analysis
4. Requires 2+ maintainer approvals

---

## REFERENCES

- **Architecture**: `docs/ARCHITECTURE.md`
- **MCP Interface**: `docs/MCP_INTERFACE.md`
- **Security**: `docs/SECURITY.md`
- **Operations**: `docs/OPERATIONS.md`
- **Principles**: `docs/PRINCIPLES.md`

---

**Last Updated**: 2024-10-30
**Next Review**: 2024-11-15
**Maintainers**: @somatechlat
