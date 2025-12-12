# VOYANT - CANONICAL ROADMAP
## The Data Clairvoyant: Next-Generation Autonomous Data Intelligence Black Box

**Version**: 2.0  
**Last Updated**: 2024-10-30  
**Status**: 🎯 Architecture Defined → 🚀 Ready for Implementation

---

## EXECUTIVE SUMMARY

**VOYANT** (French: "seer, clairvoyant") is an autonomous data intelligence system that gives AI agents supernatural data powers. It's a completely isolated black box that:

- **Consumes ANY data source** (URL, PDF, XLS, API, database, etc.)
- **Auto-discovers and connects** to data sources without human intervention
- **Applies standard statistical processes** (benchmarks, regression, forecasting, etc.)
- **Returns complete analyzed results** (data + insights + charts + predictions)

**Integration**: Voyant operates as an MCP tool in the SomaAgentHub ecosystem, using shared infrastructure (Postgres, Redis, Kafka, Temporal) but maintaining complete functional isolation.

---

## THE VISION

### What Voyant Is

**A Data Clairvoyant for AI Agents**

```
WITHOUT VOYANT:
User: "Benchmark my brand vs Nike"
Agent: "I need a developer to write code for this..."
Result: Takes days, manual work, error-prone

WITH VOYANT:
User: "Benchmark my brand vs Nike"
Agent: "Let me ask Voyant"
Voyant: [Automatically discovers 23 data sources, connects, ingests 2.3M data points, 
         analyzes market position, creates 8 charts, generates insights]
Result: Complete benchmark report in 3 minutes
```

### Core Capabilities

1. **AUTONOMOUS**: Discovers APIs, generates connectors, handles auth automatically
2. **UNIVERSAL**: Consumes any format (PDF, XLS, CSV, JSON, API, database, web, etc.)
3. **INTELLIGENT**: Auto-selects statistical methods, charts, and insights
4. **PRESET-DRIVEN**: 40+ standard workflows (benchmarks, forecasting, quality fixes)
5. **CUSTOM-CAPABLE**: Build custom workflows when presets don't fit
6. **ISOLATED**: Zero dependency on agent logic, pure data intelligence

---

## ARCHITECTURE OVERVIEW

### System Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    SOMAAGENT HUB                             │
│  Gateway → Orchestrator (Temporal) → Agent → MCP Handler    │
└────────────────────────────────┬─────────────────────────────┘
                                 │ MCP over SSE
┌────────────────────────────────▼─────────────────────────────┐
│                      VOYANT BLACK BOX                         │
│                                                              │
│  API LAYER (FastAPI + FastMCP)                              │
│    ↓                                                         │
│  ORCHESTRATION (Temporal/Airflow)                           │
│    ↓                                                         │
│  INGESTION (Airbyte + Unstructured + Scrapy)                │
│    ↓                                                         │
│  PROCESSING (Spark + Pandas + DuckDB + Great Expectations)  │
│    ↓                                                         │
│  STATISTICS (R + SciPy + Scikit-learn + XGBoost + Prophet)  │
│    ↓                                                         │
│  VISUALIZATION (Plotly + Superset)                          │
│    ↓                                                         │
│  STORAGE (DuckDB + Postgres + MinIO + Parquet)              │
└──────────────────────────────────────────────────────────────┘
```

---

## COMPLETE FEATURE SET

### TIER 1: Universal Data Ingestion

#### 1.1 Data Source Connectors
- **Airbyte** (300+ connectors): APIs, databases, cloud storage, SaaS
- **Unstructured.io**: PDF, Word, PowerPoint, HTML, images (OCR)
- **Scrapy**: Web scraping for any website
- **Custom connectors**: Auto-generated for unknown APIs

#### 1.2 Format Support
- **Structured**: CSV, Excel, JSON, XML, Parquet, Avro, ORC
- **Documents**: PDF, Word, PowerPoint, Text
- **Databases**: Postgres, MySQL, MongoDB, Cassandra, etc.
- **APIs**: REST, GraphQL, SOAP, gRPC
- **Streaming**: Kafka, Kinesis, Pub/Sub
- **Cloud**: S3, GCS, Azure Blob
- **Social**: Twitter, Reddit, LinkedIn APIs

#### 1.3 Auto-Detection
- File format detection (magic bytes)
- Encoding detection (UTF-8, Latin-1, etc.)
- Delimiter detection (comma, tab, pipe)
- Schema inference
- Data type detection
- API pattern recognition (OpenAPI/Swagger)
- Authentication method detection (OAuth, API key, Basic)

#### 1.4 Auto-Connection
- Connector generation (Airbyte configs or custom Python)
- Authentication handler generation
- Rate limiter setup
- Retry logic implementation
- Error handling
- Credential management (secure storage in Redis/Vault)

---

### TIER 2: Data Processing & Quality

#### 2.1 Data Quality Engine (Great Expectations)
- **Completeness**: Missing value detection and scoring
- **Consistency**: Duplicate detection, format validation
- **Accuracy**: Cross-source verification
- **Timeliness**: Freshness scoring
- **Validity**: Range validation, format checks
- **Overall DQS**: Data Quality Score (target ≥ 90%)

#### 2.2 Data Cleaning
- **Outlier Detection**: IQR method, Z-score, Modified Z-score
- **Outlier Treatment**: Winsorization, transformation, removal, flagging
- **Missing Data Imputation**: Mean/median, regression, K-NN, MICE
- **Deduplication**: Fuzzy matching, entity resolution
- **Standardization**: Format normalization, unit conversion

#### 2.3 Data Transformation (Spark + Pandas/Polars)
- **Normalization**: Min-max, Z-score, robust scaling
- **Transformation**: Log, Box-Cox, power transforms
- **Encoding**: One-hot, label, target encoding
- **Feature Engineering**: Binning, aggregation, derived features
- **Schema Mapping**: Field alignment across sources
- **Temporal Alignment**: Time period harmonization

#### 2.4 Data Integration (DuckDB)
- **Entity Resolution**: Fuzzy matching (Levenshtein distance)
- **Join Operations**: Inner, outer, left, right joins
- **Conflict Resolution**: Weighted average, most recent, majority vote
- **Data Harmonization**: Unified schema creation

---

### TIER 3: Statistical Analysis

#### 3.1 Descriptive Statistics (R + SciPy)
- **Central Tendency**: Mean, median, mode, trimmed mean
- **Dispersion**: Variance, std dev, range, IQR, CV
- **Shape**: Skewness, kurtosis
- **Percentiles**: P5, P10, P25, P50, P75, P90, P95
- **Correlation**: Pearson, Spearman, Kendall's Tau
- **Distribution Fitting**: Normal, log-normal, exponential, gamma, etc.

#### 3.2 Hypothesis Testing (R + StatsModels)
- **t-tests**: One-sample, two-sample, paired
- **ANOVA**: One-way, two-way, repeated measures
- **Non-parametric**: Mann-Whitney U, Kruskal-Wallis, Wilcoxon
- **Chi-square**: Independence, goodness-of-fit
- **Proportion tests**: Z-test for proportions

#### 3.3 Regression Analysis (R + Scikit-learn)
- **Linear Regression**: Simple, multiple, polynomial
- **Regularization**: Ridge, Lasso, Elastic Net
- **Logistic Regression**: Binary, multinomial
- **Non-linear**: Spline, GAM
- **Diagnostics**: R², adjusted R², VIF, residual plots

#### 3.4 Time Series Analysis (R forecast + Prophet)
- **Decomposition**: Trend, seasonal, residual (STL)
- **Stationarity**: ADF test, KPSS test
- **Forecasting**: ARIMA, ETS, Prophet, Holt-Winters
- **Anomaly Detection**: STL + residual analysis
- **Seasonality**: ACF, PACF, seasonal strength

#### 3.5 Machine Learning (Scikit-learn + XGBoost)
- **Classification**: Random Forest, XGBoost, LightGBM, CatBoost
- **Regression**: Gradient Boosting, Random Forest
- **Clustering**: K-means, DBSCAN, Hierarchical, GMM
- **Dimensionality Reduction**: PCA, t-SNE, UMAP
- **Anomaly Detection**: Isolation Forest, LOF, Autoencoder
- **Feature Importance**: SHAP, permutation importance

#### 3.6 NLP & Sentiment (spaCy + Transformers)
- **Sentiment Analysis**: VADER, BERT-based models
- **Topic Modeling**: LDA, NMF
- **Entity Recognition**: Named entities, custom entities
- **Text Classification**: Multi-class, multi-label
- **Embeddings**: Word2Vec, BERT, sentence transformers

---

### TIER 4: Preset Workflows

#### 4.1 Analytical Presets (15 Standard)
1. **BENCHMARK_MY_BRAND**: Competitive brand analysis
2. **PREDICT_SALES**: Sales forecasting with confidence intervals
3. **FORECAST_DEMAND**: Demand prediction with seasonality
4. **DETECT_ANOMALIES**: Outlier and anomaly detection
5. **SEGMENT_CUSTOMERS**: Customer clustering and profiling
6. **ANALYZE_SENTIMENT**: Social media and review sentiment
7. **IDENTIFY_TRENDS**: Trend detection and analysis
8. **PREDICT_CHURN**: Customer churn prediction
9. **OPTIMIZE_PRICING**: Price elasticity and optimization
10. **MEASURE_IMPACT**: Causal impact analysis
11. **LINEAR_REGRESSION_ANALYSIS**: Full regression workflow
12. **CORRELATION_ANALYSIS**: Correlation matrix and drivers
13. **MARKET_SHARE_ANALYSIS**: Market share calculation and trends
14. **COMPETITIVE_ANALYSIS**: Competitive positioning
15. **PRICE_ELASTICITY**: Price sensitivity analysis

#### 4.2 Operational Presets (10 Standard)
16. **FIX_DATA_QUALITY**: Auto-clean and validate data
17. **MERGE_DATASETS**: Join multiple datasets intelligently
18. **ENRICH_DATA**: Add external data sources
19. **STANDARDIZE_FORMATS**: Convert to unified schema
20. **VALIDATE_COMPLIANCE**: GDPR, HIPAA, SOX checks
21. **DEDUPLICATE_RECORDS**: Fuzzy matching and merging
22. **TRANSFORM_SCHEMA**: Migrate to new schema
23. **MIGRATE_DATA**: Move data between systems
24. **MASK_SENSITIVE_DATA**: PII/PHI masking
25. **GENERATE_SYNTHETIC_DATA**: Privacy-preserving data generation

#### 4.3 Discovery Presets (10 Standard)
26. **DISCOVER_APIS**: Find and catalog APIs
27. **MAP_DATA_SOURCES**: Inventory all data sources
28. **CATALOG_DATABASES**: Schema discovery
29. **INDEX_FILES**: File system indexing
30. **SCAN_ENDPOINTS**: API endpoint discovery
31. **DETECT_SCHEMAS**: Schema inference
32. **FIND_RELATIONSHIPS**: Foreign key detection
33. **BUILD_LINEAGE**: Data lineage mapping
34. **TRACE_DEPENDENCIES**: Dependency graph
35. **AUDIT_ACCESS**: Access pattern analysis

#### 4.4 Advanced Presets (5 Standard)
36. **CAUSAL_INFERENCE**: Causal effect estimation
37. **SURVIVAL_ANALYSIS**: Time-to-event analysis
38. **NETWORK_ANALYSIS**: Graph analytics
39. **RECOMMENDATION_ENGINE**: Collaborative filtering
40. **AB_TEST_ANALYSIS**: Experiment analysis

#### 4.5 Custom Workflow Builder
- Drag-and-drop workflow designer
- Statistical process library (100+ operations)
- Custom Python/R code injection
- Conditional logic and loops
- Error handling and retries
- Workflow versioning and templates

---

### TIER 5: Visualization & Reporting

#### 5.1 Auto-Chart Selection (Plotly)
- **Bar Chart**: Categorical comparisons
- **Line Chart**: Time series trends
- **Scatter Plot**: Correlations
- **Histogram**: Distributions
- **Box Plot**: Distributions with outliers
- **Heatmap**: Correlation matrices
- **Radar Chart**: Multi-dimensional comparisons
- **Pie Chart**: Proportions
- **Waterfall Chart**: Cumulative effects
- **Sankey Diagram**: Flow analysis

#### 5.2 Interactive Dashboards (Superset)
- SQL editor for ad-hoc queries
- Chart builder with 40+ chart types
- Dashboard creator with drag-and-drop
- Filters and drill-down
- Role-based access control
- Embedding support

#### 5.3 Report Generation
- **HTML Reports**: Self-contained with embedded charts
- **PDF Reports**: Executive summaries
- **Excel Reports**: Data + charts
- **Markdown Reports**: Technical documentation
- **Jupyter Notebooks**: Reproducible analysis

---

### TIER 6: Intelligence & Automation

#### 6.1 Smart Defaults Engine
- Auto-select statistical tests based on data type
- Auto-choose transformations based on distribution
- Auto-determine chart types based on variables
- Auto-calculate relevant metrics
- Auto-train appropriate models
- Auto-set thresholds based on data

#### 6.2 Recommendation Engine
- Data quality improvement recommendations
- Analysis method recommendations
- Visualization recommendations
- Action recommendations based on insights
- Risk warnings and alerts

#### 6.3 Self-Healing System
- Auto-retry with exponential backoff
- Token refresh for expired credentials
- Fallback to alternative sources
- Web scraping when API fails
- Cached data when source unavailable
- Error recovery and continuation

---

### TIER 7: Orchestration & Execution

#### 7.1 Workflow Engine (Temporal + Airflow)
- DAG-based workflow execution
- Parallel task execution
- Conditional branching
- Error handling and retries
- Checkpointing and resume
- Long-running workflow support

#### 7.2 Resource Management
- Memory management (Spark memory pools)
- CPU allocation (worker pools)
- Disk I/O optimization (caching)
- Network bandwidth management
- Concurrent job limits
- Priority queues

---

### TIER 8: Observability & Control

#### 8.1 Progress Tracking (SSE)
- Real-time progress updates
- Stage completion status
- ETA calculations
- Resource usage metrics
- Current operation details

#### 8.2 Audit Trail
- Data sources accessed
- Transformations applied
- Statistical tests performed
- Models trained
- Results generated
- Errors encountered
- Execution time per stage

#### 8.3 Metrics (Prometheus)
- Job success/failure rates
- Execution duration per preset
- Data quality scores
- Resource utilization
- API call counts
- Error rates

---

## TECHNOLOGY STACK (100% Open Source)

### Core Components

| Layer | Technology | Purpose | License |
|-------|-----------|---------|---------|
| **API** | FastAPI + FastMCP | MCP server, REST API | MIT |
| **Orchestration** | Temporal + Airflow | Workflow engine | MIT + Apache 2.0 |
| **Ingestion** | Airbyte + Unstructured + Scrapy | Universal data ingestion | MIT + Apache 2.0 |
| **Processing** | Spark + Pandas/Polars + DuckDB | Data transformation | Apache 2.0 + MIT |
| **Quality** | Great Expectations | Data validation | Apache 2.0 |
| **Statistics** | R + Rserve + SciPy + StatsModels | Statistical analysis | GPL + BSD |
| **ML** | Scikit-learn + XGBoost + LightGBM | Machine learning | BSD + Apache 2.0 |
| **Forecasting** | Prophet | Time series forecasting | MIT |
| **NLP** | spaCy + Transformers | Text analysis | MIT + Apache 2.0 |
| **Visualization** | Plotly + Superset | Charts and dashboards | MIT + Apache 2.0 |
| **Storage** | DuckDB + Postgres + MinIO + Parquet | Data storage | MIT + PostgreSQL + AGPL |

### Why R is Critical

**R provides the most comprehensive statistical library in existence:**
- 19,000+ packages on CRAN
- Every statistical method exists
- Industry standard for statistics
- Better statistical graphics
- More rigorous implementations
- Academic/research standard

**Integration**: Run R via Rserve, call from Python via rpy2

**Key R Packages**:
- `stats`, `MASS`, `car` (statistics)
- `forecast`, `prophet`, `tseries` (time series)
- `caret`, `randomForest`, `xgboost` (ML)
- `ggplot2`, `plotly` (visualization)

---

## STATISTICAL PROCESSES (Standard Workflows)

### Example: BENCHMARK_MY_BRAND

**Complete Statistical Pipeline:**

#### Phase 1: Data Collection (6 processes)
1. Data acquisition from multiple sources
2. Data quality assessment (DQS calculation)
3. Outlier detection and treatment
4. Missing data imputation
5. Normalization and standardization
6. Data integration and harmonization

#### Phase 2: Descriptive Statistics (8 processes)
1. Univariate analysis (mean, median, std, etc.)
2. Bivariate analysis (correlations)
3. Distribution analysis (normality tests, fitting)
4. Time series decomposition (trend, seasonal, residual)
5. Market share calculation (absolute, relative, HHI)
6. Price analysis (positioning, elasticity)
7. Sentiment analysis (NLP + scoring)
8. Brand health metrics (NPS, CSAT, awareness)

#### Phase 3: Comparative Analysis (6 processes)
1. Hypothesis testing (t-tests, ANOVA)
2. Benchmarking metrics (RPI, gap analysis)
3. Positioning analysis (MDS, PCA)
4. Competitive intensity (concentration ratios)
5. Performance gap analysis (importance-performance matrix)
6. Share of wallet analysis

#### Phase 4: Predictive Analytics (5 processes)
1. Trend forecasting (ARIMA, Prophet)
2. Regression analysis (drivers identification)
3. Scenario analysis (Monte Carlo simulation)
4. Market simulation (agent-based models)
5. Risk assessment (VaR, stress testing)

#### Phase 5: Insight Generation (4 processes)
1. Driver analysis (relative importance)
2. Segmentation analysis (clustering)
3. Anomaly detection (outliers, changes)
4. Recommendation engine (prioritized actions)

**Total: 29 standard statistical processes per benchmark**

---

## IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Weeks 1-4)

#### Week 1-2: Core Infrastructure
- [ ] FastAPI + FastMCP server setup
- [ ] Temporal workflow integration
- [ ] DuckDB setup for analytics
- [ ] Postgres metadata schema
- [ ] MinIO artifact storage
- [ ] Basic MCP tools (execute_preset, status, result)

#### Week 3-4: Basic Ingestion
- [ ] Airbyte integration (5 connectors: CSV, Postgres, REST API, S3, MySQL)
- [ ] File upload support (CSV, Excel, JSON)
- [ ] Schema detection
- [ ] Data quality checks (Great Expectations)
- [ ] Basic data cleaning

**Deliverable**: Can ingest data from 5 sources, store in DuckDB, return quality report

---

### Phase 2: Statistical Engine (Weeks 5-8)

#### Week 5-6: R Integration
- [ ] Rserve setup
- [ ] Python-R bridge (rpy2)
- [ ] Basic statistical functions (mean, median, correlation)
- [ ] Hypothesis testing (t-test, ANOVA)
- [ ] Distribution fitting

#### Week 7-8: First Preset
- [ ] BENCHMARK_MY_BRAND preset implementation
- [ ] Market share calculation
- [ ] Price analysis
- [ ] Sentiment analysis (VADER)
- [ ] Basic charts (Plotly)
- [ ] HTML report generation

**Deliverable**: Working BENCHMARK_MY_BRAND preset end-to-end

---

### Phase 3: ML & Forecasting (Weeks 9-12)

#### Week 9-10: Machine Learning
- [ ] Scikit-learn integration
- [ ] XGBoost integration
- [ ] Clustering (K-means, DBSCAN)
- [ ] Classification (Random Forest)
- [ ] Feature importance

#### Week 11-12: Time Series
- [ ] Prophet integration
- [ ] ARIMA implementation (R forecast package)
- [ ] Trend decomposition
- [ ] Anomaly detection
- [ ] PREDICT_SALES preset
- [ ] FORECAST_DEMAND preset

**Deliverable**: 3 working presets (BENCHMARK, PREDICT_SALES, FORECAST_DEMAND)

---

### Phase 4: Auto-Discovery (Weeks 13-16)

#### Week 13-14: API Discovery
- [ ] Web search for APIs
- [ ] OpenAPI/Swagger parsing
- [ ] Auth method detection
- [ ] Connector generation
- [ ] API catalog

#### Week 15-16: Auto-Connection
- [ ] Credential management
- [ ] OAuth flow handling
- [ ] Rate limiting
- [ ] Retry logic
- [ ] Fallback to web scraping

**Deliverable**: Auto-discovers and connects to unknown APIs

---

### Phase 5: Advanced Features (Weeks 17-20)

#### Week 17-18: More Presets
- [ ] FIX_DATA_QUALITY
- [ ] SEGMENT_CUSTOMERS
- [ ] DETECT_ANOMALIES
- [ ] ANALYZE_SENTIMENT (advanced)
- [ ] LINEAR_REGRESSION_ANALYSIS

#### Week 19-20: Dashboards
- [ ] Superset integration
- [ ] Interactive dashboards
- [ ] Custom chart builder
- [ ] Report templates

**Deliverable**: 8 working presets + interactive dashboards

---

### Phase 6: Production Hardening (Weeks 21-24)

#### Week 21-22: Performance
- [ ] Spark integration for big data
- [ ] Parallel execution
- [ ] Caching layer
- [ ] Query optimization

#### Week 23-24: Reliability
- [ ] Comprehensive error handling
- [ ] Circuit breakers
- [ ] Health checks
- [ ] Monitoring and alerting
- [ ] Load testing

**Deliverable**: Production-ready v1.0.0

---

## SUCCESS METRICS

### Technical KPIs
- **Ingestion Speed**: > 100K rows/second
- **Analysis Time**: < 5 minutes for standard preset (< 1M rows)
- **Accuracy**: 95%+ correct statistical method selection
- **Reliability**: 99.9% uptime, 99% job success rate
- **Concurrency**: Handle 50+ concurrent jobs

### User Experience KPIs
- **Onboarding**: < 5 minutes from install to first result
- **Autonomy**: 95%+ requests handled without intervention
- **Quality**: 90%+ users satisfied with results
- **Clarity**: < 10% requests need clarification

---

## INTEGRATION WITH SOMAAGENT HUB

### What Voyant Uses from SomaAgentHub
- ✅ Postgres (metadata storage)
- ✅ Redis (caching + credentials)
- ✅ Kafka (event bus)
- ✅ Temporal (workflow orchestration)
- ✅ MinIO (artifact storage)
- ✅ Observability stack (Prometheus, Grafana)

### What Voyant Provides
- ❌ MCP server (tool interface)
- ❌ Preset library (40+ workflows)
- ❌ Statistical engine (R + Python)
- ❌ Auto-discovery system
- ❌ Data catalog
- ❌ Visualization engine

### Communication Protocol
- **MCP over SSE** for real-time progress updates
- **Agents discover Voyant** via existing MCP handler
- **Voyant executes independently** from agent logic
- **Complete functional isolation** maintained

---

## EXAMPLE USAGE

### Agent Workflow

```python
# Agent 1 discovers available presets
presets = agent.execute_tool("voyant_list_presets")

# Agent 1 executes benchmark
result = agent.execute_tool("voyant_execute_preset", {
    "preset": "BENCHMARK_MY_BRAND",
    "params": {
        "brand": "MyBrand",
        "competitors": ["Nike", "Adidas"],
        "period": "Q4_2024"
    }
})
# Returns: {"job_id": "job_xyz123", "status": "running"}

# Agent 1 polls for completion
status = agent.execute_tool("voyant_status", {"job_id": "job_xyz123"})
# Returns: {"status": "completed", "progress": 100}

# Agent 1 retrieves result
final = agent.execute_tool("voyant_result", {"job_id": "job_xyz123"})
# Returns: Complete benchmark with insights, charts, data
```

### What Voyant Does Internally

```
1. Understands request: Need brand benchmark data
2. Discovers sources: Finds 23 relevant APIs and data sources
3. Connects: Auto-generates connectors, handles auth
4. Ingests: Pulls 2.3M data points in parallel
5. Cleans: Fixes quality issues, removes outliers
6. Analyzes: Runs 29 statistical processes
7. Visualizes: Creates 8 charts automatically
8. Generates insights: "MyBrand is #3 with 12% share, growing 15%/year"
9. Returns: Complete report with data, charts, insights, predictions
```

---

## RISKS & MITIGATIONS

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| R integration complexity | High | Medium | Use Rserve, extensive testing |
| API discovery accuracy | Medium | Medium | Fallback to manual config |
| Performance with big data | High | Medium | Spark integration, sampling |
| Statistical method selection | High | Low | Expert system + validation |
| Credential security | High | Low | Vault integration, encryption |

---

## OPEN QUESTIONS

1. **LLM for request parsing**: Use local LLM (Ollama) or rule-based?
2. **Spark deployment**: Standalone or integrate with existing cluster?
3. **R package management**: Docker image with pre-installed packages?
4. **Custom preset storage**: Database or file-based?
5. **Multi-tenancy**: How to isolate data per tenant?

---

## CONTRIBUTING

This roadmap is a living document. To propose changes:

1. Open issue with `[ROADMAP]` prefix
2. Discuss in community meetings
3. Submit PR with rationale
4. Requires 2+ maintainer approvals

---

## REFERENCES

- **Architecture**: `docs/ARCHITECTURE.md`
- **MCP Interface**: `docs/MCP_INTERFACE.md`
- **Statistical Methods**: `docs/STATISTICAL_PROCESSES.md`
- **Technology Stack**: `docs/TECHNOLOGY_STACK.md`
- **Preset Catalog**: `docs/PRESET_CATALOG.md`

---

**Last Updated**: 2024-10-30  
**Next Review**: 2024-11-15  
**Maintainers**: @somatechlat  
**Status**: 🎯 Ready for Phase 1 Implementation
