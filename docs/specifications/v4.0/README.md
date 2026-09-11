# Voyant v4.0 — Specifications

**Directory:** `docs/specifications/v4.0/`
**Status:** Active
**Last Updated:** 2026-09-08

---

## Documents in This Directory

| File | Document ID | ISO Standard | Purpose | Status |
|------|-------------|-------------|---------|--------|
| `VOYANT_SRS_V4.md` | VOYANT-SRS-4.0.0 | ISO/IEC/IEEE 29148:2018 | Software Requirements Specification — 89 requirements across 7 domains | Active (Reference) |
| `VOYANT_SCRAPER_SRS_V4.md` | VOYANT-SCRAPER-SRS-4.0.0 | ISO/IEC/IEEE 29148:2018 | Voyant Scrape (M8) SRS — 30 requirements, Octoparse parity | Active (Reference) |
| `VOYANT_SAD_V4.md` | VOYANT-SAD-4.0.0 | ISO/IEC/IEEE 42010:2011 | System Architecture — 9-layer architecture, 30 services | Active (Reference) |
| `VOYANT_STP_V4.md` | VOYANT-STP-4.0.0 | ISO/IEC/IEEE 29119-1:2013 | Software Test Plan — 200+ tests across 10 domains | Active (Reference) |
| `PALANTIR_FEATURE_MAP.md` | PALANTIR-FEATURE-MAP-4.0.0 | Internal | Complete gap analysis vs Palantir Foundry (114 features) | Active (Reference) |
| `ONTOLOGY_VIEWER_SPEC.md` | VOYANT-ONTOLOGY-VIEWER-SPEC-1.0 | ISO/IEC 29148 · 25010 · 42010 | Ontology Viewer & Designer — 5 views, interactions, algorithms (597 lines) | Normative for T2 |
| `VOYANT_COMPETITIVE_BENCHMARK.md` | VOYANT-CB-4.0.0 | Internal | Deep competitive benchmark: Palantir + Databricks vs Voyant (1,046 lines, 520 table rows) | Active (Reference) |
| `VOYANT_USER_JOURNEYS.md` | VOYANT-UJ-4.0.0 | Internal | 40 complete user journeys: Palantir vs Databricks vs Voyant step-by-step (2,796 lines) | Active (Reference) |
| `MODULE_ONTOLOGY_ENGINE.md` | VOYANT-MOD-ONT-4.0.0 | Internal | Voyant Catalog (M3) deep design: 12 models, services, APIs, Palantir comparison (1,762 lines) | Active (Reference) |
| `MODULE_DATA_INTELLIGENCE.md` | VOYANT-MOD-DI-4.0.0 | Internal | Voyant Analyze (M5) deep design: Trino, Milvus, Iceberg, Kafka, Temporal (1,418 lines) | Active (Reference) |
| `MODULE_ML_AI_PLATFORM.md` | VOYANT-MOD-ML-4.0.0 | Internal | Voyant ML (M6) deep design: MLflow compat, AIP comparison, serving (1,846 lines) | Active (Reference) |
| `MODULE_SCRAPER_OCTOPUS.md` | VOYANT-MOD-SCR-4.0.0 | Internal | Voyant Scrape (M8) deep design: 9 arms, anti-bot, templates, deep research (1,252 lines) | Active (Reference) |
| `MODULE_UI_UX_DESIGN.md` | VOYANT-MOD-UI-4.0.0 | Internal | Voyant UI/UX deep design: all 13 views, 13 components, design system, WCAG (437 lines) | Active (Reference) |
| `MODULE_AGENT_PLATFORM.md` | VOYANT-MOD-AP-4.0.0 | Internal | Voyant Agent (M7) deep design: Intent Engine, MCP, Capsules, CLI (1,714 lines) | Active (Reference) |

## Superseded Documents

The following plans were archived to `docs/archive/v4.0-superseded-plans/` on 2026-09-08:

| Former File | Document ID | Superseded By | Reason |
|-------------|-------------|---------------|--------|
| `VOYANT_SDP_V4.md` | VOYANT-SDP-4.0.0 | VOYANT-UDP-4.0.0 | Delivery sequencing consolidated into Unified Plan |
| `VOYANT_PDP_V4.md` | VOYANT-PDP-4.0.0 | VOYANT-UDP-4.0.0 | Track structure absorbed into Unified Plan |
| `VOYANT_RAPID_DEVELOPMENT_PLAN.md` | VOYANT-RDP-4.0.0 | VOYANT-UDP-4.0.0 | Phase structure absorbed into Unified Plan |

## Normative Reference

The **active plan** for all development work is:
- **[VOYANT_V4_UNIFIED_PLAN.md](../../VOYANT_V4_UNIFIED_PLAN.md)** — VOYANT-UDP-4.0.0

This is the single source of truth. Any agent reads this document to know what to build next.
