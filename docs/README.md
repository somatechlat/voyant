# Voyant v4.0 — Documentation Index

**Document ID:** VOYANT-DOCS-INDEX-4.0.0
**Version:** 5.0.0
**Date:** 2026-09-16
**Status:** Active
**Compliance:** ISO/IEC/IEEE 29148 · ISO/IEC 42010 · ISO 9001

---

## How This Index Works

**Rules:**
1. `VOYANT_V4_UNIFIED_PLAN.md` is THE plan. All other plan documents are archived.
2. Specifications (SRS, SAD, STP) are **reference** — they define WHAT to build.
3. Module design docs are **deep per-module documentation** — they define HOW to build.
4. The Unified Plan defines WHEN — with a per-item checklist.
5. Any agent reads the Unified Plan first. Module docs second. Specs third. Archive never.

---

## 1. ACTIVE PLAN (Single Source of Truth)

| Document | ID | Purpose | Status |
|----------|-----|---------|--------|
| **[Unified Development Plan](VOYANT_V4_UNIFIED_PLAN.md)** | VOYANT-UDP-4.0.0 | THE plan: 6 tracks, 16 weeks, master checklist per module | **ACTIVE** |

This document supersedes all prior plans:
- ~~VOYANT-SDP-4.0.0~~ → archived
- ~~VOYANT-PDP-4.0.0~~ → archived
- ~~VOYANT-RDP-4.0.0~~ → archived
- ~~FRONTEND_DEVELOPMENT_PLAN.md~~ → archived
- ~~UI_DEVELOPMENT_PLAN.md~~ → archived
- ~~dashboard/PLAN.md~~ → removed

---

## 2. NORMATIVE SPECIFICATIONS (ISO — WHAT to build)

| Document | ISO Standard | ID | Lines |
|----------|-------------|-----|-------|
| [Software Requirements Specification](specifications/v4.0/VOYANT_SRS_V4.md) | ISO/IEC/IEEE 29148:2018 | VOYANT-SRS-4.0.0 | 442 |
| [Scraper Module SRS](specifications/v4.0/VOYANT_SCRAPER_SRS_V4.md) | ISO/IEC/IEEE 29148:2018 | VOYANT-SCRAPER-SRS-4.0.0 | 500 |
| [System Architecture Document](specifications/v4.0/VOYANT_SAD_V4.md) | ISO/IEC/IEEE 42010:2011 | VOYANT-SAD-4.0.0 | 271 |
| [Software Test Plan](specifications/v4.0/VOYANT_STP_V4.md) | ISO/IEC/IEEE 29119-1:2013 | VOYANT-STP-4.0.0 | 252 |
| [Ontology Viewer Specification](specifications/v4.0/ONTOLOGY_VIEWER_SPEC.md) | ISO/IEC 29148 · 25010 · 42010 | VOYANT-OVS-1.0.0 | 597 |
| [Palantir Feature Map](specifications/v4.0/PALANTIR_FEATURE_MAP.md) | Internal | PALANTIR-FM-4.0.0 | 339 |
| [MIMO Merge Specification](specifications/v4.0/VOYANT_MIMO_MERGE_SPEC.md) | Internal | VOYANT-MERGE-SPEC-4.0.0 | ~1,200 |

---

## 3. COMPETITIVE BENCHMARKING & MODULE DESIGN (12,234 lines total)

### 3.1 Module Name Reference

| # | Module Name | Code Domain | Description |
|---|-------------|-------------|-------------|
| M1 | Voyant Connect | ingestion, discovery | Source ingestion and discovery |
| M2 | Voyant Pipeline | pipelines, worker | Pipeline orchestration and Temporal workers |
| M3 | Voyant Catalog | ontology | Ontology engine and data catalog |
| M4 | Voyant Lakehouse | storage, iceberg | Iceberg-based data lakehouse |
| M5 | Voyant Analyze | sql, dashboard | SQL analytics and dashboards |
| M6 | Voyant ML | ml_platform | ML experiments, registry, and serving |
| M7 | Voyant Agent | intent, mcp, capsules | Intent engine, MCP tools, capsules |
| M8 | Voyant Scrape | scraper | Web scraping and deep research |
| M9 | Voyant Shield | governance | RBAC, RLS, masking, audit |
| M10 | Voyant Workspace | new | Collaboration and workspaces |
| M11 | Voyant Admin | admin_panel | Admin dashboard and operations |
| M12 | Voyant API | core, api, sdk, cli | Core API, SDK, and CLI |
| M13 | Voyant Features | new | Feature store |
| M14 | Voyant Notify | new | Notifications |
| M15 | Voyant Approve | new | Approval workflows |
| M16 | Voyant Validate | new | Data validation |

### 3.2 Competitive Analysis

| Document | Lines | Content |
|----------|-------|---------|
| [Competitive Benchmark](specifications/v4.0/VOYANT_COMPETITIVE_BENCHMARK.md) | 1,046 | 25-dimension 3-way comparison, 520 table rows, 41 Palantir screens, 44 Databricks screens |
| [User Journeys](specifications/v4.0/VOYANT_USER_JOURNEYS.md) | 2,796 | 40 journeys across 7 roles: Palantir vs Databricks vs Voyant step-by-step |
| [MIMO Merge Specification](specifications/v4.0/VOYANT_MIMO_MERGE_SPEC.md) | ~1,200 | 205 MIMO FRs mapped, 115 merge items, 4-phase implementation plan |

### 3.2 Module Deep Design Documents

| Document | Lines | Content |
|----------|-------|---------|
| [Voyant Catalog (M3)](specifications/v4.0/MODULE_ONTOLOGY_ENGINE.md) | 1,762 | 12 models, service layer, APIs, MCP tools, Palantir comparison |
| [Voyant Analyze (M5)](specifications/v4.0/MODULE_DATA_INTELLIGENCE.md) | 1,418 | Trino 3-layer validation, Milvus hybrid search, Iceberg, Kafka, Temporal |
| [Voyant ML (M6)](specifications/v4.0/MODULE_ML_AI_PLATFORM.md) | 1,846 | MLflow compat, AIP comparison, model serving, feature store |
| [Voyant Scrape (M8)](specifications/v4.0/MODULE_SCRAPER_OCTOPUS.md) | 1,252 | 9 arms, deep research v2, SSRF defense, anti-bot design |
| [UI/UX Design](specifications/v4.0/MODULE_UI_UX_DESIGN.md) | 437 | All 13 views, 13 components, design system, wireframes, WCAG |
| [Voyant Agent (M7)](specifications/v4.0/MODULE_AGENT_PLATFORM.md) | 1,714 | Intent Engine, 69 MCP tools, Capsules, CLI, OSDK, WebSocket |

**Grand Total: 22,661 lines of documentation across 53 active files.**

### 3.3 ISO Module Functional Specifications (7,061 lines)

| Document | Lines | FR-IDs | Wireframes | Content |
|----------|-------|--------|------------|---------|
| [Voyant Catalog](specifications/v4.0/ISO_MODULE_CATALOG.md) | 809 | 42 | 6 | Ontology: 12 models, query engine, time travel, PII detection, quality scoring |
| [Voyant Analyze](specifications/v4.0/ISO_MODULE_ANALYZE.md) | 533 | 23 | 3 | SQL Console: SavedQuery, Trino read-only, query execution |
| [Voyant Connect](specifications/v4.0/ISO_MODULE_CONNECT.md) | 798 | 46 | 5 | Pipeline Builder: DAG validation, 12 transform types, import/export |
| [Voyant Scrape](specifications/v4.0/ISO_MODULE_SCRAPE.md) | 591 | 29 | — | 4-tier CAPTCHA, proxy manager, fingerprint, template engine |
| [Voyant ML](specifications/v4.0/ISO_MODULE_ML.md) | 663 | 31 | — | MLflow compat (19 endpoints), drift detection, model serving |
| [Voyant Agent](specifications/v4.0/ISO_MODULE_AGENT.md) | 705 | 33 | — | Intent Engine pipeline, 62 MCP tools, Capsules, CLI |
| [Voyant Shield](specifications/v4.0/ISO_MODULE_SHIELD.md) | 670 | — | — | RLS, column masking, GDPR, SOC2, RBAC architecture |
| [Voyant Workspace](specifications/v4.0/ISO_MODULE_WORKSPACE.md) | 767 | — | — | Workspaces, notifications, approvals, WebSocket protocol |
| [Voyant Admin](specifications/v4.0/ISO_MODULE_ADMIN.md) | 630 | — | — | System dashboard, jobs, settings, tenants, health checks |
| [Voyant API](specifications/v4.0/ISO_MODULE_API.md) | 895 | — | — | REST API, Python/TS SDKs, CLI command reference |

---

## 4. ARCHITECTURE (Reference)

| Document | Content |
|----------|---------|
| [System Architecture](architecture/voyant_system_architecture.md) | 10 modules, tool manifest, infrastructure |
| [Project Structure](architecture/PROJECT_STRUCTURE.md) | Directory layout, core lib modules, OCTOPUS engine |
| [RBAC Architecture](architecture/RBAC_ARCHITECTURE.md) | 3-layer defense-in-depth, SpiceDB, 816 lines |
| [Scraper Architecture](architecture/scraper_architecture.md) | Agent-Tool paradigm, OCTOPUS arms |
| [Design Overview](architecture/DESIGN.md) | 7 design goals, 5-layer architecture |
| [ADR Index](architecture/adr/README.md) | Architecture Decision Records |
| [ADR-001: Technology Stack](architecture/adr/001-technology-stack-choice.md) | Django 5 + Temporal + Trino (Accepted 2026-01-12) |
| [ADR-002: Governance Systems](architecture/adr/002-governance-systems.md) | Keycloak + SpiceDB + Vault (Accepted 2026-09-08) |
| [ADR-003: Intent Trust Boundary](architecture/adr/003-intent-engine-trust-boundary.md) | LLM Proposes, Code Disposes (Accepted 2026-09-08) |
| [ADR-004: Frontend Stack](architecture/adr/004-frontend-stack-lit.md) | Lit 3 (not React) (Accepted 2026-09-08) |
| [Module Docs](architecture/modules/README.md) | 9 per-module documentation files |

---

## 5. DEVELOPMENT & OPERATIONS (Reference)

| Document | Content |
|----------|---------|
| [Testing Strategy](development/TESTING_STRATEGY.md) | 131 test files, 2,203 functions, pytest config |
| [Deployment Guide](operations/DEPLOYMENT.md) | Standalone (20 services) + Integrated (3 services) |
| [DR Runbook](../scripts/ops/RUNBOOK.md) | 9 failure scenarios, backup strategy |
| [Operations CLI](../scripts/ops/voyant.sh) | Bootstrap/backup/restore/doctor |

---

## 6. PROJECT RULES

| Document | Content |
|----------|---------|
| [RULES.md](../RULES.md) | 12 VIBE coding rules (non-negotiable) |
| [README.md](../README.md) | Project overview, setup, API docs |

---

## 7. ARCHIVE (Historical — Not Active)

| Directory | Content |
|-----------|---------|
| [archive/pre-v4.0/](archive/pre-v4.0/) | Pre-v4.0 specs, audits, compliance reports |
| [archive/v4.0-superseded-plans/](archive/v4.0-superseded-plans/) | SDP, PDP, Rapid Dev Plan, UI Plan, Frontend Plan |

---

## 8. DOCUMENT CONTROL

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 4.0.0 | 2026-09-08 | Voyant Engineering | Unified plan created; scattered plans archived; index restructured |
| 4.1.0 | 2026-09-09 | MiMoCode Agent | Added 8 module design docs (14,343 lines); added competitive benchmark + user journeys |
| 5.0.0 | 2026-09-16 | MiMoCode Agent | Module naming standardization: all modules use Voyant [Name] (M1–M16) scheme. Added module name reference table. |

---

**Maintained by:** Voyant Engineering
**Review cycle:** Every sprint
**Change control:** Only the Unified Development Plan may be modified for active work items. Spec changes require SRS-ID traceability.
