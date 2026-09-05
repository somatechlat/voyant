# Voyant v4.0 — Software Development Plan

**Document ID:** VOYANT-SDP-4.0.0
**Version:** 4.0.0-draft
**Date:** 2026-09-05
**Standard:** ISO 9001:2015 §8.3 (Design & Development)
**Status:** Draft for Review

---

## 1. Development Approach

### 1.1 Methodology
Iterative, incremental development with weekly releases. Each phase delivers working software with tests, documentation, and ISO traceability.

### 1.2 Principles
1. Test before declare done — `pytest` 0 failures
2. No dead code — `ruff check --select F` 0 errors
3. No duplicate code — extract to `core/lib/` if pattern repeats 2+ times
4. Real interfaces only — every UI page fully functional
5. ISO compliance — SRS requirement ID traceability, >80% coverage
6. Lint clean — `ruff check apps/ --select E,F,W,I` 0 errors
7. Django check clean — `manage.py check --deploy` 0 issues
8. Documentation matches code — endpoint/tool/model counts must agree
9. Functions <100 lines — split if exceeded
10. Commit per unit — don't accumulate 20+ file changes
11. Security first — auth + validation on every new endpoint
12. Performance aware — <200ms p95, indexed queries

---

## 2. Team Structure

| Role | Count | Responsibilities |
|------|-------|-----------------|
| Backend Engineer | 2 | Ontology, ML, API, Temporal workflows |
| Frontend Engineer | 1 | Lit 3 dashboard, visual builders, ECharts |
| Data Engineer | 1 | NiFi, Iceberg, Spark, Flink, Kafka |
| DevOps (part-time) | 0.5 | Docker, CI/CD, monitoring |
| **Total** | **4.5** | |

---

## 3. Phase Plan

### Phase 1: Ontology Engine + Intent Engine (Weeks 1–6)

| Week | Deliverable | SRS ID | Engineer |
|------|-------------|--------|----------|
| 1 | Interface model + API | ONT-F-018 | Backend 1 |
| 1 | StructType model + API | ONT-F-020 | Backend 2 |
| 2 | SharedProperty model + API | ONT-F-021 | Backend 1 |
| 2 | ValueType model + API | ONT-F-022 | Backend 2 |
| 3 | ActionType model + API | ONT-F-026 | Backend 1 |
| 3 | Function model + API | ONT-F-029 | Backend 2 |
| 4 | Object Set Service (high-scale query) | ONT-F-030 | Backend 1 |
| 4 | Subscription Service (Redis Pub/Sub) | ONT-F-032 | Backend 2 |
| 5 | Intent Engine: query intent + LLM router | API-F-007 | Backend 1 |
| 5 | Intent Engine: pipeline intent + scraper intent | API-F-008 | Backend 2 |
| 6 | Ontology Explorer UI (table, grid, graph) | UI-F-001 | Frontend |
| 6 | Integration tests + docs | — | All |

### Phase 2: Scraper Octopus (Weeks 1–8, parallel)

| Week | Deliverable | SRS ID | Engineer |
|------|-------------|--------|----------|
| 1–2 | Template engine + ScrapeTemplate model | SCR-F-010 | Data Eng |
| 3 | 50 templates (Amazon, Maps, Twitter, etc.) | SCR-F-011 | Data Eng |
| 4 | Task CRUD + scheduling + ScrapeRun model | SCR-F-001 | Data Eng |
| 5 | CAPTCHA solver integration | SCR-F-005 | Data Eng |
| 6 | IP rotation + residential proxy | SCR-F-006 | Data Eng |
| 7 | Browser fingerprint randomizer | SCR-F-007 | Data Eng |
| 8 | Export engine + CLI + MCP tools | SCR-F-017 | Data Eng |

### Phase 3: ML Platform (Weeks 7–12)

| Week | Deliverable | SRS ID | Engineer |
|------|-------------|--------|----------|
| 7 | Experiment model + API | ML-F-001 | Backend 1 |
| 8 | Model registry + versioning | ML-F-003 | Backend 1 |
| 9 | Model serving endpoints | ML-F-004 | Backend 2 |
| 10 | MLflow-compatible REST API | ML-F-005 | Backend 1 |
| 11 | Agent definition + evaluation | ML-F-006 | Backend 2 |
| 12 | Agent deployment + monitoring | ML-F-008 | Backend 1 |

### Phase 4: Visual Builders (Weeks 9–14)

| Week | Deliverable | SRS ID | Engineer |
|------|-------------|--------|----------|
| 9–10 | Object Type Builder (Lit 3) | UI-F-002 | Frontend |
| 11 | Action Builder (Lit 3) | UI-F-004 | Frontend |
| 12 | Function Editor (Monaco + Lit) | UI-F-005 | Frontend |
| 13 | Pipeline Builder (Lit + DAG canvas) | UI-F-008 | Frontend |
| 14 | Scraper Visual Builder (Lit + workflow canvas) | SCR-F-002 | Frontend |

### Phase 5: Governance & Polish (Weeks 15–20)

| Week | Deliverable | SRS ID | Engineer |
|------|-------------|--------|----------|
| 15 | Row-level security (Ranger integration) | GOV-F-003 | Backend 1 |
| 16 | Column-level masking | GOV-F-004 | Backend 2 |
| 17 | Unified catalog UI | GOV-F-001 | Frontend |
| 18 | Dashboard builder (ECharts + Lit) | UI-F-008 | Frontend |
| 19 | CLI tool | API-F-005 | Backend 1 |
| 20 | TypeScript + Python SDK | API-F-003 | Backend 2 |

### Phase 6: Enterprise (Weeks 21–24)

| Week | Deliverable | SRS ID | Engineer |
|------|-------------|--------|----------|
| 21 | Kafka event integration | API-F-006 | Data Eng |
| 22 | GDPR compliance | GOV-F-009 | Backend 1 |
| 23 | Performance optimization (1M+ objects) | SCR-NF-003 | Backend 2 |
| 24 | ISO documentation finalization | — | All |

---

## 4. Quality Gates (Every Week)

| Gate | Criteria | Tool |
|------|----------|------|
| Tests | 0 failures, >80% coverage | `pytest` |
| Lint | 0 errors | `ruff check` |
| Django check | 0 issues | `manage.py check --deploy` |
| Security | No new auth bypasses | Manual review |
| Docs | SRS IDs traced to code | Manual review |
| Performance | <200ms p95 | Load test |

---

## 5. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| CAPTCHA solver reliability | High | High | Multi-provider fallback |
| Visual builder complexity | Medium | High | Use proven Lit patterns, start simple |
| MLflow API compatibility | Low | Medium | Use MLflow's test suite |
| Performance at scale | Medium | High | Load test weekly, optimize early |
| Scope creep | High | High | Strict phase boundaries |
| Intent engine accuracy | Medium | Medium | Cache common patterns, validate against ontology |

---

## 6. Tools & Environment

| Tool | Purpose |
|------|---------|
| Python 3.11 | Runtime |
| Django 5 + Ninja | Backend framework |
| Lit 3 + Vite | Frontend framework |
| Temporal.io | Workflow orchestration |
| Docker Compose | Local development |
| pytest | Testing |
| ruff | Linting |
| mypy | Type checking |
| Git | Version control |
| Prometheus + Grafana | Monitoring |

---

**Created:** 2026-09-05
**Next review:** 2026-09-12
