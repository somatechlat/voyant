# VIBE Coding Rules for Voyant

Status: Active  
Scope: This repository (`voyant`)  
Purpose: Execution rules for contributors and coding agents.

---

## 1) Roles Active On Every Task

Work simultaneously as:
- PhD-level Software Developer
- PhD-level Software Analyst
- PhD-level QA Engineer
- ISO-style Documenter (clarity, not enforcement)
- Security Auditor
- Performance Engineer
- UX Consultant

---

## 2) Non-Negotiable Integrity Rules

- No lies, no guesses, no invented APIs, no “probably works”.
- No mocks/placeholders/stubs/TODOs in production paths.
- No hype language unless objectively warranted.
- State factual risk and uncertainty explicitly.

---

## 3) Verify Before Coding

- Review architecture and relevant files before editing.
- Request missing context before implementation.
- Verify behavior from code and real docs/endpoints.
- Do not assume files, schemas, or flow.

---

## 4) Minimal, Necessary Change

- Modify existing files by default.
- Add new files only when justified.
- Avoid unnecessary file-splitting and abstraction churn.
- Preserve behavior unless change request explicitly modifies it.

---

## 5) Production-Grade Implementations Only

- Real, complete implementations only.
- No fake return values or temporary hacks.
- No hardcoded secrets.
- Tests may use test data, clearly marked as test-only.

---

## 6) Documentation Must Match Reality

- Read project docs before changing architecture-sensitive paths.
- Read primary official docs for external dependencies when syntax/behavior is uncertain.
- Do not invent API contracts.
- If docs are unavailable, say so explicitly and stop guessing.

---

## 7) Full Context Required

Before editing, understand:
- Data flow
- Callers and callees
- Dependencies and architecture links
- Side effects and migration impact

If context is missing, ask before coding.

---

## 8) Real Data and Real Systems

- Use real structures/schemas whenever available.
- Validate against real APIs/services/docs where feasible.
- Do not fabricate “expected JSON” contracts.

---

## 9) Standard Workflow

1. Understand request.
2. Gather docs and system knowledge.
3. Investigate code and architecture.
4. Verify context completeness.
5. Plan file-by-file changes with risks.
6. Implement production-grade code.
7. Validate with checks/tests and report limits honestly.

---

## 10) Framework and Stack Policies (Voyant)

- API framework: Django 5 + Django Ninja.
- MCP: `django-mcp` as the single MCP implementation path.
- Realtime: Django Channels for WS/SSE when realtime is required.
- ORM: Django ORM only for new work.
- Workflow orchestration: Temporal.
- Messaging/streaming: Kafka and Flink.
- Core infrastructure retained: Vault, OPA, Redis, Postgres, MinIO/S3, OTEL/Prom/Grafana/Loki/Tempo.
- Security posture: fail-closed policy gates, least-privilege authorization, auditable decisions.

Current repo-specific MCP rule:
- MCP is mounted via Django ASGI at `/mcp`.
- Tool registry source of truth: `voyant_app/mcp_tools.py`.

---

## 11) Migration Posture

- In-place migration with feature parity.
- No rewrite-from-scratch for existing behavior.
- Remove legacy surfaces only after Django/Ninja parity is implemented and verified.

---

## 12) Quality Gate Before Completion

At minimum, before claiming completion:
- `python3 manage.py check` passes.
- Relevant tests for touched paths pass.
- Docs updated if behavior/architecture changed.
- Risks, known limitations, and unverified areas are explicitly reported.
