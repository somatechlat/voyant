# Voyant Visual Pipeline Builder — Software Requirements Specification

**Document ID:** VOY-SRS-PipelineBuilder-001
**Version:** 1.0
**Date:** 2026-07-20
**Status:** DRAFT
**Classification:** Internal
**Standard:** ISO/IEC/IEEE 29148:2018

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [Specific Requirements](#3-specific-requirements)
4. [External Interface Requirements](#4-external-interface-requirements)
5. [Internal Interface Requirements](#5-internal-interface-requirements)
6. [Performance Requirements](#6-performance-requirements)
7. [Database Requirements](#7-database-requirements)
8. [Design Constraints](#8-design-constraints)
9. [Security Requirements](#9-security-requirements)
10. [Quality Attributes](#10-quality-attributes)
11. [Verification and Validation](#11-verification-and-validation)
12. [Appendices](#12-appendices)

---

## 1. Introduction

### 1.1 Purpose

This document specifies the software requirements for the Voyant Visual Pipeline Builder, a browser-based visual development environment for creating, editing, executing, and monitoring data transformation pipelines. This SRS follows ISO/IEC/IEEE 29148:2018 and provides a complete specification suitable for design, implementation, and verification.

### 1.2 Scope

The Voyant Visual Pipeline Builder encompasses:

- **Visual Editor** — Browser-based node-and-edge graph editor for pipeline construction
- **Transform Library** — 200+ built-in data transformation functions
- **Pipeline Definition Language (PDL)** — Declarative pipeline representation
- **Execution Engine** — Runtime for executing defined pipelines
- **Preview System** — Real-time pipeline output preview
- **Version Control** — Pipeline branching, merging, and history
- **Scheduling** — Cron and event-driven pipeline execution triggers
- **Monitoring** — Pipeline execution status, logs, and metrics

The system does not cover:
- Ad-hoc SQL query execution (covered by VOY-SRS-SQL-001)
- Real-time streaming pipeline construction (covered by VOY-SRS-Streaming-001)
- Dashboard/report building (covered by VOY-SRS-Workshop-001)

### 1.3 Definitions, Acronyms, Abbreviations

| Term | Definition |
|------|------------|
| **PDL** | Pipeline Definition Language — declarative YAML/JSON representation of pipelines |
| **Node** | A single step in a pipeline (source, transform, or sink) |
| **Edge** | A connection between two nodes representing data flow |
| **Transform** | A data transformation operation applied to a dataset |
| **Source** | A node that reads data from an external system |
| **Sink** | A node that writes data to an external system |
| **DAG** | Directed Acyclic Graph — the computational model for pipelines |
| **Preview** | A limited execution showing sample output without full materialization |
| **Lineage** | The graph of data dependencies from sources to sinks |

### 1.4 References

| Document | Description |
|----------|-------------|
| ISO/IEC/IEEE 29148:2018 | Systems and software engineering — Life cycle processes — Requirements engineering |
| ISO/IEC 25010:2023 | Systems and software — Quality models |
| VOY-ARCH-001 | Voyant System Architecture Document |
| VOY-SRS-Core-001 | Voyant Core Platform SRS |
| VOY-SRS-Ingestion-001 | Voyant Data Ingestion SRS |
| VOY-SRS-Analysis-001 | Voyant Analysis Engine SRS |

### 1.5 Document Overview

Section 2 provides an overall description of the product. Section 3 specifies detailed functional requirements. Sections 4-7 cover interface, performance, database, and constraint requirements. Sections 8-10 cover security, quality, and verification. Appendices provide supporting material.

---

## 2. Overall Description

### 2.1 Product Perspective

The Voyant Visual Pipeline Builder is a component of the Voyant platform that sits between the data integration layer and the analytics layer. It consumes data from connected sources (databases, APIs, files) and produces transformed datasets for analysis, profiling, and ML.

```
┌─────────────────────────────────────────────────────────────────┐
│                     VPIJAL VISUAL PIPELINE BUILDER               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │                  FRONTEND (React + TypeScript)            │     │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐  │     │
│  │  │  Graph Editor  │ │  Transform    │ │  Properties   │  │     │
│  │  │  (React Flow)  │ │  Palette      │ │  Panel        │  │     │
│  │  └───────────────┘ └───────────────┘ └───────────────┘  │     │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐  │     │
│  │  │  Preview       │ │  Version      │ │  Monitoring   │  │     │
│  │  │  Panel         │ │  Control      │ │  Dashboard    │  │     │
│  │  └───────────────┘ └───────────────┘ └───────────────┘  │     │
│  └────────────────────────┬────────────────────────────────┘     │
│                           │                                        │
│  ┌────────────────────────┴────────────────────────────────┐     │
│  │                  API LAYER (Django Ninja)                 │     │
│  │  /api/v2/pipelines/*                                     │     │
│  │  /api/v2/pipelines/{id}/execute                          │     │
│  │  /api/v2/pipelines/{id}/preview                          │     │
│  │  /api/v2/pipelines/{id}/versions                         │     │
│  │  /api/v2/transforms/*                                    │     │
│  └────────────────────────┬────────────────────────────────┘     │
│                           │                                        │
│  ┌────────────────────────┴────────────────────────────────┐     │
│  │                  EXECUTION ENGINE                         │     │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐  │     │
│  │  │  PDL Parser    │ │  DAG          │ │  Transform    │  │     │
│  │  │  & Validator   │ │  Executor     │ │  Runtime      │  │     │
│  │  └───────────────┘ └───────────────┘ └───────────────┘  │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Product Functions

The system provides the following high-level functions:

| Function | Description |
|----------|-------------|
| F-01 | Create, edit, and delete visual pipelines via browser UI |
| F-02 | Compose pipelines from 200+ built-in transforms |
| F-03 | Connect to any Voyant-supported data source |
| F-04 | Execute pipelines in batch, incremental, or streaming mode |
| F-05 | Preview pipeline output without full execution |
| F-06 | Version control pipelines with branching and merging |
| F-07 | Schedule pipelines with cron or event triggers |
| F-08 | Monitor pipeline execution status, logs, and metrics |
| F-09 | Export pipelines as code (Python, SQL) |
| F-10 | Import existing pipelines from Temporal workflows |

### 2.3 User Characteristics

| User Type | Skill Level | Description |
|-----------|-------------|-------------|
| Data Engineer | Advanced | Builds and maintains production pipelines |
| Data Analyst | Intermediate | Creates analytical pipelines for reporting |
| Data Scientist | Advanced | Builds feature engineering and ML pipelines |
| Citizen Developer | Beginner | Uses visual builder for simple transformations |

### 2.4 Constraints

| ID | Constraint | Rationale |
|----|------------|-----------|
| CON-01 | Must run in modern browsers (Chrome 90+, Firefox 88+, Safari 14+) | Target platform |
| CON-02 | Must integrate with existing Temporal workflow engine | Architecture decision |
| CON-03 | Must use existing Voyant connector infrastructure | Reuse investment |
| CON-04 | Must support pipeline sizes up to 500 nodes | Performance target |
| CON-05 | Must export to Python/SQL for code-first users | Portability |
| CON-06 | Must support offline editing with sync on reconnect | Reliability |

### 2.5 Assumptions and Dependencies

| ID | Assumption/Dependency |
|----|----------------------|
| A-01 | Users have access to a modern web browser |
| A-02 | Voyant platform services are operational |
| A-03 | Network connectivity available for API communication |
| D-01 | PostgreSQL database available for metadata storage |
| D-02 | MinIO available for artifact storage |
| D-03 | Temporal service available for workflow orchestration |
| D-04 | Redis available for caching and session management |

---

## 3. Specific Requirements

### 3.1 Functional Requirements

#### 3.1.1 Pipeline Management

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| PIPE-F-001 | System shall allow users to create new pipelines with a name, description, and optional tags | Critical | Core functionality |
| PIPE-F-002 | System shall allow users to edit pipeline properties (name, description, tags) | Critical | Core functionality |
| PIPE-F-003 | System shall allow users to delete pipelines with confirmation dialog | Critical | Core functionality |
| PIPE-F-004 | System shall list all pipelines with filtering by name, tag, status, and owner | High | Discovery |
| PIPE-F-005 | System shall support pipeline duplication (clone) | Medium | Productivity |
| PIPE-F-006 | System shall support pipeline templates (pre-defined patterns) | Medium | Productivity |
| PIPE-F-007 | System shall track pipeline creation and modification timestamps | High | Audit |
| PIPE-F-008 | System shall track pipeline owner and last modified by | High | Audit |

#### 3.1.2 Visual Editor

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| PIPE-F-010 | System shall provide a browser-based node-and-edge graph editor | Critical | Core UI |
| PIPE-F-011 | System shall support drag-and-drop node creation from transform palette | Critical | Usability |
| PIPE-F-012 | System shall support connecting nodes by dragging from output port to input port | Critical | Core UI |
| PIPE-F-013 | System shall support moving nodes via drag-and-drop | Critical | Core UI |
| PIPE-F-014 | System shall support multi-select nodes (shift-click, rubber band) | High | Efficiency |
| PIPE-F-015 | System shall support undo/redo of all editor operations (50+ levels) | High | Reliability |
| PIPE-F-016 | System shall support zoom in/out and pan navigation | Critical | Navigation |
| PIPE-F-017 | System shall support minimap overview | Medium | Navigation |
| PIPE-F-018 | System shall support node search/filter in transform palette | High | Discoverability |
| PIPE-F-019 | System shall support pipeline validation with error highlighting | Critical | Quality |
| PIPE-F-020 | System shall support automatic layout arrangement | Medium | Aesthetics |
| PIPE-F-021 | System shall support node commenting/annotations | Medium | Collaboration |
| PIPE-F-022 | System shall support color-coding nodes by category | Medium | Organization |

#### 3.1.3 Transform Library

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| PIPE-F-030 | System shall provide 50+ source connectors (database, API, file) | Critical | Connectivity |
| PIPE-F-031 | System shall provide 50+ transform operations (filter, map, join, aggregate) | Critical | Core transforms |
| PIPE-F-032 | System shall provide 20+ sink connectors (database, API, file, lake) | Critical | Output |
| PIPE-F-033 | System shall support join transforms (inner, left, right, full, cross) | Critical | Data combination |
| PIPE-F-034 | System shall support union transforms (append, union all) | Critical | Data combination |
| PIPE-F-035 | System shall support conditional branching (if/else, switch) | High | Control flow |
| PIPE-F-036 | System shall support geospatial transforms (distance, intersection) | Medium | Specialized |
| PIPE-F-037 | System shall support string manipulation transforms (regex, tokenize, clean) | High | Data cleaning |
| PIPE-F-038 | System shall support date/time transforms (parse, format, extract) | High | Data cleaning |
| PIPE-F-039 | System shall support numeric transforms (round, floor, ceil, log) | High | Data cleaning |
| PIPE-F-040 | System shall support array/map manipulation transforms | High | Complex types |
| PIPE-F-041 | System shall support aggregation transforms (count, sum, avg, min, max, group by) | Critical | Analytics |
| PIPE-F-042 | System shall support window functions (row_number, rank, lag, lead) | High | Advanced analytics |
| PIPE-F-043 | System shall support deduplication transforms | High | Data quality |
| PIPE-F-044 | System shall support pivot/unpivot transforms | High | Reshaping |
| PIPE-F-045 | System shall support custom transform (Python/SQL) nodes | High | Extensibility |
| PIPE-F-046 | System shall support LLM-powered transforms (classification, extraction) | Medium | AI integration |
| PIPE-F-047 | System shall allow users to create and register custom transforms | High | Extensibility |

#### 3.1.4 Properties Panel

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| PIPE-F-050 | System shall display properties panel when a node is selected | Critical | Configuration |
| PIPE-F-051 | System shall allow editing transform-specific parameters | Critical | Configuration |
| PIPE-F-052 | System shall provide inline help/tooltips for all parameters | High | Usability |
| PIPE-F-053 | System shall validate parameter values in real-time | High | Quality |
| PIPE-F-054 | System shall support parameter expressions (references to other nodes) | High | Flexibility |
| PIPE-F-055 | System shall support parameter templates/variables | Medium | Reusability |
| PIPE-F-056 | System shall display input/output schema for each node | High | Transparency |
| PIPE-F-057 | System shall display node execution statistics (rows, duration) | Medium | Monitoring |

#### 3.1.5 Pipeline Definition Language (PDL)

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| PIPE-F-060 | System shall support declarative pipeline definition in YAML format | Critical | Code export |
| PIPE-F-061 | System shall support declarative pipeline definition in JSON format | High | Interoperability |
| PIPE-F-062 | System shall provide bidirectional sync between visual and PDL representations | Critical | Parity |
| PIPE-F-063 | System shall validate PDL documents against schema | Critical | Quality |
| PIPE-F-064 | System shall support PDL versioning | High | History |
| PIPE-F-065 | System shall support PDL diff and merge | High | Collaboration |

#### 3.1.6 Execution Engine

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| PIPE-F-070 | System shall execute pipelines defined via visual editor or PDL | Critical | Core function |
| PIPE-F-071 | System shall support batch execution mode | Critical | Core function |
| PIPE-F-072 | System shall support incremental execution mode | High | Efficiency |
| PIPE-F-073 | System shall support parallel execution of independent nodes | High | Performance |
| PIPE-F-074 | System shall support pipeline checkpointing for recovery | High | Reliability |
| PIPE-F-075 | System shall support pipeline cancellation | Critical | Control |
| PIPE-F-076 | System shall support pipeline retry with configurable retry policy | High | Reliability |
| PIPE-F-077 | System shall emit progress events during execution | High | Monitoring |
| PIPE-F-078 | System shall capture and store execution logs | Critical | Debugging |
| PIPE-F-079 | System shall track row counts and data volumes at each node | High | Monitoring |
| PIPE-F-080 | System shall support pipeline execution timeout | High | Resource mgmt |

#### 3.1.7 Preview System

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| PIPE-F-090 | System shall support previewing pipeline output without full execution | Critical | Iteration speed |
| PIPE-F-091 | System shall support preview with configurable sample size (100-10000 rows) | High | Flexibility |
| PIPE-F-092 | System shall support preview at any node in the pipeline | High | Debugging |
| PIPE-F-093 | System shall display preview results in tabular format | Critical | Visualization |
| PIPE-F-094 | System shall display schema inference for each node output | High | Transparency |
| PIPE-F-095 | System shall complete preview within 5 seconds for < 1M row datasets | High | Responsiveness |

#### 3.1.8 Version Control

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| PIPE-F-100 | System shall automatically version pipelines on save | High | History |
| PIPE-F-101 | System shall support named versions (milestones) | Medium | Release mgmt |
| PIPE-F-102 | System shall support branching (create, switch, list) | High | Collaboration |
| PIPE-F-103 | System shall support merging branches with conflict detection | High | Collaboration |
| PIPE-F-104 | System shall display version history with diffs | High | Audit |
| PIPE-F-105 | System shall support rollback to any previous version | High | Recovery |
| PIPE-F-106 | System shall support version comparison (side-by-side diff) | Medium | Review |

#### 3.1.9 Scheduling

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| PIPE-F-110 | System shall support cron-based scheduling | Critical | Automation |
| PIPE-F-111 | System shall support event-based triggers (webhook, file arrival) | High | Automation |
| PIPE-F-112 | System shall support dependency-based triggers (upstream pipeline completion) | High | Orchestration |
| PIPE-F-113 | System shall support scheduling UI for creating/modifying schedules | High | Usability |
| PIPE-F-114 | System shall display upcoming schedule and execution history | Medium | Visibility |
| PIPE-F-115 | System shall support schedule enable/disable | High | Control |
| PIPE-F-116 | System shall support schedule parameterization | Medium | Reusability |

#### 3.1.10 Monitoring

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| PIPE-F-120 | System shall display pipeline execution status (running, completed, failed) | Critical | Visibility |
| PIPE-F-121 | System shall display execution timeline (start, duration, end) | High | Monitoring |
| PIPE-F-122 | System shall display node-level execution metrics | High | Debugging |
| PIPE-F-123 | System shall support log streaming for running pipelines | High | Debugging |
| PIPE-F-124 | System shall send notifications on pipeline failure | Critical | Alerting |
| PIPE-F-125 | System shall support pipeline execution replay | Medium | Debugging |
| PIPE-F-126 | System shall display resource usage (CPU, memory) per execution | Medium | Optimization |
| PIPE-F-127 | System shall support pipeline execution comparison (run vs run) | Medium | Analysis |

---

## 4. External Interface Requirements

### 4.1 User Interface

| ID | Requirement | Rationale |
|----|-------------|-----------|
| UI-001 | Interface shall be responsive (desktop, tablet) | Multi-device |
| UI-002 | Interface shall support keyboard shortcuts for all operations | Efficiency |
| UI-003 | Interface shall support drag-and-drop for node creation and connection | Usability |
| UI-004 | Interface shall provide real-time validation feedback | Quality |
| UI-005 | Interface shall support undo/redo operations | Reliability |
| UI-006 | Interface shall follow Voyant design system | Consistency |

### 4.2 Hardware Interface

| ID | Requirement | Rationale |
|----|-------------|-----------|
| HW-001 | System shall function on standard web browsers without plugins | Deployment |
| HW-002 | System shall support mouse and touch input | Multi-device |

### 4.3 Software Interface

| ID | Interface | Protocol | Direction |
|----|-----------|----------|-----------|
| SW-001 | Voyant API Gateway | HTTP/REST | Bidirectional |
| SW-002 | Voyant Connector Registry | HTTP/REST | Read |
| SW-003 | Voyant Temporal Service | gRPC | Bidirectional |
| SW-004 | Voyant Metadata DB (PostgreSQL) | TCP | Read/Write |
| SW-005 | Voyant Object Storage (MinIO) | HTTP/S3 | Read/Write |
| SW-006 | Voyant Cache (Redis) | TCP | Read/Write |

### 4.4 Communication Interface

| ID | Requirement | Rationale |
|----|-------------|-----------|
| COM-001 | API shall use HTTPS (TLS 1.3) | Security |
| COM-002 | API shall use JSON for request/response bodies | Standard |
| COM-003 | API shall support WebSocket for real-time updates | Responsiveness |
| COM-004 | API shall support Server-Sent Events for execution progress | Monitoring |

---

## 5. Internal Interface Requirements

### 5.1 Component Interfaces

```
┌─────────────┐     HTTP      ┌─────────────┐     gRPC      ┌─────────────┐
│  Frontend    │──────────────>│  API Layer   │──────────────>│  Temporal   │
│  (React)     │<──────────────│  (Django)    │<──────────────│  Service    │
└─────────────┘               └──────┬──────┘               └─────────────┘
                                     │
                                     │ SQL
                                     ▼
                              ┌─────────────┐
                              │  PostgreSQL  │
                              └─────────────┘
```

### 5.2 Internal APIs

| Interface | Caller | Callee | Protocol |
|-----------|--------|--------|----------|
| Pipeline CRUD | API Layer | PostgreSQL | SQL |
| Transform Registry | API Layer | Transform Catalog | In-memory |
| Execution Request | API Layer | Temporal | gRPC |
| Preview Request | API Layer | DuckDB | Embedded |
| Artifact Storage | API Layer | MinIO | S3 API |
| Cache Operations | API Layer | Redis | TCP |

---

## 6. Performance Requirements

### 6.1 Response Time

| ID | Operation | Target (p95) | Measurement |
|----|-----------|--------------|-------------|
| PERF-001 | Pipeline list load | < 500ms | APM |
| PERF-002 | Pipeline editor load | < 2s | APM |
| PERF-003 | Node properties load | < 200ms | APM |
| PERF-004 | Transform palette load | < 300ms | APM |
| PERF-005 | Preview execution (< 1M rows) | < 5s | Timer |
| PERF-006 | Pipeline save | < 1s | APM |
| PERF-007 | PDL validation | < 500ms | APM |
| PERF-008 | Version diff | < 2s | APM |
| PERF-009 | Execution log load | < 1s | APM |

### 6.2 Throughput

| ID | Operation | Target | Measurement |
|----|-----------|--------|-------------|
| PERF-010 | Concurrent editor sessions | > 100 | Load test |
| PERF-011 | Concurrent pipeline executions | > 50 | Load test |
| PERF-012 | Pipeline executions per hour | > 1000 | Stress test |

### 6.3 Scalability

| ID | Metric | Target | Measurement |
|----|--------|--------|-------------|
| PERF-020 | Max nodes per pipeline | > 500 | Scale test |
| PERF-021 | Max edges per pipeline | > 1000 | Scale test |
| PERF-022 | Max transform parameters | > 50 | Scale test |
| PERF-023 | Total pipelines per tenant | > 10,000 | Capacity test |

### 6.4 Resource Utilization

| ID | Resource | Target | Measurement |
|----|----------|--------|-------------|
| PERF-030 | Frontend bundle size | < 2MB | Build analysis |
| PERF-031 | Frontend memory usage | < 500MB | Browser devtools |
| PERF-032 | API response payload | < 1MB | API testing |
| PERF-033 | Database connection pool | < 20 per instance | Monitoring |

---

## 7. Database Requirements

### 7.1 Schema

```sql
-- Pipeline Definitions
CREATE TABLE pipeline_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace_id UUID NOT NULL REFERENCES namespaces(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tags TEXT[],
    pdl_definition JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID NOT NULL REFERENCES users(id),
    updated_by UUID NOT NULL REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    UNIQUE(namespace_id, name, deleted_at)
);

CREATE INDEX idx_pipelines_namespace ON pipeline_definitions(namespace_id);
CREATE INDEX idx_pipelines_name ON pipeline_definitions(name);
CREATE INDEX idx_pipelines_status ON pipeline_definitions(status);
CREATE INDEX idx_pipelines_tags ON pipeline_definitions USING GIN(tags);

-- Pipeline Versions
CREATE TABLE pipeline_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID NOT NULL REFERENCES pipeline_definitions(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    pdl_definition JSONB NOT NULL,
    change_description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID NOT NULL REFERENCES users(id),
    UNIQUE(pipeline_id, version)
);

CREATE INDEX idx_pipeline_versions_pipeline ON pipeline_versions(pipeline_id);

-- Pipeline Executions
CREATE TABLE pipeline_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID NOT NULL REFERENCES pipeline_definitions(id),
    pipeline_version INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    trigger_type VARCHAR(20) NOT NULL CHECK (trigger_type IN ('manual', 'schedule', 'event', 'dependency')),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    rows_processed BIGINT,
    bytes_processed BIGINT,
    error_message TEXT,
    execution_log JSONB,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_executions_pipeline ON pipeline_executions(pipeline_id);
CREATE INDEX idx_executions_status ON pipeline_executions(status);
CREATE INDEX idx_executions_started ON pipeline_executions(started_at);

-- Pipeline Schedules
CREATE TABLE pipeline_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID NOT NULL REFERENCES pipeline_definitions(id) ON DELETE CASCADE,
    schedule_type VARCHAR(20) NOT NULL CHECK (schedule_type IN ('cron', 'interval', 'event', 'dependency')),
    cron_expression VARCHAR(100),
    interval_seconds INTEGER,
    event_trigger JSONB,
    dependency_pipeline_id UUID,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    parameters JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_schedules_pipeline ON pipeline_schedules(pipeline_id);
CREATE INDEX idx_schedules_enabled ON pipeline_schedules(enabled);

-- Pipeline Branches
CREATE TABLE pipeline_branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID NOT NULL REFERENCES pipeline_definitions(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    pdl_definition JSONB NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID NOT NULL REFERENCES users(id),
    UNIQUE(pipeline_id, name)
);

CREATE INDEX idx_branches_pipeline ON pipeline_branches(pipeline_id);
```

### 7.2 Data Retention

| Data | Retention | Rationale |
|------|-----------|-----------|
| Pipeline definitions | Indefinite | Core asset |
| Pipeline versions | Indefinite | Audit trail |
| Execution logs | 90 days | Debugging |
| Execution metrics | 1 year | Analytics |
| Preview data | 24 hours | Ephemeral |

---

## 8. Design Constraints

### 8.1 Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | React 18 + TypeScript | Component model, ecosystem |
| Graph Editor | React Flow | Proven DAG editor |
| State Management | Zustand | Lightweight, performant |
| Styling | Tailwind CSS + shadcn/ui | Design system consistency |
| Build Tool | Vite | Fast HMR, ESM |
| Backend | Django 5.0 + Django Ninja | Existing stack |
| Database | PostgreSQL 16 | Existing stack |
| Workflow | Temporal.io | Existing stack |
| Preview Engine | DuckDB | Embedded analytics |

### 8.2 Architectural Patterns

| Pattern | Application |
|---------|-------------|
| CQRS | Separate read/write for pipeline metadata |
| Event Sourcing | Pipeline version history |
| Circuit Breaker | External connector calls |
| Retry with Backoff | Failed pipeline executions |
| Saga Pattern | Multi-step pipeline operations |

---

## 9. Security Requirements

| ID | Requirement | Standard | Implementation |
|----|-------------|----------|----------------|
| SEC-001 | Authentication required for all operations | ISO 27001 | OIDC/JWT |
| SEC-002 | Authorization enforced per pipeline | ISO 27001 | SpiceDB RBAC |
| SEC-003 | API communication encrypted | ISO 27001 | TLS 1.3 |
| SEC-004 | Secrets in pipelines encrypted | ISO 27001 | Vault integration |
| SEC-005 | Execution audit trail maintained | ISO 27001 | Audit logging |
| SEC-006 | Preview data access controlled | ISO 27001 | RBAC |
| SEC-007 | Pipeline code validated for injection | OWASP | Input sanitization |
| SEC-008 | Custom transforms sandboxed | OWASP | Container isolation |

---

## 10. Quality Attributes

### 10.1 Reliability

| ID | Requirement | Target |
|----|-------------|--------|
| REL-001 | System availability | 99.9% |
| REL-002 | Mean time between failures (MTBF) | > 720 hours |
| REL-003 | Mean time to recovery (MTTR) | < 30 minutes |
| REL-004 | Pipeline execution success rate | > 99% |

### 10.2 Maintainability

| ID | Requirement | Target |
|----|-------------|--------|
| MAINT-001 | Code test coverage | > 90% |
| MAINT-002 | Code complexity (cyclomatic) | < 10 |
| MAINT-003 | Documentation coverage | 100% of public APIs |
| MAINT-004 | Time to onboard new developer | < 2 weeks |

### 10.3 Usability

| ID | Requirement | Target |
|----|-------------|--------|
| USAB-001 | Time to create first pipeline | < 5 minutes |
| USAB-002 | System Usability Scale (SUS) score | > 80 |
| USAB-003 | Accessibility compliance | WCAG 2.1 AA |
| USAB-004 | Time to complete common tasks | < 2 minutes |

### 10.4 Portability

| ID | Requirement | Target |
|----|-------------|--------|
| PORT-001 | Browser support | Chrome 90+, Firefox 88+, Safari 14+ |
| PORT-002 | Screen resolution support | 1280x720 to 4K |
| PORT-003 | Export to Python code | Functional parity |
| PORT-004 | Export to SQL | Functional parity |

---

## 11. Verification and Validation

### 11.1 Verification Methods

| Method | Application | Coverage |
|--------|-------------|----------|
| Unit Testing | All transform functions | 90%+ |
| Integration Testing | API endpoints, database operations | 85%+ |
| System Testing | End-to-end pipeline workflows | 80%+ |
| Performance Testing | Response time, throughput | All PERF-* |
| Security Testing | OWASP Top 10 | All SEC-* |
| Usability Testing | User workflows | All USAB-* |
| Accessibility Testing | WCAG 2.1 AA | All public pages |

### 11.2 Acceptance Criteria

| ID | Criterion | Test Method | Pass Condition |
|----|-----------|-------------|----------------|
| AC-001 | Pipeline creation via visual editor | E2E test | Pipeline saved correctly |
| AC-002 | Pipeline execution completes | Integration test | Status = completed |
| AC-003 | Preview shows correct output | E2E test | Output matches expected |
| AC-004 | Version history maintained | Integration test | Versions accessible |
| AC-005 | Schedule triggers execution | Integration test | Execution starts on time |
| AC-006 | Export to Python works | E2E test | Python code executes |
| AC-007 | 100 concurrent users | Load test | p95 < target |
| AC-008 | 500-node pipeline works | Scale test | Executes successfully |

### 11.3 Test Traceability

| Requirement | Test Case | Test Script | Result |
|-------------|-----------|-------------|--------|
| PIPE-F-001 | TC-PIPE-001 | test_create_pipeline.py | — |
| PIPE-F-010 | TC-PIPE-010 | test_visual_editor.py | — |
| PIPE-F-030 | TC-PIPE-030 | test_transforms.py | — |
| PIPE-F-070 | TC-PIPE-070 | test_execution.py | — |
| PIPE-F-090 | TC-PIPE-090 | test_preview.py | — |
| PERF-001 | TC-PERF-001 | perf_response_time.py | — |

---

## 12. Appendices

### Appendix A: Transform Categories

| Category | Count | Examples |
|----------|-------|----------|
| Source | 50+ | PostgreSQL, MySQL, S3, GCS, Kafka, REST API |
| Filter | 10+ | Where, Regex, Null check, Duplicate |
| Map | 15+ | Select, Rename, Cast, Split, Merge |
| Join | 5+ | Inner, Left, Right, Full, Cross |
| Aggregate | 10+ | Group By, Count, Sum, Avg, Window |
| String | 20+ | Concat, Substring, Replace, Split, Clean |
| Date/Time | 15+ | Parse, Format, Extract, Diff, Truncate |
| Numeric | 10+ | Round, Floor, Ceil, Log, Abs |
| Array/Map | 10+ | Flatten, Explode, Contains, Keys |
| Geospatial | 10+ | Distance, Intersection, Buffer, Centroid |
| Conditional | 5+ | If/Else, Case, Coalesce, NullIf |
| Custom | 2 | Python transform, SQL transform |
| LLM | 5+ | Classify, Extract, Summarize, Transform |
| **Total** | **200+** | |

### Appendix B: Pipeline PDL Example

```yaml
# Voyant Pipeline Definition Language (PDL)
pipeline:
  name: customer-analysis
  description: "Analyze customer data with quality checks"
  version: 1
  tags: [analytics, customers]

nodes:
  - id: source_customers
    type: source.postgresql
    config:
      connection: production-db
      query: "SELECT * FROM customers WHERE active = true"

  - id: source_orders
    type: source.postgresql
    config:
      connection: production-db
      query: "SELECT * FROM orders WHERE created_at > '2024-01-01'"

  - id: quality_check
    type: transform.quality
    config:
      rules:
        - column: email
          rule: not_null
        - column: total_orders
          rule: range
          min: 0
          max: 10000

  - id: join_data
    type: transform.join
    config:
      type: left
      left: source_customers
      right: source_orders
      on:
        - left: id
          right: customer_id

  - id: aggregate_metrics
    type: transform.aggregate
    config:
      group_by: [id, name, email]
      aggregations:
        - column: total_orders
          function: count
        - column: order_total
          function: sum
        - column: order_total
          function: avg

  - id: sink_analysis
    type: sink.parquet
    config:
      path: "s3://data-lake/customer-analysis/"
      format: parquet
      partition_by: [year, month]

edges:
  - source: source_customers
    target: join_data
  - source: source_orders
    target: join_data
  - source: join_data
    target: quality_check
  - source: quality_check
    target: aggregate_metrics
  - source: aggregate_metrics
    target: sink_analysis

schedule:
  type: cron
  expression: "0 6 * * *"
  timezone: UTC

monitoring:
  alerts:
    - type: failure
      channels: [slack, email]
    - type: duration
      threshold: 3600
      channels: [slack]
```

### Appendix C: Glossary

| Term | Definition |
|------|------------|
| **Pipeline** | A directed acyclic graph of data transformation steps |
| **Node** | A single step in a pipeline (source, transform, or sink) |
| **Edge** | A connection between nodes representing data flow |
| **PDL** | Pipeline Definition Language — declarative pipeline representation |
| **Transform** | A data transformation operation |
| **Source** | A node that reads data from an external system |
| **Sink** | A node that writes data to an external system |
| **Preview** | Limited execution showing sample output |
| **DAG** | Directed Acyclic Graph — computational model for pipelines |
| **Lineage** | Graph of data dependencies |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-20 | Voyant Engineering | Initial release |

**Approval:**

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Engineering Manager | _________________ | ________ | _________ |
| Product Manager | _________________ | ________ | _________ |
| QA Manager | _________________ | ________ | _________ |

---

**Document Status:** DRAFT
**Classification:** Internal
**Retention:** 7 years
**Next Review:** 2026-08-20
