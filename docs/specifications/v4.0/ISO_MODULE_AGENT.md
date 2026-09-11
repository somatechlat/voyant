# ISO Module Specification: Agent & Intent Engine

> **Module:** `apps/intent` + `apps/ml_platform` (AgentDefinition) + `dashboard/src/views/view-agents.ts` + `dashboard/src/views/view-mcp.ts`  
> **Version:** 4.0 — Agent Control Center  
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
7. [Intent Engine Pipeline](#7-intent-engine-pipeline)
8. [MCP Tool Catalog](#8-mcp-tool-catalog)
9. [WebSocket Architecture](#9-websocket-architecture)
10. [Integration Points](#10-integration-points)
11. [Quality Attributes](#11-quality-attributes)
12. [Implementation References](#12-implementation-references)

---

## 1. Module Overview

### 1.1 Purpose

The Agent & Intent Engine module is Voyant's natural-language-to-execution pipeline. It translates human intent into structured MCP tool call plans via LLM with automatic failover, validates plans against security and resource constraints, and executes them against 46+ internal tools. The module also provides a full agent definition, evaluation, and live session management framework.

### 1.2 Key Differentiators

| Differentiator | Description |
|---|---|
| **NL → Execution Pipeline** | Classifies intent, resolves ontology schema, calls LLM with failover, validates, and executes |
| **46+ MCP Tool Catalog** | Full tool coverage: Data Ops, Catalog, Scraper, Ontology, Governance, ML, Streaming |
| **4-Provider Failover Chain** | Groq → OpenAI → Anthropic → MiMo with per-provider timeout |
| **Hardened Security** | SQL injection detection, prompt injection blocking, tenant scope validation, tool allowlist |
| **Rate Limiting** | Redis-backed sliding window: 100 req/hour per tenant, 20 req/min per user |
| **MCP Playground** | Interactive tool testing UI with JSON schema, parameter forms, and response history |
| **Agent Evaluations** | AI judge model evaluates agent quality with test cases and scoring |

### 1.3 Scope

- Natural language intent classification (7 types)
- LLM-based plan generation with failover
- Plan validation (tool names, SQL injection, tenant scope, resource limits)
- Plan execution with wall-clock timeout
- Agent definition CRUD (model, prompt, tools, guardrails)
- Agent evaluation framework (test cases, AI judge, scoring)
- Live session tracking via WebSocket
- MCP Playground for interactive tool testing
- Rate limiting (tenant + user level)

---

## 2. Actors and Roles

| Actor | Role | Permissions |
|---|---|---|
| **End User** | Submits natural language queries | `read:*` |
| **Agent Builder** | Defines agents, assigns tools, runs evaluations | `write:ml`, `execute:ml` |
| **Platform Admin** | Manages intent engine config, clears cache | `write:settings` |
| **AI Agent** | Executes plans against MCP tools | Via tool auth |
| **LLM Providers** | Groq, OpenAI, Anthropic, MiMo | API key auth |

---

## 3. Screen Mockups

### 3.1 Agent Control Center — Definitions

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ☰  Agent Control Center                     [● Live] [+ New Agent]      │
│ Define, test, and evaluate AI agents with MCP tool access               │
│──────────────────────────────────────────────────────────────────────────│
│ [Definitions]  [Live Sessions]  [Evaluations]                           │
│──────────────────────────────────────────────────────────────────────────│
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ Name           │ Model                │ Tools │ Status  │ Created   │ │
│ │────────────────│──────────────────────│───────│─────────│───────────│ │
│ │ Sales Analyst  │ openai/gpt-oss-120b  │ 12    │ active  │ 3d ago    │ │
│ │ Data Explorer  │ llama-3.3-70b        │ 8     │ active  │ 1w ago    │ │
│ │ Scraper Agent  │ gpt-4o               │ 15    │ draft   │ 2d ago    │ │
│ │ Compliance Bot │ claude-sonnet-4      │ 6     │ active  │ 5d ago    │ │
│ │                │                      │       │ [Edit]  │ [Delete]  │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Agent Create/Edit Modal

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [Create Agent]                                                    [✕]   │
│──────────────────────────────────────────────────────────────────────────│
│ ┌─── Left Column ──────────────────┐ ┌─── Right Column ─────────────────┐│
│ │ Name *                           │ │ System Prompt                    ││
│ │ [Sales Analyst_________]         │ │ ┌──────────────────────────────┐ ││
│ │                                  │ │ │ You are a helpful data       │ ││
│ │ Description                      │ │ │ analyst agent with access    │ ││
│ │ [Analyzes sales data_______]    │ │ │ to the company's data        │ ││
│ │                                  │ │ │ warehouse...                 │ ││
│ │ Model                            │ │ │                              │ ││
│ │ [GPT-OSS 120B (Groq) ▾]        │ │ │                              │ ││
│ │                                  │ │ │                              │ ││
│ │ Temperature: [0.1]  Max: [4096] │ │ │                              │ ││
│ │                                  │ │ └──────────────────────────────┘ ││
│ │ Status: [Draft ▾]               │ │                                  ││
│ └──────────────────────────────────┘ └──────────────────────────────────┘│
│──────────────────────────────────────────────────────────────────────────│
│ MCP Tools (12 selected / 62 total)  [Search tools...  ] [All Cat. ▾]    │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ ☑ voyant.sql          [Data Ops]    Execute read-only SQL via Trino │ │
│ │ ☑ voyant.search       [Data Ops]    Semantic vector search          │ │
│ │ ☑ voyant.kpi          [Data Ops]    Run KPI queries                 │ │
│ │ ☐ voyant.tables.list  [Data Ops]    List available tables           │ │
│ │ ☑ scrape.fetch        [Scraper]     Fetch a web page with JS render │ │
│ │ ☐ scrape.ocr          [Scraper]     OCR on images via Tesseract     │ │
│ │ ☑ voyant.ontology.*   [Ontology]    ...                             │ │
│ │ ☐ voyant.quotas.*     [Governance]  ...                             │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
│──────────────────────────────────────────────────────────────────────────│
│ Guardrails (JSON)                                                        │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ {                                                                    │ │
│ │   "max_queries_per_session": 50,                                     │ │
│ │   "blocked_tables": [],                                              │ │
│ │   "max_sql_rows": 10000,                                             │ │
│ │   "require_approval": false,                                         │ │
│ │   "cost_limit_usd": 5.00                                             │ │
│ │ }                                                                    │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
│ [Cancel]                                              [Create Agent]     │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.3 MCP Playground

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ☰  MCP Playground                            Explore and test 62 tools  │
│──────────────────────────────────────────────────────────────────────────│
│ ┌── Tool Tree ──┐ ┌── Tool Detail + Test ──────────────────────────────┐│
│ │ [Search...]   │ │ voyant.sql  [Data Ops]                             ││
│ │               │ │ Execute read-only SQL via Trino                    ││
│ │ All (62)      │ │                                                    ││
│ │ ⚡ Data Ops (5)│ │ PARAMETERS              2 params · 1 required      ││
│ │   └ sql       │ │ ┌────────────────────────────────────────────────┐ ││
│ │   └ search    │ │ │ sql*  string                                  │ ││
│ │   └ kpi       │ │ │ [SELECT * FROM customers LIMIT 10___________] │ ││
│ │ 📚 Catalog (8)│ │ │                                               │ ││
│ │ 🕷️ Scraper(13)│ │ │ limit  integer = 1000                        │ ││
│ │ 🧬 Ontology(12│ │ │ [1000_____________________________________]  │ ││
│ │ 🛡️ Govern. (5)│ │ │                                               │ ││
│ │ 🤖 ML (8)     │ │ │ Raw JSON                                      │ ││
│ │ 📡 Stream (6) │ │ │ { "sql": "SELECT...", "limit": 1000 }        │ ││
│ │               │ │ └────────────────────────────────────────────────┘ ││
│ │               │ │                                                    ││
│ │               │ │ [▶ Run Tool]  ✓ Success · 234ms                   ││
│ │               │ │                                                    ││
│ │               │ │ JSON SCHEMA          │ RESPONSE                   ││
│ │               │ │ {                    │ {                          ││
│ │               │ │  "type": "object",   │  "columns": ["id","name"], ││
│ │               │ │  "properties": {     │  "rows": [["1","Acme"]],   ││
│ │               │ │   "sql": {...}       │  "row_count": 1            ││
│ │               │ │  },                  │ }                          ││
│ │               │ │  "required":["sql"]  │                            ││
│ │               │ │ }                    │ HISTORY (3)                ││
│ │               │ │                      │ ✓ 234ms  10:32:01         ││
│ │               │ │                      │ ✗ 502ms  10:31:45         ││
│ │               │ │                      │ ✓ 189ms  10:30:22         ││
│ └───────────────┘ └────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Functional Requirements

### 4.1 Intent Classification & Plan Generation

| FR-ID | Requirement | Priority | Ref |
|---|---|---|---|
| FR-AG-001 | System shall classify natural language into 7 intent types: query, pipeline, scraper, analyze, ontology, governance, search | P0 | `engine.py:146-472` |
| FR-AG-002 | System shall resolve tenant ontology schema for LLM context (object types, properties, link types) | P0 | `engine.py:474-517` |
| FR-AG-003 | System shall generate structured JSON execution plans via LLM with intent_type, confidence, steps, and assumptions | P0 | `engine.py:519-560` |
| FR-AG-004 | System shall provide keyword-based fallback plan when LLM is unavailable | P0 | `engine.py:677-752` |
| FR-AG-005 | System shall cache generated plans keyed by `tenant_id:intent` when caching is enabled | P1 | `engine.py:535-558` |

### 4.2 LLM Failover

| FR-ID | Requirement | Priority | Ref |
|---|---|---|---|
| FR-AG-010 | System shall try LLM providers in failover order: primary → Groq → OpenAI → Anthropic → MiMo | P0 | `engine.py:78-143` |
| FR-AG-011 | System shall fall back to keyword-based plan when all providers fail | P0 | `engine.py:613-619` |
| FR-AG-012 | System shall load additional providers from the LLMProvider database model | P1 | `engine.py:97-128` |
| FR-AG-013 | System shall request JSON object response format from LLM | P1 | `engine.py:645` |

### 4.3 Plan Validation & Security

| FR-ID | Requirement | Priority | Ref |
|---|---|---|---|
| FR-AG-020 | System shall validate all tool names against the 60+ tool allowlist (VALID_TOOL_NAMES) | P0 | `engine.py:289-360, 820-837` |
| FR-AG-021 | System shall detect SQL injection patterns in plan parameters (6 patterns) | P0 | `engine.py:363-370, 863-883` |
| FR-AG-022 | System shall detect prompt injection attempts in raw intent (8 patterns) | P0 | `engine.py:373-382, 754-771` |
| FR-AG-023 | System shall reject plans that access resources for a different tenant | P0 | `engine.py:850-861` |
| FR-AG-024 | System shall enforce max_tool_calls_per_plan limit (default 10) | P0 | `engine.py:784-793` |
| FR-AG-025 | System shall enforce max_tokens_per_plan limit (default 4096) | P1 | `engine.py:796-807` |
| FR-AG-026 | System shall enforce max_execution_time_seconds limit (default 30s) per plan | P0 | `engine.py:886-910` |

### 4.4 Plan Execution

| FR-ID | Requirement | Priority | Ref |
|---|---|---|---|
| FR-AG-030 | System shall execute plan steps sequentially, routing each tool to the correct handler | P0 | `engine.py:885-948` |
| FR-AG-031 | System shall support 12 prefix-based handler groups (ontology, discovery, quotas, kpi_templates, presets, vector, sources, jobs, artifacts, tables, governance, scrape) | P0 | `engine.py:930-948` |
| FR-AG-032 | System shall stop execution when wall-clock timeout is exceeded and report remaining steps as skipped | P0 | `engine.py:892-910` |

### 4.5 Rate Limiting

| FR-ID | Requirement | Priority | Ref |
|---|---|---|---|
| FR-AG-040 | System shall limit intent requests to 100 per hour per tenant (Redis sliding window) | P0 | `api.py:38-39` |
| FR-AG-041 | System shall limit intent requests to 20 per minute per user | P0 | `api.py:40-41` |
| FR-AG-042 | System shall fail open (allow request) when Redis is unavailable | P1 | `api.py:80-82` |
| FR-AG-043 | System shall return 429 with Retry-After header when rate limit is exceeded | P1 | `api.py:200-210` |

### 4.6 Agent Management

| FR-ID | Requirement | Priority | Ref |
|---|---|---|---|
| FR-AG-050 | System shall create/update/delete agent definitions with model, prompt, tools, and guardrails | P0 | `api.py:732-845` |
| FR-AG-051 | System shall provide 62 MCP tools across 7 categories for agent tool assignment | P0 | `view-agents.ts:53-128` |
| FR-AG-052 | System shall support tool search and category filtering in the tool picker | P1 | `view-agents.ts:460-470` |
| FR-AG-053 | System shall create and run evaluations with test cases and AI judge scoring | P0 | `api.py:851-963` |

---

## 5. Data Models

### 5.1 IntentPlan (in-memory dataclass)

**File:** `engine.py:157-175`

| Field | Type | Description |
|---|---|---|
| `intent_type` | IntentType (StrEnum) | query/pipeline/scraper/analyze/ontology/governance/search/unknown |
| `confidence` | float | 0.0–1.0 confidence score |
| `steps` | list[dict] | Ordered tool calls: [{tool, params}] |
| `assumptions` | list[str] | Plan assumptions |
| `cached` | bool | Whether plan was from cache |
| `raw_llm_response` | str | Raw LLM output for debugging |

### 5.2 IntentType (StrEnum)

**File:** `engine.py:146-154`

```
QUERY, PIPELINE, SCRAPER, ANALYZE, ONTOLOGY, GOVERNANCE, SEARCH, UNKNOWN
```

### 5.3 LLMProviderConfig (dataclass)

**File:** `engine.py:62-71`

| Field | Type | Description |
|---|---|---|
| `name` | str | Provider slug (groq, openai, etc.) |
| `api_url` | str | API base URL |
| `api_key` | str | API key |
| `model` | str | Model identifier |
| `timeout_seconds` | int | Request timeout (default 30) |
| `priority` | int | Lower = tried first |

### 5.4 AgentDefinition (Django ORM)

**Table:** `ml_agent_definition` — `apps/ml_platform/models.py:182-221`

| Field | Type | Description |
|---|---|---|
| `name` | CharField(255) | Agent name, unique per tenant |
| `description` | TextField | Description |
| `status` | CharField(20) | draft/active/archived |
| `system_prompt` | TextField | System prompt |
| `model_provider` | CharField(100) | LLM provider slug |
| `model_name` | CharField(255) | Model identifier |
| `temperature` | FloatField | Default 0.1 |
| `max_tokens` | IntegerField | Default 4096 |
| `tools` | JSONField | MCP tool name list |
| `guardrails` | JSONField | Safety rules dict |
| `metadata` | JSONField | Additional metadata |

### 5.5 AgentEvaluation (Django ORM)

**Table:** `ml_agent_evaluation` — `apps/ml_platform/models.py:224-268`

| Field | Type | Description |
|---|---|---|
| `agent` | FK → AgentDefinition | Parent agent |
| `name` | CharField(255) | Evaluation name |
| `status` | CharField(20) | pending/running/completed |
| `test_cases` | JSONField | [{input, expected, tools_used}] |
| `results` | JSONField | [{input, output, score, judge_notes}] |
| `overall_score` | FloatField | 0.0–1.0 aggregate |
| `judge_model` | CharField(255) | AI judge model |
| `run_count` | PositiveIntegerField | Total runs |
| `passed_count` | PositiveIntegerField | Passed runs |

---

## 6. API Endpoints

### 6.1 Intent Engine API (`intent_router`)

| Method | Path | Auth | Description | Ref |
|---|---|---|---|---|
| POST | `/intent/query` | read:* | Generate execution plan (optionally execute) | `api.py:216-257` |
| POST | `/intent/execute` | read:* | Generate AND execute plan | `api.py:260-290` |
| GET | `/intent/config` | read:* | Get engine configuration | `api.py:293-312` |
| PUT | `/intent/config` | write:settings | Update config at runtime | `api.py:315-360` |
| GET | `/intent/cache/stats` | read:* | Cache statistics | `api.py:363-372` |
| POST | `/intent/cache/clear` | write:settings | Clear plan cache | `api.py:375-383` |

### 6.2 Agent Management API (`ml_router`)

| Method | Path | Auth | Description | Ref |
|---|---|---|---|---|
| GET | `/ml/agents` | read:ml | List all agents | `api.py:732-749` |
| POST | `/ml/agents` | write:ml | Create agent | `api.py:752-770` |
| GET | `/ml/agents/{id}` | read:ml | Get agent + evaluations | `api.py:773-804` |
| PUT | `/ml/agents/{id}` | write:ml | Update agent | `api.py:807-831` |
| DELETE | `/ml/agents/{id}` | write:ml | Delete agent | `api.py:834-845` |
| POST | `/ml/agents/{id}/evaluations` | write:ml | Create evaluation | `api.py:851-871` |
| GET | `/ml/agents/{id}/evaluations` | read:ml | List evaluations | `api.py:874-893` |
| POST | `/ml/evaluations/{id}/run` | execute:ml | Run evaluation | `api.py:896-963` |

### 6.3 MCP Tool Invoke

| Method | Path | Auth | Description | Ref |
|---|---|---|---|---|
| POST | `/mcp/tools/{name}/invoke` | — | Invoke MCP tool directly | `view-mcp.ts:199` |
| POST | `/mcp/invoke` | — | Generic tool invocation | `view-mcp.ts:251` |

### 6.4 WebSocket

| Path | Auth | Description | Ref |
|---|---|---|---|
| `ws://host/ws/agents/{token}` | JWT token | Live agent session events | `view-agents.ts:194-237` |

**Events subscribed:** `agent_events` channel
**Event types:** `agent_definition.created`, `agent_definition.updated`, `agent_definition.deleted`, `agent_session.started`, `agent_session.updated`, `agent_session.ended`, `agent_evaluation.completed`

---

## 7. Intent Engine Pipeline

### 7.1 Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         IntentEngine Pipeline                            │
│                    (engine.py:385-948)                                   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Natural Language Input                                                  │
│  "Show me top 10 customers by revenue"                                  │
│         │                                                                │
│         ▼                                                                │
│  ┌──────────────────┐                                                   │
│  │ 1. Prompt        │  Check 8 injection patterns                       │
│  │    Injection     │  (engine.py:373-382)                              │
│  │    Detection     │  → Reject if detected (PlanValidationError)       │
│  └────────┬─────────┘                                                   │
│           ▼                                                              │
│  ┌──────────────────┐                                                   │
│  │ 2. Intent        │  Keyword-based classification (no LLM)           │
│  │    Classification│  (engine.py:413-472)                              │
│  │                  │  7 types: query|pipeline|scraper|analyze|         │
│  │                  │           ontology|governance|search              │
│  └────────┬─────────┘                                                   │
│           ▼                                                              │
│  ┌──────────────────┐                                                   │
│  │ 3. Schema        │  Load tenant ontology:                            │
│  │    Resolution    │  - ObjectType (max 50)                            │
│  │                  │  - Properties per type                            │
│  │                  │  - LinkType (max 100)                             │
│  │                  │  (engine.py:474-517)                              │
│  └────────┬─────────┘                                                   │
│           ▼                                                              │
│  ┌──────────────────┐                                                   │
│  │ 4. LLM Plan      │  Try providers in order:                          │
│  │    Generation     │  primary → Groq → OpenAI → Anthropic → MiMo    │
│  │                  │  (engine.py:562-654)                              │
│  │                  │                                                   │
│  │  System prompt:  │  Contains full TOOL_CATALOG (46+ tools)          │
│  │  User message:   │  Intent + type + tenant_id + schema              │
│  │  Response:       │  JSON object: {intent_type, confidence,          │
│  │                  │                steps[], assumptions[]}            │
│  └────────┬─────────┘                                                   │
│           │ fail → fallback keyword-based plan (engine.py:677-752)      │
│           ▼                                                              │
│  ┌──────────────────┐                                                   │
│  │ 5. Plan          │                                                   │
│  │    Validation    │                                                   │
│  │                  │                                                   │
│  │  Limits:         │  (engine.py:773-807)                              │
│  │  - Max 10 steps  │  → PlanLimitExceeded if violated                 │
│  │  - Max 4096 tkns │                                                   │
│  │                  │                                                   │
│  │  Security:       │  (engine.py:809-883)                              │
│  │  - Tool allowlist│  → PlanValidationError if violated               │
│  │  - SQL injection │                                                   │
│  │  - Tenant scope  │                                                   │
│  └────────┬─────────┘                                                   │
│           ▼                                                              │
│  ┌──────────────────┐                                                   │
│  │ 6. Plan          │  Sequential execution with timeout                │
│  │    Execution     │  (engine.py:885-948)                              │
│  │                  │                                                   │
│  │  For each step:  │  1. Check wall-clock timeout                     │
│  │                  │  2. Route to handler (_TOOL_HANDLERS or prefix)  │
│  │                  │  3. Record result or error                        │
│  │                  │  4. Continue or break on timeout                  │
│  └────────┬─────────┘                                                   │
│           ▼                                                              │
│  {plan: {...}, execution: {steps: [{step, tool, result}]}}               │
└──────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Tool Handler Routing

**Direct handlers** (`engine.py:951-1113`):

| Tool | Handler | Description |
|---|---|---|
| `voyant.sql` | `_handle_sql` | Trino SQL execution |
| `voyant.search` | `_handle_search` | Hybrid vector search |
| `voyant.ingest` | `_handle_ingest` | Temporal workflow dispatch |
| `voyant.profile` | `_handle_profile` | Profiling workflow |
| `voyant.quality` | `_handle_quality` | Quality workflow |
| `voyant.analyze` | `_handle_analyze` | Full analysis workflow |
| `voyant.kpi` | `_handle_kpi` | KPI query execution |
| `voyant.discover` | `_handle_discover` | Source type detection |
| `voyant.connect` | `_handle_connect` | Source registration |
| `voyant.status` | `_handle_status` | Job status check |
| `voyant.artifact` | `_handle_artifact` | Artifact metadata |

**Prefix-based handlers** (`engine.py:930-948`):

| Prefix | Handler | Coverage |
|---|---|---|
| `voyant.ontology.*` | `_handle_ontology` | 14 ontology tools |
| `voyant.discovery.*` | `_handle_discovery` | 4 discovery tools |
| `voyant.quotas.*` | `_handle_quotas` | 4 governance tools |
| `voyant.kpi_templates.*` | `_handle_kpi_templates` | 4 KPI template tools |
| `voyant.presets.*` | `_handle_presets` | 2 preset tools |
| `voyant.vector.*` | `_handle_vector` | 2 vector tools |
| `voyant.sources.*` | `_handle_sources` | 3 source tools |
| `voyant.jobs.*` | `_handle_jobs` | 2 job tools |
| `voyant.artifacts.*` | `_handle_artifacts` | 1 artifact tool |
| `voyant.tables.*` | `_handle_tables` | 2 table tools |
| `voyant.governance.*` | `_handle_governance` | 1 governance tool |
| `scrape.*` | `_handle_scrape` | 6 scraper tools |

---

## 8. MCP Tool Catalog

### 8.1 Complete Tool Inventory (62 tools, 7 categories)

#### Data Ops (5 tools)

| Tool | Description | Params | Ref |
|---|---|---|---|
| `voyant.sql` | Execute read-only SQL via Trino | sql*, limit=1000 | `view-mcp.ts:26` |
| `voyant.search` | Semantic vector search | query*, limit=5 | `view-mcp.ts:27` |
| `voyant.kpi` | Run KPI queries | kpis*, limit=1000 | `view-mcp.ts:28` |
| `voyant.tables.list` | List warehouse tables | schema | `view-mcp.ts:29` |
| `voyant.tables.columns` | List table columns | table*, schema | `view-mcp.ts:30` |

#### Catalog (9 tools)

| Tool | Description | Ref |
|---|---|---|
| `voyant.sources.list` | List data sources | `view-mcp.ts:32` |
| `voyant.sources.get` | Get source with config | `view-mcp.ts:33` |
| `voyant.sources.delete` | Delete source | `view-mcp.ts:34` |
| `voyant.discover` | Auto-detect source type | `view-mcp.ts:35` |
| `voyant.connect` | Register data source | `view-mcp.ts:36` |
| `voyant.discovery.services.list` | List microservices | `view-mcp.ts:37` |
| `voyant.discovery.services.get` | Get service definition | `view-mcp.ts:38` |
| `voyant.discovery.services.register` | Register microservice | `view-mcp.ts:39` |
| `voyant.discovery.scan` | Scan OpenAPI spec | `view-mcp.ts:40` |
| `voyant.lineage` | Fetch data lineage | `view-mcp.ts:41` |

#### Scraper (16 tools)

| Tool | Description | Ref |
|---|---|---|
| `scrape.fetch` | Fetch web page (JS rendering) | `view-mcp.ts:43` |
| `scrape.deep_archive` | Deep archival scrape | `view-mcp.ts:44` |
| `scrape.extract` | CSS/XPath extraction | `view-mcp.ts:45` |
| `scrape.ocr` | Tesseract OCR | `view-mcp.ts:46` |
| `scrape.parse_pdf` | PDF text/table extraction | `view-mcp.ts:47` |
| `scrape.transcribe` | Whisper transcription | `view-mcp.ts:48` |
| `voyant.scraper.templates.list` | List templates | `view-mcp.ts:49` |
| `voyant.scraper.templates.get` | Get template detail | `view-mcp.ts:50` |
| `voyant.scraper.templates.search` | Search templates | `view-mcp.ts:51` |
| `voyant.scraper.templates.create` | Create template | `view-mcp.ts:52` |
| `voyant.scraper.templates.validate` | Validate template | `view-mcp.ts:53` |
| `voyant.scraper.templates.run` | Run template | `view-mcp.ts:54` |
| `voyant.scraper.templates.generate` | Auto-generate from URL | `view-mcp.ts:55` |
| `voyant.scraper.templates.export` | Export template (JSON/Python) | `view-mcp.ts:56` |
| `voyant.templates.execute` | Execute UPTP template | `view-mcp.ts:57` |

#### Ontology (12 tools)

| Tool | Description | Ref |
|---|---|---|
| `voyant.ontology.types.list` | List object types | `view-mcp.ts:59` |
| `voyant.ontology.types.get` | Get type with properties | `view-mcp.ts:60` |
| `voyant.ontology.types.create` | Create object type | `view-mcp.ts:61` |
| `voyant.ontology.objects.list` | List object instances | `view-mcp.ts:62` |
| `voyant.ontology.objects.create` | Create object instance | `view-mcp.ts:63` |
| `voyant.ontology.objects.get` | Get object with links | `view-mcp.ts:64` |
| `voyant.ontology.objects.update` | Update object (optimistic) | `view-mcp.ts:65` |
| `voyant.ontology.objects.batch_create` | Batch create 1000+ | `view-mcp.ts:66` |
| `voyant.ontology.links.create` | Create link | `view-mcp.ts:67` |
| `voyant.ontology.links.delete` | Delete link | `view-mcp.ts:68` |
| `voyant.ontology.traverse` | Traverse graph (10 hops) | `view-mcp.ts:69` |
| `voyant.ontology.interfaces.list` | List interfaces | `view-mcp.ts:70` |
| `voyant.ontology.actions.execute` | Execute action | `view-mcp.ts:71` |
| `voyant.ontology.functions.run` | Run function | `view-mcp.ts:72` |

#### Governance (5 tools)

| Tool | Description | Ref |
|---|---|---|
| `voyant.governance.schema` | Fetch governance schema | `view-mcp.ts:74` |
| `voyant.quotas.tiers` | List quota tiers | `view-mcp.ts:75` |
| `voyant.quotas.usage` | Get current usage | `view-mcp.ts:76` |
| `voyant.quotas.limits` | Get quota limits | `view-mcp.ts:77` |
| `voyant.quotas.set_tier` | Set tenant tier | `view-mcp.ts:78` |
| `voyant.presets.list` | List preset jobs | `view-mcp.ts:79` |
| `voyant.presets.get` | Get preset job | `view-mcp.ts:80` |
| `voyant.preset` | Create preset job | `view-mcp.ts:81` |

#### ML (8 tools)

| Tool | Description | Ref |
|---|---|---|
| `voyant.ingest` | Start data ingestion | `view-mcp.ts:83` |
| `voyant.profile` | Run data profiling | `view-mcp.ts:84` |
| `voyant.quality` | Run quality checks | `view-mcp.ts:85` |
| `voyant.analyze` | Full analysis pipeline | `view-mcp.ts:86` |
| `voyant.status` | Check job status | `view-mcp.ts:87` |
| `voyant.artifact` | Get artifact metadata | `view-mcp.ts:88` |
| `voyant.artifacts.list` | List job artifacts | `view-mcp.ts:89` |
| `voyant.vector.search` | Hybrid vector search | `view-mcp.ts:90` |
| `voyant.vector.index` | Index into vector store | `view-mcp.ts:91` |

#### Streaming (6 tools)

| Tool | Description | Ref |
|---|---|---|
| `voyant.jobs.list` | List jobs | `view-mcp.ts:93` |
| `voyant.jobs.cancel` | Cancel job | `view-mcp.ts:94` |
| `voyant.kpi_templates.list` | List KPI templates | `view-mcp.ts:95` |
| `voyant.kpi_templates.categories` | List categories | `view-mcp.ts:96` |
| `voyant.kpi_templates.get` | Get template | `view-mcp.ts:97` |
| `voyant.kpi_templates.render` | Render to SQL | `view-mcp.ts:98` |

### 8.2 MCP Playground REST Fallbacks

The MCP Playground (`view-mcp.ts:227-252`) provides REST API fallback mappings when the MCP invoke endpoint is unavailable:

| MCP Tool | REST Fallback |
|---|---|
| `voyant.sql` | `POST /sql/query` |
| `voyant.search` | `POST /search/query` |
| `voyant.tables.list` | `GET /sql/tables` |
| `voyant.sources.list` | `GET /sources` |
| `voyant.jobs.list` | `GET /jobs` |
| `voyant.ontology.types.list` | `GET /ontology/types` |
| `voyant.ingest` | `POST /jobs/ingest` |
| `voyant.profile` | `POST /jobs/profile` |
| `voyant.quality` | `POST /jobs/quality` |
| `voyant.analyze` | `POST /analyze` |
| `voyant.status` | `GET /jobs/{id}` |

---

## 9. WebSocket Architecture

### 9.1 Connection Flow

```
┌──────────────┐                    ┌──────────────┐
│  Dashboard    │                    │  Server      │
│  (LitElement) │                    │  (WS Handler)│
└──────┬───────┘                    └──────┬───────┘
       │                                   │
       │  ws://host/ws/agents/{token}      │
       │──────────────────────────────────▶│
       │                                   │
       │  authenticated                    │
       │◀──────────────────────────────────│
       │                                   │
       │  {action: "subscribe",            │
       │   channels: ["agent_events"]}     │
       │──────────────────────────────────▶│
       │                                   │
       │  subscription.confirmed           │
       │◀──────────────────────────────────│
       │                                   │
       │  {type: "event",                  │
       │   channel: "agent_events",        │
       │   data: {event_type, ...}}        │
       │◀──────────────────────────────────│ (on agent create/update/delete/session)
       │                                   │
```

### 9.2 Reconnection Strategy

**Configuration** (`view-agents.ts:174-177`):

| Parameter | Value | Description |
|---|---|---|
| `maxReconnectAttempts` | 10 | Maximum reconnection attempts |
| `baseDelay` | 1000ms | Base delay for exponential backoff |

**Algorithm** (`view-agents.ts:253-264`):
```
delay = min(baseDelay × 2^attempt, 30000ms)
```

### 9.3 Event Types

| Event Type | Handler | Description |
|---|---|---|
| `agent_definition.created` | `loadAgents()` | Refresh agent list |
| `agent_definition.updated` | `loadAgents()` | Refresh agent list |
| `agent_definition.deleted` | `loadAgents()` | Refresh agent list |
| `agent_session.started` | `_upsertSession()` | Add/update session in list |
| `agent_session.updated` | `_upsertSession()` | Update session metrics |
| `agent_session.ended` | `_upsertSession()` | Mark session ended |
| `agent_evaluation.completed` | `_updateEvaluationScore()` | Update score display |

---

## 10. Integration Points

| System | Integration | Direction | Ref |
|---|---|---|---|
| **Groq** | LLM provider (failover priority 1) | Outbound | `engine.py:100-101` |
| **OpenAI** | LLM provider (failover priority 2) | Outbound | `engine.py:100-101` |
| **Anthropic** | LLM provider (failover priority 3) | Outbound | `engine.py:100-101` |
| **MiMo** | LLM provider (failover priority 4) | Outbound | `engine.py:100-101` |
| **Redis** | Rate limiting (sliding window) | Outbound | `api.py:56-64` |
| **Temporal** | Workflow dispatch for tool execution | Outbound | `engine.py:993-1004` |
| **Trino** | SQL query execution | Outbound | `engine.py:954-963` |
| **Milvus** | Vector search/index | Outbound | `engine.py:966-990` |
| **Ontology Engine** | Object/Link CRUD + traversal | Outbound | `engine.py:1118-1258` |
| **WebSocket** | Live session events | Bidirectional | `view-agents.ts:194-340` |
| **MCP Protocol** | Tool invocation | Inbound | `view-mcp.ts:182-252` |

---

## 11. Quality Attributes

| Attribute | Target | Evidence |
|---|---|---|
| **Intent Classification** | <10ms (keyword-based, no LLM) | `engine.py:413-472` |
| **Plan Generation** | <30s (with LLM timeout) | `engine.py:409-411` |
| **Rate Limit Accuracy** | ±1 request (Redis sliding window) | `api.py:113-154` |
| **Failover Reliability** | 4-provider chain with fallback | `engine.py:78-143` |
| **Security** | 6 SQL injection + 8 prompt injection patterns | `engine.py:363-382` |
| **Tool Coverage** | 62 tools, 7 categories | `view-mcp.ts:24-99` |
| **WS Reconnection** | Exponential backoff, max 10 attempts | `view-agents.ts:253-264` |
| **Plan Validation** | 100% tool name allowlist check | `engine.py:289-360` |
| **Execution Timeout** | Hard wall-clock limit (30s default) | `engine.py:892-910` |

---

## 12. Implementation References

| Component | File | Key Lines |
|---|---|---|
| Intent Engine core | `apps/intent/engine.py` | 1–1457+ |
| Intent API | `apps/intent/api.py` | 1–394 |
| Agent models | `apps/ml_platform/models.py` | 182–268 |
| Agent API | `apps/ml_platform/api.py` | 732–963 |
| Agent dashboard | `dashboard/src/views/view-agents.ts` | 1–733+ |
| MCP Playground | `dashboard/src/views/view-mcp.ts` | 1–473 |
| MCP scraper tools | `apps/mcp/tools_scraper_ops.py` | 1–1295 |
| Valid tool names | `apps/intent/engine.py` | 289–360 |
| SQL injection patterns | `apps/intent/engine.py` | 363–370 |
| Prompt injection patterns | `apps/intent/engine.py` | 373–382 |
| Rate limiter | `apps/intent/api.py` | 30–210 |
| LLM failover chain | `apps/intent/engine.py` | 59–143 |
| Tool handlers | `apps/intent/engine.py` | 951–1457+ |
