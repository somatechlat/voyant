# ADR 003: Intent Engine Trust Boundary — LLM Proposes, Deterministic Code Disposes

- **Status:** Accepted
- **Date:** 2026-09-08
- **Context:** The Intent Engine (`apps/intent/engine.py`) is the only component where an LLM influences execution. It classifies natural-language intent, injects a TOOL_CATALOG prompt of all 67 MCP tools, calls an OpenAI-compatible LLM (Groq by default, via `apps/llm_providers`), and receives a structured `IntentPlan` (JSON steps) which is then validated against the tenant ontology and executed as MCP tool calls. This makes the intent endpoint the system's primary prompt-injection surface: untrusted NL input reaches an LLM that proposes tool executions. All downstream layers (plan validator, MCP RBAC per tool, TenantModel ORM filtering, Trino SQL validation) are deterministic and fail-closed.
- **Forces:** ISO 27001 A.14 (secure development) and the SOC 2 roadmap require a documented trust boundary; STP INT-T-001..005 covers happy paths but not adversarial input; an LLM that hallucinates tool names/parameters must not be able to cause execution, data exposure, or cost amplification.

## Decision

The trust boundary is drawn **between plan generation (untrusted) and plan validation/execution (trusted)**:

1. **LLM output is always untrusted data.** An `IntentPlan` is never executed directly; it passes the deterministic Plan Validator, which rejects unknown tools, invalid parameters, ontology mismatches, and permission violations. No validator bypass is permitted for any caller or config.
2. **Execution inherits the caller's identity.** Plan steps execute as MCP calls under the *requesting user's* JWT/RBAC context — never under an elevated service identity. The LLM cannot grant the plan more authority than the caller already has.
3. **Resource bounds on every plan:** max steps per plan, per-plan wall-clock timeout, per-tenant rate limits, and LLM token/cost caps enforced in the engine (not the provider).
4. **Adversarial test suite is a release gate:** prompt-injection, tool-hallucination, schema-confusion, and tenant-escape test cases (PDP T4-04) run in CI; a failing case blocks release like any SEC-T test.
5. **Plan cache stores validated plans only**, keyed by normalized intent + tenant, so cached reuse never re-consults the LLM and never skips validation.
6. **Provider failover is explicit:** LLM Router failover (per `apps/llm_providers` ActiveLLMConfig) degrades to "intent unavailable" (503) rather than executing partial/unvalidated plans.

## Alternatives Considered

- **LLM-in-the-loop execution (agentic tool-calling without validation):** rejected — non-deterministic, unbillable, undebuggable; violates the SAD §2 "LLM translates, code executes" principle.
- **Regex-only intent classification:** rejected as sole mechanism — loses the NL flexibility that is the product's differentiator; retained as a fast-path classifier for common patterns.
- **Service-account execution with post-hoc audit:** rejected — audit-after-the-fact does not prevent tenant escape; enforcement must precede execution.

## Consequences

- **Positive:** a single, auditable choke point for all LLM influence; prompt injection degrades to plan rejection, not execution; SOC 2 CC6/CC7 evidence falls out of validator logs + AuditLog; cost amplification bounded.
- **Negative:** validator must be maintained as the MCP tool catalog grows (tool schema changes require validator updates — covered by contract tests); strict bounds may reject legitimate complex plans (tunable per tenant).
- **Follow-ups:** PDP-4.0.0 T4-04 (adversarial suite, rate/cost limits); STP amendment adding adversarial INT-T cases.
