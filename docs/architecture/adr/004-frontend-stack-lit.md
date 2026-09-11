# ADR 004: Frontend Stack Ratified — Lit 3 + Vite + Tailwind (Not React)

- **Status:** Accepted
- **Date:** 2026-09-08
- **Context:** Two V4.0 planning documents conflicted. PALANTIR_FEATURE_MAP.md §10 prescribes "New Frontend (React)" with React Flow and Sigma.js React components. VOYANT_RAPID_DEVELOPMENT_PLAN.md (newer) mandates "Lit 3 + Vite + Tailwind — Already proven (13 views, 96KB). NOT React," with custom Lit canvases. The shipped dashboard (`dashboard/`) is Lit 3 + TypeScript + Vite with Tailwind via CDN, 13 views, 13 components, hand-rolled router, ECharts 6, Monaco 0.56, and a custom HTML/SVG graph view (Sigma.js abandoned in practice; deps unused). This ADR ratifies one stack to end the ambiguity.
- **Forces:** Team size (1–1.5 frontend engineers); bundle size and cold-start targets (dashboard load <3s, PERF-T-009); longevity of web standards vs framework churn; the existing investment (13 working views); visual builders (DAG canvas, graph view, scraper builder) need custom canvas/SVG work that framework component models do not simplify.

## Decision

1. **The Voyant dashboard is Lit 3 + Vite + TypeScript + Tailwind (CDN) — permanently for V4.x.** React, React Flow, and Sigma.js-React are rejected.
2. **Custom canvases in Lit:** DAG/pipeline builder, graph view, and scraper visual builder are hand-built HTML/SVG/canvas Lit components (pattern established by `voyant-graph-view.ts` and `voyant-browser-canvas.ts`). No external diagramming framework.
3. **Approved visualization/editor deps:** Apache ECharts (charts), Monaco Editor (code/SQL/functions). Any further addition requires a comment in this ADR's revision notes.
4. **Shadow DOM remains disabled app-wide** (`createRenderRoot() { return this; }`) so Tailwind utilities and the global design tokens (`styles/globals.css`) apply inside components. Component-local styles use inline styles or global token classes, not shadow stylesheets.
5. **Sigma.js/graphology/leaflet and @lit-labs/router are removed** from package.json (unused). The hand-rolled regex router (`src/lib/router.ts`) is the router. WebGL graph rendering is a future optimization only if the 1k-node <500ms target (ONTOLOGY_VIEWER_SPEC §5) fails with SVG.

## Alternatives Considered

- **React + React Flow + Sigma.js (PALANTIR_FEATURE_MAP §10):** rejected — doubles hiring/skill surface for a 1.5-person frontend track, larger bundles, ecosystem churn, and the custom-canvas work (the hard part) is framework-independent anyway.
- **Svelte/Solid or vanilla TS:** rejected — Lit's web-component output is framework-agnostic (embeddable in any host, including future iframes/portals) and the team already ships it.
- **Sigma.js (non-React) for graph view:** deferred, not rejected — retained as the fallback if SVG misses performance targets.

## Consequences

- **Positive:** one stack across docs and code; small bundle (Monaco/ECharts dominate; the framework is ~5KB); components usable outside the SPA; no framework-migration risk during the 16-week delivery.
- **Negative:** visual-builder complexity (drag-drop DAG, minimap, lasso) is built by hand — mitigated by PDP T2 scoping (2 graph layouts before feature cuts); smaller hiring pool than React (mitigated: Lit is close to standard web components).
- **Doc updates:** PALANTIR_FEATURE_MAP §10 is superseded by this ADR; UI_DEVELOPMENT_PLAN and FRONTEND_DEVELOPMENT_PLAN are to be read with `voyant-*` component naming and this stack.
