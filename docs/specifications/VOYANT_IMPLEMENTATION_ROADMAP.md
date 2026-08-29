# Voyant Platform — Feature Implementation Roadmap

**Document ID:** VOY-Roadmap-2026-001
**Version:** 1.0
**Date:** 2026-07-20
**Status:** DRAFT
**Classification:** Internal
**Standard:** ISO/IEC/IEEE 29148:2018

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State](#2-current-state)
3. [Target State](#3-target-state)
4. [Gap Analysis](#4-gap-analysis)
5. [Implementation Phases](#5-implementation-phases)
6. [Resource Requirements](#6-resource-requirements)
7. [Risk Assessment](#7-risk-assessment)
8. [Success Criteria](#8-success-criteria)
9. [Dependencies](#9-dependencies)
10. [Appendices](#10-appendices)

---

## 1. Executive Summary

This document defines the implementation roadmap for expanding Voyant's capabilities across three major feature areas: Ontology Engine, Visual Pipeline Builder, and Workshop (Application Builder). The roadmap follows a docs-first approach where all specifications are completed before development begins.

**Timeline:** 24 months (8 quarters)
**Team Size:** 12-16 engineers
**Estimated Investment:** $5.5M-7.8M

---

## 2. Current State

### 2.1 Implemented Features

| Module | Status | Coverage | SRS Document |
|--------|--------|----------|--------------|
| Core Platform | ✅ Complete | 100% | VOY-SRS-Core-001 |
| Data Ingestion | ✅ Complete | 100% | VOY-SRS-Ingestion-001 |
| Connector Registry | ✅ Complete | 100% | VOY-SRS-Ingestion-001 |
| Airbyte Integration | ✅ Complete | 100% | VOY-SRS-Ingestion-001 |
| Data Profiling | ✅ Complete | 100% | VOY-SRS-Analysis-001 |
| Data Quality | ✅ Complete | 100% | VOY-SRS-Analysis-001 |
| Statistical Analysis | ✅ Complete | 100% | VOY-SRS-Analysis-001 |
| Forecasting | ✅ Complete | 100% | VOY-SRS-Analysis-001 |
| Anomaly Detection | ✅ Complete | 100% | VOY-SRS-Analysis-001 |
| SQL Querying | ✅ Complete | 100% | VOY-SRS-SQL-001 |
| Semantic Search | ✅ Complete | 100% | VOY-SRS-Search-001 |
| Streaming (Flink) | ✅ Complete | 100% | VOY-SRS-Streaming-001 |
| Web Scraping | ✅ Complete | 100% | VOY-SRS-Scraper-001 |
| MCP Tools | ✅ Complete | 100% | VOY-SRS-MCP-001 |
| Data Governance | ✅ Complete | 100% | VOY-SRS-Governance-001 |
| Audit Logging | ✅ Complete | 100% | VOY-SRS-Governance-001 |

### 2.2 Planned Features

| Module | Status | SRS Document |
|--------|--------|--------------|
| Ontology Engine | 🔧 Planned | VOY-SRS-Ontology-001 |
| Visual Pipeline Builder | 🔧 Planned | VOY-SRS-PipelineBuilder-001 |
| Workshop (App Builder) | 🔧 Planned | VOY-SRS-Workshop-001 |

---

## 3. Target State

### 3.1 Vision

Voyant will be a complete data intelligence platform providing:

1. **Data Integration** — Connect to any data source (databases, APIs, files, streams)
2. **Data Engineering** — Build and manage data pipelines visually or via code
3. **Data Knowledge** — Define ontologies connecting data to real-world entities
4. **Data Analytics** — Profile, analyze, and forecast from data
5. **Data Applications** — Build custom applications for operational workflows
6. **AI Agent Integration** — Enable AI agents to discover, connect, and analyze data

### 3.2 Feature Completeness

| Capability | Current | Target | Gap |
|------------|---------|--------|-----|
| Data Connectors | 10 native + 300 via Airbyte | 170+ native | Low |
| Batch Pipelines | Temporal workflows | Visual + Code | Critical |
| Streaming | Flink integration | Flink + Visual | Medium |
| Data Profiling | ydata-profiling | ydata-profiling | None |
| Data Quality | Great Expectations | Great Expectations | None |
| SQL | Trino | Trino + SQL IDE | Medium |
| Ontology | None | Full engine | Critical |
| Visual Builder | None | Drag-and-drop | Critical |
| App Builder | None | Low-code apps | Critical |
| AI Agents | MCP tools | MCP + Ontology | Medium |

---

## 4. Gap Analysis

### 4.1 Critical Gaps (Must Close)

| Gap | Impact | Effort | SRS |
|-----|--------|--------|-----|
| Ontology Engine | Core knowledge graph | 9 months | VOY-SRS-Ontology-001 |
| Visual Pipeline Builder | User adoption | 6 months | VOY-SRS-PipelineBuilder-001 |
| Workshop (App Builder) | End-user applications | 9 months | VOY-SRS-Workshop-001 |

### 4.2 Moderate Gaps (Should Close)

| Gap | Impact | Effort | SRS |
|-----|--------|--------|-----|
| Enhanced Scheduling | Automation | 2 months | VOY-SRS-PipelineBuilder-001 |
| Media Sets | Unstructured data | 3 months | VOY-SRS-Ontology-001 |
| Dataset Branching | Version control | 2 months | VOY-SRS-PipelineBuilder-001 |
| Dashboard Engine | Analytics UI | 4 months | VOY-SRS-Workshop-001 |

### 4.3 Minor Gaps (Nice to Have)

| Gap | Impact | Effort | SRS |
|-----|--------|--------|-----|
| Additional connectors (via Airbyte) | Coverage | Low | VOY-SRS-Ingestion-001 |
| Custom widget marketplace | Extensibility | Medium | VOY-SRS-Workshop-001 |
| Multi-language support | Global users | Medium | VOY-SRS-Workshop-001 |

---

## 5. Implementation Phases

### Phase 1: Ontology Foundation (Months 1-6)

**Objective:** Deliver core Ontology Engine with object/link management

| Sprint | Duration | Deliverables | SRS Reference |
|--------|----------|--------------|---------------|
| 1-2 | Month 1 | Database schema, migrations, API scaffolding | VOY-SRS-Ontology-001 §7 |
| 3-4 | Month 2 | Object type CRUD, property validation | VOY-SRS-Ontology-001 §5.1 |
| 5-6 | Month 3 | Object instance CRUD, batch operations | VOY-SRS-Ontology-001 §5.2 |
| 7-8 | Month 4 | Link types, link instances, traversal | VOY-SRS-Ontology-001 §5.3-5.4 |
| 9-10 | Month 5 | Search, filtering, pivot navigation | VOY-SRS-Ontology-001 §5.8 |
| 11-12 | Month 6 | Integration tests, performance optimization | VOY-SRS-Ontology-001 §11 |

**Exit Criteria:**
- [ ] Object types created/updated/deleted via API
- [ ] Object instances CRUD with validation
- [ ] Link types with cardinality constraints
- [ ] Link traversal (multi-hop)
- [ ] Full-text search with filtering
- [ ] 90%+ test coverage
- [ ] p95 < 100ms for object queries

### Phase 2: Actions & Functions (Months 7-9)

**Objective:** Deliver action types and custom function framework

| Sprint | Duration | Deliverables | SRS Reference |
|--------|----------|--------------|---------------|
| 13-14 | Month 7 | Action type management, execution engine | VOY-SRS-Ontology-001 §5.5 |
| 15-16 | Month 8 | Function framework (Python sandbox) | VOY-SRS-Ontology-001 §5.6 |
| 17-18 | Month 9 | Interfaces, scenarios, MCP integration | VOY-SRS-Ontology-001 §5.7, §5.9 |

**Exit Criteria:**
- [ ] Action types with input/output schemas
- [ ] Action execution with audit trail
- [ ] Side effects (notifications, webhooks)
- [ ] Python functions in sandbox
- [ ] Function versioning
- [ ] Interface definitions
- [ ] MCP tools for Ontology

### Phase 3: Visual Pipeline Builder (Months 10-15)

**Objective:** Deliver visual pipeline editor and execution engine

| Sprint | Duration | Deliverables | SRS Reference |
|--------|----------|--------------|---------------|
| 19-20 | Month 10 | PDL parser, validator, executor | VOY-SRS-PipelineBuilder-001 §3.1.5-3.1.6 |
| 21-22 | Month 11 | Transform library (100+ transforms) | VOY-SRS-PipelineBuilder-001 §3.1.3 |
| 23-24 | Month 12 | React Flow editor, node palette | VOY-SRS-PipelineBuilder-001 §3.1.2 |
| 25-26 | Month 13 | Properties panel, node configuration | VOY-SRS-PipelineBuilder-001 §3.1.4 |
| 27-28 | Month 14 | Preview system, execution monitoring | VOY-SRS-PipelineBuilder-001 §3.1.7, §3.1.10 |
| 29-30 | Month 15 | Version control, scheduling, export | VOY-SRS-PipelineBuilder-001 §3.1.8-3.1.9 |

**Exit Criteria:**
- [ ] Visual editor with drag-and-drop
- [ ] 200+ transforms available
- [ ] Pipeline execution (batch, incremental)
- [ ] Preview without full execution
- [ ] Version history with diff
- [ ] Cron/event scheduling
- [ ] Python/SQL export

### Phase 4: Workshop (Months 16-21)

**Objective:** Deliver application builder with widgets and deployment

| Sprint | Duration | Deliverables | SRS Reference |
|--------|----------|--------------|---------------|
| 31-32 | Month 16 | Widget framework, 15 core widgets | VOY-SRS-Workshop-001 §3.1.3 |
| 33-34 | Month 17 | Page builder, grid layout | VOY-SRS-Workshop-001 §3.1.2 |
| 35-36 | Month 18 | Data binding engine | VOY-SRS-Workshop-001 §3.1.4 |
| 37-38 | Month 19 | Action integration, event handlers | VOY-SRS-Workshop-001 §3.1.5 |
| 39-40 | Month 20 | Deployment, versioning, sharing | VOY-SRS-Workshop-001 §3.1.8 |
| 41-42 | Month 21 | Theming, navigation, custom scripting | VOY-SRS-Workshop-001 §3.1.6-3.1.9 |

**Exit Criteria:**
- [ ] 30+ widgets available
- [ ] Drag-and-drop page builder
- [ ] Data binding to Ontology/Pipelines/SQL
- [ ] Action triggering from UI
- [ ] Application deployment
- [ ] Multi-page navigation
- [ ] Custom themes

### Phase 5: Enterprise & Polish (Months 22-24)

**Objective:** Enterprise features, performance, and documentation

| Sprint | Duration | Deliverables | SRS Reference |
|--------|----------|--------------|---------------|
| 43-44 | Month 22 | Enhanced scheduling, media sets | VOY-SRS-PipelineBuilder-001 §3.1.9 |
| 45-46 | Month 23 | Performance optimization, load testing | All SRS §6 |
| 47-48 | Month 24 | Security audit, documentation, training | All SRS §9 |

**Exit Criteria:**
- [ ] All SRS requirements met
- [ ] Performance targets achieved
- [ ] Security audit passed
- [ ] Documentation complete
- [ ] Training materials ready

---

## 6. Resource Requirements

### 6.1 Team Composition

| Role | Phase 1-2 | Phase 3 | Phase 4 | Phase 5 | Total |
|------|-----------|---------|---------|---------|-------|
| Engineering Manager | 1 | 1 | 1 | 1 | 1 |
| Software Architect | 1 | 1 | 1 | 1 | 1 |
| Backend Engineers | 4 | 4 | 3 | 2 | 4-5 |
| Frontend Engineers | 0 | 3 | 4 | 2 | 3-4 |
| DevOps Engineer | 1 | 1 | 1 | 1 | 1-2 |
| QA Engineer | 1 | 2 | 2 | 2 | 1-2 |
| Product Manager | 1 | 1 | 1 | 1 | 1 |
| **Total** | **9** | **13** | **13** | **10** | **12-16** |

### 6.2 Infrastructure

| Component | Purpose | Monthly Cost |
|-----------|---------|--------------|
| Development Environment | Team development | $5K |
| Staging Environment | Integration testing | $3K |
| Production (Reference) | Enterprise deployment | $10-50K |
| CI/CD | GitHub Actions | $1K |
| Monitoring | Prometheus + Grafana | $1K |
| **Total Monthly** | | **$20-60K** |

### 6.3 Budget Summary

| Category | Monthly | 24-Month Total |
|----------|---------|----------------|
| Salaries (12-16 FTEs) | $180-240K | $4.3-5.8M |
| Infrastructure | $20-60K | $480K-1.4M |
| Tools & Licenses | $5-10K | $120-240K |
| Training | $2-5K | $48-120K |
| Contingency (15%) | $31-47K | $740K-1.1M |
| **Total** | **$238-362K** | **$5.7-8.7M** |

---

## 7. Risk Assessment

### 7.1 Risk Register

| Risk ID | Description | Probability | Impact | Severity | Mitigation |
|---------|-------------|-------------|--------|----------|------------|
| RSK-001 | Ontology complexity exceeds estimates | Medium | High | High | Phased delivery, MVP first |
| RSK-002 | Visual builder performance issues | Medium | Medium | Medium | Prototype early, optimize |
| RSK-003 | Widget library incomplete | Low | Medium | Low | Prioritize core widgets |
| RSK-004 | Integration testing gaps | High | Medium | High | Automated testing day 1 |
| RSK-005 | Team scaling challenges | Medium | High | High | Phased hiring, contractors |
| RSK-006 | Security vulnerabilities | Medium | High | High | Security audits quarterly |
| RSK-007 | Performance regression | Medium | High | High | Performance testing CI |
| RSK-008 | Scope creep | High | Medium | High | Strict change control |

### 7.2 Risk Response Plan

| Risk ID | Response | Owner | Trigger |
|---------|----------|-------|---------|
| RSK-001 | Mitigate: Deliver MVP, iterate | PM | Estimate > 20% |
| RSK-002 | Mitigate: Benchmark early | Architect | Load test fail |
| RSK-003 | Mitigate: Core widgets first | Frontend Lead | < 20 widgets |
| RSK-004 | Mitigate: Test-first development | QA Lead | Coverage < 80% |
| RSK-005 | Mitigate: Start hiring early | HR | Delay > 2 weeks |
| RSK-006 | Mitigate: Quarterly audits | Security | Finding > 0 |
| RSK-007 | Mitigate: Perf tests in CI | DevOps | p95 > target |
| RSK-008 | Mitigate: Change control board | PM | Scope > 10% |

---

## 8. Success Criteria

### 8.1 Phase Success Criteria

| Phase | Criterion | Measurement | Target |
|-------|-----------|-------------|--------|
| Phase 1 | Ontology MVP complete | SRS compliance | 100% critical reqs |
| Phase 2 | Actions/Functions working | Integration tests | 90%+ pass |
| Phase 3 | Visual Builder functional | E2E tests | 80%+ pass |
| Phase 4 | Workshop deployable | E2E tests | 80%+ pass |
| Phase 5 | Enterprise ready | Security audit | Pass |

### 8.2 Overall Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Feature completeness | 90%+ of planned features | SRS traceability |
| Test coverage | > 90% unit, > 85% integration | Coverage reports |
| Performance | All PERF-* targets met | Load testing |
| Security | Zero critical vulnerabilities | Security audit |
| Documentation | 100% API coverage | Doc review |
| User satisfaction | SUS > 80 | User testing |

---

## 9. Dependencies

### 9.1 External Dependencies

| Dependency | Type | Risk | Mitigation |
|------------|------|------|------------|
| PostgreSQL | Infrastructure | Low | Managed service |
| Redis | Infrastructure | Low | Managed service |
| MinIO | Infrastructure | Low | Managed service |
| Temporal | Infrastructure | Medium | Self-hosted option |
| Trino | Infrastructure | Medium | Managed option |
| Milvus | Infrastructure | Medium | Managed option |

### 9.2 Internal Dependencies

| Dependency | Type | Risk | Mitigation |
|------------|------|------|------------|
| Ontology → Pipeline Builder | Feature | High | API contract first |
| Ontology → Workshop | Feature | High | API contract first |
| Pipeline Builder → Workshop | Feature | Medium | Independent work |
| All → Core Platform | Infrastructure | Low | Stable foundation |

---

## 10. Appendices

### Appendix A: SRS Document Index

| Document | ID | Status |
|----------|-----|--------|
| Voyant Core Platform SRS | VOY-SRS-Core-001 | ✅ Complete |
| Voyant Data Ingestion SRS | VOY-SRS-Ingestion-001 | ✅ Complete |
| Voyant Analysis Engine SRS | VOY-SRS-Analysis-001 | ✅ Complete |
| Voyant SQL Engine SRS | VOY-SRS-SQL-001 | ✅ Complete |
| Voyant Search Engine SRS | VOY-SRS-Search-001 | ✅ Complete |
| Voyant Streaming SRS | VOY-SRS-Streaming-001 | ✅ Complete |
| Voyant Scraper SRS | VOY-SRS-Scraper-001 | ✅ Complete |
| Voyant MCP Tools SRS | VOY-SRS-MCP-001 | ✅ Complete |
| Voyant Governance SRS | VOY-SRS-Governance-001 | ✅ Complete |
| **Voyant Ontology SRS** | **VOY-SRS-Ontology-001** | **🔧 New** |
| **Voyant Pipeline Builder SRS** | **VOY-SRS-PipelineBuilder-001** | **🔧 New** |
| **Voyant Workshop SRS** | **VOY-SRS-Workshop-001** | **🔧 New** |

### Appendix B: Technology Stack Summary

| Layer | Current | Target |
|-------|---------|--------|
| Backend | Django 5.0 + Django Ninja | Same |
| Frontend | Lit Web Components | React 18 + TypeScript |
| Workflow | Temporal.io | Same |
| Database | PostgreSQL 16 | Same |
| Analytical DB | DuckDB + Trino | Same |
| Object Storage | MinIO | Same |
| Message Queue | Apache Kafka | Same |
| Cache | Redis | Same |
| Vector DB | Milvus | Same |
| Auth | Keycloak | Same |
| AuthZ | SpiceDB | Same |
| Observability | Prometheus + OTel | Same |

### Appendix C: Glossary

| Term | Definition |
|------|------------|
| **Ontology** | Semantic knowledge graph connecting data to real-world entities |
| **PDL** | Pipeline Definition Language — declarative pipeline representation |
| **Workshop** | Low-code application builder |
| **Widget** | Reusable UI component |
| **Data Binding** | Connection between widget property and data source |
| **Action** | Ontology operation that mutates state |
| **Function** | Custom business logic in Python/TypeScript |
| **Interface** | Type contract for object types |
| **Scenario** | Isolated branch for experimentation |

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
| Architecture Lead | _________________ | ________ | _________ |

---

**Document Status:** DRAFT
**Classification:** Internal
**Retention:** 7 years
**Next Review:** 2026-08-20
