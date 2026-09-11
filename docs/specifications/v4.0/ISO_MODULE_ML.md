# ISO Module Specification: ML Platform

> **Module:** `apps/ml_platform` + `dashboard/src/views/view-drift.ts`  
> **Version:** 4.0 — Phase 3 ML Platform  
> **Status:** Production  
> **Standard:** ISO/IEC/IEEE 29148:2018  

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Actors and Roles](#2-actors-and-roles)
3. [Screen Mockups](#3-screen-mockups)
4. [Functional Requirements](#4-functional-requirements)
5. [Data Models](#5-data-models)
6. [API Endpoints](#6-api-endpoints)
7. [MLflow Compatibility Matrix](#7-mlflow-compatibility-matrix)
8. [Model Serving Engine](#8-model-serving-engine)
9. [Drift Detection Engine](#9-drift-detection-engine)
10. [Agent Definition & Evaluation](#10-agent-definition--evaluation)
11. [Integration Points](#11-integration-points)
12. [Quality Attributes](#12-quality-attributes)
13. [Implementation References](#13-implementation-references)

---

## 1. Module Overview

### 1.1 Purpose

The ML Platform is Voyant's end-to-end machine learning lifecycle management system. It provides experiment tracking, model registry, real-time and batch model serving, drift monitoring with statistical tests, and an AI agent definition/evaluation framework. The platform is **MLflow-compatible**, enabling drop-in use with the standard `mlflow` Python client.

### 1.2 Key Differentiators

| Differentiator | Description |
|---|---|
| **MLflow Drop-in Compatible** | Full `/api/2.0/mlflow/*` endpoint surface — `mlflow.set_tracking_uri("voyant")` works out of the box |
| **Integrated Drift Detection** | KS test (numeric), chi-square (categorical), PSI (prediction) — zero external dependency |
| **Model Serving with LRU Cache** | In-memory model cache with pickle/joblib/ONNX format support, MinIO artifact fetching |
| **Approval-Gated Production** | Production deployment requires approval workflow (403 → approval request) |
| **Agent Evaluation Framework** | AI judge model evaluates agent quality with test cases, scoring, and pass/fail metrics |
| **Real-Time Drift Dashboard** | Live feature drift visualization with prediction distribution comparison charts |

### 1.3 Scope

- Experiment tracking (create, log metrics/params/tags, search)
- Model registry (register, version, stage transition with approval gates)
- Real-time single prediction and batch prediction via Temporal
- Latency percentile monitoring (p50/p95/p99)
- Feature drift detection (KS test, chi-square) and prediction drift (PSI)
- Agent definition (model, prompt, tools, guardrails)
- Agent evaluation (test cases, AI judge, scoring)
- MLflow-compatible REST API (experiments, runs, models, versions)

---

## 2. Actors and Roles

| Actor | Role | Permissions |
|---|---|---|
| **ML Engineer** | Creates experiments, logs runs, registers models | `read:ml`, `write:ml` |
| **Data Scientist** | Runs evaluations, monitors drift, analyzes results | `read:ml` |
| **Platform Admin** | Manages deployments, approves production, rollbacks | `write:ml`, admin |
| **MLflow Client** | Standard Python client interacting via compat API | `write:ml` |
| **Agent Builder** | Defines and evaluates AI agents | `write:ml`, `execute:ml` |

---

## 3. Screen Mockups

### 3.1 Model Drift Monitoring Dashboard

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ☰  Model Drift Monitoring                              [🔄 Refresh]     │
│ Track feature drift, prediction distribution shifts, and model health   │
│──────────────────────────────────────────────────────────────────────────│
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────┐ │
│ │ Total Deployments│ │ Models w/ Drift  │ │ Healthy Models   │ │ Alerts (24h) │ │
│ │       12         │ │       3 ⚠️       │ │       9 ✅       │ │      7 🔔    │ │
│ └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────┘ │
│──────────────────────────────────────────────────────────────────────────│
│ Drift Overview                                    12 deployments         │
│──────────────────────────────────────────────────────────────────────────│
│ Model Name      │ Version │ Endpoint         │ Status  │ Last Check │ Drifted│
│─────────────────│─────────│──────────────────│─────────│────────────│────────│
│ churn-predictor │ v3      │ /predict/churn   │ 🟡 drift│ 2m ago     │   3    │
│ fraud-detector  │ v7      │ /predict/fraud   │ 🔴 crit │ 5m ago     │   6    │
│ recommender     │ v2      │ /predict/recs    │ 🟢 OK   │ 1m ago     │   0    │
│ price-optimizer │ v1      │ /predict/price   │ 🟢 OK   │ 3m ago     │   0    │
│                 │         │                  │         │            │[Details]│
│                 │         │                  │         │            │[Ack]   │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Drift Detail Slide-In Panel

```
┌──────────────────────────────────────────────────────────────┐
│ churn-predictor v3  [🟡 drifted] [/predict/churn]    [✕]    │
│──────────────────────────────────────────────────────────────│
│ Last Check: 2m ago    │ Features Drifted: 3  │ Status: drift │
│──────────────────────────────────────────────────────────────│
│                                                              │
│ FEATURE DRIFT                                                │
│ ┌──────────────┬─────────┬────────┬─────────┬──────────────┐│
│ │ Feature      │ Metric  │ Value  │Threshold│ Status       ││
│ │──────────────│─────────│────────│─────────│──────────────││
│ │ age          │ KS      │ 0.1523 │ 0.1000  │ ▓▓▓▓▓▓░░ 🟡 ││
│ │ income       │ KS      │ 0.0891 │ 0.1000  │ ▓▓▓▓▓░░░ 🟢 ││
│ │ tenure       │ KS      │ 0.2104 │ 0.1000  │ ▓▓▓▓▓▓▓░ 🔴 ││
│ │ plan_type    │ Chi²    │ 12.34  │ 0.05    │ ▓▓▓▓▓▓▓▓ 🔴 ││
│ └──────────────┴─────────┴────────┴─────────┴──────────────┘│
│                                                              │
│ PREDICTION DISTRIBUTION                                      │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ ▓▓▓▓▓▓▓▓▓░░░  Training                                  ││
│ │ ░░░▓▓▓▓▓▓▓▓▓  Current                                   ││
│ │  Low  ────────────────────────────  High                 ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ LATENCY OVER TIME                                            │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ p99 ─── ─ ─ ─ ── ─ ─ ────                               ││
│ │ p95 ──── ─ ─── ─── ────                                  ││
│ │ p50 ───────────────────                                  ││
│ │ Time ─────────────────────────────→                      ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ ALERT HISTORY                                                │
│ ┌─ 🔴 critical ────────────────────────────────────────────┐│
│ │ Feature 'tenure' KS=0.2104 > 0.1 threshold              ││
│ │ 5 minutes ago                                            ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ [Acknowledge Drift]  [Close]                                 │
└──────────────────────────────────────────────────────────────┘
```

### 3.3 Agent Definitions Table

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ☰  Agent Control Center                   [● Live] [+ New Agent]        │
│ Define, test, and evaluate AI agents with MCP tool access               │
│──────────────────────────────────────────────────────────────────────────│
│ [Definitions]  [Live Sessions]  [Evaluations]                           │
│──────────────────────────────────────────────────────────────────────────│
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ Name            │ Model                │ Tools │ Status │ Created   │ │
│ │─────────────────│──────────────────────│───────│────────│───────────│ │
│ │ Sales Analyst   │ openai/gpt-oss-120b  │ 12    │ active │ 3d ago    │ │
│ │ Data Explorer   │ llama-3.3-70b        │ 8     │ active │ 1w ago    │ │
│ │ Scraper Agent   │ gpt-4o               │ 15    │ draft  │ 2d ago    │ │
│ │ Compliance Bot  │ claude-sonnet-4      │ 6     │ active │ 5d ago    │ │
│ │                 │                      │       │[Edit]  │[Delete]   │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Functional Requirements

### 4.1 Experiment Tracking

| FR-ID | Requirement | Priority | Ref |
|---|---|---|---|
| FR-ML-001 | System shall create experiments with name, description, tags, and artifact_location | P0 | `models.py:15-28` |
| FR-ML-002 | System shall log run parameters (hyperparameters), metrics, and tags | P0 | `api.py:94-135` |
| FR-ML-003 | System shall search experiments by name filter with pagination | P1 | `mlflow_api.py:305-352` |
| FR-ML-004 | System shall search runs with filter expressions (status, tags, params) and ordering | P1 | `mlflow_api.py:488-538` |
| FR-ML-005 | System shall log metrics/params/tags individually and in batch (log_batch) | P1 | `mlflow_api.py:558-662` |

### 4.2 Model Registry

| FR-ID | Requirement | Priority | Ref |
|---|---|---|---|
| FR-ML-010 | System shall register models with name, description, and tags | P0 | `models.py:97-109` |
| FR-ML-011 | System shall create versioned model entries linked to runs | P0 | `models.py:112-146` |
| FR-ML-012 | System shall enforce stage transitions: none→staging→production→archived | P0 | `api.py:226-273` |
| FR-ML-013 | System shall require approval for production deployment | P0 | `api.py:250-269` |
| FR-ML-014 | System shall support deployment rollback to previous version | P0 | `api.py:635-720` |

### 4.3 Model Serving

| FR-ID | Requirement | Priority | Ref |
|---|---|---|---|
| FR-ML-020 | System shall serve real-time predictions via named endpoints | P0 | `api.py:494-529` |
| FR-ML-021 | System shall support batch predictions via Temporal workflow | P0 | `api.py:532-565` |
| FR-ML-022 | System shall load models from local FS, MinIO URIs, or content-addressable store | P0 | `serving.py:238-273` |
| FR-ML-023 | System shall cache loaded models in an LRU cache (max 10) | P1 | `serving.py:30-73` |
| FR-ML-024 | System shall support pickle (.pkl), joblib (.joblib), and ONNX (.onnx) formats | P1 | `serving.py:81-120` |
| FR-ML-025 | System shall record per-minute serving metrics (latency p50/p95/p99, throughput, error rate) | P1 | `serving.py:486-525` |

### 4.4 Drift Monitoring

| FR-ID | Requirement | Priority | Ref |
|---|---|---|---|
| FR-ML-030 | System shall detect numeric feature drift via two-sample Kolmogorov-Smirnov test | P0 | `drift.py:92-153` |
| FR-ML-031 | System shall detect categorical feature drift via chi-square test | P0 | `drift.py:155-219` |
| FR-ML-032 | System shall detect prediction drift via Population Stability Index (PSI) | P0 | `drift.py:254-342` |
| FR-ML-033 | System shall persist drift reports with feature name, metric, value, threshold, and is_drifted flag | P0 | `drift.py:403-455` |
| FR-ML-034 | System shall send notifications when drift is detected | P1 | `drift.py:435-455` |
| FR-ML-035 | System shall generate comprehensive drift reports for deployments | P1 | `drift.py:346-401` |

### 4.5 Agent Definition & Evaluation

| FR-ID | Requirement | Priority | Ref |
|---|---|---|---|
| FR-ML-040 | System shall define agents with system_prompt, model, temperature, max_tokens, tools, and guardrails | P0 | `models.py:182-221` |
| FR-ML-041 | System shall evaluate agents with test cases using an AI judge model | P0 | `api.py:896-963` |
| FR-ML-042 | System shall compute overall_score (0.0–1.0) and pass/fail counts | P0 | `api.py:949-955` |
| FR-ML-043 | Agent guardrails shall support: max_queries_per_session, blocked_tables, max_sql_rows, blocked_tools, require_approval, cost_limit_usd | P1 | `view-agents.ts:774` |

---

## 5. Data Models

### 5.1 Experiment

**Table:** `ml_experiment` — `models.py:15-28`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUIDField | PK | Experiment identifier |
| `tenant_id` | CharField(128) | indexed | Multi-tenant isolation |
| `name` | CharField(255) | indexed, unique per tenant | Experiment name |
| `description` | TextField | blank | Description |
| `tags` | JSONField | default=dict | Key-value tags |
| `artifact_location` | CharField(512) | blank | Storage path for artifacts |

**Unique constraint:** `(tenant_id, name)`

### 5.2 Run

**Table:** `ml_run` — `models.py:31-67`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUIDField | PK | Run identifier |
| `tenant_id` | CharField(128) | indexed | Multi-tenant |
| `experiment` | FK → Experiment | CASCADE | Parent experiment |
| `name` | CharField(255) | blank | Run name |
| `status` | CharField(20) | indexed, choices: running/finished/failed/killed | Run status |
| `params` | JSONField | default=dict | Hyperparameters |
| `metrics` | JSONField | default=dict | Evaluation metrics |
| `tags` | JSONField | default=dict | Run-level tags |
| `started_at` | DateTimeField | auto_now_add | Start timestamp |
| `ended_at` | DateTimeField | nullable | End timestamp |

**Indexes:** `(experiment_id, status)`, `(tenant_id, -started_at)`

### 5.3 RunArtifact

**Table:** `ml_run_artifact` — `models.py:70-94`

| Field | Type | Description |
|---|---|---|
| `run` | FK → Run | Parent run |
| `name` | CharField(255) | Artifact name |
| `artifact_type` | CharField(50) | model/dataset/image/metric/log/other |
| `storage_path` | CharField(512) | Storage location |
| `size_bytes` | BigIntegerField | File size |

### 5.4 RegisteredModel

**Table:** `ml_registered_model` — `models.py:97-109`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUIDField | PK | Model identifier |
| `tenant_id` | CharField(128) | indexed | Multi-tenant |
| `name` | CharField(255) | indexed, unique per tenant | Model name |
| `description` | TextField | blank | Description |
| `tags` | JSONField | default=dict | Model-level tags |

### 5.5 ModelVersion

**Table:** `ml_model_version` — `models.py:112-146`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `registered_model` | FK → RegisteredModel | CASCADE | Parent model |
| `version` | PositiveIntegerField | unique per model | Version number |
| `stage` | CharField(20) | indexed, choices: none/staging/production/archived | Lifecycle stage |
| `status` | CharField(20) | default="ready" | Status |
| `run` | FK → Run | SET_NULL, nullable | Linked experiment run |
| `storage_path` | CharField(512) | blank | Artifact storage path |
| `metrics` | JSONField | default=dict | Version metrics |
| `description` | TextField | blank | Description |

### 5.6 ModelEndpoint

**Table:** `ml_model_endpoint` — `models.py:149-179`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `name` | CharField(255) | indexed | Endpoint name |
| `model_version` | FK → ModelVersion | SET_NULL, nullable | Deployed version |
| `status` | CharField(20) | indexed, choices: active/inactive | Endpoint status |
| `config` | JSONField | default=dict | Config (timeout_ms, max_batch_size) |
| `endpoint_path` | CharField(255) | blank | Generated path |
| `invocation_count` | PositiveIntegerField | default=0 | Total invocations |
| `avg_latency_ms` | FloatField | default=0.0 | Exponential moving average |

### 5.7 DriftReport

**Table:** `ml_drift_report` — `models.py:274-338`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `deployment` | FK → ModelEndpoint | CASCADE | Target deployment |
| `tenant_id` | CharField(128) | indexed | Multi-tenant |
| `feature_name` | CharField(255) | indexed | Feature being tested |
| `drift_metric` | CharField(50) | | ks_statistic / chi_square / psi |
| `drift_value` | FloatField | | Computed metric value |
| `threshold` | FloatField | | Threshold for flagging |
| `is_drifted` | BooleanField | indexed | True if value > threshold |
| `details` | JSONField | default=dict | p-values, bin counts, sample sizes |
| `timestamp` | DateTimeField | auto_now_add, indexed | Measurement time |

**Indexes:** `(deployment, -timestamp)`, `(tenant_id, is_drifted)`

### 5.8 ServingMetric

**Table:** `ml_serving_metric` — `models.py:341-394`

| Field | Type | Description |
|---|---|---|
| `deployment` | FK → ModelEndpoint | Target deployment |
| `timestamp` | DateTimeField | Minute-granularity bucket |
| `latency_p50` | FloatField | Median latency (ms) |
| `latency_p95` | FloatField | 95th percentile (ms) |
| `latency_p99` | FloatField | 99th percentile (ms) |
| `throughput_rps` | FloatField | Requests per second |
| `error_rate` | FloatField | Error fraction (0.0–1.0) |
| `request_count` | PositiveIntegerField | Total requests in bucket |

### 5.9 AgentDefinition

**Table:** `ml_agent_definition` — `models.py:182-221`

| Field | Type | Description |
|---|---|---|
| `name` | CharField(255) | Agent name, unique per tenant |
| `description` | TextField | Description |
| `status` | CharField(20) | draft/active/archived |
| `system_prompt` | TextField | System prompt |
| `model_provider` | CharField(100) | groq/openai/anthropic/ollama |
| `model_name` | CharField(255) | Model identifier |
| `temperature` | FloatField | Default 0.1 |
| `max_tokens` | IntegerField | Default 4096 |
| `tools` | JSONField | MCP tool name list |
| `guardrails` | JSONField | Safety rules dict |
| `metadata` | JSONField | Additional metadata |

### 5.10 AgentEvaluation

**Table:** `ml_agent_evaluation` — `models.py:224-268`

| Field | Type | Description |
|---|---|---|
| `agent` | FK → AgentDefinition | Parent agent |
| `name` | CharField(255) | Evaluation name |
| `status` | CharField(20) | pending/running/completed |
| `test_cases` | JSONField | List of {input, expected, tools_used} |
| `results` | JSONField | List of {input, output, score, judge_notes} |
| `overall_score` | FloatField | 0.0–1.0 aggregate score |
| `judge_model` | CharField(255) | AI judge model identifier |
| `run_count` | PositiveIntegerField | Total runs |
| `passed_count` | PositiveIntegerField | Passed runs |

---

## 6. API Endpoints

### 6.1 Native ML API (`ml_router`)

| Method | Path | Auth | Description | Ref |
|---|---|---|---|---|
| GET | `/ml/experiments` | read:* | List experiments | `api.py:31-46` |
| POST | `/ml/experiments` | write:ml | Create experiment | `api.py:49-59` |
| GET | `/ml/experiments/{id}` | read:* | Get experiment + runs | `api.py:62-88` |
| POST | `/ml/experiments/{id}/runs` | write:ml | Create run | `api.py:94-112` |
| PUT | `/ml/runs/{id}/metrics` | write:ml | Update run metrics | `api.py:115-135` |
| GET | `/ml/experiments/{id}/runs` | read:* | List experiment runs | `api.py:318-346` |
| GET | `/ml/models` | read:* | List registered models | `api.py:141-158` |
| POST | `/ml/models` | write:ml | Register model | `api.py:161-171` |
| GET | `/ml/models/{id}` | read:* | Get model + versions | `api.py:174-198` |
| POST | `/ml/models/{id}/versions` | write:ml | Create version | `api.py:201-223` |
| PUT | `/ml/model-versions/{id}/stage` | write:ml | Transition stage | `api.py:226-273` |
| GET | `/ml/models/{id}/versions` | read:* | List versions | `api.py:349-378` |
| POST | `/ml/models/{id}/deploy` | write:ml | Deploy model | `api.py:381-454` |
| GET | `/ml/endpoints` | read:* | List endpoints | `api.py:279-297` |
| POST | `/ml/endpoints` | write:ml | Create endpoint | `api.py:300-315` |
| GET | `/ml/endpoints/{id}/metrics` | read:* | Endpoint metrics | `api.py:457-488` |
| POST | `/ml/predict/{name}` | write:ml | Real-time prediction | `api.py:494-529` |
| POST | `/ml/predict-batch/{name}` | write:ml | Batch prediction | `api.py:532-565` |
| GET | `/ml/deployments/{id}/metrics` | read:* | Serving metrics | `api.py:571-607` |
| GET | `/ml/deployments/{id}/drift` | read:* | Drift report | `api.py:610-632` |
| POST | `/ml/deployments/{id}/rollback` | write:ml | Rollback deployment | `api.py:635-720` |
| GET | `/ml/agents` | read:ml | List agents | `api.py:732-749` |
| POST | `/ml/agents` | write:ml | Create agent | `api.py:752-770` |
| GET | `/ml/agents/{id}` | read:ml | Get agent + evals | `api.py:773-804` |
| PUT | `/ml/agents/{id}` | write:ml | Update agent | `api.py:807-831` |
| DELETE | `/ml/agents/{id}` | write:ml | Delete agent | `api.py:834-845` |
| POST | `/ml/agents/{id}/evaluations` | write:ml | Create evaluation | `api.py:851-871` |
| GET | `/ml/agents/{id}/evaluations` | read:ml | List evaluations | `api.py:874-893` |
| POST | `/ml/evaluations/{id}/run` | execute:ml | Run evaluation | `api.py:896-963` |

---

## 7. MLflow Compatibility Matrix

The `mlflow_api.py` (859 lines) provides full MLflow Tracking Server API compatibility:

### 7.1 Endpoint Mapping

| MLflow API Endpoint | Voyant Endpoint | Status | Ref |
|---|---|---|---|
| `POST /api/2.0/mlflow/experiments/create` | `POST /mlflow/experiments/create` | ✅ Full | `mlflow_api.py:258-278` |
| `GET /api/2.0/mlflow/experiments/get` | `GET /mlflow/experiments/get` | ✅ Full | `mlflow_api.py:281-302` |
| `GET /api/2.0/mlflow/experiments/search` | `GET /mlflow/experiments/search` | ✅ Full | `mlflow_api.py:305-352` |
| `POST /api/2.0/mlflow/experiments/update` | `POST /mlflow/experiments/update` | ✅ Full | `mlflow_api.py:355-384` |
| `POST /api/2.0/mlflow/experiments/delete` | `POST /mlflow/experiments/delete` | ✅ Full | `mlflow_api.py:387-401` |
| `POST /api/2.0/mlflow/runs/create` | `POST /mlflow/runs/create` | ✅ Full | `mlflow_api.py:407-431` |
| `GET /api/2.0/mlflow/runs/get` | `GET /mlflow/runs/get` | ✅ Full | `mlflow_api.py:434-446` |
| `POST /api/2.0/mlflow/runs/update` | `POST /mlflow/runs/update` | ✅ Full | `mlflow_api.py:449-485` |
| `POST /api/2.0/mlflow/runs/search` | `POST /mlflow/runs/search` | ✅ Full | `mlflow_api.py:488-538` |
| `POST /api/2.0/mlflow/runs/delete` | `POST /mlflow/runs/delete` | ✅ Full | `mlflow_api.py:541-555` |
| `POST /api/2.0/mlflow/runs/log-metric` | `POST /mlflow/runs/log-metric` | ✅ Full | `mlflow_api.py:558-584` |
| `POST /api/2.0/mlflow/runs/log-parameter` | `POST /mlflow/runs/log-parameter` | ✅ Full | `mlflow_api.py:587-611` |
| `POST /api/2.0/mlflow/runs/log-batch` | `POST /mlflow/runs/log-batch` | ✅ Full | `mlflow_api.py:614-662` |
| `POST /api/2.0/mlflow/registered-models/create` | `POST /mlflow/registered-models/create` | ✅ Full | `mlflow_api.py:668-688` |
| `GET /api/2.0/mlflow/registered-models/get` | `GET /mlflow/registered-models/get` | ✅ Full | `mlflow_api.py:691-702` |
| `GET /api/2.0/mlflow/registered-models/search` | `GET /mlflow/registered-models/search` | ✅ Full | `mlflow_api.py:705-745` |
| `POST /api/2.0/mlflow/model-versions/create` | `POST /mlflow/model-versions/create` | ✅ Full | `mlflow_api.py:751-785` |
| `GET /api/2.0/mlflow/model-versions/get` | `GET /mlflow/model-versions/get` | ✅ Full | `mlflow_api.py:788-814` |
| `POST /api/2.0/mlflow/model-versions/update` | `POST /mlflow/model-versions/update` | ✅ Full | `mlflow_api.py:817-859` |

### 7.2 MLflow Client Usage

```python
import mlflow

# Point MLflow client to Voyant
mlflow.set_tracking_uri("http://voyant-host/mlflow")

# Works natively
mlflow.set_experiment("my-experiment")
with mlflow.start_run():
    mlflow.log_param("learning_rate", 0.01)
    mlflow.log_metric("accuracy", 0.95)
    mlflow.sklearn.log_model(model, "model")
```

### 7.3 Serialization Conventions

| Aspect | MLflow Convention | Voyant Implementation |
|---|---|---|
| Timestamps | Epoch milliseconds | `_ts_ms()` helper (`mlflow_api.py:36-41`) |
| Status | UPPERCASE string | Status map: RUNNING→running, FINISHED→finished (`mlflow_api.py:69-74`) |
| Stages | Title case | Stage map: None→none, Staging→staging (`mlflow_api.py:136-140`) |
| Tags | `[{key, value}]` list | `_mlflow_tags_to_dict()` (`mlflow_api.py:172-176`) |
| Pagination | `page_token` (opaque) | Offset-based string token (`mlflow_api.py:336-341`) |
| Filters | `name = 'value'`, `LIKE '%v%'` | `_parse_filter()` and `_parse_run_filter()` (`mlflow_api.py:179-252`) |

---

## 8. Model Serving Engine

### 8.1 Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                   ModelServingEngine                           │
│                   (serving.py:156-542)                        │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  load_model(version_id)          predict(endpoint_id, data)   │
│       │                                │                      │
│       ▼                                ▼                      │
│  ┌─────────┐    ┌──────────┐    ┌───────────┐                │
│  │ ModelVer │───▶│ Fetch    │───▶│ LRU Cache │───▶ predict() │
│  │ (DB)     │    │ Artifact │    │ (10 max)  │    transform()│
│  └─────────┘    └──────────┘    └───────────┘                │
│                        │                                      │
│                   ┌────┴────┐                                 │
│                   ▼         ▼                                 │
│              ┌────────┐ ┌──────────┐                          │
│              │ Local  │ │ MinIO    │                          │
│              │ FS     │ │ minio:// │                          │
│              └────────┘ └──────────┘                          │
│                                                               │
│  Supported Formats:                                           │
│  ┌─────────┐ ┌──────────┐ ┌────────┐                         │
│  │ pickle  │ │ joblib   │ │ ONNX   │                         │
│  │ (.pkl)  │ │ (.joblib)│ │ (.onnx)│                         │
│  └─────────┘ └──────────┘ └────────┘                         │
│                                                               │
│  Post-prediction:                                             │
│  ├── Update endpoint stats (EMA latency)                     │
│  └── Record ServingMetric (per-minute bucket)                │
└───────────────────────────────────────────────────────────────┘
```

### 8.2 Model Cache

- **Type:** `OrderedDict`-based LRU cache (`serving.py:30-73`)
- **Max size:** 10 models (`MAX_CACHED_MODELS`)
- **Thread safety:** `threading.Lock` on all mutations
- **Eviction:** Least-recently-used model evicted when cache full

### 8.3 Prediction Flow

```
POST /ml/predict/{endpoint_name}
  → Lookup ModelEndpoint by name + tenant_id
  → Check endpoint status == ACTIVE
  → Get model_version_id
  → Check LRU cache → miss → load_model()
    → Fetch artifact bytes (local FS / MinIO / content-addressable)
    → Detect format from extension
    → Deserialize (pickle.loads / joblib.load / onnxruntime.InferenceSession)
    → Cache
  → Run prediction (model.predict / model.transform / session.run)
  → Update endpoint stats (invocation_count, avg_latency_ms EMA)
  → Record ServingMetric in per-minute bucket
  → Return {prediction, endpoint_id, model_version_id, latency_ms, timestamp}
```

---

## 9. Drift Detection Engine

### 9.1 Statistical Tests

| Test | Use Case | Threshold | Implementation | Ref |
|---|---|---|---|---|
| **KS Test** | Numeric features | KS > 0.1 | Two-sample Kolmogorov-Smirnov with empirical CDF | `drift.py:92-153` |
| **Chi-Square** | Categorical features | p < 0.05 | Frequency table comparison with regularized incomplete gamma | `drift.py:155-219` |
| **PSI** | Prediction distributions | PSI ≥ 0.2 | Binned distribution comparison (10 bins) | `drift.py:254-342` |

### 9.2 Threshold Configuration

```python
# drift.py:24-26
KS_THRESHOLD = 0.1        # Kolmogorov-Smirnov statistic
PSI_THRESHOLD = 0.2       # Population Stability Index
CHI2_PVALUE_THRESHOLD = 0.05  # Chi-square p-value
```

### 9.3 Drift Report Flow

```
POST /ml/deployments/{id}/drift
  → get_drift_detector().generate_drift_report(deployment_id)
    → Fetch DriftReport records from DB
    → Count features_checked, features_drifted
    → Build per-feature results
    → Return {deployment_id, features_checked, features_drifted,
               overall_drifted, results[], generated_at}
```

### 9.4 Alert Flow

```
drift.check_and_alert(deployment_id, feature_name, drift_result, tenant_id)
  → Create DriftReport record in DB
  → If is_drifted:
      → NotificationService.create(
          type="warning",
          title="Data drift detected: {endpoint.name}",
          message="Feature '{feature_name}' has drifted. Metric: {metric}={value} (threshold: {threshold})"
        )
```

---

## 10. Agent Definition & Evaluation

### 10.1 Agent Model Options

| Provider | Models | Ref |
|---|---|---|
| Groq | openai/gpt-oss-120b, llama-3.3-70b-versatile | `view-agents.ts:133-134` |
| OpenAI | gpt-4o, gpt-4o-mini | `view-agents.ts:135-136` |
| Anthropic | claude-sonnet-4-20250514, claude-haiku-4-20250414 | `view-agents.ts:137-138` |
| Ollama | llama3:70b | `view-agents.ts:139` |

### 10.2 Guardrails Schema

```json
{
  "max_queries_per_session": 50,
  "blocked_tables": ["sensitive_data"],
  "max_sql_rows": 10000,
  "blocked_tools": ["voyant.sources.delete"],
  "require_approval": false,
  "cost_limit_usd": 5.00
}
```

### 10.3 Evaluation Pipeline

```
POST /ml/evaluations/{id}/run
  → Set status = "running", started_at = now
  → For each test_case in evaluation.test_cases:
      → get_intent_engine().generate_plan(input_text, tenant_id)
      → get_intent_engine().execute_plan(plan, tenant_id)
      → Score: 1.0 if exec_result has steps, 0.0 otherwise
      → If score >= 0.8: increment passed_count
  → overall_score = total_score / len(results)
  → Set status = "completed", completed_at = now
  → Return {id, status, overall_score, run_count, passed_count}
```

---

## 11. Integration Points

| System | Integration | Direction | Ref |
|---|---|---|---|
| **MLflow Client** | Drop-in tracking API | Inbound | `mlflow_api.py` |
| **Temporal** | Batch prediction workflows | Outbound | `serving.py:396-428` |
| **MinIO** | Artifact storage (model files) | Outbound | `serving.py:275-309` |
| **Content-Addressable Store** | Hash-based artifact retrieval | Outbound | `serving.py:258-266` |
| **Approval Service** | Production deployment gates | Outbound | `api.py:250-269` |
| **Notification Service** | Drift alerts | Outbound | `drift.py:436-455` |
| **Intent Engine** | Agent evaluation execution | Outbound | `api.py:920-938` |
| **WebSocket** | Live agent session tracking | Bidirectional | `view-agents.ts:194-340` |

---

## 12. Quality Attributes

| Attribute | Target | Evidence |
|---|---|---|
| **MLflow Compatibility** | 100% endpoint coverage | 19/19 endpoints implemented |
| **Prediction Latency** | <100ms (cached model) | LRU cache + `serving.py:349-352` |
| **Drift Detection** | Zero-dependency statistical tests | Pure Python KS, chi-square, PSI |
| **Multi-Tenancy** | Full isolation on all queries | tenant_id filtering |
| **Thread Safety** | Model cache + drift detector | `threading.Lock` on singletons |
| **Stage Safety** | Valid transitions only | `api.py:237-248` validation map |
| **Approval Workflow** | Production gate enforcement | 403 with approval request ID |
| **Rollback** | Automatic version promotion/demotion | `api.py:635-720` |

---

## 13. Implementation References

| Component | File | Key Lines |
|---|---|---|
| All models | `apps/ml_platform/models.py` | 1–394 |
| Native API | `apps/ml_platform/api.py` | 1–963 |
| MLflow compat API | `apps/ml_platform/mlflow_api.py` | 1–859 |
| Serving engine | `apps/ml_platform/serving.py` | 1–542 |
| Drift detector | `apps/ml_platform/drift.py` | 1–472 |
| Drift dashboard | `dashboard/src/views/view-drift.ts` | 1–486 |
| Agent definitions view | `dashboard/src/views/view-agents.ts` | 1–733+ |
