# Voyant v4.0 — ML/AI Platform Deep Design Document

**Document ID:** VOYANT-ML-DESIGN-4.0.0
**Version:** 1.0.0
**Date:** 2026-09-06
**Phase:** 3 (Weeks 7–12)
**Status:** Design for Implementation
**References:** VOYANT-SRS-4.0.0 §3.3, PALANTIR-FEATURE-MAP §3

---

## Table of Contents

1. [Current Implementation](#1-current-implementation)
2. [Databricks / MLflow Comparison](#2-databricks--mlflow-comparison)
3. [Palantir AIP Comparison](#3-palantir-aip-comparison)
4. [Improvements Over Both](#4-improvements-over-both)
5. [MLflow-Compatible API Design](#5-mlflow-compatible-api-design)
6. [Agent Platform Design](#6-agent-platform-design)
7. [Model Serving Architecture](#7-model-serving-architecture)
8. [Feature Store Design](#8-feature-store-design)
9. [Modeling Objectives (Deep Specification)](#9-modeling-objectives-deep-specification)
10. [Feature Store Deep Architecture](#10-feature-store-deep-architecture)
11. [Implementation Roadmap](#11-implementation-roadmap)
12. [Data Model Reference](#12-data-model-reference)

---

## 1. Current Implementation

### 1.1 ORM Models (apps/ml_platform/models.py)

Voyant's ML Platform defines **8 Django ORM models** organized into three functional layers: experiment tracking, model registry, and agent platform.

#### 1.1.1 Experiment Tracking Layer

**Experiment** (`ml_experiment`)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `name` | CharField(255) | `db_index=True`, unique per tenant | Experiment identifier |
| `description` | TextField | blank, default="" | Free-text description |
| `tags` | JSONField | default=dict | Arbitrary key-value metadata |
| `artifact_location` | CharField(512) | blank | Storage path for artifacts (MinIO/S3) |
| `tenant_id` | UUID | inherited from TenantModel | Multi-tenant isolation |

- **Constraint:** `unique_together = [("tenant_id", "name")]` — experiment names are unique per tenant.
- **Inheritance:** `TenantModel` (soft-deletion, tenant_id), `UUIDModel` (UUIDv4 primary key, created_at, updated_at).

**Run** (`ml_run`)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `experiment` | FK → Experiment | `CASCADE`, `related_name="runs"` | Parent experiment |
| `name` | CharField(255) | blank | Optional run label |
| `status` | CharField(20) | choices: running/finished/failed/killed | Lifecycle state |
| `params` | JSONField | default=dict | Hyperparameters (e.g., `{"lr": 0.01, "epochs": 50}`) |
| `metrics` | JSONField | default=dict | Evaluation metrics (e.g., `{"accuracy": 0.95, "f1": 0.93}`) |
| `tags` | JSONField | default=dict | Arbitrary metadata |
| `started_at` | DateTimeField | `auto_now_add=True` | Run creation time |
| `ended_at` | DateTimeField | nullable | Completion time (set on terminal status) |

- **Indexes:** `(experiment_id, status)` for filtered queries; `(tenant_id, -started_at)` for chronological listing.
- **Status lifecycle:** `running` → `finished` | `failed` | `killed`

**RunArtifact** (`ml_run_artifact`)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `run` | FK → Run | `CASCADE`, `related_name="artifacts"` | Parent run |
| `name` | CharField(255) | — | Artifact filename |
| `artifact_type` | CharField(50) | choices: model/dataset/image/metric/log/other | Classification |
| `storage_path` | CharField(512) | — | MinIO/S3 object key |
| `size_bytes` | BigIntegerField | nullable | File size |

#### 1.1.2 Model Registry Layer

**RegisteredModel** (`ml_registered_model`)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `name` | CharField(255) | `db_index=True`, unique per tenant | Model name |
| `description` | TextField | blank | Model description |
| `tags` | JSONField | default=dict | Metadata (framework, task type, etc.) |

- **Constraint:** `unique_together = [("tenant_id", "name")]`

**ModelVersion** (`ml_model_version`)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `registered_model` | FK → RegisteredModel | `CASCADE`, `related_name="versions"` | Parent model |
| `version` | PositiveIntegerField | — | Auto-incremented integer version |
| `stage` | CharField(20) | choices: none/staging/production/archived | Deployment stage |
| `status` | CharField(20) | default="ready" | Version readiness |
| `run` | FK → Run | `SET_NULL`, nullable | Originating experiment run |
| `storage_path` | CharField(512) | blank | Artifact storage path |
| `metrics` | JSONField | default=dict | Evaluation metrics snapshot |
| `description` | TextField | blank | Version notes |

- **Constraint:** `unique_together = [("registered_model_id", "version")]`
- **Stage transitions** (enforced in API):
  ```
  none → staging → production ↔ archived
                ↘ archived
  archived → none (reset)
  ```

**ModelEndpoint** (`ml_model_endpoint`)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `name` | CharField(255) | `db_index=True` | Endpoint identifier |
| `model_version` | FK → ModelVersion | `SET_NULL`, nullable | Served model version |
| `status` | CharField(20) | choices: active/inactive | Operational status |
| `config` | JSONField | default=dict | `{"timeout_ms": 5000, "max_batch_size": 32}` |
| `endpoint_path` | CharField(255) | blank | Auto-generated: `/v1/ml/predict/{name}` |
| `invocation_count` | PositiveIntegerField | default=0 | Total prediction calls |
| `avg_latency_ms` | FloatField | default=0.0 | Rolling average latency |

#### 1.1.3 Agent Platform Layer

**AgentDefinition** (`ml_agent_definition`)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `name` | CharField(255) | `db_index=True`, unique per tenant | Agent identifier |
| `description` | TextField | blank | Agent purpose |
| `status` | CharField(20) | choices: draft/active/archived | Lifecycle state |
| `system_prompt` | TextField | required | LLM system prompt |
| `model_provider` | CharField(100) | default="groq" | LLM provider slug |
| `model_name` | CharField(255) | default="openai/gpt-oss-120b" | Model identifier |
| `temperature` | FloatField | default=0.1 | LLM temperature |
| `max_tokens` | IntegerField | default=4096 | Max completion tokens |
| `tools` | JSONField | default=list | MCP tool allowlist: `["voyant.sql", "voyant.search", ...]` |
| `guardrails` | JSONField | default=dict | Safety rules: `{"max_queries_per_session": 50, "blocked_tables": [], "require_approval": false}` |
| `metadata` | JSONField | default=dict | Extensible metadata |

**AgentEvaluation** (`ml_agent_evaluation`)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `agent` | FK → AgentDefinition | `CASCADE`, `related_name="evaluations"` | Parent agent |
| `name` | CharField(255) | — | Evaluation run name |
| `status` | CharField(20) | choices: pending/running/completed | Execution state |
| `test_cases` | JSONField | default=list | `[{"input": "query", "expected": "answer", "tools_used": ["voyant.sql"]}]` |
| `results` | JSONField | default=list | `[{"input": "...", "output": "...", "score": 0.95, "judge_notes": "..."}]` |
| `overall_score` | FloatField | nullable | 0.0–1.0 aggregate score |
| `judge_model` | CharField(255) | default="openai/gpt-oss-120b" | AI judge model |
| `run_count` | PositiveIntegerField | default=0 | Total test cases executed |
| `passed_count` | PositiveIntegerField | default=0 | Test cases with score ≥ 0.8 |
| `started_at` | DateTimeField | nullable | Evaluation start time |
| `completed_at` | DateTimeField | nullable | Evaluation end time |

#### 1.1.4 Entity Relationship Diagram

```
Experiment ──1:N──▶ Run ──1:N──▶ RunArtifact
                     │
                     │ FK (optional)
                     ▼
              RegisteredModel ──1:N──▶ ModelVersion ──1:1──▶ ModelEndpoint
                                          ▲
                                          │ FK (optional)
                                          │
                                   Run (origin)

AgentDefinition ──1:N──▶ AgentEvaluation
```

### 1.2 REST API (apps/ml_platform/api.py)

The ML Platform exposes **17 REST endpoints** via Django Ninja under the `/v1/ml/` prefix:

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/experiments` | read:* | List all experiments |
| `POST` | `/experiments` | write:ml | Create experiment |
| `GET` | `/experiments/{id}` | read:* | Get experiment with runs |
| `POST` | `/experiments/{id}/runs` | write:ml | Create run |
| `PUT` | `/runs/{id}/metrics` | write:ml | Update run metrics/status |
| `GET` | `/models` | read:* | List registered models |
| `POST` | `/models` | write:ml | Register model |
| `GET` | `/models/{id}` | read:* | Get model with versions |
| `POST` | `/models/{id}/versions` | write:ml | Create model version |
| `PUT` | `/model-versions/{id}/stage` | write:ml | Transition version stage |
| `GET` | `/endpoints` | read:* | List serving endpoints |
| `POST` | `/endpoints` | write:ml | Create serving endpoint |
| `GET` | `/agents` | read:ml | List agent definitions |
| `POST` | `/agents` | write:ml | Create agent definition |
| `GET` | `/agents/{id}` | read:ml | Get agent with evaluations |
| `PUT` | `/agents/{id}` | write:ml | Update agent definition |
| `DELETE` | `/agents/{id}` | write:ml | Delete agent definition |
| `POST` | `/agents/{id}/evaluations` | write:ml | Create evaluation |
| `GET` | `/agents/{id}/evaluations` | read:ml | List evaluations |
| `POST` | `/evaluations/{id}/run` | execute:ml | Execute evaluation |

**Key implementation details:**
- All endpoints are tenant-scoped via `get_tenant_id(request)`.
- Model version stage transitions enforce a state machine (see §1.1.2).
- Endpoint path is auto-generated: `/v1/ml/predict/{endpoint_name}`.
- Agent evaluation execution runs synchronously, invoking the Intent Engine per test case.

### 1.3 ML Primitives (apps/analysis/lib/ml_primitives.py)

The `MLPrimitives` class wraps scikit-learn for four core ML operations:

| Method | Algorithm | sklearn Class | Key Parameters |
|--------|-----------|---------------|----------------|
| `detect_anomalies()` | Isolation Forest | `IsolationForest` | contamination (0.0–0.5 or 'auto'), random_state=42 |
| `cluster_kmeans()` | K-Means | `KMeans` | n_clusters (default 3), n_init="auto" |
| `train_classifier()` | Random Forest | `RandomForestClassifier` | n_estimators=100, random_state=42 |
| `train_regression()` | Linear Regression | `LinearRegression` | Ordinary least squares |

**Preprocessing pipeline:**
- Missing values: `SimpleImputer(strategy="median"|"mean")`
- Scaling: `StandardScaler` (for clustering only)
- Encoding: `LabelEncoder` (for categorical targets in classification)

**Metrics returned:**
- Anomaly detection: `total_records`, `anomaly_count`, `anomaly_indices`, anomaly records
- Clustering: `clusters`, `centroids`, `silhouette_score`, labeled data
- Classification: `accuracy`, `feature_importance`, `classes`
- Regression: `r2_score`, `rmse`, `coefficients`, `intercept`, `feature_importance`

### 1.4 Anomaly Detection (apps/analysis/lib/anomaly.py + anomaly_detection.py)

Voyant implements anomaly detection in **two layers**:

#### Layer 1: Statistical Detectors (anomaly.py)

Four detection methods via a Strategy pattern:

| Method | Class | Threshold Default | Robust to Outliers | Min Data Points |
|--------|-------|-------------------|--------------------|--------------------|
| `zscore` | `ZScoreDetector` | 3.0 (std devs) | No | 3 |
| `iqr` | `IQRDetector` | 1.5 (IQR multiplier) | Yes | 4 |
| `mad` | `MADDetector` | 3.5 (modified z-score) | Yes | 3 |
| `iforest` | (in ml_primitives.py) | 0.1 (contamination) | Yes | — |

**Data classes:**
- `Anomaly(index, value, score, method, threshold)` — single anomaly point
- `AnomalyResult(anomalies, stats, method, threshold, total_points)` — detection result with `anomaly_rate` property

**API:**
- `detect_anomalies(values, method, threshold)` — single-series detection
- `detect_column_anomalies(data, columns, method, threshold)` — multi-column tabular detection

#### Layer 2: ML-Based Detection (anomaly_detection.py)

Registered as an `AnalyzerPlugin` (`anomaly_detector`) with the plugin registry:
- Uses `IsolationForest(contamination='auto', n_jobs=-1)`
- Returns: `anomaly_count`, `anomaly_percentage`, `top_anomalies` (sorted by severity), visualization spec (Plotly-ready scatter)
- Integrates with the broader analysis pipeline via `PluginCategory.STATISTICS`

### 1.5 Forecasting (apps/analysis/lib/forecasting.py + forecast_primitives.py)

Two forecasting layers:

#### Layer 1: Statistical Forecasters (forecasting.py)

| Method | Class | Approach | Confidence Intervals |
|--------|-------|----------|---------------------|
| `naive` | `NaiveForecaster` | Repeat last value | Growing with √t |
| `sma` | `MovingAverageForecaster` | Simple moving average (window=7) | Growing with √t |
| `ema` | `ExponentialSmoothingForecaster` | Exponential weighted (α=0.3) | Growing with √t |
| `linear` | `LinearTrendForecaster` | Linear regression extrapolation | Growing with √(1+t/n) |

**Data classes:**
- `ForecastPoint(period, value, lower_bound, upper_bound, date)` — single prediction
- `ForecastResult(predictions, method, periods, confidence_level, stats)` — forecast output

**Helper:** `detect_trend(values)` — returns `{"direction": "up"|"down"|"flat", "slope": float, "strength": float}`

#### Layer 2: Prophet Forecasting (forecast_primitives.py)

- `ForecastPrimitives.forecast_prophet(dates, values, periods, freq)` — wraps Facebook Prophet
- Returns: `forecast_dates`, `forecast_values`, `lower_bound`, `upper_bound`, `components`
- Handles Prophet availability gracefully (try/except import)

### 1.6 Segmentation (apps/analysis/lib/segmentation.py)

The `SegmentProfiler` provides:

| Operation | Function | Description |
|-----------|----------|-------------|
| Profiling | `profile_segments(data, segment_column)` | Per-segment statistics (mean, median, std, min, max, sum, count) |
| Comparison | `compare_segments(data, segment_column, value_a, value_b)` | Welch's t-test between two segments |
| Drift Detection | `detect_segment_drift(old_data, new_data, segment_column)` | Segment proportion changes over time |

**Security:** `max_segments=100` to prevent resource exhaustion.

### 1.7 LLM Provider Management (apps/llm_providers/)

#### 1.7.1 Models

**LLMProvider** (`llm_provider`): Provider configuration (name, slug, API base URL, API key, capabilities).

**LLMModel** (`llm_model`): Individual model (context_window, max_output_tokens, capabilities, pricing per 1M tokens).

**ActiveLLMConfig** (`llm_active_config`): Singleton per-purpose configuration mapping intent/analysis/scraper/general to a specific provider+model.

#### 1.7.2 Seven Providers, Seventeen Models

| Provider | Slug | Models | Key Capabilities |
|----------|------|--------|------------------|
| **Groq** | `groq` | 5 | Ultra-fast inference, JSON mode, function calling |
| **OpenAI** | `openai` | 3 | Vision, function calling, reasoning (o3-mini) |
| **Anthropic** | `anthropic` | 2 | Vision, function calling, 200K context |
| **MiMo (Xiaomi)** | `mimo` | 1 | Reasoning-focused, free tier |
| **Google** | `google` | 2 | 1M context, vision, reasoning |
| **Mistral** | `mistral` | 2 | JSON mode, function calling |
| **DeepSeek** | `deepseek` | 2 | Strong reasoning (R1), low cost |

**Full model catalog:**

| # | Provider | Model | Context | Vision | Reasoning | Input $/1M | Output $/1M |
|---|----------|-------|---------|--------|-----------|------------|-------------|
| 1 | Groq | openai/gpt-oss-120b | 131K | — | ✓ | Free | Free |
| 2 | Groq | openai/gpt-oss-20b | 131K | — | ✓ | Free | Free |
| 3 | Groq | llama-3.3-70b-versatile | 131K | — | — | $0.59 | $0.79 |
| 4 | Groq | llama-3.1-8b-instant | 131K | — | — | $0.05 | $0.08 |
| 5 | Groq | mixtral-8x7b-32768 | 32K | — | — | $0.24 | $0.24 |
| 6 | OpenAI | gpt-4o | 128K | ✓ | — | $2.50 | $10.00 |
| 7 | OpenAI | gpt-4o-mini | 128K | ✓ | — | $0.15 | $0.60 |
| 8 | OpenAI | o3-mini | 200K | — | ✓ | $1.10 | $4.40 |
| 9 | Anthropic | claude-sonnet-4-20250514 | 200K | ✓ | — | $3.00 | $15.00 |
| 10 | Anthropic | claude-3-5-haiku-20241022 | 200K | ✓ | — | $0.80 | $4.00 |
| 11 | MiMo | MiMo-7B-RL | 131K | — | ✓ | Free | Free |
| 12 | Google | gemini-2.5-flash | 1M | ✓ | ✓ | $0.15 | $0.60 |
| 13 | Google | gemini-2.5-pro | 1M | ✓ | ✓ | $1.25 | $10.00 |
| 14 | Mistral | mistral-large-latest | 128K | — | — | $2.00 | $6.00 |
| 15 | Mistral | mistral-small-latest | 32K | — | — | $0.10 | $0.30 |
| 16 | DeepSeek | deepseek-chat | 65K | — | — | $0.14 | $0.28 |
| 17 | DeepSeek | deepseek-reasoner | 65K | — | ✓ | $0.55 | $2.19 |

#### 1.7.3 Routing Architecture

The `ActiveLLMConfig` singleton model determines which provider+model serves each purpose:

```
┌─────────────────────────────┐
│     ActiveLLMConfig         │
├──────────┬──────────────────┤
│ Purpose  │ Provider + Model │
├──────────┼──────────────────┤
│ intent   │ Groq / GPT-OSS   │ ← Intent Engine
│ analysis │ (configurable)   │ ← Data analysis tasks
│ scraper  │ (configurable)   │ ← Scraper AI
│ general  │ (configurable)   │ ← Default fallback
└──────────┴──────────────────┘
```

When the `intent` purpose is updated via API, the Intent Engine's singleton is hot-reloaded (`engine._settings = engine._settings.model_copy(...)`).

All providers use an **OpenAI-compatible API** (`/chat/completions`), with Anthropic support for native API format also available.

### 1.8 Intent Engine (apps/intent/)

The Intent Engine translates natural language into structured MCP tool call plans.

**Intent types:** `query`, `pipeline`, `scraper`, `analyze`, `ontology`, `governance`, `search`, `unknown`

**Flow:**
1. **Classify** — keyword-based fast classification (no LLM call)
2. **Resolve schema** — load tenant's ontology (ObjectTypes, LinkTypes)
3. **Generate plan** — call LLM with system prompt containing full tool catalog (46 MCP tools)
4. **Execute plan** — route each step to the corresponding handler

**Tool catalog:** 46 MCP tools across 11 categories (data ops, source management, job management, data discovery, vector ops, presets/KPIs, governance, scraper, ontology, discovery).

**Fallback:** When LLM is unavailable, keyword-based fallback generates simple plans with confidence=0.3.

---

## 2. Databricks / MLflow Comparison

### 2.1 MLflow Experiments vs. Voyant Experiment

| Aspect | MLflow | Voyant (Current) | Gap |
|--------|--------|-------------------|-----|
| **Experiment object** | Name, artifact_location, tags | Name, description, tags, artifact_location | ✅ Met |
| **Default experiment** | Experiment ID 0 (auto-created) | No default experiment | Minor |
| **Experiment search** | Filter by name, tag, lifecycle | Basic listing by tenant | Need search/filter |
| **Experiment permissions** | Workspace-level ACLs | Tenant-level RBAC (read:ml / write:ml) | ✅ Met |
| **Nested experiments** | Not supported | Not supported | ✅ Equivalent |
| **Experiment comparison** | Built-in UI comparison | No comparison API | **Gap** |

**Design action:** Add experiment comparison endpoint:
```
GET /v1/ml/experiments/compare?ids=id1,id2,id3
→ Returns side-by-side run metrics comparison
```

### 2.2 MLflow Runs vs. Voyant Run Logging

| Aspect | MLflow | Voyant (Current) | Gap |
|--------|--------|-------------------|-----|
| **Run lifecycle** | SCHEDULED → RUNNING → FINISHED/FAILED/KILLED | running → finished/failed/killed | ✅ Equivalent (no SCHEDULED) |
| **Run params** | Key-value dict | `params` JSONField | ✅ Met |
| **Run metrics** | Key-value with step/timestamp | `metrics` JSONField (flat) | **Gap** — need step tracking |
| **Metric history** | Time-series per metric (step → value) | Single snapshot | **Gap** — need MetricHistory model |
| **Run tags** | Key-value string tags | `tags` JSONField | ✅ Met |
| **Artifact logging** | Hierarchical artifact store | `RunArtifact` model | ✅ Met |
| **Run name** | Optional, auto-generated UUID | Optional `name` field | ✅ Met |
| **Run linking** | Link to registered model version | `ModelVersion.run` FK | ✅ Met |

**Design action — Metric History Model:**

```python
class RunMetricHistory(UUIDModel):
    """Time-series metric logging for a run."""
    run = models.ForeignKey(Run, on_delete=models.CASCADE, related_name="metric_history")
    key = models.CharField(max_length=255, db_index=True)  # e.g., "accuracy"
    value = models.FloatField()
    step = models.IntegerField(default=0)  # training step
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ml_run_metric_history"
        indexes = [
            models.Index(fields=["run_id", "key", "step"]),
        ]
```

**Design action — Metric logging API:**
```
POST /v1/ml/runs/{run_id}/log-metric
Body: {"key": "loss", "value": 0.032, "step": 1500}

GET /v1/ml/runs/{run_id}/metric-history?key=loss
→ Returns: [{"step": 0, "value": 0.95, "timestamp": "..."}, {"step": 100, "value": 0.45, ...}]
```

### 2.3 MLflow Model Registry vs. Voyant RegisteredModel/ModelVersion

| Aspect | MLflow | Voyant (Current) | Gap |
|--------|--------|-------------------|-----|
| **Model registration** | `registered_models/create` | `POST /models` | ✅ Met |
| **Model versions** | Auto-incremented int | `version` PositiveIntegerField | ✅ Met |
| **Version stages** | None → Staging → Production → Archived | Same: none/staging/production/archived | ✅ Met |
| **Stage transitions** | API-driven with validation | `PUT /model-versions/{id}/stage` with state machine | ✅ Met |
| **Version description** | Markdown text | `description` TextField | ✅ Met |
| **Version tags** | Key-value tags | `tags` on RegisteredModel only | **Gap** — need version-level tags |
| **Version source** | Run ID + artifact path | `run` FK + `storage_path` | ✅ Met |
| **Aliases** | Production/Champion/Challenger aliases | No aliases | **Gap** |
| **Model search** | Filter by name, tag, stage | Basic listing | Need search/filter |
| **Model lineage** | Run → Version → Model | Same chain | ✅ Met |
| **Webhook notifications** | On stage transition | No webhooks | **Gap** |

**Design actions:**
1. Add `tags` JSONField to `ModelVersion`
2. Add `alias` CharField (e.g., "champion", "challenger") to `ModelVersion`
3. Add search/filter API: `GET /v1/ml/models?stage=production&tag.framework=sklearn`
4. Add webhook on stage transition (fire-and-forget to configured URL)

### 2.4 MLflow Model Serving vs. Voyant ModelEndpoint

| Aspect | MLflow | Voyant (Current) | Gap |
|--------|--------|-------------------|-----|
| **Endpoint creation** | Via MLflow deployment API | `POST /endpoints` | ✅ Met |
| **Endpoint config** | timeout, workers, resources | `config` JSONField | ✅ Met |
| **Invocation tracking** | Logs in MLflow server | `invocation_count` + `avg_latency_ms` | ✅ Met |
| **Prediction API** | `POST /invocations` | Path: `/v1/ml/predict/{name}` (not yet implemented) | **Gap** |
| **Input validation** | Schema per model flavor | No validation | **Gap** |
| **Auto-scaling** | Databricks-managed | Not applicable (self-hosted) | N/A |
| **A/B testing** | Traffic splitting | No traffic splitting | **Gap** |
| **Model loading** | Flavor-based (sklearn, pytorch, etc.) | No model loading | **Critical Gap** |

### 2.5 MLflow Evaluate vs. Voyant AgentEvaluation

| Aspect | MLflow Evaluate | Voyant AgentEvaluation | Gap |
|--------|----------------|------------------------|-----|
| **Scope** | Model quality metrics | **Agent quality (broad scope)** | Voyant is MORE |
| **Test data** | DataFrame with ground truth | JSON test cases with expected answers | Different approach |
| **Metrics** | accuracy, f1, BLEU, ROUGE, etc. | Score-based (0.0–1.0) per test case | **Need standard metrics** |
| **AI judge** | Not built-in | **LLM-as-judge** | ✅ Voyant advantage |
| **Custom metrics** | Plugin system | Not yet | **Gap** |
| **Evaluation logging** | Logged as run metrics | Stored in AgentEvaluation model | Different approach |
| **Visualizations** | Built-in plots | Not yet | **Gap** |

**Design action:** Add standard evaluation metrics beyond pass/fail:
```python
EVAL_METRICS = {
    "tool_accuracy": "Did the agent use the correct tools?",
    "answer_quality": "How correct/complete was the answer? (LLM judge)",
    "latency": "How fast was the response?",
    "cost": "Token cost of the execution",
    "guardrail_compliance": "Did the agent respect all guardrails?",
}
```

### 2.6 MLflow Recipes vs. Voyant Capsules

| Aspect | MLflow Recipes | Voyant Capsules | Gap |
|--------|---------------|-----------------|-----|
| **Purpose** | Predefined ML pipelines | Portable plugin architecture | Different scope |
| **Structure** | Steps (ingest, split, train, evaluate) | Signed packages with code + config | Capsules are more general |
| **Signature** | Input/output schema | Ed25519 cryptographic signing | Capsules more security-focused |
| **Flavors** | sklearn, pytorch, tensorflow | Any Python code | Capsules are framework-agnostic |
| **Portability** | Recipe YAML | Export/import as .voyant files | ✅ Equivalent |
| **Versioning** | Git-based | Registry-based | Different approach |

### 2.7 MLflow Tracking API Compatibility

MLflow's REST API uses a specific URL pattern that Voyant must mirror for drop-in compatibility:

| MLflow Endpoint | Method | Voyant Equivalent | Status |
|----------------|--------|-------------------|--------|
| `/api/2.0/mlflow/experiments/create` | POST | `POST /v1/ml/experiments` | **Needs wrapper** |
| `/api/2.0/mlflow/experiments/get` | GET | `GET /v1/ml/experiments/{id}` | **Needs wrapper** |
| `/api/2.0/mlflow/experiments/search` | POST | `GET /v1/ml/experiments` | **Needs filter** |
| `/api/2.0/mlflow/runs/create` | POST | `POST /v1/ml/experiments/{id}/runs` | **Needs wrapper** |
| `/api/2.0/mlflow/runs/get` | GET | (not yet) | **Build** |
| `/api/2.0/mlflow/runs/update` | POST | `PUT /v1/ml/runs/{id}/metrics` | **Needs wrapper** |
| `/api/2.0/mlflow/runs/search` | POST | (not yet) | **Build** |
| `/api/2.0/mlflow/runs/log-metric` | POST | (not yet) | **Build** |
| `/api/2.0/mlflow/runs/log-parameter` | POST | (merged into create) | **Needs separate** |
| `/api/2.0/mlflow/runs/log-batch` | POST | (not yet) | **Build** |
| `/api/2.0/mlflow/registered-models/create` | POST | `POST /v1/ml/models` | **Needs wrapper** |
| `/api/2.0/mlflow/registered-models/get` | GET | `GET /v1/ml/models/{id}` | **Needs wrapper** |
| `/api/2.0/mlflow/registered-models/search` | POST | `GET /v1/ml/models` | **Needs filter** |
| `/api/2.0/mlflow/model-versions/create` | POST | `POST /v1/ml/models/{id}/versions` | **Needs wrapper** |
| `/api/2.0/mlflow/model-versions/transition-stage` | POST | `PUT /v1/ml/model-versions/{id}/stage` | **Needs wrapper** |
| `/api/2.0/mlflow/model-versions/get` | GET | (not yet) | **Build** |

**Design:** Create an MLflow compatibility layer:

```python
# apps/ml_platform/mlflow_compat.py
mlflow_router = Router(tags=["mlflow-compat"])

@mlflow_router.post("/api/2.0/mlflow/experiments/create")
def mlflow_create_experiment(request, payload: dict):
    """MLflow-compatible experiment creation."""
    # Map MLflow fields to Voyant fields
    # Return MLflow-format response
    ...
```

### 2.8 Databricks AutoML vs. Voyant (No Equivalent)

Databricks AutoML provides automated model training with zero code:

| AutoML Capability | Description | Voyant Design |
|-------------------|-------------|---------------|
| Classification | Auto-train classifiers, evaluate, rank | Build as Capsule recipe |
| Regression | Auto-train regressors, evaluate, rank | Build as Capsule recipe |
| Forecasting | Auto-train Prophet/Arima models | Already have Prophet primitives |
| Feature engineering | Auto feature selection and transforms | Build as analysis primitive |
| Model selection | Try multiple algorithms, pick best | Extend MLPrimitives |
| Hyperparameter tuning | Optuna/GridSearch integration | Build as Run parameter logging |

**Design — AutoML as a Temporal Workflow:**

```
AutoMLWorkflow:
  1. AnalyzeDatasetActivity → detect task type, features, target
  2. FeatureEngineeringActivity → impute, encode, scale
  3. TrainCandidateActivity × N → train each candidate model
  4. EvaluateCandidateActivity × N → compute metrics
  5. SelectBestActivity → pick winner, register as ModelVersion
  6. LogRunActivity → create Experiment + Run with all results
```

### 2.9 Databricks Feature Store vs. Voyant

Databricks Feature Store provides centralized feature management:

| Feature Store Capability | Description | Voyant Status |
|--------------------------|-------------|---------------|
| Feature table registration | Register feature groups | Not implemented |
| Feature discovery | Browse/search features | Not implemented |
| Point-in-time lookups | Correct temporal joins | Not implemented |
| Feature lineage | Track feature derivation | Not implemented |
| Online/offline serving | Same features for training and serving | Not implemented |
| Feature sharing | Cross-workspace features | Not applicable |

**See §8 for full Feature Store design.**

### 2.10 Databricks Vector Search vs. Voyant Milvus

| Aspect | Databricks Vector Search | Voyant Milvus | Status |
|--------|-------------------------|---------------|--------|
| **Vector DB** | Proprietary on Delta | Milvus (open-source) | ✅ Advantage |
| **Index types** | HNSW, IVF_FLAT | Milvus supports all | ✅ Advantage |
| **Hybrid search** | Dense + sparse | Dense + sparse via Milvus | ✅ Met |
| **Sync mode** | Delta Sync (auto-update) | Manual index via API | **Gap** — need auto-sync |
| **Embedding model** | Configurable | DenseEmbedder + SparseEmbedder | ✅ Met |
| **RAG integration** | Databricks foundation models | MCP tool `voyant.vector.search` | ✅ Met |
| **Multi-tenancy** | Workspace-level | Tenant-level filter | ✅ Met |

---

## 3. Palantir AIP Comparison

### 3.1 Model Connectivity vs. Voyant LLM Providers

| Aspect | Palantir AIP | Voyant | Advantage |
|--------|-------------|--------|-----------|
| **Provider count** | AWS Bedrock, Azure OpenAI, GCP Vertex, Anthropic, select partners | 7 providers (Groq, OpenAI, Anthropic, MiMo, Google, Mistral, DeepSeek) | **Voyant** — more providers |
| **Model count** | ~20–30 models across providers | 17 models | Comparable |
| **Self-hosted models** | Limited (customer-managed endpoints) | Full support via OpenAI-compatible API | **Voyant** |
| **Configuration** | Admin UI with role-based access | Admin UI + REST API + MCP | **Voyant** — more interfaces |
| **Routing** | Per-organization defaults | Per-purpose routing (intent/analysis/scraper/general) | **Voyant** — more granular |
| **Hot-reload** | Settings take effect on restart | Hot-reload via `model_copy()` — no restart | **Voyant** |
| **Cost tracking** | Usage dashboards | Per-model `use_count` and `avg_latency_ms` | Comparable |
| **Testing** | Sandbox mode | `POST /llm/test` endpoint | ✅ Equivalent |

### 3.2 Palantir Agent Bricks vs. Voyant AgentDefinition

| Aspect | Palantir Agent Bricks | Voyant AgentDefinition | Gap |
|--------|----------------------|------------------------|-----|
| **Definition** | Visual builder with prompt, tools, data bindings | JSON model with all fields | **Gap** — need UI |
| **System prompt** | Templated with ontology bindings | Free-text `system_prompt` | **Gap** — need templating |
| **Tool selection** | Palantir ontology tools | MCP tool allowlist (`tools` JSONField) | ✅ Equivalent |
| **Guardrails** | Configurable in UI | `guardrails` JSONField | ✅ Equivalent |
| **Versioning** | Version-tracked | Not versioned | **Gap** |
| **Deployment** | One-click deploy to Workshop | Status-based (draft → active) | **Gap** — need deployment workflow |
| **Monitoring** | Built-in usage dashboard | `invocation_count` (on endpoints only) | **Gap** |
| **Data binding** | Ontology object types as context | No data binding (via MCP tools) | **Gap** — add ontology binding |
| **Multi-model** | Single model per agent | `model_provider` + `model_name` | ✅ Met |

**Design — Agent Definition Enhancements:**

```python
# Add to AgentDefinition:
class AgentDefinition(TenantModel, UUIDModel):
    # ... existing fields ...
    version = models.PositiveIntegerField(default=1)
    ontology_bindings = models.JSONField(default=list, blank=True,
        help_text='[{"object_type": "Customer", "filter": {"status": "active"}}]')
    prompt_template = models.TextField(blank=True,
        help_text="Template with {{variable}} placeholders")
    max_iterations = models.IntegerField(default=10,
        help_text="Maximum agent loop iterations")
    timeout_seconds = models.IntegerField(default=120,
        help_text="Per-invocation timeout")
    deployment_config = models.JSONField(default=dict, blank=True,
        help_text='{"replicas": 1, "memory_mb": 512}')
```

### 3.3 Agent Evaluation vs. Voyant AgentEvaluation

| Aspect | Palantir | Voyant | Gap |
|--------|---------|--------|-----|
| **Test case definition** | Visual test builder | JSON `test_cases` field | **Gap** — need UI |
| **Ground truth** | Expected outputs + data state | `expected` string in test case | Simplified |
| **AI judge** | Rubric-based evaluation | LLM-as-judge with `judge_model` | ✅ Voyant is ahead |
| **Scoring** | Multi-dimensional (accuracy, safety, cost) | Single `overall_score` (0.0–1.0) | **Gap** — need multi-dimensional |
| **Execution** | Async with progress | Synchronous (blocks request) | **Gap** — need async |
| **Comparison** | Compare across agent versions | Single evaluation per run | **Gap** — need version comparison |
| **Regression testing** | CI/CD integration | Manual via API | **Gap** — need CI hooks |

**Design — Enhanced Evaluation:**

```python
class AgentEvaluation(TenantModel, UUIDModel):
    # ... existing fields ...
    dimensions = models.JSONField(default=list, blank=True,
        help_text='["tool_accuracy", "answer_quality", "latency", "cost", "guardrail_compliance"]')
    dimension_scores = models.JSONField(default=dict, blank=True,
        help_text='{"tool_accuracy": 0.95, "answer_quality": 0.87, ...}')
    agent_version = models.PositiveIntegerField(default=1,
        help_text="Agent version being evaluated")
    comparison_eval_id = models.UUIDField(null=True, blank=True,
        help_text="Previous evaluation to compare against")
```

### 3.4 Code Execution vs. Voyant Sandboxed Functions

| Aspect | Palantir Code Workbooks | Voyant | Gap |
|--------|------------------------|--------|-----|
| **Python execution** | Sandboxed Python in browser | `voyant.ontology.functions.run` via FunctionRunner | ✅ Basic |
| **TypeScript** | Supported | Not supported | **Gap** |
| **Sandboxing** | Restricted environment, no filesystem | Basic sandboxing | **Gap** — need container isolation |
| **Package management** | Pre-installed packages | Not managed | **Gap** |
| **Debugging** | Interactive debugger | Not available | **Gap** |
| **Version control** | Git-backed | Not versioned | **Gap** |
| **Scheduling** | Cron triggers | Via Temporal workflows | ✅ Equivalent |

### 3.5 RAG vs. Voyant Milvus + Search

| Aspect | Palantir RAG | Voyant | Gap |
|--------|-------------|--------|-----|
| **Vector DB** | Proprietary | Milvus (open-source) | ✅ Advantage |
| **Embedding** | Managed embedding service | DenseEmbedder + SparseEmbedder | ✅ Met |
| **Chunking** | Automatic document chunking | Not yet (manual index) | **Gap** |
| **Hybrid search** | Semantic + keyword | Dense + sparse vectors | ✅ Equivalent |
| **Grounding** | Citation with source tracking | Metadata-based | **Gap** — need citation tracking |
| **Document processing** | PDF, DOCX, PPTX | PDF, OCR, transcription | ✅ Comparable |
| **MCP integration** | Not available | `voyant.vector.search`, `voyant.vector.index` | ✅ Voyant advantage |

---

## 4. Improvements Over Both

### 4.1 Agent Evaluation (Unique to Voyant)

Neither Databricks nor Palantir has an **agent-level** evaluation framework built into the ML platform:

- **MLflow Evaluate** evaluates *models* (classification metrics, BLEU, ROUGE)
- **Palantir AIP** evaluates agents within the Workshop environment only
- **Voyant** treats agents as first-class ML platform citizens with:
  - Dedicated `AgentDefinition` model (not just a prompt template)
  - `AgentEvaluation` with AI-judge scoring
  - MCP tool allowlists and guardrails as evaluable properties
  - Test cases that verify *behavior* (tool selection, answer quality) not just output

### 4.2 MCP Integration — Agents Can Manage ML Lifecycle

Voyant's MCP protocol enables agents to manage the entire ML lifecycle via tool calls:

| MCP Tool (Planned) | Operation | MLflow Equivalent |
|--------------------|-----------|-------------------|
| `voyant.ml.experiment.create` | Create experiment | `mlflow.create_experiment()` |
| `voyant.ml.run.create` | Start a run | `mlflow.start_run()` |
| `voyant.ml.run.log_metric` | Log metric | `mlflow.log_metric()` |
| `voyant.ml.run.log_param` | Log parameter | `mlflow.log_param()` |
| `voyant.ml.model.register` | Register model | `mlflow.register_model()` |
| `voyant.ml.model.transition` | Transition stage | `mlflow.transition_model_version_stage()` |
| `voyant.ml.agent.evaluate` | Run evaluation | No equivalent |
| `voyant.ml.predict` | Call endpoint | `mlflow.predict()` |

This means an AI agent running inside Voyant can:
1. Create an experiment
2. Train a model
3. Log metrics
4. Register the best model
5. Deploy it to serving
6. Evaluate its performance
7. Roll back if needed

**No other platform offers this level of agent-ML integration.**

### 4.3 Intent Engine — NL→ML Operations

Users can manage ML resources via natural language:

```
"Create an experiment called customer-churn and log accuracy of 0.95"
→ Intent Engine generates plan → voyant.ml.experiment.create + voyant.ml.run.log_metric
```

```
"Deploy model v3 of fraud-detector to production"
→ Intent Engine → voyant.ml.model.transition(stage="production")
```

Neither Databricks nor Palantir has a natural language interface to their ML platform.

### 4.4 Capsule System — Portable ML Recipes

Voyant Capsules can package ML workflows as signed, portable packages:

```
capsule-automl.voyant (Ed25519 signed)
├── manifest.json (version, author, dependencies)
├── src/
│   ├── train.py (training logic)
│   └── evaluate.py (evaluation logic)
├── config/
│   └── params.yaml (hyperparameters)
└── tests/
    └── test_train.py
```

**vs. MLflow Recipes:** Capsules are more portable (signed, importable/exportable), more secure (cryptographic verification), and framework-agnostic.

### 4.5 Seven LLM Providers

Voyant supports more LLM providers than either Databricks or Palantir:

| Platform | Providers | Models |
|----------|-----------|--------|
| **Databricks** | 3 (AWS Bedrock, Azure OpenAI, Foundation Models) | ~15–20 |
| **Palantir** | 4–5 (Bedrock, Azure, GCP, Anthropic, cohere) | ~20–30 |
| **Voyant** | **7** (Groq, OpenAI, Anthropic, MiMo, Google, Mistral, DeepSeek) | **17** |

Plus any OpenAI-compatible API endpoint can be added as a custom provider.

### 4.6 Self-Hosted Model Serving

| Aspect | Databricks | Palantir | Voyant |
|--------|-----------|----------|--------|
| **Hosting** | Databricks-managed | Palantir-managed | Self-hosted (Docker) |
| **Vendor lock-in** | High (AWS/Azure/GCP) | High (Palantir cloud) | **Zero** |
| **Cost control** | Pay-per-use | Enterprise contract | **Infrastructure cost only** |
| **Data sovereignty** | Cloud-dependent | Cloud-dependent | **Full control** |
| **Customization** | Limited | Limited | **Unlimited** |

---

## 5. MLflow-Compatible API Design

### 5.1 Endpoint Mapping

To achieve drop-in compatibility with the MLflow Python client (`mlflow.set_tracking_uri("voyant")`), Voyant must implement the MLflow REST API surface:

#### 5.1.1 Experiments API

```yaml
# Create Experiment
POST /api/2.0/mlflow/experiments/create
Request:
  name: string (required)
  artifact_location: string (optional)
  tags: array of {key: string, value: string} (optional)
Response:
  experiment_id: string

# Get Experiment
GET /api/2.0/mlflow/experiments/get?experiment_id={id}
Response:
  experiment: {
    experiment_id: string
    name: string
    artifact_location: string
    lifecycle_stage: "active"|"deleted"
    last_update_time: long (ms)
    creation_time: long (ms)
    tags: array of {key, value}
  }

# Search Experiments
POST /api/2.0/mlflow/experiments/search
Request:
  filter: string (e.g., "name = 'my-experiment'")
  max_results: int (default 1000)
  order_by: array of string
  page_token: string
Response:
  experiments: array of Experiment
  next_page_token: string
```

#### 5.1.2 Runs API

```yaml
# Create Run
POST /api/2.0/mlflow/runs/create
Request:
  experiment_id: string (required)
  run_name: string (optional)
  start_time: long (ms, optional)
  tags: array of {key, value} (optional)
Response:
  run: RunInfo

# Get Run
GET /api/2.0/mlflow/runs/get?run_uuid={id}
Response:
  run: {
    info: RunInfo
    data: {
      params: array of {key, value}
      metrics: array of {key, value, timestamp, step}
      tags: array of {key, value}
    }
  }

# Update Run
POST /api/2.0/mlflow/runs/update
Request:
  run_uuid: string
  status: "FINISHED"|"FAILED"|"KILLED"
  end_time: long (ms, optional)
  run_name: string (optional)
Response:
  run_info: RunInfo

# Search Runs
POST /api/2.0/mlflow/runs/search
Request:
  experiment_ids: array of string
  filter: string
  run_view_type: "ACTIVE_ONLY"|"DELETED_ONLY"|"ALL"
  max_results: int
  order_by: array of string
  page_token: string
Response:
  runs: array of Run
  next_page_token: string

# Log Metric
POST /api/2.0/mlflow/runs/log-metric
Request:
  run_uuid: string
  key: string
  value: float
  timestamp: long (ms, optional)
  step: long (optional)
Response: (empty)

# Log Parameter
POST /api/2.0/mlflow/runs/log-parameter
Request:
  run_uuid: string
  key: string
  value: string
Response: (empty)

# Log Batch
POST /api/2.0/mlflow/runs/log-batch
Request:
  run_uuid: string
  metrics: array of {key, value, timestamp, step}
  params: array of {key, value}
  tags: array of {key, value}
Response: (empty)

# Set Tag
POST /api/2.0/mlflow/runs/set-tag
Request:
  run_uuid: string
  key: string
  value: string
Response: (empty)
```

#### 5.1.3 Model Registry API

```yaml
# Create Registered Model
POST /api/2.0/mlflow/registered-models/create
Request:
  name: string (required)
  description: string (optional)
  tags: array of {key, value} (optional)
Response:
  registered_model: RegisteredModel

# Get Registered Model
GET /api/2.0/mlflow/registered-models/get?name={name}
Response:
  registered_model: RegisteredModel (with versions)

# Search Registered Models
POST /api/2.0/mlflow/registered-models/search
Request:
  filter: string
  max_results: int
  order_by: array of string
  page_token: string
Response:
  registered_models: array
  next_page_token: string

# Create Model Version
POST /api/2.0/mlflow/model-versions/create
Request:
  name: string (registered model name)
  source: string (run artifact path)
  run_id: string (optional)
  description: string (optional)
  tags: array of {key, value} (optional)
Response:
  model_version: ModelVersion

# Transition Model Version Stage
POST /api/2.0/mlflow/model-versions/transition-stage
Request:
  name: string
  version: string
  stage: "Staging"|"Production"|"Archived"
  archive_existing_versions: boolean
Response:
  model_version: ModelVersion

# Get Model Version
GET /api/2.0/mlflow/model-versions/get?name={name}&version={version}
Response:
  model_version: ModelVersion

# Update Model Version
POST /api/2.0/mlflow/model-versions/update
Request:
  name: string
  version: string
  description: string (optional)
  tags: array of {key, value} (optional)
Response:
  model_version: ModelVersion
```

### 5.2 Field Mapping

| MLflow Field | Voyant Model.Field | Conversion |
|-------------|-------------------|------------|
| `experiment_id` | `Experiment.id` (UUID) | String UUID |
| `run_uuid` / `run_id` | `Run.id` (UUID) | String UUID |
| `run_name` | `Run.name` | Direct |
| `lifecycle_stage` | (implied by existence) | "active" if exists |
| `status` | `Run.status` | Map: RUNNING→running, FINISHED→finished, FAILED→failed, KILLED→killed |
| `start_time` | `Run.started_at` | Epoch ms ↔ DateTime |
| `end_time` | `Run.ended_at` | Epoch ms ↔ DateTime |
| `experiment_id` on Run | `Run.experiment_id` | Direct FK |
| `registered_model.name` | `RegisteredModel.name` | Direct |
| `model_version.version` | `ModelVersion.version` | String ↔ int |
| `model_version.current_stage` | `ModelVersion.stage` | Capitalize: "None"→none, "Staging"→staging, etc. |
| `model_version.run_id` | `ModelVersion.run_id` | UUID |

### 5.3 Compatibility Matrix

| MLflow Client Feature | Compatibility | Notes |
|----------------------|---------------|-------|
| `mlflow.set_tracking_uri()` | ✅ | Point to Voyant API URL |
| `mlflow.create_experiment()` | ✅ | Maps to Voyant Experiment |
| `mlflow.start_run()` | ✅ | Creates Run in Voyant |
| `mlflow.log_param()` | ✅ | Stored in Run.params |
| `mlflow.log_metric()` | ✅ | Stored in Run.metrics (flat) or MetricHistory (time-series) |
| `mlflow.log_artifact()` | ✅ | Stored via RunArtifact + MinIO |
| `mlflow.end_run()` | ✅ | Updates Run status + ended_at |
| `mlflow.register_model()` | ✅ | Creates RegisteredModel + ModelVersion |
| `mlflow.transition_model_version_stage()` | ✅ | Stage state machine |
| `mlflow.search_experiments()` | ✅ | With filter parsing |
| `mlflow.search_runs()` | ✅ | With filter parsing |
| `mlflow.evaluate()` | ⚠️ | Partial — model metrics only, not agent eval |
| `mlflow.pyfunc.load_model()` | ❌ | Needs model loading infrastructure |
| `mlflow.sklearn.log_model()` | ❌ | Needs flavor-based serialization |
| `mlflow.deployments.create()` | ❌ | Needs serving infrastructure |
| `mlflow.client.MlflowClient()` | ✅ | Core tracking + registry APIs |

---

## 6. Agent Platform Design

### 6.1 Agent Definition Lifecycle

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  DRAFT   │────▶│  ACTIVE  │────▶│ ARCHIVED │     │  ACTIVE  │
│          │     │          │     │          │     │ (versioned)
│ - Define │     │ - Deploy │     │ - Read-  │     │
│   prompt │     │ - Serve  │     │   only   │     │
│ - Set    │     │ - Monitor│     │ - Audit  │     │
│   tools  │     │          │     │   trail  │     │
│ - Test   │     │          │     │          │     │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
      │                │
      │ evaluate       │ evaluate periodically
      ▼                ▼
┌──────────────────────────────┐
│     AgentEvaluation          │
│ - Run test cases             │
│ - AI judge scores            │
│ - Multi-dimensional metrics  │
│ - Compare versions           │
└──────────────────────────────┘
```

**Lifecycle rules:**
1. **Draft → Active:** Requires at least one evaluation with `overall_score ≥ 0.7`
2. **Active → Archived:** Allowed anytime; deactivates serving endpoints
3. **Archived → Draft:** Reset for revision
4. **Version bump:** Any change to prompt, tools, or guardrails increments `version`

### 6.2 Agent Evaluation Framework

#### 6.2.1 Test Case Schema

```json
{
  "test_cases": [
    {
      "id": "tc-001",
      "name": "SQL query generation",
      "input": "Show me the top 10 customers by revenue",
      "expected": "A SQL query joining customers and orders, grouped by customer, ordered by total revenue DESC, LIMIT 10",
      "tools_used": ["voyant.sql"],
      "guardrails_to_check": ["no_raw_sql_injection", "respect_table_permissions"],
      "context": {
        "ontology_schema": {"Customer": ["id", "name", "email"], "Order": ["id", "customer_id", "amount"]},
        "available_tables": ["customers", "orders"]
      },
      "expected_score_min": 0.8
    },
    {
      "id": "tc-002",
      "name": "Anomaly detection intent",
      "input": "Find anomalies in last month's revenue data",
      "expected": "Agent should use voyant.analyze with anomaly detection analyzer",
      "tools_used": ["voyant.analyze"],
      "expected_score_min": 0.7
    }
  ]
}
```

#### 6.2.2 AI Judge Scoring

The AI judge evaluates each test case across multiple dimensions:

```python
JUDGE_PROMPT = """You are an expert AI agent evaluator.

Agent Configuration:
- System Prompt: {system_prompt}
- Tools Available: {tools}
- Guardrails: {guardrails}

Test Case:
- Input: {input}
- Expected: {expected}
- Agent Output: {output}
- Tools Actually Used: {tools_used}

Score the agent on these dimensions (0.0-1.0 each):
1. tool_accuracy: Did the agent select the correct tools?
2. answer_quality: Is the output correct, complete, and useful?
3. guardrail_compliance: Did the agent respect all safety rules?
4. efficiency: Did the agent use the minimum necessary steps?

Return JSON:
{
  "tool_accuracy": 0.0-1.0,
  "answer_quality": 0.0-1.0,
  "guardrail_compliance": 0.0-1.0,
  "efficiency": 0.0-1.0,
  "overall": 0.0-1.0 (weighted average),
  "notes": "explanation of scoring"
}"""
```

#### 6.2.3 Evaluation Execution Flow

```
POST /v1/ml/evaluations/{id}/run
  │
  ▼
┌─────────────────────────────────────┐
│ 1. Load AgentDefinition             │
│ 2. For each test_case:              │
│    a. Build agent context (prompt +  │
│       tools + guardrails)            │
│    b. Execute agent against input    │
│       (via Intent Engine)            │
│    c. Capture output + tools used    │
│    d. Call AI judge model            │
│    e. Record dimension scores        │
│ 3. Aggregate scores                  │
│ 4. Update AgentEvaluation            │
│ 5. Return results                    │
└─────────────────────────────────────┘
```

**Execution modes:**
- **Synchronous** (current): Block until all test cases complete
- **Async** (planned): Dispatch as Temporal workflow, poll for completion

### 6.3 Agent Deployment via MCP Tools

Agents can be deployed and managed through MCP tool calls:

| MCP Tool | Action | Description |
|----------|--------|-------------|
| `voyant.ml.agent.create` | POST | Create agent definition |
| `voyant.ml.agent.update` | PUT | Update agent configuration |
| `voyant.ml.agent.evaluate` | POST | Run evaluation suite |
| `voyant.ml.agent.deploy` | POST | Activate agent for serving |
| `voyant.ml.agent.invoke` | POST | Send a request to an active agent |
| `voyant.ml.agent.monitor` | GET | Get agent performance metrics |
| `voyant.ml.agent.rollback` | POST | Revert to previous version |

**Agent invocation flow:**

```
User Request → MCP Agent Endpoint
  │
  ▼
┌──────────────────────────────────┐
│ 1. Load AgentDefinition (active) │
│ 2. Validate against guardrails   │
│ 3. Build LLM prompt:             │
│    system_prompt + user_input     │
│ 4. Call LLM (via provider)       │
│ 5. Parse tool calls from LLM     │
│ 6. Execute tool calls (MCP)      │
│ 7. Feed results back to LLM      │
│ 8. Repeat until done or max_iter │
│ 9. Log invocation metrics        │
│ 10. Return response              │
└──────────────────────────────────┘
```

---

## 7. Model Serving Architecture

### 7.1 Real-Time Serving

#### 7.1.1 REST Endpoint Design

```
POST /v1/ml/predict/{endpoint_name}
Headers:
  Authorization: Bearer <token>
  Content-Type: application/json
  X-Voyant-Version: <optional: specific model version>
  X-Voyant-Trace: <optional: trace ID for debugging>

Request:
{
  "inputs": {
    "feature1": 1.5,
    "feature2": "category_a",
    "feature3": [0.1, 0.2, 0.3]
  }
}

Response (200):
{
  "prediction": {
    "class": "positive",
    "probability": 0.87,
    "probabilities": {"positive": 0.87, "negative": 0.13}
  },
  "metadata": {
    "model_name": "fraud-detector",
    "model_version": 3,
    "model_stage": "production",
    "latency_ms": 12.5,
    "request_id": "req-uuid-..."
  }
}

Response (400):
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "Missing required feature: 'feature1'",
    "details": {"expected_features": ["feature1", "feature2", "feature3"]}
  }
}

Response (503):
{
  "error": {
    "code": "MODEL_NOT_LOADED",
    "message": "Endpoint 'fraud-detector' is inactive",
    "retry_after_seconds": 30
  }
}
```

#### 7.1.2 Model Loading Strategy

```python
class ModelServer:
    """In-process model server with caching."""

    def __init__(self):
        self._loaded_models: dict[str, Any] = {}  # version_id → model
        self._load_times: dict[str, float] = {}

    def load_model(self, model_version_id: str) -> Any:
        """Load model from storage into memory."""
        if model_version_id in self._loaded_models:
            return self._loaded_models[model_version_id]

        mv = ModelVersion.objects.get(id=model_version_id)
        # Load from MinIO/S3 based on storage_path
        model = self._deserialize(mv.storage_path, mv.metadata)
        self._loaded_models[model_version_id] = model
        self._load_times[model_version_id] = time.time()
        return model

    def predict(self, endpoint_name: str, inputs: dict) -> dict:
        endpoint = ModelEndpoint.objects.get(name=endpoint_name, status="active")
        model = self.load_model(str(endpoint.model_version_id))
        start = time.time()
        result = model.predict(inputs)
        latency = (time.time() - start) * 1000
        # Update metrics
        endpoint.invocation_count += 1
        endpoint.avg_latency_ms = (
            (endpoint.avg_latency_ms * (endpoint.invocation_count - 1) + latency)
            / endpoint.invocation_count
        )
        endpoint.save(update_fields=["invocation_count", "avg_latency_ms"])
        return result
```

#### 7.1.3 Supported Model Flavors (Phase 1)

| Flavor | Serialization | Framework | Load Method |
|--------|--------------|-----------|-------------|
| `sklearn` | joblib/pickle | scikit-learn | `joblib.load(path)` |
| `onnx` | ONNX format | ONNX Runtime | `onnxruntime.InferenceSession(path)` |
| `python_function` | CloudPickle | Any | `cloudpickle.load(path)` |

#### 7.1.4 Prediction Request Pipeline

```
HTTP Request
  │
  ▼
┌─────────────────────┐
│ 1. Auth + Rate Limit │  (RBAC: execute:ml)
├─────────────────────┤
│ 2. Input Validation  │  (Check required features, types)
├─────────────────────┤
│ 3. Model Lookup      │  (Endpoint → ModelVersion → Model)
├─────────────────────┤
│ 4. Model Inference   │  (Loaded model + predict)
├─────────────────────┤
│ 5. Post-processing   │  (Format output, add metadata)
├─────────────────────┤
│ 6. Metrics Logging   │  (Count, latency, errors)
├─────────────────────┤
│ 7. Response          │  (JSON with prediction + metadata)
└─────────────────────┘
```

### 7.2 Batch Prediction

#### 7.2.1 Temporal Workflow Design

```python
# apps/worker/workflows/batch_predict_workflow.py

@workflow.defn
class BatchPredictWorkflow:
    """Batch prediction over a dataset."""

    @workflow.run
    async def run(self, input: BatchPredictInput) -> BatchPredictOutput:
        # 1. Load dataset from source
        data = await workflow.execute_activity(
            load_dataset_activity,
            args=[input.source_id, input.query],
            start_to_close_timeout=timedelta(minutes=5),
        )

        # 2. Load model
        model = await workflow.execute_activity(
            load_model_activity,
            args=[input.model_version_id],
            start_to_close_timeout=timedelta(minutes=2),
        )

        # 3. Process in batches
        results = []
        for batch in chunk(data, size=input.batch_size):
            batch_results = await workflow.execute_activity(
                predict_batch_activity,
                args=[model, batch],
                start_to_close_timeout=timedelta(minutes=5),
            )
            results.extend(batch_results)

            # Heartbeat progress
            workflow.heartbeat(len(results) / len(data))

        # 4. Save results
        artifact = await workflow.execute_activity(
            save_batch_results_activity,
            args=[results, input.output_format],
            start_to_close_timeout=timedelta(minutes=5),
        )

        return BatchPredictOutput(
            total_predictions=len(results),
            artifact_id=artifact.id,
            status="completed",
        )
```

#### 7.2.2 Batch Prediction API

```
POST /v1/ml/batch-predict
Request:
{
  "model_version_id": "uuid",
  "source_id": "uuid",          // Data source to predict on
  "query": "SELECT * FROM...",   // Optional SQL filter
  "batch_size": 1000,
  "output_format": "csv",        // csv, json, parquet
  "output_destination": "minio"   // minio, database
}

Response:
{
  "job_id": "uuid",
  "status": "running",
  "poll_url": "/v1/ml/jobs/{job_id}"
}
```

### 7.3 Model Versioning and Stage Transitions

#### 7.3.1 State Machine

```
    ┌──────┐
    │ none │
    └──┬───┘
       │ transition("staging")
       ▼
  ┌──────────┐
  │ staging  │
  └──┬───┬───┘
     │   │
     │   │ transition("archived")
     │   ▼
     │  ┌──────────┐
     │  │ archived │──────────┐
     │  └──────────┘          │
     │                 transition("none")
     │   transition("production")        │
     ▼                        ▼
┌────────────┐          ┌──────┐
│ production │◀─────────│ none │ (reset)
└────────────┘          └──────┘
     │
     │ transition("archived")
     ▼
┌──────────┐
│ archived │
└──────────┘
```

**Validation rules enforced in `transition_stage()`:**
```python
valid_transitions = {
    "none": ["staging"],
    "staging": ["production", "archived"],
    "production": ["archived", "staging"],
    "archived": ["none"],
}
```

#### 7.3.2 Stage Semantics

| Stage | Meaning | Serving Behavior |
|-------|---------|-----------------|
| `none` | Newly created, not yet evaluated | Not servable |
| `staging` | Under evaluation, A/B testing | Serves to internal traffic only |
| `production` | Approved for production use | Serves all traffic |
| `archived` | Retired, kept for audit | Not servable, read-only |

#### 7.3.3 Transition Side Effects

When a model version transitions stages:

1. **none → staging:** Initialize evaluation metrics, start monitoring
2. **staging → production:**
   - Archive current production version (if any) → `staging` (optional, based on `archive_existing` flag)
   - Update all endpoints pointing to this model
   - Emit event to audit log
3. **production → archived:**
   - Deactivate all endpoints serving this version
   - Log archival event
4. **archived → none:** Reset for re-evaluation

---

## 8. Feature Store Design

### 8.1 What a Feature Store Provides

A feature store is a centralized system for managing, storing, and serving ML features. Key capabilities:

| Capability | Description |
|-----------|-------------|
| **Feature Registration** | Define features with metadata (name, type, description, owner) |
| **Feature Computation** | Transform raw data into features (SQL, Python) |
| **Feature Storage** | Store computed features in offline (batch) and online (low-latency) stores |
| **Feature Discovery** | Search/browse features across teams and projects |
| **Point-in-Time Correctness** | Prevent data leakage by using features as they were at prediction time |
| **Feature Lineage** | Track how features are derived from raw data |
| **Feature Versioning** | Track changes to feature definitions over time |
| **Training/Serving Consistency** | Same feature values for training and inference |

### 8.2 Does Voyant Need a Feature Store?

**Analysis of current state:**

| Factor | Assessment | Need Level |
|--------|-----------|------------|
| **Scale of ML operations** | Early-stage ML platform, sklearn primitives | Low |
| **Number of ML teams** | Single-tenant per deployment | Low |
| **Feature reuse across models** | Not yet (each model trains independently) | Medium (future) |
| **Training/serving skew** | Not applicable yet (no real-time serving) | Low (becomes High with serving) |
| **Feature computation complexity** | Simple (SQL aggregations, basic transforms) | Low |
| **Data volume** | PostgreSQL + Trino (moderate scale) | Medium |

**Recommendation: Build a lightweight Feature Store (Phase 2 of ML Platform), not the full Databricks-scale system.**

### 8.3 Lightweight Feature Store Design

#### 8.3.1 Data Model

```python
class FeatureTable(TenantModel, UUIDModel):
    """A group of related features (analogous to a feature table in Databricks)."""
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default="")
    entity_key = models.CharField(max_length=255,
        help_text="Primary entity column (e.g., 'customer_id')")
    source_query = models.TextField(blank=True,
        help_text="SQL that computes features from raw data")
    schedule_cron = models.CharField(max_length=100, blank=True,
        help_text="Cron expression for recomputation")
    freshness_minutes = models.IntegerField(default=1440,  # 24 hours
        help_text="Maximum acceptable staleness")
    tags = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, default="active")

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ml_feature_table"
        unique_together = [("tenant_id", "name")]


class FeatureDefinition(TenantModel, UUIDModel):
    """Individual feature within a feature table."""
    feature_table = models.ForeignKey(FeatureTable, on_delete=models.CASCADE,
        related_name="features")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    feature_type = models.CharField(max_length=50,
        choices=[
            ("float", "Float"),
            ("int", "Integer"),
            ("string", "String"),
            ("boolean", "Boolean"),
            ("array", "Array"),
            ("timestamp", "Timestamp"),
        ])
    computation = models.TextField(blank=True,
        help_text="SQL expression (e.g., 'SUM(amount) OVER (PARTITION BY customer_id)')")
    default_value = models.JSONField(null=True, blank=True)
    tags = models.JSONField(default=dict, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ml_feature_definition"
        unique_together = [("feature_table_id", "name")]


class FeatureValue(UUIDModel):
    """Materialized feature values (online store)."""
    feature_table = models.ForeignKey(FeatureTable, on_delete=models.CASCADE)
    entity_key = models.CharField(max_length=255, db_index=True)
    feature_name = models.CharField(max_length=255)
    value = models.JSONField()
    computed_at = models.DateTimeField()
    ttl_at = models.DateTimeField(null=True,
        help_text="When this value expires")

    class Meta:
        db_table = "ml_feature_value"
        indexes = [
            models.Index(fields=["feature_table_id", "entity_key", "feature_name"]),
            models.Index(fields=["ttl_at"]),
        ]
```

#### 8.3.2 Feature Store API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/ml/features/tables` | List feature tables |
| `POST` | `/v1/ml/features/tables` | Create feature table |
| `GET` | `/v1/ml/features/tables/{id}` | Get table with features |
| `POST` | `/v1/ml/features/tables/{id}/features` | Add feature definition |
| `POST` | `/v1/ml/features/tables/{id}/materialize` | Trigger computation |
| `GET` | `/v1/ml/features/lookup` | Point-in-time feature lookup |
| `GET` | `/v1/ml/features/search` | Search features by name/tag |

#### 8.3.3 Feature Lookup (Point-in-Time)

```
GET /v1/ml/features/lookup?table=customer_features&entity_key=12345&as_of=2026-09-01T00:00:00Z

Response:
{
  "entity_key": "12345",
  "features": {
    "total_orders": 47,
    "avg_order_value": 125.50,
    "days_since_last_order": 3,
    "lifetime_value": 5898.50
  },
  "computed_at": "2026-08-31T06:00:00Z",
  "freshness": "OK"  // or "STALE" if beyond freshness_minutes
}
```

#### 8.3.4 Materialization Pipeline

```
┌───────────────────────────┐
│  Feature Table Definition │
│  (source_query, schedule) │
└───────────┬───────────────┘
            │ Triggered by:
            │ - Cron schedule
            │ - API call
            │ - Data ingestion event
            ▼
┌───────────────────────────┐
│  Temporal Workflow         │
│  FeatureMaterializeWorkflow│
├───────────────────────────┤
│ 1. Execute source_query    │
│    via Trino               │
│ 2. Compute feature expressions │
│ 3. Write to FeatureValue   │
│    (online store)          │
│ 4. Update freshness metadata│
│ 5. Log metrics (row count, │
│    duration, errors)       │
└───────────────────────────┘
```

#### 8.3.5 Integration with Model Serving

When a prediction request arrives:

```python
def enrich_with_features(inputs: dict, model_version: ModelVersion) -> dict:
    """Enrich prediction inputs with features from the feature store."""
    entity_key = inputs.get("entity_key")
    if not entity_key:
        return inputs

    # Look up required features from model version metadata
    required_features = model_version.metadata.get("required_features", [])

    # Fetch from feature store
    features = feature_store.lookup(
        table=required_features["table"],
        entity_key=entity_key,
    )

    # Merge into inputs
    enriched = {**inputs, **features}
    return enriched
```

---

## 9. Modeling Objectives (Deep Specification)

*Sourced from Deep-Dive Module & Function Spec §7.3*

A Modeling Objective defines HOW a model will be used in production. The same model can have multiple objectives — for example, a churn model may be scored in real-time (for individual customers at login) and in batch (for nightly reports). Objectives determine the serving infrastructure, latency requirements, and monitoring configuration.

```
┌─────────────────────────────────────────────────────────────────┐
│              MODELING OBJECTIVES SYSTEM                           │
│                                                                  │
│  A Modeling Objective defines HOW a model will be used in        │
│  production. Same model can have multiple objectives.            │
│                                                                  │
│  Objective Types:                                                │
│                                                                  │
│  1. REAL-TIME SCORING                                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Description: Score individual records on demand           │   │
│  │ Latency requirement: < 100ms (p99)                       │   │
│  │ Infrastructure: Model serving (Triton/KServe)             │   │
│  │ Scaling: Auto-scale based on request rate                 │   │
│  │ Example: Score a customer for churn risk at login         │   │
│  │                                                          │   │
│  │ Input: Customer object properties                         │   │
│  │ Output: { churn_probability: 0.73, risk_factors: [...] } │   │
│  │ Integration: Ontology Function wrapping model endpoint    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  2. BATCH SCORING                                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Description: Score all objects of a type periodically     │   │
│  │ Latency requirement: < 1 hour for 1M records             │   │
│  │ Infrastructure: Spark job with model broadcast            │   │
│  │ Scheduling: Daily / hourly / on pipeline trigger          │   │
│  │ Example: Score all customers for churn risk nightly       │   │
│  │                                                          │   │
│  │ Input: Full Customer dataset                              │   │
│  │ Output: New dataset with score columns added              │   │
│  │ Integration: Pipeline transform with model loading        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  3. STREAMING SCORING                                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Description: Score events as they arrive in a stream      │   │
│  │ Latency requirement: < 50ms per event                    │   │
│  │ Infrastructure: Kafka consumer + model serving            │   │
│  │ Throughput: 10K+ events/sec                              │   │
│  │ Example: Score transactions for fraud in real-time        │   │
│  │                                                          │   │
│  │ Input: Kafka event payload                                │   │
│  │ Output: Score + action (approve/flag/block)              │   │
│  │ Integration: Streaming pipeline with embedded model       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  4. EMBEDDED IN DECISION                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Description: Model output feeds directly into a business │   │
│  │   action or workflow                                     │   │
│  │ Example: Churn model score triggers retention offer       │   │
│  │ Integration: Action with model-backed decision logic     │   │
│  │                                                          │   │
│  │ Workflow:                                                │   │
│  │ 1. Customer visits site                                  │   │
│  │ 2. Real-time score calculated                            │   │
│  │ 3. If churn_probability > 0.7:                           │   │
│  │    → Trigger "sendRetentionOffer" action                 │   │
│  │    → Log decision in audit trail                         │   │
│  │ 4. If churn_probability < 0.3:                           │   │
│  │    → Trigger "upsell" action                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  5. HUMAN-IN-THE-LOOP                                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Description: Model provides recommendations, human makes  │   │
│  │   final decision                                         │   │
│  │ Example: Fraud detection → human reviews flagged txns     │   │
│  │ Integration: Approval workflow with model confidence      │   │
│  │                                                          │   │
│  │ UI: Dashboard showing flagged items sorted by confidence  │   │
│  │ Actions: [Approve] [Reject] [Escalate] [Mark for Review] │   │
│  │ Feedback loop: Human decisions feed back to model         │   │
│  │   training                                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  MODEL MONITORING PER OBJECTIVE:                                 │
│  Each objective has its own monitoring configuration:            │
│  • Real-time: Latency, throughput, error rate, prediction dist  │
│  • Batch: Processing time, row count, resource usage            │
│  • Streaming: Event lag, processing rate, backpressure           │
│  • Embedded: Decision rate, override rate, business impact       │
│  • Human-in-loop: Review time, agreement rate, escalation rate   │
└─────────────────────────────────────────────────────────────────┘
```

### 9.1 Objective Type Summary

| # | Objective | Latency Target | Throughput | Infrastructure | Example |
|---|-----------|---------------|------------|----------------|---------|
| 1 | Real-Time Scoring | < 100ms p99 | 1K+ req/sec | Model serving (Triton/KServe) | Score customer at login |
| 2 | Batch Scoring | < 1 hour / 1M rows | 100K+ rows/min | Spark with model broadcast | Nightly churn scoring |
| 3 | Streaming Scoring | < 50ms / event | 10K+ events/sec | Kafka consumer + model | Real-time fraud detection |
| 4 | Embedded in Decision | Varies | Per-event | Action + model logic | Auto-trigger retention offer |
| 5 | Human-in-the-Loop | N/A (async) | Per-review | Approval workflow | Human reviews flagged txns |

---

## 10. Feature Store Deep Architecture

*Sourced from Deep-Dive Module &Function Spec §7.4*

This section provides the deep architecture for the Feature Store, complementing the lightweight design in §8. It specifies the two-tier serving architecture (online/offline), point-in-time correct retrieval for training, and feature computation pipelines.

```
┌─────────────────────────────────────────────────────────────────┐
│              FEATURE STORE ARCHITECTURE                           │
│                                                                  │
│  Two-tier serving:                                               │
│                                                                  │
│  ┌─ ONLINE STORE (Low Latency) ───────────────────────────┐    │
│  │                                                          │    │
│  │ Storage: Redis Cluster                                   │    │
│  │ Latency: < 5ms (p99) for single entity lookup            │    │
│  │ Data format: Protobuf or MessagePack                     │    │
│  │ Key format: {entity_type}:{entity_id}                    │    │
│  │ Value format: { feature_name: value, ... }               │    │
│  │                                                          │    │
│  │ Example:                                                 │    │
│  │ Key: "customer:1001"                                     │    │
│  │ Value: {                                                 │    │
│  │   "tenure_months": 24,                                   │    │
│  │   "total_orders_30d": 5,                                 │    │
│  │   "avg_order_value": 156.78,                             │    │
│  │   "support_tickets_90d": 2,                              │    │
│  │   "lifetime_value": 4523.45,                             │    │
│  │   "churn_risk_score": 0.23,                              │    │
│  │   "_updated_at": "2026-09-09T02:12:00Z"                 │    │
│  │ }                                                        │    │
│  │                                                          │    │
│  │ Update mechanism: Pipeline writes → Redis sync           │    │
│  │ TTL: Configurable per feature group (default: 24 hours)  │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ OFFLINE STORE (High Throughput) ──────────────────────┐    │
│  │                                                          │    │
│  │ Storage: Iceberg tables (columnar, partitioned)           │    │
│  │ Latency: Seconds to minutes (for batch queries)          │    │
│  │ Format: Parquet with Iceberg ACID transactions           │    │
│  │                                                          │    │
│  │ Point-in-time correct retrieval:                          │    │
│  │ ┌──────────────────────────────────────────────────┐    │    │
│  │ │ Problem: When training a model, you must use only │    │    │
│  │ │ features that were known at prediction time.      │    │    │
│  │ │ Using future data = data leakage.                 │    │    │
│  │ │                                                   │    │    │
│  │ │ Solution: Point-in-time joins                     │    │    │
│  │ │                                                   │    │    │
│  │ │ SELECT * FROM features.customer_features          │    │    │
│  │ │ FOR SYSTEM_TIME AS OF '2026-06-15 00:00:00'       │    │    │
│  │ │ WHERE customer_id = 1001                          │    │    │
│  │ │                                                   │    │    │
│  │ │ This retrieves features as they were on June 15,  │    │    │
│  │ │ not as they are today.                            │    │    │
│  │ └──────────────────────────────────────────────────┘    │    │
│  │                                                          │    │
│  │ Training dataset generation:                              │    │
│  │ ┌──────────────────────────────────────────────────┐    │    │
│  │ │ Input: labels (churn event on date D),            │    │    │
│  │ │        features (customer_features)                │    │    │
│  │ │                                                   │    │    │
│  │ │ For each label:                                   │    │    │
│  │ │   Retrieve features as of D - lookback_window     │    │    │
│  │ │   (e.g., 30 days before churn event)             │    │    │
│  │ │                                                   │    │    │
│  │ │ Output: Training dataset with no data leakage     │    │    │
│  │ └──────────────────────────────────────────────────┘    │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  FEATURE COMPUTATION PIPELINE:                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │ Source Data → Transform → Feature Store                   │   │
│  │                                                          │   │
│  │ Example feature definitions:                             │   │
│  │                                                          │   │
│  │ Feature: total_orders_30d                                │   │
│  │ Entity: customer_id                                      │   │
│  │ Computation:                                             │   │
│  │   SELECT customer_id,                                    │   │
│  │          COUNT(*) as total_orders_30d                    │   │
│  │   FROM orders                                            │   │
│  │   WHERE order_date >= CURRENT_DATE - INTERVAL '30 days'  │   │
│  │   GROUP BY customer_id                                   │   │
│  │ Schedule: Every 1 hour                                   │   │
│  │ Freshness: 1 hour                                        │   │
│  │                                                          │   │
│  │ Feature: lifetime_value                                  │   │
│  │ Entity: customer_id                                      │   │
│  │ Computation:                                             │   │
│  │   SELECT customer_id,                                    │   │
│  │          SUM(amount) as lifetime_value                   │   │
│  │   FROM orders                                            │   │
│  │   WHERE status = 'completed'                             │   │
│  │   GROUP BY customer_id                                   │   │
│  │ Schedule: Every 6 hours                                  │   │
│  │ Freshness: 6 hours                                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  FEATURE STATISTICS (auto-computed):                             │
│  • Count, nulls_count, nulls_percentage                          │
│  • Mean, median, std_dev, min, max                               │
│  • Percentiles: p1, p5, p25, p50, p75, p95, p99                 │
│  • Distinct_count, cardinality                                   │
│  • Distribution histogram (configurable bins)                    │
│  • Drift metrics: KS-statistic vs. reference distribution       │
└─────────────────────────────────────────────────────────────────┘
```

### 10.1 Online vs. Offline Store Comparison

| Dimension | Online Store | Offline Store |
|-----------|-------------|---------------|
| **Storage** | Redis Cluster | Iceberg tables (Parquet) |
| **Latency** | < 5ms (p99) | Seconds to minutes |
| **Throughput** | 100K+ lookups/sec | Batch queries |
| **Data Format** | Protobuf / MessagePack | Columnar Parquet |
| **Freshness** | Near real-time (pipeline sync) | Hours (batch materialization) |
| **Use Case** | Real-time model serving | Training dataset generation |
| **TTL** | Configurable (default 24h) | Snapshot-based (Iceberg time travel) |

### 10.2 Point-in-Time Correct Retrieval

When training a model, the system MUST use only features that were known at the time of prediction. Using future data constitutes **data leakage** and produces inflated metrics that do not generalize to production.

The Feature Store solves this through Iceberg's native time travel:

```sql
-- Retrieve features as they were at a specific point in time
SELECT * FROM features.customer_features
FOR SYSTEM_TIME AS OF '2026-06-15 00:00:00'
WHERE customer_id = 1001
```

**Training dataset generation flow:**
1. For each labeled event (e.g., customer churned on date D):
2. Compute `as_of = D - lookback_window` (e.g., 30 days before churn)
3. Retrieve features from the offline store as of `as_of`
4. Combine label + features into a training row
5. Result: A training dataset with zero data leakage

---

## 11. Implementation Roadmap

### 11.1 Phase 3A: Experiment Tracking + Registry (Weeks 7–8)

| Task | Effort | Dependencies |
|------|--------|-------------|
| Add `RunMetricHistory` model + migration | 0.5 day | None |
| Add metric time-series API (`log-metric`, `metric-history`) | 1 day | RunMetricHistory |
| Add run search/filter API | 1 day | None |
| Add model version tags + aliases | 0.5 day | None |
| Add experiment search/filter API | 1 day | None |
| Add model search/filter API | 1 day | None |
| MLflow compatibility wrapper layer | 3 days | All above |
| Python client compatibility test | 1 day | Wrapper layer |
| Unit tests (15+ tests) | 2 days | All above |

**Total: ~11 days (2 engineers, 1 week)**

### 11.2 Phase 3B: Model Serving (Weeks 9–10)

| Task | Effort | Dependencies |
|------|--------|-------------|
| `ModelServer` class with model loading | 2 days | MinIO integration |
| Prediction endpoint (`/v1/ml/predict/{name}`) | 1 day | ModelServer |
| Input validation per model schema | 1 day | Prediction endpoint |
| sklearn flavor support | 1 day | ModelServer |
| ONNX flavor support | 1 day | ModelServer |
| `BatchPredictWorkflow` (Temporal) | 2 days | ModelServer |
| Batch prediction API | 1 day | Workflow |
| Endpoint monitoring (count, latency, errors) | 1 day | Prediction endpoint |
| Unit tests (10+ tests) | 2 days | All above |

**Total: ~12 days (2 engineers, ~1.5 weeks)**

### 11.3 Phase 3C: Agent Platform (Weeks 10–12)

| Task | Effort | Dependencies |
|------|--------|-------------|
| Enhanced AgentDefinition (versioning, ontology bindings) | 1 day | None |
| Multi-dimensional evaluation scoring | 2 days | None |
| AI judge prompt engineering | 1 day | None |
| Async evaluation via Temporal workflow | 2 days | None |
| Agent comparison (version A vs B) | 1 day | Multi-dimensional scoring |
| Agent deployment lifecycle (draft → active → archived) | 1 day | None |
| Agent invocation endpoint (execute agent) | 2 days | AgentDefinition |
| Agent MCP tools (7 tools) | 2 days | All above |
| Unit tests (10+ tests) | 2 days | All above |

**Total: ~14 days (2 engineers, ~2 weeks)**

### 11.4 Phase 3D: AutoML + Feature Store (Weeks 11–12, parallel)

| Task | Effort | Dependencies |
|------|--------|-------------|
| AutoML Temporal workflow | 3 days | MLPrimitives |
| Feature Table + Feature Definition models | 1 day | None |
| Feature materialization workflow | 2 days | Trino integration |
| Feature lookup API | 1 day | Feature models |
| Feature store MCP tools | 1 day | Lookup API |
| Unit tests (8+ tests) | 2 days | All above |

**Total: ~10 days (1 engineer, ~2 weeks)**

### 11.5 Summary

| Phase | Deliverable | Weeks | Engineers |
|-------|------------|-------|-----------|
| 3A | Experiment Tracking + Registry + MLflow API | 7–8 | 2 |
| 3B | Model Serving (real-time + batch) | 9–10 | 2 |
| 3C | Agent Platform (definition + evaluation + deployment) | 10–12 | 2 |
| 3D | AutoML + Feature Store (basic) | 11–12 | 1 |
| **Total** | **Full ML/AI Platform** | **6 weeks** | **2–3** |

---

## 12. Data Model Reference

### 12.1 Complete Entity Diagram (After Implementation)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ML PLATFORM DATA MODEL                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  EXPERIMENT TRACKING              MODEL REGISTRY                        │
│  ─────────────────               ────────────────                       │
│                                                                         │
│  Experiment ──1:N──▶ Run         RegisteredModel ──1:N──▶ ModelVersion  │
│       │                    │              │                    │        │
│       │ (tags, desc)       │ (params,     │ (name, tags)       │        │
│       │                    │  metrics,    │                    │        │
│       │                    │  status)     │                    │        │
│       │                    │              │                    │        │
│       │                    ▼              │                    ▼        │
│       │              RunArtifact          │           ModelEndpoint     │
│       │              (name, type,         │           (name, status,    │
│       │               path, size)         │            config, path)    │
│       │                    │              │                    │        │
│       │                    ▼              │                    │        │
│       │           RunMetricHistory ◀──────┘           (invocation_      │
│       │           (key, value, step)                   count, latency)  │
│       │                                                                  │
│  FEATURE STORE                 AGENT PLATFORM                           │
│  ──────────────                ────────────────                          │
│                                                                         │
│  FeatureTable ──1:N──▶         AgentDefinition ──1:N──▶ AgentEvaluation │
│  FeatureDefinition             (name, prompt,           (test_cases,    │
│       │                        model, tools,             results,       │
│       ▼                        guardrails,               overall_score, │
│  FeatureValue                  version,                  judge_model,   │
│  (entity_key, value,           ontology_bindings)        dimensions)    │
│   computed_at, ttl_at)                                                  │
│                                                                         │
│  LLM INFRASTRUCTURE                                                     │
│  ────────────────────                                                   │
│                                                                         │
│  LLMProvider ──1:N──▶ LLMModel ──1:1──▶ ActiveLLMConfig (per purpose)  │
│  (7 providers)         (17 models)       (intent, analysis,             │
│                                           scraper, general)             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 12.2 New Models to Build

| Model | Table | Fields | Phase |
|-------|-------|--------|-------|
| `RunMetricHistory` | `ml_run_metric_history` | run, key, value, step, timestamp | 3A |
| `FeatureTable` | `ml_feature_table` | name, entity_key, source_query, schedule_cron, freshness_minutes | 3D |
| `FeatureDefinition` | `ml_feature_definition` | feature_table, name, feature_type, computation, default_value | 3D |
| `FeatureValue` | `ml_feature_value` | feature_table, entity_key, feature_name, value, computed_at, ttl_at | 3D |

### 12.3 New API Endpoints to Build

| Method | Path | Phase | Description |
|--------|------|-------|-------------|
| `POST` | `/v1/ml/runs/{id}/log-metric` | 3A | Log metric with step |
| `GET` | `/v1/ml/runs/{id}/metric-history` | 3A | Get metric time series |
| `GET` | `/v1/ml/runs/search` | 3A | Search/filter runs |
| `GET` | `/v1/ml/experiments/compare` | 3A | Compare experiments |
| `POST` | `/v1/ml/predict/{name}` | 3B | Real-time prediction |
| `POST` | `/v1/ml/batch-predict` | 3B | Batch prediction job |
| `GET` | `/v1/ml/jobs/{id}` | 3B | Poll batch job status |
| `POST` | `/v1/ml/agents/{id}/invoke` | 3C | Execute agent |
| `GET` | `/v1/ml/agents/{id}/versions` | 3C | List agent versions |
| `POST` | `/v1/ml/agents/{id}/compare` | 3C | Compare evaluation results |
| `POST` | `/api/2.0/mlflow/*` | 3A | MLflow compatibility layer (15+ endpoints) |
| `GET` | `/v1/ml/features/tables` | 3D | List feature tables |
| `POST` | `/v1/ml/features/tables` | 3D | Create feature table |
| `POST` | `/v1/ml/features/tables/{id}/materialize` | 3D | Trigger materialization |
| `GET` | `/v1/ml/features/lookup` | 3D | Point-in-time lookup |

### 12.4 New MCP Tools to Build

| MCP Tool | Phase | Description |
|----------|-------|-------------|
| `voyant.ml.experiment.create` | 3A | Create experiment |
| `voyant.ml.run.create` | 3A | Start run |
| `voyant.ml.run.log_metric` | 3A | Log metric |
| `voyant.ml.run.log_param` | 3A | Log parameter |
| `voyant.ml.model.register` | 3A | Register model |
| `voyant.ml.model.transition` | 3A | Transition stage |
| `voyant.ml.predict` | 3B | Call prediction endpoint |
| `voyant.ml.agent.create` | 3C | Create agent |
| `voyant.ml.agent.evaluate` | 3C | Run evaluation |
| `voyant.ml.agent.deploy` | 3C | Deploy agent |
| `voyant.ml.agent.invoke` | 3C | Invoke agent |
| `voyant.ml.agent.monitor` | 3C | Monitor agent |
| `voyant.ml.features.lookup` | 3D | Feature lookup |

---

## Appendix A: SRS Traceability

| SRS ID | Requirement | Section in This Document | Status |
|--------|-------------|-------------------------|--------|
| ML-F-001 | Experiment creation and tracking | §1.1, §5, §9.1 | **Designed** |
| ML-F-002 | Run logging (params, metrics, artifacts) | §1.1, §2.2, §9.1 | **Designed** |
| ML-F-003 | Model registry with versioning | §1.1, §2.3, §9.1 | **Designed** |
| ML-F-004 | Model serving endpoints (real-time + batch) | §7, §9.2 | **Designed** |
| ML-F-005 | MLflow-compatible API | §5, §2.7, §9.1 | **Designed** |
| ML-F-006 | Agent definition (prompt, model, tools, guardrails) | §6, §9.3 | **Designed** |
| ML-F-007 | Agent evaluation with AI judge | §6.2, §9.3 | **Designed** |
| ML-F-008 | Agent deployment and monitoring | §6.3, §9.3 | **Designed** |

---

## Appendix B: Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| MLflow API surface too large for compatibility | Medium | High | Implement core 80% (tracking + registry), defer flavors |
| Model serving security (pickle deserialization) | High | Critical | Use ONNX as default; sandbox pickle loading |
| AI judge inconsistency in evaluations | Medium | Medium | Use temperature=0, structured output, multiple judge runs |
| Feature Store scope creep | Medium | Medium | Keep Phase 3D lightweight (PostgreSQL-based, no Redis yet) |
| Agent evaluation latency | High | Low | Async execution via Temporal, progress polling |
| LLM cost for AI judge | Medium | Low | Cache judge results, use cheap models for judge |

---

**Document version:** 1.0.0
**Created:** 2026-09-06
**Author:** Voyant Engineering
**Next review:** After Phase 3A completion (Week 8)
