# Voyant v4.0 — Product Delivery Plan (PDP)

## Document Control

| Field | Value |
|---|---|
| Document ID | VOYANT-PDP-4.0.0 |
| Title | Voyant v4.0 Product Delivery Plan — Production Release |
| Status | Draft for Review |
| Version | 1.0.0 |
| Date | 2026-09-08 |
| Supersedes | VOYANT-SDP-4.0.0 (delivery sequencing only; SRS/SAD remain normative) |
| Compliance | ISO 9001:2015 §8.3 (Design & Development), ISO/IEC/IEEE 29148:2018 (Requirements), ISO/IEC/IEEE 42010:2011 (Architecture), ISO/IEC/IEEE 29119-1:2013 (Testing), ISO/IEC 25010:2011 (Quality), ISO/IEC 27001:2022 (Security) |
| Traceability | All work items reference VOYANT-SRS-4.0.0 requirement IDs |

---

## 1. Purpose & Positioning

### 1.1 Mission Statement

Voyant v4.0 is the first open-source, self-hosted **agentic data operating system**: a platform in which AI agents — not humans — are the primary operators of the full data lifecycle (discover → ingest → profile → analyze → govern → act), with humans elevated to oversight through a Palantir-grade visual console. V4.0 is the evolution of data systems from *tools humans operate* to *infrastructure agents operate*.

### 1.2 Differentiation (normative, from SRS §2.3)

1. Agent-native: 67+ MCP tools; competitors have zero MCP surface.
2. Intent-driven: "LLM translates, code executes" — deterministic Temporal execution below a validated LLM intent layer.
3. Palantir-grade ontology with kinetics (Actions, Functions, undo) — open source.
4. Octopus scraper: 9 arms, 51 templates, zero-LLM deep research.
5. Capsules: signed (Ed25519) portable intelligence plugins.
6. Self-hosted, Apache 2.0, ~24-service Docker stack.

### 1.3 This Plan's Authority

This PDP re-sequences the VOYANT-SDP-4.0.0 phases based on a full code-and-documentation audit (2026-09-08). Where SDP and actual code disagree, **measured code state governs** (§2). Requirement scope is unchanged from SRS; only delivery order, quality gates, and production-readiness scope are modified.

---

## 2. Measured Baseline (As-Audited, 2026-09-08)

| Dimension | SRS v3.0 baseline | Audited current state | Delta |
|---|---|---|---|
| Django apps | 16 | 19 (ontology, ml_platform, intent, llm_providers, admin_panel landed) | +3 |
| REST routes | 66 | ~181 measured; openapi.json documents 63 (stale) | docs drift |
| MCP tools | 46 | 67 registered | +21 |
| Temporal workflows | 17 | 17 | — |
| Dashboard views | 13 | 13 (3 with contract bugs; design system CSS unloaded) | quality gap |
| Tests | 2,203 (0 failing) | 2,128 passing / 51 skipped / 0 failing | stable |
| Phases 1–3 (Ontology, Scraper core, ML) | planned | **substantially implemented** | ahead of docs |
| Phase 4 (Visual Builders) | planned wk 9–14 | **0%** — the critical gap | behind |
| Governance P1 (RLS, masking) | planned wk 15–20 | 0% | behind |

**Completion re-assessment vs SRS §4 (37%):** accounting for landed code, effective completion is ≈ **50–55%**. The residual is concentrated in: UI/UX (15% complete — weakest), Governance P1, Scraper anti-bot/visual-builder, API surface (OSDK, WebSocket, CLI), and enterprise hardening.

---

## 3. Governing Principles

1. **UI-first resequencing.** Backend P0 is ≈85% complete; UI is ≈15%. No new backend domain surface is added until the human-facing product reaches parity. Every new endpoint without a screen (or MCP tool) has negative marginal value.
2. **Truth automation.** Docs drift from code is treated as a build failure, not a hygiene issue. Quantitative claims (endpoint counts, tool counts, app counts) are CI-generated or CI-linted.
3. **Fail-closed everywhere, including the LLM.** The Intent Engine is the single non-deterministic entry point; it is threat-modeled and adversarially tested before enterprise claims (SOC 2) are made.
4. **Infra discipline.** No new infrastructure service ships without an ADR justifying its operational cost. Ranger, Atlas, NiFi, Superset, APISIX are deferred to "integrate-on-demand" (see §9, Risk R-2).
5. **No test = not done** (SDP rule, retained). Weekly gates retained and extended to the frontend.

---

## 4. Release Definition: V4.0.0 Production

V4.0.0 ships when **all exit criteria in §10 pass**. Scope is organized into 6 delivery tracks (T1–T6) over **16 weeks**, replacing SDP phases 4–6 (phases 1–3 closed as built).

### Track T1 — Foundation & Truth (Week 1) — *blocking*

| ID | Work item | Traces to | Effort |
|---|---|---|---|
| T1-01 | Import `globals.css`; resolve Tailwind CDN vs `tailwind.config.ts` divergence; single styling generation | UI-F-001..012 | 2 d |
| T1-02 | Fix dashboard contract bugs: services dict-vs-list (`view-dashboard.ts:32`), SQL tables `TableInfo[]` (`view-sql.ts:22`), job-create double `/v1` (`view-jobs.ts:69`) | API-F-001 | 1 d |
| T1-03 | Regenerate `openapi.json` in CI; add doc-count lint (endpoints, MCP tools, apps) failing on drift | API-F-001 | 2 d |
| T1-04 | Playwright smoke: all 13 routes load, zero JS errors (UI-T-012) wired into CI | STP §2.8 | 2 d |
| T1-05 | Production dashboard build: multi-stage Dockerfile, corrected nginx (`/v1`), compose service | DEPLOYMENT | 2 d |
| T1-06 | Gate localhost login bypass behind build-time flag (`view-login.ts:59`) | SEC-T-005 | 0.5 d |
| T1-07 | Write ADRs 002–004 (governance-system selection; intent trust boundary; frontend stack ratification Lit-over-React) | SAD §2 | 2 d |

**Exit:** CI green with smoke + lint; dashboard deployable via compose; docs truthful.

### Track T2 — Ontology Explorer & Visual Builders (Weeks 2–7) — *the Palantir-parity track*

Per `docs/ONTOLOGY_VIEWER_SPEC.md` (normative) and UI_DEVELOPMENT_PLAN sprints B–D.

| ID | Work item | Traces to |
|---|---|---|
| T2-01 | Explorer Phase 2: Table view — 4 table specs (types, instances w/ dynamic columns, link types, links), sort/filter, CSV/JSON export | UI-F-001, ONT-F-013 |
| T2-02 | Explorer Phase 2: Grid view + drag-card-to-card link creation | UI-F-001 |
| T2-03 | Detail panel: editable properties, instance forms, link navigation, audit trail w/ diffs; wire the 4 dead action buttons (`view-ontology.ts:242`) | UI-F-001, ONT-F-026 |
| T2-04 | Object Type Builder (Schema view): drag-drop type designer, JSON schema preview, migration generation | UI-F-002 |
| T2-05 | Link Type Builder | UI-F-003 |
| T2-06 | Action Builder + Function Editor (Monaco, sandboxed run via `/v1/ontology/functions`) | UI-F-004, UI-F-005, ONT-F-029 |
| T2-07 | Filter Builder (visual condition editor) | UI-F-007 |
| T2-08 | Graph view hardening: pan/zoom, minimap, 2+ layouts, un-hardcode XTRIM colors (`voyant-graph-view.ts:20`) — HTML/SVG per spec §14 Phase 1; WebGL only if 1k-node perf target fails | UI-F-009 |
| T2-09 | Remove dead UI: orphan components, unused deps (sigma, graphology, leaflet, @lit-labs/router), mock metrics | — |

**Exit:** ONTOLOGY_VIEWER_SPEC §16 acceptance tests pass; UI-T-007/008 E2E green; graph renders 1k nodes <500ms.

### Track T3 — Scraper Octopus Completion (Weeks 4–9, parallel)

| ID | Work item | Traces to |
|---|---|---|
| T3-01 | Wire `voyant-browser-canvas` into Builder tab: point-and-click element selection, auto-selectors, live preview | SCR-F-060/061/062 |
| T3-02 | Workflow JSON import/export; step engine (navigate/click/scroll/extract/paginate/wait/login) | SCR-F-063, SCR-F-030..036 |
| T3-03 | Scraper Jobs tab: live data from `/v1/admin/scraper/jobs` (endpoint exists, unused) | SCR-F-006 |
| T3-04 | CAPTCHA solving (reCAPTCHA v2/v3 >90%, hCaptcha/Turnstile >85%) with multi-provider fallback chain | SCR-F-020/021/022 |
| T3-05 | IP rotation + residential proxy pool + fingerprint randomization | SCR-F-023/024/025 |
| T3-06 | Export engine: JSONL streaming, XLSX, XML, PostgreSQL/MySQL targets, auto-export | SCR-F-040..047 |
| T3-07 | Template library hardening: 51 templates validated E2E (SCR-T-014/015); deprecation path for brittle selectors | SCR-F-011 |
| T3-08 | NL→scraper + URL→template matching via Intent Engine | SCR-F-050/051 |

**Exit:** SCR-T-001..025 green; PERF-T-005/006 (<5s simple, <30s SPA); 50 concurrent tasks no degradation.

### Track T4 — Governance & Security Hardening (Weeks 8–12, parallel)

| ID | Work item | Traces to |
|---|---|---|
| T4-01 | Row-level security: SecurityPolicy model + enforcement in Trino client | GOV-F-003 |
| T4-02 | Column masking: ColumnMask + query-time masking | GOV-F-004 |
| T4-03 | Unified catalog UI (browse schemas/tables/columns/lineage) | GOV-F-001 |
| T4-04 | **Intent Engine trust boundary**: adversarial prompt-injection test suite, per-plan cost/rate limits, validator coverage proof, LLM failover behavior | INT-T-004, SEC-T |
| T4-05 | WebSocket API for subscriptions (Redis Pub/Sub + Channels); ontology Subscription Service | API-F-004, ONT-F-032 |
| T4-06 | DataHub lineage UI surface (client exists); deprecate Atlas stub or ADR-justify | GOV-F-006 |
| T4-07 | Remove deprecated models (ServiceDefinition, QuotaTier, AnalysisJob) with migrations | SDP §6 |
| T4-08 | Fix double-prefix routing `/v1/intent/intent/*` → `/v1/intent/*` (versioned redirect) | API-F-001 |

**Exit:** GOV-T-001..007 green; SEC-T-001..010 green incl. injection tests against intent endpoints.

### Track T5 — Agent & ML Surface (Weeks 10–13, parallel)

| ID | Work item | Traces to |
|---|---|---|
| T5-01 | Agent Control Center view: Definitions / Live Sessions / MCP Tools / Evaluations tabs | ML-F-006/007/008 |
| T5-02 | MCP Playground (67-tool registry, category tree, test panel) | API-F-002 |
| T5-03 | ML Platform views: experiments, registry, endpoints, drift monitor | ML-F-001..005 |
| T5-04 | MLflow-compatible API conformance run against MLflow test suite at `/api/2.0/mlflow/*` | ML-F-005 |
| T5-05 | OSDK: TypeScript + Python clients generated from regenerated OpenAPI | API-F-003 |
| T5-06 | CLI (`click`): auth, jobs, ontology, scraper, sql | API-F-005 |

**Exit:** ML-T-001..006 green; SDK round-trip integration tests; CLI E2E.

### Track T6 — Enterprise Production Gate (Weeks 14–16)

| ID | Work item | Traces to |
|---|---|---|
| T6-01 | Load test: 1M+ objects/type, 1,000 concurrent users, <200ms p95 / <50ms object queries | PERF-T-001..010, SRS §7.1 |
| T6-02 | GDPR: right-to-deletion workflow, retention enforcement, audit completeness | GOV-F-009 |
| T6-03 | SOC 2 readiness checklist (CC6 mapping exists in RBAC doc; extend to ops) | SRS §7.2 |
| T6-04 | WCAG 2.1 AA audit + remediation | UI-F-012 |
| T6-05 | Backup/DR drill: Postgres + MinIO + Vault restore rehearsal, workflow replay proof | ISO 27001 A.17 |
| T6-06 | Release package: OpenAPI 3.1 final, user/admin guides, migration notes, SBOM + dependency scan | ISO 9001 §8.5 |

---

## 5. Team & Capacity (per SDP §2, adjusted)

| Role | Allocation | Primary tracks |
|---|---|---|
| Frontend engineer ×1 (+0.5 borrowed backend, wk 1–7) | 1.5 | T1, T2, T3-01..03, T5-01..03 |
| Backend engineer ×2 | 2.0 | T3, T4, T5-04 |
| Data engineer ×1 | 1.0 | T3-04..06, T6-01 |
| DevOps ×0.5 | 0.5 | T1-05, T6 |

Note: T2 requires 1.5 frontend for 6 weeks — this is the deliberate rebalancing; backend engineers do not start new domain surface until T4.

## 6. Quality Gates (weekly, CI-enforced; extends SDP §rules)

1. pytest: 0 failures; coverage >80% on changed code.
2. `ruff check apps/ --select E,F,W,I`: clean.
3. `manage.py check --deploy`: clean.
4. Playwright route smoke: 13+ routes, zero JS errors.
5. OpenAPI regenerated; doc-count lint passes (no drift).
6. New endpoints: auth decorator + validation + <200ms p95 evidence.
7. New views: real API data only (no mocks), WCAG AA contrast check.
8. SRS-ID traceability on every PR.

## 7. Risk Register (supersedes SDP §5 where conflicting)

| ID | Risk | P | I | Mitigation |
|---|---|---|---|---|
| R-1 | Visual builder complexity (T2/T3) slips | M | H | HTML/SVG first (spec §14); defer WebGL; weekly demo gate; cut Graph layouts to 2 before cutting Builders |
| R-2 | Infra sprawl (Ranger/Atlas/NiFi/Superset/APISIX) consumes ops capacity | H | M | **Deferred** to integrate-on-demand; ADR required to re-enter scope; RLS/masking implemented in Trino client (T4-01/02) instead of Ranger |
| R-3 | CAPTCHA provider reliability | H | H | Multi-provider chain (2Captcha → AntiCaptcha → CapSolver); >90% gate or feature flagged |
| R-4 | Prompt injection via Intent Engine | M | H | T4-04 adversarial suite; validator is fail-closed; plan cache; cost limits |
| R-5 | Frontend single-point-of-failure staffing | M | H | 0.5 backend cross-trained wk 1–7; component patterns documented in ADR-004 |
| R-6 | Doc drift recurs | H | L | CI lint (T1-03) makes drift a build failure |
| R-7 | Scope creep (new backend domains) | H | H | PDP §3.1 moratorium; change control via this document only |

## 8. Milestones

| Milestone | Week | Criteria |
|---|---|---|
| M1 Truth & Deploy | 1 | T1 exit |
| M2 Explorer Parity | 7 | T2 exit — Ontology Explorer spec acceptance |
| M3 Octopus Complete | 9 | T3 exit |
| M4 Governed Core | 12 | T4 exit |
| M5 Agent Surface | 13 | T5 exit |
| **M6 V4.0.0 GA** | **16** | All §10 exit criteria |

## 9. Deferred Scope (explicit, with authority)

Deferred to V4.1+ or integrate-on-demand, each requiring an ADR to re-enter: Apache Ranger, Apache Atlas, Apache NiFi, Apache Superset, APISIX (nginx suffices until multi-tenant gateway billing), Flink streaming beyond stub (DATA-F-014, P2), Dashboard Builder (UI-F-008, P2), Scenario Engine, ontology branching, Machinery process mining, map/Leaflet views.

## 10. V4.0.0 Release Exit Criteria (all must pass)

1. All P0 requirements in SRS §4 demonstrably complete (trace matrix signed).
2. Test pyramid green: unit + integration + 12 UI E2E + 10 performance + 10 security suites.
3. PERF: <200ms p95 API, <50ms object query @1M, dashboard load <3s, scrape <5s/<30s, 50 concurrent tasks, MCP <500ms.
4. SEC-T-001..010 pass, including intent-injection suite; zero auth bypasses; secrets only in Vault.
5. One-command production deploy (`infra/standalone`) including dashboard; DR drill evidenced.
6. openapi.json current; doc counts CI-verified; ADRs 002–004 accepted.
7. WCAG 2.1 AA on all routes; zero console errors.
8. GDPR deletion + retention demonstrated; SOC 2 checklist gap-free or exceptions documented.

---

## Appendix A — Traceability Summary

SRS domains → tracks: Ontology (ONT-F) → T2; Data Intelligence (DATA-F-012 pipeline DAG) → V4.1 (deferred per §9, ADR candidate); ML (ML-F) → T5; Governance (GOV-F) → T4; UI (UI-F) → T1/T2/T3/T5; Scraper (SCR-F/NF) → T3; API (API-F) → T1/T4/T5.

## Appendix B — Change Control

Changes to scope, sequence, or exit criteria require: written change request → impact assessment vs SRS trace matrix → approval recorded in this document's revision history. Emergency security fixes exempt with retrospective documentation within 48h.
