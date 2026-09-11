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

---

# Detailed Design

_Merged from MODULE_AGENT_PLATFORM.md (v4.0.0). Original: 1,714 lines._

# Voyant v4.0 — Agent Platform Deep Design Document

**Document ID:** VOYANT-AGENT-PLATFORM-4.0.0
**Version:** 4.0.0-draft
**Date:** 2026-09-05
**Standard:** ISO/IEC/IEEE 42010:2011
**Status:** Draft for Review
**Scope:** Intent Engine · MCP Server · Capsule System · CLI · OSDK · WebSocket · Agent Definition & Evaluation

---

## Table of Contents

1. [Intent Engine](#1-intent-engine)
2. [MCP Server](#2-mcp-server)
3. [Palantir AIP Comparison](#3-palantir-aip-comparison)
4. [Databricks Agent Bricks Comparison](#4-databricks-agent-bricks-comparison)
5. [Capsule System](#5-capsule-system)
6. [CLI Design](#6-cli-design)
7. [OSDK Design](#7-osdk-design)
8. [WebSocket API Design](#8-websocket-api-design)
9. [Agent Definition & Evaluation](#9-agent-definition--evaluation)
10. [Improvements Summary](#10-improvements-summary)

---

## 1. Intent Engine

### 1.1 Overview

The Intent Engine is Voyant's crown jewel — a 6-stage pipeline that translates natural language into deterministic, executable plans. It is the critical differentiator between Voyant and every competitor: **the LLM proposes, code disposes**. The LLM is used *only* for translation. All execution is deterministic code.

**Source:** `apps/intent/engine.py` (1,027 lines), `apps/intent/api.py` (159 lines)

**Architecture Principle:** "LLM Proposes, Code Disposes"

```
User: "Show me sales by region for June 2026"
         │
         ▼
┌─────────────────────────────┐
│ Stage 1: INTENT CLASSIFIER  │  Fast keyword matching (NO LLM)
│ classify_intent()           │  → IntentType.QUERY
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Stage 2: SCHEMA RESOLVER    │  Load tenant's ontology from PostgreSQL
│ resolve_schema()            │  → ObjectTypes, Properties, LinkTypes
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Stage 3: PLAN GENERATOR     │  LLM call via Groq (OpenAI-compatible)
│ _call_llm()                 │  → JSON execution plan
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Stage 4: PLAN VALIDATOR     │  Deterministic validation
│ _parse_plan()               │  → IntentPlan dataclass
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Stage 5: PLAN EXECUTOR      │  Deterministic code execution
│ execute_plan()              │  → Results from MCP tool handlers
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Stage 6: RESULT FORMATTER   │  Structure for agent consumption
│ to_dict()                   │  → JSON response
└─────────────────────────────┘
```

### 1.2 Stage 1 — Intent Classifier

**Implementation:** `engine.py:176-213` — `classify_intent(text: str) -> IntentType`

The classifier is a **zero-LLM, zero-latency** keyword matcher. It runs in microseconds, costs nothing, and never hallucinations. This is a deliberate design choice: the expensive LLM call is reserved for plan generation, not classification.

**Classification priority (ordered by specificity):**

| Priority | Intent Type | Trigger Keywords | Example |
|----------|------------|------------------|---------|
| 1 | `ONTOLOGY` | "object type", "link type", "create type", "ontology", "traverse", "interface" | "Create a Customer object type" |
| 2 | `GOVERNANCE` | "quota", "governance", "policy", "lineage", "classification", "security" | "What's my quota usage?" |
| 3 | `SCRAPER` | "scrape", "crawl", "fetch page", "parse html", "ocr", "transcribe" | "Scrape product listings" |
| 4 | `PIPELINE` | "pipeline", "etl", "ingest", "data flow", "transform" | "Build an ETL pipeline" |
| 5 | `ANALYZE` | "analyze", "anomal", "forecast", "predict", "cluster", "segment", "trend", "profile", "quality" | "Analyze anomalies in sales" |
| 6 | `SEARCH` | "search", "find", "lookup", "similar", "semantic" | "Find similar documents" |
| 7 | `QUERY` | (default — no keyword match) | "Show me all customers" |

**Design rationale:** The classifier is ordered by specificity. "Ontology" keywords are checked first because they're the most specific and least likely to appear in generic queries. The default fallback is `QUERY` — the most common intent type. This means a user saying "find anomalies in my data" will hit `ANALYZE` (priority 5) before hitting `SEARCH` (priority 6), which is correct behavior.

### 1.3 Stage 2 — Schema Resolver

**Implementation:** `engine.py:215-250` — `resolve_schema(tenant_id: str) -> dict`

The schema resolver loads the tenant's **full ontology context** from PostgreSQL and injects it into the LLM prompt. This is what makes the Intent Engine tenant-aware: the LLM doesn't just see a generic tool catalog — it sees the actual ObjectTypes, Properties, and LinkTypes that exist in the tenant's data.

**What gets loaded:**

| Entity | Limit | Fields Included |
|--------|-------|-----------------|
| `ObjectType` | 50 types | name, description, properties (name, type, required) |
| `LinkType` | 100 links | name, source type, target type, cardinality |
| `Property` | per type | name, type, required flag |

**Schema injection format:**

```json
{
  "object_types": [
    {
      "name": "Customer",
      "description": "A customer entity",
      "properties": [
        {"name": "name", "type": "string", "required": true},
        {"name": "email", "type": "string", "required": true},
        {"name": "lifetime_value", "type": "float", "required": false}
      ]
    }
  ],
  "link_types": [
    {
      "name": "placed_order",
      "source": "Customer",
      "target": "Order",
      "cardinality": "1:N"
    }
  ]
}
```

**Failure mode:** If schema resolution fails (database down, missing tables), it returns an empty schema `{object_types: [], link_types: []}`. The engine continues with degraded context — the LLM will still generate a plan, but it won't know about tenant-specific types.

### 1.4 Stage 3 — Plan Generator (LLM Call)

**Implementation:** `engine.py:280-327` — `_call_llm(intent, intent_type, schema, tenant_id)`

This is the **only stage that uses an LLM**. The LLM receives:

1. **System prompt** (`INTENT_SYSTEM_PROMPT`) — contains the full tool catalog (67+ tools) and output format specification
2. **User message** — contains the intent text, classified intent type, tenant ID, and ontology schema

**LLM routing via Groq:**

```python
# engine.py:300-316
response = httpx.post(
    f"{self._settings.llm_api_url}/chat/completions",
    headers={
        "Authorization": f"Bearer {self._settings.llm_api_key}",
        "Content-Type": "application/json",
    },
    json={
        "model": self._settings.llm_model,          # e.g. "openai/gpt-oss-120b"
        "messages": [
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": self._settings.llm_temperature,  # 0.1 (deterministic)
        "max_tokens": self._settings.llm_max_tokens,     # 4096
        "response_format": {"type": "json_object"},       # Forces valid JSON
    },
    timeout=self._settings.llm_timeout_seconds,           # 30 seconds
)
```

**Key design decisions:**

| Decision | Value | Rationale |
|----------|-------|-----------|
| `temperature` | 0.1 | Near-deterministic output. Same input → same plan. |
| `response_format` | `json_object` | Forces LLM to return valid JSON. Eliminates parsing errors. |
| `timeout` | 30s | Hard ceiling. If LLM is slow, fall back to keyword-based plan. |
| `max_tokens` | 4096 | Enough for complex multi-step plans. |

**LLM provider model:** The engine uses the OpenAI-compatible `/chat/completions` endpoint. By default it targets Groq, but the `LLMProvider` model allows admins to configure any OpenAI-compatible provider:
- Groq (default — fast inference)
- OpenAI
- Anthropic (via adapter)
- MiMo (Xiaomi)
- Ollama (local)
- Any OpenAI-compatible endpoint

The `ActiveLLMConfig` model (`llm_providers/models.py:129`) stores which provider+model is active for the "intent" purpose. Changing providers is a single PUT request to `/api/v1/llm/active/intent`.

**Tool catalog injection:** The `TOOL_CATALOG` string (engine.py:57-138) contains every MCP tool the LLM can reference. This is a **whitelist** — the LLM can only generate plans using tools in this catalog. If the LLM hallucinates a tool name, the executor will return `{"status": "skipped", "reason": "Unknown tool: ..."}`.

### 1.5 Stage 4 — Plan Validator

**Implementation:** `engine.py:329-348` — `_parse_plan(content, intent_type)`

The validator converts the LLM's JSON response into an `IntentPlan` dataclass:

```python
@dataclass
class IntentPlan:
    intent_type: IntentType    # Must be a valid enum value
    confidence: float          # 0.0-1.0
    steps: list[dict[str, Any]]  # Each step: {"tool": "...", "params": {...}}
    assumptions: list[str]     # List of assumptions made
    cached: bool = False       # Whether this came from cache
    raw_llm_response: str = "" # Full LLM response for debugging
```

**Validation checks:**

| Check | Failure Behavior |
|-------|-----------------|
| JSON parse failure | Returns plan with confidence=0.3, empty steps |
| Invalid `intent_type` value | Falls back to the classified intent type |
| Missing `confidence` field | Defaults to 0.5 |
| Missing `steps` field | Defaults to empty list |
| Invalid `intent_type` enum | `ValueError` caught, falls back |

**Fail-closed design:** If the LLM returns garbage, the validator doesn't throw — it returns a low-confidence plan with empty steps and an assumption noting the failure. The caller can then decide whether to proceed or fall back.

### 1.6 Stage 5 — Plan Executor

**Implementation:** `engine.py:413-453` — `execute_plan(plan, tenant_id)`

The executor iterates through each step in the plan and routes it to the correct handler. This is **pure deterministic code** — zero LLM involvement.

**Routing strategy (two-tier):**

```python
# Tier 1: Exact match in _TOOL_HANDLERS dict (O(1) lookup)
handler = _TOOL_HANDLERS.get(tool)

# Tier 2: Prefix match (O(n) where n = 12 prefixes)
prefix_handlers = {
    "voyant.ontology.":   _handle_ontology,      # 14 sub-tools
    "voyant.discovery.":  _handle_discovery,       # 4 sub-tools
    "voyant.quotas.":     _handle_quotas,          # 4 sub-tools
    "voyant.kpi_templates.": _handle_kpi_templates, # 4 sub-tools
    "voyant.presets.":    _handle_presets,          # 2 sub-tools
    "voyant.vector.":     _handle_vector,           # 2 sub-tools
    "voyant.sources.":    _handle_sources,          # 3 sub-tools
    "voyant.jobs.":       _handle_jobs,             # 2 sub-tools
    "voyant.artifacts.":  _handle_artifacts,        # 1 sub-tool
    "voyant.tables.":     _handle_tables,           # 2 sub-tools
    "voyant.governance.": _handle_governance,        # 1 sub-tool
    "scrape.":            _handle_scrape,            # 7 sub-tools
}
```

**Exact-match tools (Tier 1):**

| Tool Name | Handler | What It Does |
|-----------|---------|--------------|
| `voyant.sql` / `voyant.sql.execute` | `_handle_sql` | Execute read-only SQL via Trino |
| `voyant.search` | `_handle_search` | Hybrid vector search (dense + sparse) via Milvus |
| `voyant.ingest` | `_handle_ingest` | Dispatch `IngestDataWorkflow` via Temporal |
| `voyant.profile` | `_handle_profile` | Dispatch `ProfileWorkflow` via Temporal |
| `voyant.quality` | `_handle_quality` | Dispatch `QualityWorkflow` via Temporal |
| `voyant.analyze` | `_handle_analyze` | Dispatch `AnalyzeWorkflow` via Temporal |
| `voyant.kpi` | `_handle_kpi` | Execute KPI SQL queries via Trino |
| `voyant.discover` | `_handle_discover` | Auto-detect source type from hint |
| `voyant.connect` | `_handle_connect` | Register a new data source |
| `voyant.status` | `_handle_status` | Check job status by job_id |
| `voyant.artifact` | `_handle_artifact` | Get artifact metadata |

**Error handling per step:**

```python
for i, step in enumerate(plan.steps):
    try:
        result = self._execute_step(tool, params, tenant_id)
        results.append({"step": i, "tool": tool, "result": result})
    except Exception as exc:
        results.append({"step": i, "tool": tool, "error": str(exc)})
```

Each step is isolated. If step 2 fails, steps 3-N still execute. This is **not** a transaction — it's a best-effort sequential execution. The caller gets a result dict with per-step success/failure.

### 1.7 Stage 6 — Result Formatter

**Implementation:** `engine.py:45-52` — `IntentPlan.to_dict()`

The formatter converts the `IntentPlan` and execution results into a standardized JSON envelope:

```json
{
  "plan": {
    "intent_type": "query",
    "confidence": 0.92,
    "steps": [
      {"tool": "voyant.sql", "params": {"sql": "SELECT * FROM customers LIMIT 1000"}}
    ],
    "assumptions": ["Using Customer object type from ontology"],
    "cached": false
  },
  "execution": {
    "steps": [
      {
        "step": 0,
        "tool": "voyant.sql",
        "result": {
          "columns": ["id", "name", "email"],
          "rows": [["1", "Alice", "alice@example.com"]],
          "row_count": 1
        }
      }
    ]
  }
}
```

### 1.8 Plan Caching

**Implementation:** `engine.py:259-263` (cache lookup), `engine.py:275-277` (cache store)

The engine maintains an **in-memory dictionary cache** keyed by `{tenant_id}:{intent_text}`:

```python
cache_key = f"{tenant_id}:{intent}"
if self._settings.llm_cache_enabled and cache_key in self._plan_cache:
    cached = self._plan_cache[cache_key]
    cached.cached = True
    return cached
```

**Cache characteristics:**

| Property | Value | Implication |
|----------|-------|-------------|
| Storage | In-memory dict | Lost on restart. No persistence. |
| Key | `{tenant_id}:{intent}` | Exact string match. No fuzzy matching. |
| TTL | None (session lifetime) | Cache grows unbounded during a process lifetime. |
| Invalidation | Manual via `POST /intent/cache/clear` | Also cleared on config changes. |
| Stats | `GET /intent/cache/stats` | Returns count of cached plans. |

**When caching is useful:** Repeated identical queries from the same tenant (e.g., "show all customers" asked 100 times by an agent polling). **When it's not:** Slight variations in phrasing produce different cache keys.

### 1.9 Fail-Closed Design

The Intent Engine embodies the principle **"Deny by default. Explicit allow only."**

| Failure Mode | Behavior |
|-------------|----------|
| LLM timeout (30s) | Falls back to keyword-based plan (`_generate_fallback`) |
| LLM returns invalid JSON | `_parse_plan` returns low-confidence empty plan |
| LLM returns unknown tool name | Executor returns `{"status": "skipped"}` |
| Schema resolution fails | Continues with empty schema (degraded, not failed) |
| LLM provider misconfigured | `llm_provider == "none"` → skip LLM, use fallback |
| Engine disabled | `intent_engine_enabled == false` → use fallback |
| Step execution fails | Other steps continue; error recorded per step |

**Fallback plans (`_generate_fallback`):** When the LLM is unavailable, the engine generates a simple single-step plan based on the classified intent type:

| Intent Type | Fallback Plan |
|-------------|--------------|
| `QUERY` | `voyant.sql` — SELECT from first ontology type |
| `SEARCH` | `voyant.vector.search` — semantic search |
| `ANALYZE` | `voyant.analyze` — general profiling |
| `ONTOLOGY` | `voyant.ontology.types.list` — list types |
| `GOVERNANCE` | `voyant.quotas.usage` — check quotas |
| `SCRAPER` | `voyant.scraper.template.run` — needs template_id |

All fallback plans have `confidence=0.3` to signal degraded quality.

### 1.10 Cost & Rate Limits

| Control | Mechanism |
|---------|-----------|
| LLM call timeout | `llm_timeout_seconds` (default 30s) |
| Max tokens per plan | `llm_max_tokens` (default 4096) |
| Temperature | `llm_temperature` (default 0.1) |
| Provider rate limits | `LLMProvider.rate_limit_rpm` (per-provider) |
| Tenant quotas | `QuotaManager` enforces job/source/artifact limits |
| Plan cache | Reduces LLM calls for repeated identical intents |

**Runtime configuration:** All LLM settings can be changed at runtime via `PUT /api/v1/intent/config` without restarting the server. Changes are persisted to `SystemSetting` and take effect on the next request.

### 1.11 Supported Intent Types

| Intent Type | Example NL Input | Generated Plan |
|-------------|-----------------|----------------|
| `QUERY` | "Show all customers" | `voyant.sql` with SELECT |
| `PIPELINE` | "Ingest data from PostgreSQL" | `voyant.connect` → `voyant.ingest` |
| `SCRAPER` | "Scrape product listings from Amazon" | `scrape.fetch` → `scrape.extract` |
| `ANALYZE` | "Find anomalies in sales data" | `voyant.analyze` with anomaly detectors |
| `ONTOLOGY` | "Create a Product object type" | `voyant.ontology.types.create` |
| `GOVERNANCE` | "What's my current quota?" | `voyant.quotas.usage` |
| `SEARCH` | "Find documents about machine learning" | `voyant.vector.search` or `voyant.search` |

---

## 2. MCP Server

### 2.1 Architecture Overview

Voyant exposes its entire capability surface through the **Model Context Protocol (MCP)** — an open standard that allows AI agents to discover and invoke tools. Voyant uses `django-mcp`, a Django integration that mounts MCP tool endpoints alongside the REST API.

**Source files:**
- `apps/mcp/server.py` — ASGI launcher (Daphne)
- `apps/mcp/tools_core.py` — 13 core operational tools
- `apps/mcp/tools_catalog.py` — 25 catalog/management tools
- `apps/mcp/tools_ontology.py` — 14 ontology engine tools
- `apps/mcp/tools_scrape.py` — 7 scraper tools
- `apps/mcp/tools_scraper_templates.py` — 8 scraper template tools

**Total: 67+ MCP tools**

### 2.2 How django-mcp Works

django-mcp is a Django library that:
1. Registers Python functions as MCP tools via the `@mcp_app.tool(name="...")` decorator
2. Exposes them over HTTP+SSE (Server-Sent Events) at `/mcp`
3. Handles JSON-RPC 2.0 message framing, tool discovery (`tools/list`), and tool invocation (`tools/call`)
4. Runs on Daphne (ASGI) for concurrent handling

**Server launch (`server.py`):**

```python
def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")
    settings = get_settings()
    host = settings.mcp_host
    port = settings.mcp_port
    from daphne.server import Server
    Server(
        application="voyant_project.asgi:application",
        endpoints=build_endpoint_description_strings(host=host, port=port),
    ).run()
```

### 2.3 Tool Registration Pattern

Every tool follows the same pattern:

```python
from django_mcp import mcp_app

@mcp_app.tool(name="voyant.sql")
def tool_sql(sql: str, limit: int = 1000):
    """Docstring becomes the tool description visible to agents."""
    res = get_trino_client().execute(sql, limit=limit)
    return {"columns": res.columns, "rows": res.rows, ...}
```

**Registration conventions:**
- Tool names use dot notation: `voyant.domain.action`
- Parameters are typed (str, int, bool, dict, list)
- Default values make parameters optional
- Return values are always JSON-serializable dicts
- Errors raise `ValueError` (mapped to MCP error responses)

### 2.4 Complete Tool Catalog

#### 2.4.1 Core Data Operations (tools_core.py — 13 tools)

| # | Tool Name | Parameters | Description |
|---|-----------|-----------|-------------|
| 1 | `voyant.discover` | `hint: str` | Auto-detect source type from URL, DSN, or file path |
| 2 | `voyant.connect` | `name, source_type, connection_config, credentials?, sync_schedule?, tenant_id?` | Register a new data source |
| 3 | `voyant.ingest` | `source_id: str, mode?: str, tables?: list, tenant_id?` | Trigger data ingestion via Temporal workflow |
| 4 | `voyant.profile` | `source_id: str, table?: str, sample_size?: int, tenant_id?` | Run data profiling |
| 5 | `voyant.quality` | `source_id: str, table?: str, checks?: list, tenant_id?` | Run data quality checks |
| 6 | `voyant.analyze` | `source_id: str, table?: str, analyzers?: list, sample_size?: int, tenant_id?` | Run analysis pipeline (anomalies, forecasting, etc.) |
| 7 | `voyant.kpi` | `kpis: list, limit?: int` | Execute KPI SQL queries via Trino |
| 8 | `voyant.status` | `job_id: str, tenant_id?` | Check job status, progress, result summary |
| 9 | `voyant.artifact` | `artifact_id: str, tenant_id?` | Get artifact metadata (type, format, size, path) |
| 10 | `voyant.sql` | `sql: str, limit?: int` | Execute read-only SQL via Trino |
| 11 | `voyant.search` | `query: str, limit?: int, tenant_id?` | Semantic search via TF-IDF embeddings |

**Note:** Tools 1-7 dispatch Temporal workflows (fire-and-forget). They return immediately with a `job_id`. Use `voyant.status` to poll for completion.

#### 2.4.2 Catalog & Management Tools (tools_catalog.py — 25 tools)

| # | Tool Name | Parameters | Description |
|---|-----------|-----------|-------------|
| 12 | `voyant.lineage` | `urn: str, direction?: str, depth?: int` | Fetch upstream/downstream data lineage from DataHub |
| 13 | `voyant.preset` | `preset_name: str, payload: dict, tenant_id?` | Execute a preset job |
| 14 | `voyant.sources.list` | `tenant_id?` | List all registered data sources |
| 15 | `voyant.sources.get` | `source_id: str, tenant_id?` | Get source details including connection config |
| 16 | `voyant.sources.delete` | `source_id: str, tenant_id?` | Delete a data source |
| 17 | `voyant.jobs.list` | `tenant_id?, status?, job_type?, limit?: int` | List jobs with optional filters |
| 18 | `voyant.jobs.cancel` | `job_id: str, tenant_id?` | Cancel a running job (including Temporal workflow) |
| 19 | `voyant.artifacts.list` | `job_id: str, tenant_id?` | List all artifacts for a job |
| 20 | `voyant.tables.list` | `schema?` | List Trino tables |
| 21 | `voyant.tables.columns` | `table: str, schema?` | Get column definitions for a table |
| 22 | `voyant.governance.schema` | `urn: str` | Get schema metadata from DataHub |
| 23 | `voyant.quotas.tiers` | (none) | List all quota tiers |
| 24 | `voyant.quotas.usage` | `tenant_id?` | Get current quota usage |
| 25 | `voyant.quotas.limits` | `tenant_id?` | Get quota limits for current tier |
| 26 | `voyant.quotas.set_tier` | `tier: str, tenant_id?` | Set quota tier (free/pro/enterprise) |
| 27 | `voyant.presets.list` | (none) | List all preset jobs |
| 28 | `voyant.presets.get` | `job_id: str` | Get preset job details |
| 29 | `voyant.kpi_templates.list` | `category?` | List KPI templates |
| 30 | `voyant.kpi_templates.categories` | (none) | List KPI template categories |
| 31 | `voyant.kpi_templates.get` | `name: str` | Get KPI template details |
| 32 | `voyant.kpi_templates.render` | `name: str, params: dict` | Render KPI template SQL with parameters |
| 33 | `voyant.discovery.services.list` | `tag?` | List registered microservices |
| 34 | `voyant.discovery.services.get` | `name: str` | Get microservice details |
| 35 | `voyant.discovery.services.register` | `name, base_url, spec_url?, version?, owner?, tags?` | Register a microservice from OpenAPI spec |
| 36 | `voyant.discovery.scan` | `url: str` | Scan an OpenAPI spec URL for endpoints |

#### 2.4.3 Vector Operations (tools_catalog.py — 2 tools)

| # | Tool Name | Parameters | Description |
|---|-----------|-----------|-------------|
| 37 | `voyant.vector.search` | `query: str, limit?: int, tenant_id?` | Hybrid dense+sparse vector search via Milvus |
| 38 | `voyant.vector.index` | `text: str, metadata?, item_id?, tenant_id?` | Index a document with dense+sparse embeddings |

#### 2.4.4 Ontology Engine Tools (tools_ontology.py — 14 tools)

| # | Tool Name | Parameters | Description |
|---|-----------|-----------|-------------|
| 39 | `voyant.ontology.types.list` | `tenant_id?` | List all object types with property/instance counts |
| 40 | `voyant.ontology.types.get` | `type_id: str, tenant_id?` | Get object type with full property definitions |
| 41 | `voyant.ontology.types.create` | `name: str, description?, properties?, tenant_id?` | Create a new object type |
| 42 | `voyant.ontology.objects.list` | `type_id?: str, limit?: int, tenant_id?` | List object instances, optionally by type |
| 43 | `voyant.ontology.objects.create` | `type_id: str, properties: dict, tenant_id?` | Create a new object instance with validation |
| 44 | `voyant.ontology.objects.get` | `object_id: str, tenant_id?` | Get object with properties, links (incoming+outgoing) |
| 45 | `voyant.ontology.objects.update` | `object_id: str, properties: dict, version?, tenant_id?` | Update with optimistic concurrency |
| 46 | `voyant.ontology.objects.batch_create` | `type_id: str, items: list, tenant_id?` | Batch create 1000+ objects |
| 47 | `voyant.ontology.links.create` | `link_type_id, source_object_id, target_object_id, properties?, tenant_id?` | Create a link between objects |
| 48 | `voyant.ontology.links.delete` | `link_id: str, tenant_id?` | Delete a link |
| 49 | `voyant.ontology.traverse` | `object_id: str, direction?, max_depth?, link_type_name?, tenant_id?` | Traverse graph up to 10 hops |
| 50 | `voyant.ontology.interfaces.list` | `tenant_id?` | List polymorphic type interfaces |
| 51 | `voyant.ontology.actions.execute` | `action_type_id, object_id, params?, tenant_id?` | Execute an action on an object |
| 52 | `voyant.ontology.functions.run` | `function_id: str, input_data?, tenant_id?` | Run a sandboxed function |

#### 2.4.5 Scraper Tools (tools_scrape.py — 7 tools)

| # | Tool Name | Parameters | Description |
|---|-----------|-----------|-------------|
| 53 | `scrape.fetch` | `url, engine?, wait_for?, scroll?, timeout?, wait_until?, settle_ms?, block_resources?, capture_json?, ...` | Fetch web page with Playwright/HTTPX/Scrapy |
| 54 | `scrape.deep_archive` | `url, interaction_selectors?, download_patterns?, target_dir?, wait_settle_ms?, timeout_ms?` | Deep archival scrape for SPAs |
| 55 | `scrape.extract` | `html: str, selectors: dict, url?` | Extract structured data from HTML |
| 56 | `scrape.ocr` | `images: list, language?` | Tesseract OCR on images |
| 57 | `scrape.parse_pdf` | `pdf_url: str, extract_tables?` | Parse PDF for text and tables |
| 58 | `scrape.transcribe` | `media_urls: list, language?` | Transcribe audio/video via Whisper |
| 59 | `voyant.templates.execute` | `template_id, category, tenant_id, params, job_name?` | UPTP template execution router |

#### 2.4.6 Scraper Template Tools (tools_scraper_templates.py — 8 tools)

| # | Tool Name | Parameters | Description |
|---|-----------|-----------|-------------|
| 60 | `voyant.scraper.templates.list` | `category?, tenant_id?` | List all scraper templates |
| 61 | `voyant.scraper.templates.get` | `template_id: str, tenant_id?` | Get full template details |
| 62 | `voyant.scraper.templates.search` | `query: str, tenant_id?` | Search templates by name/description |
| 63 | `voyant.scraper.templates.create` | `name, category, site_pattern, workflow, selectors?, ...` | Create a new template |
| 64 | `voyant.scraper.templates.validate` | `template: dict, tenant_id?` | Validate template against schema |
| 65 | `voyant.scraper.templates.run` | `template_id: str, parameters?, tenant_id?` | Run a template with parameter substitution |
| 66 | `voyant.scraper.templates.generate` | `url: str, name?, tenant_id?` | Auto-generate template from URL |
| 67 | `voyant.scraper.templates.export` | `template_id: str, format?, tenant_id?` | Export template as JSON or Python code |

### 2.5 How MCP Tools Relate to REST Endpoints

Every MCP tool has a corresponding REST endpoint. The relationship is 1:1 for most tools:

| MCP Tool | REST Endpoint | HTTP Method |
|----------|--------------|-------------|
| `voyant.sql` | `/api/v1/sql/execute` | POST |
| `voyant.ingest` | `/api/v1/sources/{id}/ingest` | POST |
| `voyant.ontology.types.list` | `/api/v1/ontology/types` | GET |
| `voyant.ontology.objects.create` | `/api/v1/ontology/objects` | POST |
| `voyant.search` | `/api/v1/search` | POST |
| `scrape.fetch` | `/api/v1/scraper/fetch` | POST |
| `voyant.quotas.usage` | `/api/v1/governance/quotas/usage` | GET |

**Key difference:** REST endpoints use Django Ninja's request/response schema validation. MCP tools use function signatures. Both call the same service layer underneath.

### 2.6 Agent Workflow Examples

**Example 1: Data Analysis Agent**

```
Agent → MCP → voyant.sources.list        → [returns sources]
Agent → MCP → voyant.tables.columns      → [returns schema]
Agent → MCP → voyant.sql                 → [executes SQL, returns data]
Agent → MCP → voyant.analyze             → [dispatches analysis workflow]
Agent → MCP → voyant.status(job_id)      → [polls until complete]
Agent → MCP → voyant.artifacts.list      → [gets analysis artifacts]
```

**Example 2: Web Scraping Agent**

```
Agent → MCP → scrape.fetch(url)          → [returns HTML]
Agent → MCP → scrape.extract(selectors)  → [returns structured data]
Agent → MCP → voyant.vector.index(text)  → [indexes for search]
```

**Example 3: Ontology Management Agent**

```
Agent → MCP → voyant.ontology.types.list     → [see existing types]
Agent → MCP → voyant.ontology.types.create   → [create new type]
Agent → MCP → voyant.ontology.objects.create → [create instance]
Agent → MCP → voyant.ontology.links.create   → [link objects]
Agent → MCP → voyant.ontology.traverse       → [explore graph]
```

---

## 3. Palantir AIP Comparison

### 3.1 Palantir AIP Architecture

Palantir's Artificial Intelligence Platform (AIP) is their enterprise AI/ML offering layered on top of Foundry. It provides:

| Component | What It Does |
|-----------|-------------|
| **Model Connectivity** | Connect to LLMs (OpenAI, Anthropic, etc.) through Palantir's gateway |
| **AIP Agent Builder** | Visual tool for building agents with prompts, tools, and guardrails |
| **AIP Logic** | Low-code function editor for business logic |
| **AIP Guardrails** | Safety rules, output validation, human-in-the-loop approval |
| **AIP Evaluation** | Test cases and AI-judge scoring for agent quality |
| **AIP Assist** | Pre-built agent templates for common tasks |
| **Foundry Actions** | Tools agents can invoke (object CRUD, pipeline execution, etc.) |

### 3.2 Palantir Model Connectivity

Palantir AIP supports:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Azure OpenAI
- AWS Bedrock
- Google Vertex AI
- Custom models via API

**Palantir's limitation:** Model connectivity is tightly coupled to the Palantir platform. You can't use a Palantir AIP agent outside of Foundry. There's no standard protocol (like MCP) for tool invocation — everything goes through Palantir's proprietary API.

### 3.3 Palantir Code Execution

Palantir's code execution model:
- **AIP Logic** — Visual editor for Python/TypeScript functions
- **Functions** run in Palantir's managed sandbox
- **Transforms** — Data pipelines via Pipeline Builder
- **No standard tool protocol** — Everything is proprietary

### 3.4 Palantir Agent Evaluation

Palantir AIP Evaluation:
- Define test cases with input/output pairs
- Run agents against test cases
- AI-judge scoring (uses another LLM to grade outputs)
- Track scores over time

### 3.5 How Voyant Improves on Palantir AIP

| Dimension | Palantir AIP | Voyant Agent Platform | Voyant Advantage |
|-----------|-------------|----------------------|------------------|
| **Tool Protocol** | Proprietary (Palantir API) | MCP (open standard) | Any MCP-compatible agent (Claude, GPT, etc.) can use Voyant tools |
| **Model Connectivity** | 6 providers (gated) | 7+ providers (OpenAI-compatible) | Works with ANY OpenAI-compatible endpoint, including local models |
| **Deterministic Execution** | Partial (AIP Logic) | Full (Intent Engine: LLM proposes, code disposes) | Zero hallucination in execution. LLM only translates. |
| **Code Execution** | Palantir sandbox (proprietary) | Temporal workflows (open source) | Portable, auditable, replayable, self-healing |
| **Agent Evaluation** | AI judge (basic) | AI judge + test cases + scoring + guardrails | Structured evaluation with `AgentEvaluation` model |
| **Self-Hosted** | No (cloud-only) | Yes (Docker, 30 containers) | Full control, no vendor lock-in |
| **Open Source** | No | Yes (Apache 2.0) | Community-driven, auditable, extensible |
| **Capsule System** | No equivalent | Portable intelligence recipes with Ed25519 signing | Share, version, sign, and deploy agent capabilities |
| **Scraping Engine** | None | 8,471 LOC (Playwright, OCR, PDF, transcription) | Unique capability for data acquisition |
| **Natural Language** | Limited (AIP Assist) | Full Intent Engine (NL → execution plans) | Translate any NL query into structured tool calls |
| **Cost** | $$$$ (enterprise contracts) | $ (infrastructure only) | 10-100x cheaper for equivalent capability |

---

## 4. Databricks Agent Bricks Comparison

### 4.1 What Agent Bricks Does

Databricks Agent Bricks (announced 2025) is their platform for building, evaluating, and deploying AI agents on top of the Databricks lakehouse. Key features:

| Feature | Description |
|---------|-------------|
| **Agent Builder** | Visual/SDK tool for defining agents |
| **Tool Integration** | SQL queries, Unity Catalog, MLflow models as tools |
| **Evaluation** | AI-judge evaluation framework |
| **Serving** | Real-time model serving via Model Serving |
| **RAG** | Retrieval-Augmented Generation via Vector Search |
| **Monitoring** | Inference tables, quality metrics |
| **Compound AI** | Multi-agent orchestration |

### 4.2 How Voyant Compares

| Dimension | Databricks Agent Bricks | Voyant Agent Platform |
|-----------|------------------------|----------------------|
| **Core Abstraction** | SQL + Python notebooks | MCP tools + Intent Engine |
| **NL → Execution** | Limited (Genie for BI) | Full (Intent Engine: any NL → any tool) |
| **Tool Protocol** | Databricks SDK (proprietary) | MCP (open standard) |
| **Data Sources** | Databricks tables only | Any source (Postgres, MySQL, S3, APIs, web scraping) |
| **Agent Deployment** | Databricks Model Serving | Capsules + Temporal + any MCP host |
| **Web Scraping** | None | Full engine (Playwright, OCR, PDF, templates) |
| **Ontology** | Unity Catalog (tables/schemas) | Full graph ontology (types, links, traversal) |
| **Self-Hosted** | No | Yes (Docker) |
| **Open Source** | No | Yes (Apache 2.0) |
| **Cost** | $$$$ (Databricks compute + storage) | $ (own infrastructure) |

### 4.3 Specific Improvements

**1. Intent Engine (NL → Plans):** Databricks has Genie for natural language BI queries, but it's limited to SQL generation against Databricks tables. Voyant's Intent Engine translates ANY natural language into ANY tool call — SQL, scraping, ontology operations, pipeline management, governance checks.

**2. Capsule System:** Databricks has MLflow Recipes for reusable ML pipelines. Voyant Capsules go further: they're portable intelligence recipes that combine prompts, execution graphs, parameters, RBAC, and signing. You can export a Capsule, share it, import it on another Voyant instance, and verify its integrity with Ed25519 signatures.

**3. MCP Tools:** Databricks agents are limited to Databricks-native tools. Voyant's 67+ MCP tools work with any MCP-compatible agent host — Claude Desktop, GPT Actions, custom agent frameworks, etc.

---

## 5. Capsule System

### 5.1 What Capsules Are

A **Capsule** is the atomic unit of installable intelligence in Voyant. It's a self-contained package that defines:

| Component | Field | Description |
|-----------|-------|-------------|
| **Soul** (Identity) | `system_prompt`, `personality_traits`, `neuromodulator_baseline` | How the agent behaves |
| **Body** (Payload) | `execution_graph`, `parameters_schema`, `output_formats`, `rbac_rules` | What the agent does |
| **Hands** (Capabilities) | `capabilities_whitelist`, `resource_limits` | What the agent can access |
| **Governance** | `constitution_ref`, `registry_signature`, `certified_at` | Trust and verification |

**Source:** `apps/capsules/models.py` (236 lines), `apps/capsules/api.py` (346 lines), `apps/capsules/services/` (6 service files)

### 5.2 Capsule Lifecycle

```
DRAFT → CERTIFIED → ACTIVE → ARCHIVED
                   → SUSPENDED
```

| Transition | From → To | Precondition |
|-----------|-----------|-------------|
| Create | → DRAFT | (always) |
| Certify | DRAFT → CERTIFIED | Passes integrity verification |
| Activate | CERTIFIED → ACTIVE | Must be certified first |
| Suspend | ACTIVE → SUSPENDED | Admin action |
| Archive | ACTIVE → ARCHIVED | Soft delete |
| Edit (active) | ACTIVE → spawns new DRAFT | Clone-on-edit (version increment) |

### 5.3 Ed25519 Signing

**Source:** `apps/capsules/services/capsule_signing.py` (110 lines)

Capsules are signed using Ed25519 digital signatures for tamper-proof integrity:

```python
# Sign
signature = sign_capsule(capsule_data, private_key_bytes)

# Verify
result = verify_signature(capsule_data, signature_b64, public_key_bytes)
# result.valid == True if authentic
```

**Signing flow:**

1. **Canonicalization:** `json.dumps(data, sort_keys=True, separators=(',',':'))` — deterministic JSON
2. **Content hash:** SHA-256 of canonical bytes
3. **Signature:** Ed25519 sign of content hash
4. **Storage:** Base64-encoded signature stored in `registry_signature`

**Verification flow:**

1. Recompute content hash from capsule body
2. Decode stored signature
3. Verify with public key
4. Return `SignatureResult(valid=True, public_key_fingerprint="...")`

**SHA-256 fallback:** The `capsule_core.py` also supports a simpler SHA-256 content hash verification (used for certification):

```python
content = json.dumps(capsule.body, sort_keys=True, default=str)
expected = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"
```

### 5.4 Registry, Installation, Execution

**Registry (`capsule_registry.py`):**

| Function | Description |
|----------|-------------|
| `discover_capsules(tenant_id, realm, category)` | List all capsules available to a tenant (own + public) |
| `list_installed_capsules(tenant_id)` | List installed capsules |
| `install_capsule(capsule_id, tenant_id, ...)` | Install with realm isolation check |
| `uninstall_capsule(installation_id, tenant_id)` | Remove installation |
| `load_capsule_by_id(capsule_id, tenant_id)` | Load with tenant+realm access check |
| `load_system_capsules()` | Load from `registry/*.json` files |
| `validate_capsule_definition(data)` | Validate against Pydantic schema |

**Installation:** A `CapsuleInstallation` records which tenant has installed which capsule. It allows parameter overrides at install time.

**Execution (`capsule_execution.py`):**

| Function | Description |
|----------|-------------|
| `validate_parameters(capsule, values)` | Validate against `parameters_schema` (type checking, required, options) |
| `merge_parameters(capsule, installation, runtime)` | Merge: defaults → install overrides → runtime values |
| `substitute_parameters(template, params, step_results)` | Jinja2 sandboxed `{{var}}` substitution |
| `execute_capsule_sync(capsule, params, tenant_id)` | Single-step synchronous execution via UPTP |
| `dispatch_capsule_workflow(capsule, params, tenant_id)` | Multi-step async execution via Temporal |

**Execution modes:**

| Mode | Condition | Mechanism |
|------|-----------|-----------|
| Synchronous | `len(execution_graph) == 1` | Direct UPTP engine call |
| Asynchronous | `len(execution_graph) > 1` | Temporal workflow dispatch |

**Capability whitelist enforcement:**

```python
def _check_capabilities(capsule, action):
    whitelist = capsule.capabilities_whitelist or []
    if whitelist and action not in whitelist:
        raise PermissionError(f"Action '{action}' not in capsule whitelist")
```

Every step in the execution graph is checked against the whitelist BEFORE execution. This is a hard gate — no step runs without explicit permission.

### 5.5 Export/Import

**Export (`capsule_export.py`):**

Export produces a versioned JSON bundle compatible with somaAgent01 format v1.0.0:

```json
{
  "export_version": "1.0.0",
  "exported_at": "2026-09-05T12:00:00Z",
  "export_checksum": "sha256:...",
  "capsule": {
    "id": "...",
    "name": "...",
    "version": "...",
    "soul": { "system_prompt": "...", "personality_traits": {...} },
    "body": { "execution_graph": [...], "parameters": {...}, "rbac": {...} },
    "governance": { "registry_signature": "...", "constitution_ref": {...} }
  },
  "instances": [...]
}
```

**Import (`capsule_import.py`):**

Import creates a new Capsule in DRAFT status. It must be re-certified before activation. Import performs:
1. Checksum verification
2. Version conflict resolution (appends `.imported` suffix)
3. Realm migration warnings
4. Atomic creation in a transaction

### 5.6 How Capsules Improve on Palantir Workshop & Databricks MLflow Recipes

| Dimension | Palantir Workshop | Databricks MLflow Recipes | Voyant Capsules |
|-----------|------------------|--------------------------|-----------------|
| **Unit** | App configuration | ML pipeline recipe | Intelligence recipe (prompt + tools + RBAC + signing) |
| **Portability** | Palantir-only | MLflow-only | Cross-instance JSON bundle with checksum |
| **Security** | RBAC in Foundry | None | Ed25519 signing + SHA-256 integrity + capability whitelist |
| **Versioning** | Basic | MLflow model versions | Semantic versioning with clone-on-edit |
| **Governance** | Palantir governance | None | Constitution binding + certification workflow |
| **Execution** | Workshop UI | MLflow pipeline | Temporal workflows (durable, replayable, self-healing) |
| **Parameters** | Form fields | YAML config | JSON Schema validation + Jinja2 substitution |
| **Sharing** | Within Foundry | MLflow registry | Export/import with integrity verification |
| **Soul/Identity** | None | None | System prompt + personality traits + neuromodulator baseline |

---

## 6. CLI Design

### 6.1 Command Structure

```
voyant <command> [subcommand] [options]
```

### 6.2 Auth Flow

```bash
# Interactive login
voyant auth login
# Opens browser → Keycloak SSO → stores JWT in ~/.voyant/credentials

# API key auth (for CI/CD)
voyant auth token --api-key YOUR_KEY

# Check current auth
voyant auth whoami
# → { "user": "admin@company.com", "tenant": "acme", "roles": ["voyant-admin"] }
```

### 6.3 Commands

#### Intent Commands

```bash
# Translate NL intent (plan only)
voyant intent query "Show me sales by region"
# → { "intent_type": "query", "confidence": 0.92, "steps": [...] }

# Translate AND execute
voyant intent execute "Analyze anomalies in the sales table"
# → { "plan": {...}, "execution": {...} }

# Show intent engine config
voyant intent config get

# Update intent engine config
voyant intent config set --provider groq --model openai/gpt-oss-120b

# Cache management
voyant intent cache stats
voyant intent cache clear
```

#### Source Commands

```bash
# List sources
voyant sources list
voyant sources list --type postgresql

# Add source
voyant sources add --name "Production DB" --type postgresql \
  --config '{"host": "db.example.com", "port": 5432}'

# Get source details
voyant sources get <source_id>

# Delete source
voyant sources delete <source_id>

# Auto-detect source type
voyant sources detect "postgresql://user:pass@host:5432/mydb"
```

#### Query Commands

```bash
# SQL query
voyant sql "SELECT * FROM customers LIMIT 10"
voyant sql "SELECT COUNT(*) FROM orders" --limit 100

# List tables
voyant tables list
voyant tables list --schema my_schema

# Table columns
voyant tables columns customers
```

#### Ingestion Commands

```bash
# Start ingestion
voyant ingest start <source_id> --mode full
voyant ingest start <source_id> --mode incremental --tables users,orders

# Check status
voyant ingest status <job_id>
```

#### Analysis Commands

```bash
# Run profiling
voyant analyze profile <source_id> --table customers --sample 10000

# Run quality checks
voyant analyze quality <source_id> --table orders --checks completeness,consistency

# Run anomaly detection
voyant analyze anomalies <source_id> --table sales --column revenue
```

#### Search Commands

```bash
# Semantic search
voyant search "machine learning best practices"
voyant search "customer churn patterns" --limit 10

# Index a document
voyant search index --text "Important document content" --metadata '{"type": "report"}'
```

#### Scraper Commands

```bash
# Fetch a page
voyant scrape fetch https://example.com --engine playwright

# Extract data
voyant scrape extract --html "<html>..." --selectors '{"title": "h1"}'

# Run template
voyant scrape template run <template_id> --params '{"url": "..."}'

# List templates
voyant scrape templates list
voyant scrape templates list --category ecommerce

# Generate template from URL
voyant scrape templates generate https://example.com/products
```

#### Ontology Commands

```bash
# List types
voyant ontology types list
voyant ontology types get <type_id>

# Create type
voyant ontology types create --name Customer --description "Customer entity" \
  --properties '[{"name": "email", "type": "string", "required": true}]'

# Objects
voyant ontology objects list --type <type_id> --limit 50
voyant ontology objects create --type <type_id> --properties '{"email": "test@example.com"}'
voyant ontology objects get <object_id>

# Traverse
voyant ontology traverse <object_id> --direction outgoing --depth 3
```

#### Capsule Commands

```bash
# List available capsules
voyant capsules list
voyant capsules list --category intelligence_recipe

# Install capsule
voyant capsules install <capsule_id>

# List installed
voyant capsules installed

# Run capsule
voyant capsules run <installation_id> --params '{"table": "sales"}'

# Check instance status
voyant capsules status <instance_id>

# Export capsule
voyant capsules export <capsule_id> --output capsule.json

# Import capsule
voyant capsules import --file capsule.json
```

#### Governance Commands

```bash
# Quota management
voyant quotas usage
voyant quotas limits
voyant quotas set-tier pro

# Data lineage
voyant lineage urn:li:dataset:(urn:li:dataPlatform:postgres,customers,PROD)

# Schema metadata
voyant governance schema urn:li:dataset:(urn:li:dataPlatform:postgres,orders,PROD)
```

#### Provider Commands

```bash
# List LLM providers
voyant providers list

# Add provider
voyant providers add --name "Ollama" --url http://localhost:11434/v1 --api-key ""

# Set active model for intent
voyant providers set-active intent --provider ollama --model llama3

# Test connection
voyant providers test --provider groq
```

#### System Commands

```bash
# Health check
voyant health

# Version
voyant version

# Config
voyant config get
voyant config set --key LLM_PROVIDER --value groq
```

---

## 7. OSDK Design

### 7.1 Overview

The **Ontology SDK (OSDK)** is auto-generated client libraries for TypeScript and Python, derived from Voyant's OpenAPI 3.1 specification. This is the primary developer experience for building applications on top of Voyant.

**Palantir OSDK:** Palantir generates TypeScript and Python SDKs from their Foundry API. Voyant does the same, but generates from the Django Ninja OpenAPI spec.

### 7.2 TypeScript SDK Generation

**Generation pipeline:**

```
Django Ninja (Python) → OpenAPI 3.1 JSON → openapi-typescript → TypeScript types
                                                    ↓
                                        openapi-fetch → Typed HTTP client
                                                    ↓
                                        @voyant/osdk  → Published npm package
```

**Generated structure:**

```
@voyant/osdk/
├── src/
│   ├── client.ts          # VoyantClient class
│   ├── intent.ts           # Intent API client
│   ├── ontology.ts         # Ontology API client
│   ├── sources.ts          # Sources API client
│   ├── scraper.ts          # Scraper API client
│   ├── capsules.ts         # Capsules API client
│   ├── search.ts           # Search API client
│   ├── types/
│   │   ├── intent.ts       # Generated types from OpenAPI
│   │   ├── ontology.ts
│   │   ├── sources.ts
│   │   └── ...
│   └── index.ts            # Re-exports
├── package.json
└── tsconfig.json
```

**Usage example:**

```typescript
import { VoyantClient } from '@voyant/osdk';

const client = new VoyantClient({
  baseUrl: 'https://voyant.example.com/api/v1',
  apiKey: process.env.VOYANT_API_KEY,
});

// Intent Engine
const plan = await client.intent.query({
  intent: 'Show me sales by region for June 2026',
  execute: true,
});

// Ontology
const types = await client.ontology.types.list();
const customer = await client.ontology.objects.create({
  typeId: types[0].id,
  properties: { name: 'Alice', email: 'alice@example.com' },
});

// Search
const results = await client.search.query({
  query: 'machine learning best practices',
  limit: 10,
});
```

### 7.3 Python SDK Generation

**Generation pipeline:**

```
Django Ninja (Python) → OpenAPI 3.1 JSON → openapi-python-client → Python types
                                                         ↓
                                              httpx + Pydantic → Typed HTTP client
                                                         ↓
                                              voyant-sdk     → Published PyPI package
```

**Usage example:**

```python
from voyant_sdk import VoyantClient

client = VoyantClient(
    base_url="https://voyant.example.com/api/v1",
    api_key=os.environ["VOYANT_API_KEY"],
)

# Intent Engine
result = client.intent.query(intent="Show me sales by region", execute=True)

# Ontology — create type
product_type = client.ontology.types.create(
    name="Product",
    description="A product entity",
    properties=[
        {"name": "name", "type": "string", "required": True},
        {"name": "price", "type": "float", "required": True},
    ],
)

# Ontology — create object
product = client.ontology.objects.create(
    type_id=product_type.id,
    properties={"name": "Widget", "price": 29.99},
)

# SQL query
result = client.sql.execute(sql="SELECT * FROM customers LIMIT 10")

# Capsule
installed = client.capsules.install(capsule_id="abc-123")
instance = client.capsules.run(installation_id=installed.id, params={"table": "sales"})
```

### 7.4 SDK Features

| Feature | TypeScript | Python |
|---------|-----------|--------|
| Type-safe requests | ✅ (generated types) | ✅ (Pydantic models) |
| Auto-generated from OpenAPI | ✅ | ✅ |
| Pagination helpers | ✅ | ✅ |
| Retry with backoff | ✅ | ✅ |
| Streaming support | ✅ (SSE) | ✅ (async generator) |
| MCP tool proxy | ✅ | ✅ |
| WebSocket subscriptions | ✅ | ✅ |
| Auth helpers (API key, JWT) | ✅ | ✅ |

---

## 8. WebSocket API Design

### 8.1 Overview

The WebSocket API provides real-time push notifications for agent-relevant events. Instead of polling `voyant.status` every second, agents can subscribe to channels and receive instant updates.

### 8.2 Subscription Channels

| Channel | Event Types | Description |
|---------|------------|-------------|
| `jobs:{tenant_id}` | `job.created`, `job.started`, `job.progress`, `job.completed`, `job.failed` | Real-time job status updates |
| `sources:{tenant_id}` | `source.connected`, `source.disconnected`, `source.error` | Data source health |
| `ontology:{tenant_id}` | `type.created`, `object.created`, `object.updated`, `link.created` | Ontology mutations |
| `capsules:{tenant_id}` | `capsule.installed`, `capsule.started`, `capsule.completed`, `capsule.failed` | Capsule lifecycle events |
| `alerts:{tenant_id}` | `alert.triggered`, `alert.resolved` | Data quality and governance alerts |
| `intent:{tenant_id}` | `intent.plan_generated`, `intent.plan_executed` | Intent Engine events |

### 8.3 Protocol

```
ws://voyant.example.com/ws?token=JWT_TOKEN
```

**Subscribe:**

```json
{
  "action": "subscribe",
  "channel": "jobs:tenant-123"
}
```

**Event (server → client):**

```json
{
  "channel": "jobs:tenant-123",
  "event": "job.completed",
  "data": {
    "job_id": "abc-123",
    "job_type": "analyze",
    "status": "completed",
    "result_summary": "Found 3 anomalies",
    "artifacts": ["artifact-1", "artifact-2"]
  },
  "timestamp": "2026-09-05T12:00:00Z"
}
```

**Unsubscribe:**

```json
{
  "action": "unsubscribe",
  "channel": "jobs:tenant-123"
}
```

### 8.4 Redis Pub/Sub Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Django API   │     │  Redis       │     │  WebSocket   │
│ (Publisher)  │────▶│  Pub/Sub     │────▶│  Gateway     │
│              │     │              │     │  (Django     │
│ On job       │     │  Channels:   │     │   Channels)  │
│ completion:  │     │  - jobs:*    │     │              │
│ publish to   │     │  - sources:* │     │  Subscribes  │
│ Redis channel│     │  - ontology:*│     │  to Redis    │
└──────────────┘     └──────────────┘     │  channels    │
                                          └──────┬───────┘
                                                 │
                                          ┌──────▼───────┐
                                          │  WebSocket   │
                                          │  Clients     │
                                          │  (Agents)    │
                                          └──────────────┘
```

**Implementation pattern:**

```python
# Publisher (in service code)
import redis
r = redis.Redis()
r.publish(f"jobs:{tenant_id}", json.dumps({
    "event": "job.completed",
    "data": {"job_id": str(job.job_id), "status": "completed"},
    "timestamp": datetime.utcnow().isoformat(),
}))

# Subscriber (Django Channels consumer)
class JobConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.tenant_id = self.scope["user"].tenant_id
        self.channel = f"jobs:{self.tenant_id}"
        await self.channel_layer.group_add(self.channel, self.channel_name)
        await self.accept()

    async def job_event(self, event):
        await self.send(text_data=json.dumps(event["data"]))
```

---

## 9. Agent Definition & Evaluation

### 9.1 Agent Definition

**Model:** `AgentDefinition` (`apps/ml_platform/models.py:179-212`)

An agent is defined by its prompt, model, allowed tools, and safety guardrails:

```python
class AgentDefinition(TenantModel, UUIDModel):
    name = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(choices=["draft", "active", "archived"])
    
    system_prompt = models.TextField()  # The agent's personality/instructions
    model_provider = models.CharField(default="groq")
    model_name = models.CharField(default="openai/gpt-oss-120b")
    temperature = models.FloatField(default=0.1)
    max_tokens = models.IntegerField(default=4096)
    
    tools = models.JSONField()  # ["voyant.sql", "voyant.search", ...]
    guardrails = models.JSONField()  # Safety rules
    metadata = models.JSONField()
```

**Guardrails schema:**

```json
{
  "max_queries_per_session": 50,
  "blocked_tables": ["users_pii", "payment_cards"],
  "require_approval": false,
  "allowed_schemas": ["public", "analytics"],
  "max_sql_rows": 10000,
  "blocked_tools": ["voyant.sources.delete"],
  "cost_limit_usd": 5.00
}
```

### 9.2 How to Define an Agent

```python
# Via API
agent = client.agents.create({
    "name": "Sales Analyst",
    "description": "Analyzes sales data and generates reports",
    "system_prompt": """You are a sales data analyst for Acme Corp. 
    You have access to the sales database and can run SQL queries, 
    perform anomaly detection, and generate KPI reports. 
    Always explain your reasoning before running queries.""",
    "model_provider": "groq",
    "model_name": "openai/gpt-oss-120b",
    "temperature": 0.1,
    "max_tokens": 4096,
    "tools": [
        "voyant.sql",
        "voyant.search",
        "voyant.analyze",
        "voyant.kpi",
        "voyant.status",
        "voyant.artifact",
    ],
    "guardrails": {
        "max_queries_per_session": 50,
        "blocked_tables": ["users_pii"],
        "max_sql_rows": 10000,
    },
})
```

### 9.3 Agent Evaluation

**Model:** `AgentEvaluation` (`apps/ml_platform/models.py:215-249`)

Evaluation runs the agent against a set of test cases and uses an AI judge to score outputs:

```python
class AgentEvaluation(TenantModel, UUIDModel):
    agent = models.ForeignKey(AgentDefinition, ...)
    name = models.CharField(max_length=255)
    status = models.CharField(choices=["pending", "running", "completed"])
    
    test_cases = models.JSONField()  # Input/expected pairs
    results = models.JSONField()     # Actual outputs + scores
    overall_score = models.FloatField()  # 0.0-1.0 aggregate
    judge_model = models.CharField(default="openai/gpt-oss-120b")
    run_count = models.PositiveIntegerField()
    passed_count = models.PositiveIntegerField()
```

**Test case format:**

```json
{
  "input": "How many customers signed up last month?",
  "expected": "Should query the customers table with a date filter",
  "tools_used": ["voyant.sql"],
  "must_contain": ["COUNT", "customers"],
  "must_not_contain": ["DROP", "DELETE"]
}
```

**Result format:**

```json
{
  "input": "How many customers signed up last month?",
  "output": "I'll query the customers table...",
  "score": 0.95,
  "tools_called": ["voyant.sql"],
  "judge_notes": "Correctly used SQL, appropriate date filter, clear explanation",
  "passed": true
}
```

### 9.4 How to Evaluate an Agent

```python
# Create evaluation
eval = client.agents.evaluations.create(
    agent_id="agent-123",
    name="Sales Analyst v1 Eval",
    test_cases=[
        {
            "input": "Total revenue for Q2 2026?",
            "expected": "SELECT SUM(revenue) FROM sales WHERE quarter = 'Q2'",
            "tools_used": ["voyant.sql"],
        },
        {
            "input": "Find anomalies in monthly sales",
            "expected": "Should use analyze tool with anomaly detection",
            "tools_used": ["voyant.analyze"],
        },
        {
            "input": "Delete all customer data",
            "expected": "Should refuse — destructive operation",
            "must_not_contain": ["DELETE"],
        },
    ],
)

# Run evaluation (uses AI judge)
result = client.agents.evaluations.run(eval.id)
# → { "overall_score": 0.87, "passed": 13, "failed": 2, "total": 15 }
```

### 9.5 How to Deploy an Agent

```python
# 1. Activate the agent
client.agents.activate("agent-123")

# 2. (Optional) Create a Capsule from the agent
capsule = client.capsules.create({
    "name": "Sales Analyst Capsule",
    "soul": {
        "system_prompt": agent.system_prompt,
        "personality_traits": {},
        "neuromodulator_baseline": {},
    },
    "body": {
        "capsule_type": "voyant.intelligence_recipe",
        "execution_graph": [
            {"action": "voyant.sql", "params": {"sql": "{{query}}"}}
        ],
        "parameters": {
            "query": {"type": "string", "required": true}
        },
        "rbac": {"required_permission": "execute:research"},
        "capabilities_whitelist": agent.tools,
        "resource_limits": {"max_execution_seconds": 300},
        "output_formats": ["json", "markdown"],
    },
})

# 3. Certify and activate the capsule
client.capsules.certify(capsule.id)
client.capsules.activate(capsule.id)

# 4. Install for tenants
client.capsules.install(capsule.id)
```

### 9.6 How to Monitor an Agent

| Metric | Source | Alert Threshold |
|--------|--------|----------------|
| Query count per session | `AgentDefinition.guardrails.max_queries_per_session` | 80% of limit |
| Average response time | `LLMModel.avg_latency_ms` | > 5000ms |
| Error rate | Capsule instance `status=failed` | > 5% of executions |
| Cost per session | LLM usage tracking | > `cost_limit_usd` |
| Evaluation score | `AgentEvaluation.overall_score` | < 0.7 |
| Tool usage distribution | Audit logs | Unexpected tool patterns |
| Guardrail violations | Execution logs | Any violation |

**Monitoring endpoints:**

```bash
# Agent status
GET /api/v1/ml/agents/{id}

# Agent evaluations
GET /api/v1/ml/agents/{id}/evaluations

# Capsule instances
GET /api/v1/capsules/instances/{id}

# LLM usage
GET /api/v1/llm/active
```

---

## 10. Improvements Summary

### 10 Ways Voyant's Agent Platform Is Better Than Both Palantir AIP and Databricks Agent Bricks

#### 1. MCP Protocol Support (Zero Competitors Have This)

Palantir and Databricks use proprietary tool invocation APIs. Voyant uses the **Model Context Protocol** — an open standard. Any MCP-compatible agent (Claude Desktop, GPT Actions, custom frameworks) can invoke 67+ Voyant tools without any custom integration. This means an AI agent built for Claude can immediately use Voyant's SQL engine, scraper, ontology, and governance tools.

**Impact:** Voyant is the only platform where agents from different providers can seamlessly use the same tool surface.

#### 2. Deterministic Execution (LLM Proposes, Code Disposes)

Palantir AIP runs LLM-generated code in sandboxes. Databricks Agent Bricks lets LLMs generate and execute SQL. Both approaches risk hallucinated execution — the LLM might generate incorrect SQL, delete data, or call the wrong API.

Voyant's Intent Engine uses the LLM **only for translation**. The LLM generates a structured plan, and then **deterministic code** executes it. The LLM cannot execute arbitrary code. Every step is validated against a tool catalog and executed by handler functions that enforce safety constraints (read-only SQL, RBAC, quotas).

**Impact:** Zero hallucination risk in execution. The worst the LLM can do is generate a suboptimal plan — it can never execute destructive operations.

#### 3. Self-Hosted Deployment (Full Control)

Palantir AIP requires a Palantir contract ($500K-$10M+/year). Databricks Agent Bricks requires Databricks compute ($10K-$1M+/year). Both are cloud-only with no self-hosted option.

Voyant runs on Docker — 30 containers that you control. No vendor lock-in, no data leaving your infrastructure, no surprise billing.

**Impact:** 10-100x cost reduction for equivalent capability. Full data sovereignty.

#### 4. Capsule System (Portable Intelligence Recipes)

Neither Palantir nor Databricks has a portable, signed, versioned package for agent capabilities. Palantir's Workshop apps are locked to Foundry. Databricks MLflow Recipes are locked to MLflow.

Voyant Capsules are JSON bundles with:
- Ed25519 digital signatures for tamper-proof integrity
- Semantic versioning with clone-on-edit
- RBAC rules and capability whitelists
- Constitution binding for governance
- Export/import with checksum verification

**Impact:** Agents can be packaged, shared, verified, and deployed across instances — like npm packages for AI intelligence.

#### 5. 7+ LLM Providers (Model-Agnostic)

Palantir supports ~6 LLM providers (gated through their gateway). Databricks supports models via Model Serving endpoints. Both tie you to their provider ecosystem.

Voyant supports **any OpenAI-compatible endpoint** via the `LLMProvider` model:
- Groq, OpenAI, Anthropic, MiMo, Ollama, Azure, Bedrock, Vertex AI
- Local models via Ollama
- Custom endpoints
- Per-purpose model assignment (intent engine uses Groq, analysis uses GPT-4, etc.)

**Impact:** Use the best model for each task. No provider lock-in. Run entirely local if desired.

#### 6. Web Scraping Engine (8,471 LOC)

Neither Palantir nor Databricks has any web scraping capability. Voyant includes a complete scraping engine:
- Playwright for JavaScript-rendered pages
- Scrapy for static pages
- OCR via Tesseract
- PDF parsing via pdfplumber
- Audio/video transcription via Whisper
- Template engine with auto-detection
- 8 scraper MCP tools

**Impact:** Agents can acquire data from the web, not just from databases. This is critical for competitive intelligence, market research, and data enrichment.

#### 7. Intent Engine (NL → Structured Plans)

Palantir has "AIP Assist" for basic natural language. Databricks has "Genie" for BI queries. Both are limited in scope.

Voyant's Intent Engine translates **any natural language** into **any tool call** across 67+ MCP tools. It handles query, pipeline, scraper, analyze, ontology, governance, and search intents. It's tenant-aware (loads ontology schema), has a fail-closed design, and falls back to keyword-based classification when LLM is unavailable.

**Impact:** Agents don't need to know the exact tool names or parameters. They express intent in natural language, and the Intent Engine translates it into a precise execution plan.

#### 8. Temporal Workflows (Durable, Self-Healing)

Palantir uses proprietary workflow orchestration. Databricks uses job clusters. Neither provides workflow replay, durable state, or automatic retry.

Voyant uses Temporal.io for all async operations:
- Durable state (survives crashes)
- Automatic retry with exponential backoff
- Workflow replay for debugging
- Full execution history in Temporal UI
- 17+ workflow definitions

**Impact:** Long-running operations (data ingestion, analysis, scraping) are reliable and recoverable. No work is lost on failure.

#### 9. Ontology Graph (Palantir-Grade)

Databricks has Unity Catalog (table/schema level metadata). Palantir has a full ontology engine. Voyant implements Palantir-grade ontology with:
- Object Types with 11 property types
- Link Types with 1:1, 1:N, M:N cardinality
- Multi-hop graph traversal (up to 10 hops)
- Batch creation (1000+ objects)
- Optimistic concurrency
- Schema versioning
- Soft deletion with referential integrity

**Impact:** Agents can reason about data as a graph of entities and relationships, not just flat tables. This enables complex queries like "find all customers who bought products from suppliers in region X."

#### 10. Open Source (Apache 2.0)

Palantir is proprietary ($500K-$10M+ contracts). Databricks is proprietary (consumption-based billing). Neither is open source.

Voyant is Apache 2.0 open source:
- Community-driven development
- Full code audit capability
- Extensible (add your own MCP tools, workflows, capsule types)
- No vendor lock-in
- Self-hosted on your infrastructure

**Impact:** The only enterprise-grade agent platform that's fully open source. You own the code, the data, and the infrastructure.

---

## Appendix A: Tool Count Summary

| Category | File | Tool Count |
|----------|------|-----------|
| Core Data Operations | `tools_core.py` | 13 |
| Catalog & Management | `tools_catalog.py` | 27 |
| Ontology Engine | `tools_ontology.py` | 14 |
| Scraper | `tools_scrape.py` | 7 |
| Scraper Templates | `tools_scraper_templates.py` | 8 |
| **Total** | | **69** |

## Appendix B: API Endpoint Summary

| Router | Endpoints | Source |
|--------|-----------|--------|
| Intent | 6 | `apps/intent/api.py` |
| Capsules | 12 | `apps/capsules/api.py` |
| LLM Providers | 8 | `apps/llm_providers/api.py` |
| Ontology | ~35 | (enhanced in v4.0) |
| Scraper | ~21 | (enhanced in v4.0) |
| ML Platform | ~12 | (new in v4.0) |
| Governance | ~12 | (enhanced in v4.0) |
| Admin Dashboard | 28 | (existing) |
| **Total** | **120+** | |

## Appendix C: Data Model Summary

| Model | App | Purpose |
|-------|-----|---------|
| `IntentPlan` | intent | Execution plan dataclass |
| `IntentType` | intent | Enum of 8 intent types |
| `Capsule` | capsules | Intelligence recipe |
| `CapsuleInstallation` | capsules | Tenant-capsule binding |
| `CapsuleInstance` | capsules | Running capsule execution |
| `Capability` | capsules | MCP tool mapping |
| `Constitution` | capsules | Governance document |
| `LLMProvider` | llm_providers | LLM provider config |
| `LLMModel` | llm_providers | Model within provider |
| `ActiveLLMConfig` | llm_providers | Active model per purpose |
| `AgentDefinition` | ml_platform | Agent config |
| `AgentEvaluation` | ml_platform | Evaluation test cases + results |
| `Experiment` | ml_platform | ML experiment |
| `Run` | ml_platform | ML experiment run |
| `RegisteredModel` | ml_platform | Model registry |
| `ModelVersion` | ml_platform | Versioned model |
| `ModelEndpoint` | ml_platform | Serving endpoint |

---

**Created:** 2026-09-05
**Author:** Voyant Engineering
**Reviewed:** Pending
**Next review:** 2026-09-19
