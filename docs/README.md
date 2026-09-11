# Voyant v4.0.0 — Documentation Index

**Document ID:** VOYANT-DOCS-INDEX-4.0.0
**Version:** 6.0.0
**Date:** 2026-09-11
**Status:** Active
**Compliance:** ISO/IEC/IEEE 29148:2018 · ISO/IEC/IEEE 42010:2011 · ISO 9001:2015

---

## How This Index Works

**Rules:**
1. `VOYANT-UDP-V4.0.md` is THE plan. All other plan documents are archived.
2. Module docs (`VOYANT-MOD-*.md`) are the single authoritative reference per module — requirements + design combined.
3. Normative specs (SRS, SAD, STP) define cross-cutting requirements.
4. Any agent reads the Unified Plan first. Module docs second. Specs third. Archive never.
5. All documents follow ISO/IEC/IEEE naming: `VOYANT-{TYPE}-{SCOPE}-{VERSION}.md`

---

## 1. ACTIVE PLAN (Single Source of Truth)

| Document | ID | Purpose | Status |
|----------|-----|---------|--------|
| **[Unified Development Plan](VOYANT_V4_UNIFIED_PLAN.md)** | VOYANT-UDP-V4.0 | THE plan: 6 tracks, 16 weeks, master checklist per module | **ACTIVE** |

Supersedes: SDP, PDP, Rapid Dev Plan, UI Plan, Frontend Plan (all archived).

---

## 2. NORMATIVE SPECIFICATIONS (ISO — WHAT to build)

| Document ID | File | ISO Standard | Lines |
|-------------|------|-------------|-------|
| VOYANT-SRS-V4.0 | [VOYANT-SRS-V4.0.md](specifications/v4.0/VOYANT-SRS-V4.0.md) | ISO/IEC/IEEE 29148:2018 | ~460 |
| VOYANT-SCRAPER-SRS-V4.0 | [VOYANT-SCRAPER-SRS-V4.0.md](specifications/v4.0/VOYANT-SCRAPER-SRS-V4.0.md) | ISO/IEC/IEEE 29148:2018 | 500 |
| VOYANT-SAD-V4.0 | [VOYANT-SAD-V4.0.md](specifications/v4.0/VOYANT-SAD-V4.0.md) | ISO/IEC/IEEE 42010:2011 | 271 |
| VOYANT-STP-V4.0 | [VOYANT-STP-V4.0.md](specifications/v4.0/VOYANT-STP-V4.0.md) | ISO/IEC/IEEE 29119-1:2013 | 252 |
| VOYANT-OVS-1.0 | [VOYANT-OVS-1.0.md](specifications/v4.0/VOYANT-OVS-1.0.md) | ISO/IEC 29148 · 25010 · 42010 | 597 |
| VOYANT-MERGE-SPEC-V4.0 | [VOYANT-MERGE-SPEC-V4.0.md](specifications/v4.0/VOYANT-MERGE-SPEC-V4.0.md) | Internal | ~470 |
| VOYANT-SOC2-V4.0 | [VOYANT-SOC2-V4.0.md](specifications/v4.0/VOYANT-SOC2-V4.0.md) | Internal | — |
| VOYANT-GRAPH-DESIGN-V1.0 | [VOYANT-GRAPH-DESIGN-V1.0.md](specifications/v4.0/VOYANT-GRAPH-DESIGN-V1.0.md) | Internal | — |

---

## 3. MODULE SPECIFICATIONS (Single Source Per Module)

Each module has ONE authoritative doc containing ISO requirements + detailed design.

| # | Module | Document ID | File | Lines | Content |
|---|--------|-------------|------|-------|---------|
| M1 | Voyant Connect | VOYANT-MOD-CONNECT-V4.0 | [VOYANT-MOD-CONNECT-V4.0.md](specifications/v4.0/VOYANT-MOD-CONNECT-V4.0.md) | 798 | Pipeline Builder: DAG validation, 12 transforms, import/export |
| M3 | Voyant Catalog | VOYANT-MOD-CATALOG-V4.0 | [VOYANT-MOD-CATALOG-V4.0.md](specifications/v4.0/VOYANT-MOD-CATALOG-V4.0.md) | 2,787 | 43 FRs, 12 models, query engine, time travel, PII, quality |
| M5 | Voyant Analyze | VOYANT-MOD-ANALYZE-V4.0 | [VOYANT-MOD-ANALYZE-V4.0.md](specifications/v4.0/VOYANT-MOD-ANALYZE-V4.0.md) | 2,181 | SQL Console, Trino, Milvus, Iceberg, Kafka |
| M6 | Voyant ML | VOYANT-MOD-ML-V4.0 | [VOYANT-MOD-ML-V4.0.md](specifications/v4.0/VOYANT-MOD-ML-V4.0.md) | 2,769 | MLflow compat, drift detection, model serving, agents |
| M7 | Voyant Agent | VOYANT-MOD-AGENT-V4.0 | [VOYANT-MOD-AGENT-V4.0.md](specifications/v4.0/VOYANT-MOD-AGENT-V4.0.md) | 2,426 | Intent Engine, 80 MCP tools, Capsules, CLI, OSDK |
| M8 | Voyant Scrape | VOYANT-MOD-SCRAPE-V4.0 | [VOYANT-MOD-SCRAPE-V4.0.md](specifications/v4.0/VOYANT-MOD-SCRAPE-V4.0.md) | 1,850 | 9 arms, deep research v2, CAPTCHA, anti-bot, templates |
| M9 | Voyant Shield | VOYANT-MOD-SHIELD-V4.0 | [VOYANT-MOD-SHIELD-V4.0.md](specifications/v4.0/VOYANT-MOD-SHIELD-V4.0.md) | 670 | RLS, column masking, GDPR, SOC2, RBAC |
| M10 | Voyant Workspace | VOYANT-MOD-WORKSPACE-V4.0 | [VOYANT-MOD-WORKSPACE-V4.0.md](specifications/v4.0/VOYANT-MOD-WORKSPACE-V4.0.md) | 767 | Workspaces, notifications, approvals, WebSocket |
| M11 | Voyant Admin | VOYANT-MOD-ADMIN-V4.0 | [VOYANT-MOD-ADMIN-V4.0.md](specifications/v4.0/VOYANT-MOD-ADMIN-V4.0.md) | 630 | System dashboard, jobs, settings, tenants |
| M12 | Voyant API | VOYANT-MOD-API-V4.0 | [VOYANT-MOD-API-V4.0.md](specifications/v4.0/VOYANT-MOD-API-V4.0.md) | 895 | REST API, Python/TS/Go/Java SDKs, CLI |
| — | UI/UX Design | VOYANT-MOD-UIUX-V4.0 | [VOYANT-MOD-UIUX-V4.0.md](specifications/v4.0/VOYANT-MOD-UIUX-V4.0.md) | 764 | 38 views, 16 components, design system, WCAG |

**Total: 11 module specs, 16,537 lines**

---

## 4. COMPETITIVE ANALYSIS

| Document ID | File | Lines | Content |
|-------------|------|-------|---------|
| VOYANT-COMPETITIVE-V4.0 | [VOYANT-COMPETITIVE-V4.0.md](specifications/v4.0/VOYANT-COMPETITIVE-V4.0.md) | 4,208 | Palantir feature map + 3-way benchmark + 40 user journeys |

---

## 5. ARCHITECTURE (Reference)

| Document ID | File | Content |
|-------------|------|---------|
| VOYANT-ARCH-V4.0 | [ARCHITECTURE_OVERVIEW.md](architecture/ARCHITECTURE_OVERVIEW.md) | 7 design goals, 5-layer architecture |
| VOYANT-SYSARCH-V4.0 | [voyant_system_architecture.md](architecture/voyant_system_architecture.md) | 10 modules, tool manifest, infrastructure |
| VOYANT-STRUCT-V4.0 | [PROJECT_STRUCTURE.md](architecture/PROJECT_STRUCTURE.md) | Directory layout, core lib, OCTOPUS engine |
| VOYANT-RBAC-V3.1 | [RBAC_ARCHITECTURE.md](architecture/RBAC_ARCHITECTURE.md) | 3-layer defense-in-depth, SpiceDB |
| VOYANT-SCRAPER-ARCH | [scraper_architecture.md](architecture/scraper_architecture.md) | Agent-Tool paradigm, OCTOPUS arms |
| ADR-001 | [001-technology-stack-choice.md](architecture/adr/001-technology-stack-choice.md) | Django 5 + Temporal + Trino |
| ADR-002 | [002-governance-systems.md](architecture/adr/002-governance-systems.md) | Keycloak + SpiceDB + Vault |
| ADR-003 | [003-intent-engine-trust-boundary.md](architecture/adr/003-intent-engine-trust-boundary.md) | LLM Proposes, Code Disposes |
| ADR-004 | [004-frontend-stack-lit.md](architecture/adr/004-frontend-stack-lit.md) | Lit 3 (not React) |

---

## 6. DEVELOPMENT & OPERATIONS (Reference)

| Document ID | File | Content |
|-------------|------|---------|
| VOYANT-TEST-STRAT | [TESTING_STRATEGY.md](development/TESTING_STRATEGY.md) | 148 test files, 2,203 functions |
| VOYANT-DEPLOY-V4.0 | [DEPLOYMENT.md](operations/DEPLOYMENT.md) | Standalone (20 services) + Integrated (3 services) |
| VOYANT-DR-RUNBOOK | [RUNBOOK.md](../scripts/ops/RUNBOOK.md) | 9 failure scenarios, backup strategy |

---

## 7. PROJECT RULES

| Document | File | Content |
|----------|------|---------|
| RULES.md | [RULES.md](../RULES.md) | 12 VIBE coding rules (non-negotiable) |
| README.md | [README.md](../README.md) | Project overview, setup, API docs |

---

## 8. ARCHIVE (Historical — Not Active)

| Directory | Content |
|-----------|---------|
| [archive/pre-v4.0/](archive/pre-v4.0/) | Pre-v4.0 specs, audits, compliance reports (26 files) |
| [archive/v4.0-superseded-plans/](archive/v4.0-superseded-plans/) | SDP, PDP, Rapid Dev Plan, UI Plan, Frontend Plan |

---

## 9. CURRENT PROJECT STATUS

| Metric | Value |
|--------|-------|
| Version | 4.0.0 |
| Python LOC | ~73,416 |
| TypeScript LOC | ~9,099 |
| Django apps | 22 |
| REST endpoints | ~240 |
| MCP tools | 80 |
| Temporal workflows | 17 |
| Test functions | 2,203 (2,128 passing, 51 skipped, 0 failing) |
| Playwright E2E | 17/17 passing |
| Docker services | 20 |
| SRS completion (high-level) | 83% (69/89) |
| ISO FR completion (detailed) | 96% (363/377) |
| Remaining gaps | 14 (2 P0, 7 P1, 5 P2) |

---

## 10. DOCUMENT CONTROL

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 4.0.0 | 2026-09-08 | Voyant Engineering | Unified plan created; scattered plans archived; index restructured |
| 4.1.0 | 2026-09-09 | MiMoCode Agent | Added 8 module design docs (14,343 lines); competitive benchmark + user journeys |
| 5.0.0 | 2026-09-16 | MiMoCode Agent | Module naming standardization: all modules use Voyant [Name] (M1–M16) scheme |
| 6.0.0 | 2026-09-11 | MiMoCode Agent | **Documentation overhaul.** ISO-compliant file naming (VOYANT-{TYPE}-{VERSION}.md). Merged 16 duplicate module docs into 11. Merged 3 competitive analysis docs into 1. Updated all versions from 3.0.0 to 4.0.0. Reconciled SRS from 57% to 83%. Renamed architecture DESIGN.md to ARCHITECTURE_OVERVIEW.md. Pruned dead links. |

---

**Maintained by:** Voyant Engineering
**Review cycle:** Every sprint
**Change control:** Only the Unified Development Plan may be modified for active work items. Spec changes require SRS-ID traceability.
**Naming convention:** All documents follow `VOYANT-{TYPE}-{SCOPE}-{VERSION}.md` per ISO/IEC/IEEE 29148:2018 §6.4.
