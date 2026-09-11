# VOYANT Frontend Development Plan
## From Backend Powerhouse to World-Class Product

**Goal:** Build a UI that makes Palantir and Databricks look outdated.
**Stack:** Lit 3 + Vite + Tailwind + Sigma.js + Apache ECharts + Monaco Editor
**Timeline:** 8 sprints (16 weeks)

---

## What We're Copying And How We're Making It Better

### From Palantir Foundry → Improved

| Palantir Feature | What They Do | VOYANT Improvement |
|-----------------|-------------|-------------------|
| **Object Explorer** | Table view with filters, pivot tables | **Multi-view**: Table + Grid + Graph + Map + Timeline. Switch instantly. AI-powered natural language filter bar. |
| **Ontology Graph** | Static node-link diagram | **Live Graph**: Force-directed with Sigma.js, click to expand, real-time updates via WebSocket, semantic zoom (show more detail as you zoom in). |
| **Pipeline Builder** | Drag-and-drop DAG editor | **AI-Assisted DAG**: Describe pipeline in NL → Intent Engine generates DAG → visual editor to refine. Both no-code AND code. |
| **Workshop (App Builder)** | Low-code app builder | **Capsule Builder**: Build reusable intelligence capsules visually, test with AI judge, deploy as MCP tools. |
| **AIP (AI Platform)** | Chat with your data | **MCP Playground**: Test any of59 MCP tools directly, see raw request/response, chain tools visually. |

### From Databricks → Improved

| Databricks Feature | What They Do | VOYANT Improvement |
|-------------------|-------------|-------------------|
| **Workspace** | File browser + notebooks | **Context Workspace**: Files + Ontology + Data + Agents in one sidebar. Context-aware: show related objects, not just files. |
| **SQL Editor** | Monaco editor with autocomplete | **AI SQL Editor**: Monaco + NL-to-SQL via Intent Engine. Type "show me all customers in Quito" → SQL generated. |
| **Dashboard Builder** | Drag-and-drop widgets | **Live Dashboards**: Widgets auto-refresh via WebSocket. Embed ontology objects, not just charts. Agent-generated insights panel. |
| **MLflow Experiments** | Table of runs with metrics | **Agent Experiments**: Track agent evaluations, not just ML runs. Compare prompts, tools, guardrails. |
| **Unity Catalog** | Hierarchical data catalog | **Ontology Catalog**: Browse types → objects → links → actions → functions. Visual relationship map. |
| **Genie (AI Assistant)** | NL chat for data questions | **Voyant Agent**: NL chat that uses ALL59 MCP tools. Not just SQL — scrape, analyze, build ontology, run actions. |

### VOYANT-Unique (Neither Has This)

| Feature | What It Does |
|---------|-------------|
| **Scraper Visual Builder** | Point-and-click web scraping. Select elements on live page → build template → run. |
| **Action Builder** | Visual action configuration: parameters, pre-conditions, side effects, undo rules. |
| **Function Editor** | Monaco editor for Python/TS functions attached to ontology objects. Run sandboxed. |
| **Capsule Marketplace** | Browse, install, certify intelligence capsules. Ed25519 signing. |
| **MCP Tool Playground** | Test any MCP tool, see schema, chain tools, export as agent config. |
| **Governance Console** | RLS policies, column masks, data classifications — visual editor. |

---

## Architecture

```
dashboard/src/
├── main.ts                    # Entry point, router setup
├── lib/
│   ├── api.ts                 # HTTP client (fetch wrapper)
│   ├── router.ts              # Client-side router
│   ├── state.ts               # Global state (reactive)
│   ├── theme.ts               # Tailwind theme tokens
│   └── websocket.ts           # WebSocket client
├── components/
│   ├── saas-layout.ts         # Shell layout (sidebar + topbar + content)
│   ├── saas-sidebar.ts        # Navigation sidebar
│   ├── saas-topbar.ts         # Top bar (search, notifications, user)
│   ├── saas-modal.ts          # Modal dialog
│   ├── saas-table.ts          # Data table (sortable, filterable)
│   ├── saas-graph.ts          # Sigma.js graph wrapper
│   ├── saas-chart.ts          # Apache ECharts wrapper
│   ├── saas-editor.ts         # Monaco editor wrapper
│   ├── saas-dag-canvas.ts     # DAG canvas (pipeline/scraper builder)
│   ├── saas-property-panel.ts # Right-side property inspector
│   ├── saas-ai-chat.ts        # AI assistant chat panel
│   └── saas-toast.ts          # Toast notifications
├── views/
│   ├── view-dashboard.ts      # Overview dashboard (stat cards, charts)
│   ├── view-ontology.ts       # Ontology Explorer (table + graph + builder)
│   ├── view-objects.ts        # Object instances (table + grid + detail)
│   ├── view-pipelines.ts      # Pipeline builder (DAG canvas)
│   ├── view-scraper.ts        # Scraper builder (visual + templates)
│   ├── view-sql.ts            # AI SQL editor
│   ├── view-search.ts         # Semantic search
│   ├── view-agents.ts         # Agent definitions + evaluations
│   ├── view-governance.ts     # RLS, masks, classifications
│   ├── view-capsules.ts       # Capsule marketplace
│   ├── view-sources.ts        # Data source management
│   ├── view-jobs.ts           # Job monitor (Temporal workflows)
│   ├── view-ml.ts             # ML experiments + model registry
│   ├── view-mcp.ts            # MCP tool playground
│   ├── view-audit.ts          # Audit log
│   ├── view-settings.ts       # System settings
│   └── view-login.ts          # Login page
└── styles/
    └── global.css             # Global styles, font imports
```

---

## Sprint Plan

### Sprint 1: Foundation (Week 1-2)
**Goal:** Shell layout, routing, API client, theme

| Task | Effort | Files |
|------|--------|-------|
| Design system: colors, typography, spacing, components | 2 days | `theme.ts`, `global.css` |
| Shell layout: sidebar + topbar + content area | 1 day | `saas-layout.ts` |
| Sidebar navigation with icons + labels | 1 day | `saas-sidebar.ts` |
| Client-side router with lazy loading | 1 day | `router.ts` |
| API client with auth header injection | 1 day | `api.ts` |
| WebSocket client for real-time updates | 1 day | `websocket.ts` |
| Global state management (reactive store) | 1 day | `state.ts` |
| Login page with Keycloak integration | 1 day | `view-login.ts` |
| Dashboard overview (stat cards + charts) | 1 day | `view-dashboard.ts` |

**Design Tokens:**
```css
--brand: #FF4D00;          /* Voyant orange */
--brand-light: #FF7A3D;
--brand-dark: #CC3D00;
--bg-primary: #0A0A0A;     /* Dark mode default */
--bg-secondary: #141414;
--bg-tertiary: #1E1E1E;
--text-primary: #FAFAFA;
--text-secondary: #A0A0A0;
--border: #2A2A2A;
--success: #22C55E;
--warning: #F59E0B;
--error: #EF4444;
--info: #3B82F6;
--font-display: 'Inter', sans-serif;
--font-mono: 'JetBrains Mono', monospace;
--radius: 8px;
--shadow: 0 4px 24px rgba(0,0,0,0.3);
```

### Sprint 2: Ontology Explorer (Week 3-4)
**Goal:** THE Palantir killer — multi-view ontology explorer

| Task | Effort | Files |
|------|--------|-------|
| Object Types table (sortable, filterable) | 1 day | `view-ontology.ts` |
| Object Type detail panel (properties, links) | 1 day | `saas-property-panel.ts` |
| Graph view: Sigma.js force-directed layout | 2 days | `saas-graph.ts` |
| Object instances table with pagination | 1 day | `view-objects.ts` |
| Object detail: JSON editor + link navigator | 1 day | `view-objects.ts` |
| Search bar: NL → filter (via Intent Engine) | 1 day | `view-ontology.ts` |
| Create/Edit Object Type modal | 1 day | `saas-modal.ts` |
| Batch import objects (CSV/JSON upload) | 1 day | `view-ontology.ts` |

**Graph View Specification (Sigma.js):**
- Nodes = Object Types (colored by category)
- Edges = Link Types (labeled, thickness = cardinality)
- Click node → expand to show instances
- Semantic zoom: zoom out = types, zoom in = properties
- Search: highlight matching nodes
- Layout: force-directed (FA2 algorithm)
- Minimap in bottom-right corner
- Export as PNG/SVG

### Sprint 3: AI SQL Editor + Search (Week 5-6)
**Goal:** Monaco editor with AI-powered SQL and semantic search

| Task | Effort | Files |
|------|--------|-------|
| Monaco editor wrapper component | 1 day | `saas-editor.ts` |
| SQL editor with Trino autocomplete | 1 day | `view-sql.ts` |
| NL-to-SQL: type question → Intent Engine → SQL | 1 day | `view-sql.ts` |
| Query results table (paginated, exportable) | 1 day | `view-sql.ts` |
| Query history (saved queries) | 0.5 day | `view-sql.ts` |
| Schema browser (tables → columns) | 0.5 day | `view-sql.ts` |
| Semantic search view (Milvus-powered) | 1 day | `view-search.ts` |
| Search results with relevance scores | 0.5 day | `view-search.ts` |
| Document index manager | 0.5 day | `view-search.ts` |

### Sprint 4: Pipeline Builder (Week 7-8)
**Goal:** Visual DAG editor — compete with Databricks Lakeflow

| Task | Effort | Files |
|------|--------|-------|
| DAG canvas component (drag nodes, draw edges) | 2 days | `saas-dag-canvas.ts` |
| Node types: Source, Transform, Filter, Aggregate, Export | 1 day | `view-pipelines.ts` |
| Node configuration panel (right sidebar) | 1 day | `saas-property-panel.ts` |
| NL-to-pipeline: describe → Intent Engine → DAG | 1 day | `view-pipelines.ts` |
| Pipeline execution via Temporal | 0.5 day | `view-pipelines.ts` |
| Pipeline monitor (job status, logs) | 0.5 day | `view-pipelines.ts` |
| Pipeline templates (pre-built ETL flows) | 0.5 day | `view-pipelines.ts` |
| Import/export pipeline as JSON | 0.5 day | `view-pipelines.ts` |

**DAG Canvas Specification:**
- Canvas: infinite scroll, zoom (mouse wheel), pan (middle mouse)
- Nodes: draggable, resizable, color-coded by type
- Edges: Bezier curves, arrow direction, label
- Toolbar: add node, delete, undo, redo, zoom-to-fit
- Grid snapping for clean layouts
- Validation: check for cycles, missing connections
- Export: JSON, PNG

### Sprint 5: Scraper Visual Builder (Week 9-10)
**Goal:** Point-and-click web scraping — unique differentiator

| Task | Effort | Files |
|------|--------|-------|
| Template browser (116 templates, categories) | 1 day | `view-scraper.ts` |
| Template detail: selectors, workflow, params | 0.5 day | `view-scraper.ts` |
| Live page preview (iframe + Playwright screenshot) | 1 day | `view-scraper.ts` |
| Element selector overlay (click to select CSS) | 2 days | `view-scraper.ts` |
| Selector tree editor (CSS/XPath) | 1 day | `view-scraper.ts` |
| Workflow builder (fetch → extract → paginate → export) | 1.5 days | `view-scraper.ts` |
| Job monitor (status, artifacts, errors) | 0.5 day | `view-scraper.ts` |
| Export results (JSON, CSV, XLSX) | 0.5 day | `view-scraper.ts` |

### Sprint 6: Agent Builder + MCP Playground (Week 11-12)
**Goal:** Build and test AI agents visually — neither Palantir nor Databricks has this

| Task | Effort | Files |
|------|--------|-------|
| Agent list (definitions with status) | 0.5 day | `view-agents.ts` |
| Agent editor: prompt, model, tools, guardrails | 1 day | `view-agents.ts` |
| Tool picker: browse59 MCP tools, add to agent | 1 day | `view-agents.ts` |
| Agent chat: test agent in browser | 1 day | `view-agents.ts` |
| Evaluation runner: test cases, AI judge scores | 1 day | `view-agents.ts` |
| MCP tool playground: test any tool directly | 1 day | `view-mcp.ts` |
| Tool schema viewer (JSON Schema) | 0.5 day | `view-mcp.ts` |
| Tool chain builder (visual tool pipeline) | 1 day | `view-mcp.ts` |
| Export agent config as JSON | 0.5 day | `view-agents.ts` |

### Sprint 7: Governance + ML (Week 13-14)
**Goal:** Visual governance console + ML experiment tracker

| Task | Effort | Files |
|------|--------|-------|
| RLS policy editor (table, column, filter config) | 1 day | `view-governance.ts` |
| Column mask editor (mask type, preview) | 0.5 day | `view-governance.ts` |
| Data classification browser | 0.5 day | `view-governance.ts` |
| Lineage graph (upstream/downstream) | 1 day | `view-governance.ts` |
| Quota management (tiers, usage charts) | 0.5 day | `view-governance.ts` |
| ML experiments list (runs, metrics) | 1 day | `view-ml.ts` |
| Model registry (versions, stages) | 0.5 day | `view-ml.ts` |
| Model serving endpoints | 0.5 day | `view-ml.ts` |
| Capsule marketplace (browse, install, certify) | 1 day | `view-capsules.ts` |

### Sprint 8: Polish + Dashboards (Week 15-16)
**Goal:** Dashboard builder, dark/light theme, responsive, accessibility

| Task | Effort | Files |
|------|--------|-------|
| Dashboard builder: drag-and-drop widgets | 2 days | `view-dashboard.ts` |
| Widget types: chart, table, stat, text, iframe | 1 day | `view-dashboard.ts` |
| Chart types: line, bar, pie, scatter, heatmap, gauge | 1 day | `saas-chart.ts` |
| Auto-refresh via WebSocket | 0.5 day | `view-dashboard.ts` |
| Dark/light theme toggle | 0.5 day | `theme.ts` |
| Responsive layout (mobile sidebar collapse) | 0.5 day | `saas-layout.ts` |
| Keyboard shortcuts (Cmd+K search, etc.) | 0.5 day | `main.ts` |
| Loading states, error boundaries, empty states | 0.5 day | All views |
| Final polish: animations, transitions, micro-interactions | 0.5 day | All views |

---

## Key Component Specifications

### 1. Graph Component (Sigma.js)

```
┌─────────────────────────────────────────────────┐
│ Ontology Explorer          [Table] [Graph] [Map] │
│ ┌─────────────────────────────────────────────┐  │
│ │  🔍 Search types, objects, properties...    │  │
│ └─────────────────────────────────────────────┘  │
│ ┌──────────────────────────────────┐ ┌────────┐ │
│ │                                  │ │Details │ │
│ │    ● Customer ──── ● Order      │ │        │ │
│ │    │               │            │ │Name:   │ │
│ │    │               │            │ │Customer│ │
│ │    ● Address       ● Product    │ │        │ │
│ │                    │            │ │Props:  │ │
│ │                    ● Category   │ │ name   │ │
│ │                                  │ │ email  │ │
│ │                                  │ │ phone  │ │
│ │                                  │ │        │ │
│ │                                  │ │Links:  │ │
│ │                                  │ │ →Order │ │
│ │                                  │ │ →Addr  │ │
│ └──────────────────────────────────┘ └────────┘ │
│ [Zoom In] [Zoom Out] [Fit] [Export] [Fullscreen]│
└─────────────────────────────────────────────────┘
```

### 2. AI SQL Editor

```
┌─────────────────────────────────────────────────┐
│ SQL Editor              [Run ▶] [Format] [Save] │
│ ┌─────────────────────────────────────────────┐  │
│ │ SELECT c.name, COUNT(o.id) as order_count   │  │
│ │ FROM customer c                              │  │
│ │ JOIN order o ON o.customer_id = c.id         │  │
│ │ GROUP BY c.name                              │  │
│ │ ORDER BY order_count DESC                    │  │
│ │ LIMIT 100                                    │  │
│ └─────────────────────────────────────────────┘  │
│ ┌─────────────────────────────────────────────┐  │
│ │ 💬 "Show me top customers by order count"   │  │
│ │ → SQL generated above ↑                     │  │
│ └─────────────────────────────────────────────┘  │
│ Results (100 rows, 0.23s)  [CSV] [JSON] [Copy]  │
│ ┌─────────────────────────────────────────────┐  │
│ │ name          │ order_count                  │  │
│ │───────────────│─────────────                  │  │
│ │ Juan Perez    │ 47                            │  │
│ │ Maria Garcia  │ 32                            │  │
│ │ Carlos Lopez  │ 28                            │  │
│ └─────────────────────────────────────────────┘  │
│ ┌── Schema ───────────────────────────────────┐  │
│ │ ▸ customer (5 columns)                       │  │
│ │ ▸ order (8 columns)                          │  │
│ │ ▸ product (6 columns)                        │  │
│ └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### 3. Pipeline Builder (DAG Canvas)

```
┌─────────────────────────────────────────────────┐
│ Pipeline: Customer Analytics    [Run] [Save]     │
│ ┌─────────────────────────────────────────────┐  │
│ │ ┌──────────┐    ┌──────────┐    ┌─────────┐ │  │
│ │ │ Source   │───▶│ Filter   │───▶│Aggregate│ │  │
│ │ │ Postgres │    │ active=1 │    │ COUNT   │ │  │
│ │ └──────────┘    └──────────┘    └────┬────┘ │  │
│ │                                      │      │  │
│ │ ┌──────────┐                         ▼      │  │
│ │ │ Source   │───▶┌──────────┐    ┌─────────┐ │  │
│ │ │ CSV file │    │Transform │───▶│ Export  │ │  │
│ │ └──────────┘    │ normalize│    │ MinIO   │ │  │
│ │                 └──────────┘    └─────────┘ │  │
│ └─────────────────────────────────────────────┘  │
│ ┌── Node Config ──────────────────────────────┐  │
│ │ Type: Filter                                 │  │
│ │ Column: status                               │  │
│ │ Operator: =                                  │  │
│ │ Value: active                                │  │
│ └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### 4. MCP Tool Playground

```
┌─────────────────────────────────────────────────┐
│ MCP Playground              [59 tools available]  │
│ ┌── Categories ──┐ ┌── Tool Detail ────────────┐ │
│ │ ▸ Data Ops (7) │ │ voyant.vector.search       │ │
│ │ ▸ Scraper (7)  │ │                            │ │
│ │ ▸ Ontology (14)│ │ Parameters:                │ │
│ │ ▸ Governance(4)│ │  query: string (required)  │ │
│ │ ▸ Vector (2)   │ │  limit: number (default 5) │ │
│ │ ▸ Discovery(4) │ │  tenant_id: string         │ │
│ │ ▸ ML (12)      │ │                            │ │
│ └────────────────┘ │ ┌── Test ─────────────────┐ │
│                    │ │ query: "planes fibra"    │ │
│                    │ │ limit: 3                 │ │
│                    │ │                          │ │
│                    │ │ [▶ Run]                  │ │
│                    │ │                          │ │
│                    │ │ Response:                │ │
│                    │ │ {                        │ │
│                    │ │   "results": [...]       │ │
│                    │ │ }                        │ │
│                    │ └──────────────────────────┘ │
│                    └─────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### 5. Agent Builder

```
┌─────────────────────────────────────────────────┐
│ Agent: XTRIM Call Center     [Test] [Deploy]     │
│ ┌── Config ─────────────┐ ┌── Tools ───────────┐ │
│ │ Name: XTRIM Call Ctr  │ │ ☑ voyant.sql       │ │
│ │ Model: gpt-oss-120b   │ │ ☑ voyant.search    │ │
│ │ Temp: 0.1             │ │ ☑ voyant.ontology. │ │
│ │ Max tokens: 4096      │ │   types.list       │ │
│ │                       │ │ ☑ voyant.ontology. │ │
│ │ System Prompt:        │ │   objects.get      │ │
│ │ ┌───────────────────┐ │ │ ☐ voyant.ingest    │ │
│ │ │ You are a call    │ │ │ ☐ scrape.fetch     │ │
│ │ │ center agent for  │ │ │                    │ │
│ │ │ XTRIM telecom...  │ │ │ [Select All]       │ │
│ │ └───────────────────┘ │ │ [Deselect All]     │ │
│ └───────────────────────┘ └────────────────────┘ │
│ ┌── Guardrails ────────────────────────────────┐ │
│ │ Max queries/session: 50                       │ │
│ │ Blocked tables: [admin_*, secrets_*]          │ │
│ │ Require approval: false                       │ │
│ └──────────────────────────────────────────────┘ │
│ ┌── Chat Test ─────────────────────────────────┐ │
│ │ Agent: "Hola! Soy el agente de XTRIM.        │ │
│ │ ¿En qué puedo ayudarte?"                     │ │
│ │                                               │ │
│ │ You: "¿Qué planes tienen fibra óptica?"      │ │
│ │ Agent: [Using: voyant.vector.search]          │ │
│ │ "XTRIM ofrece los siguientes planes..."       │ │
│ └──────────────────────────────────────────────┘ │
│ ┌── Evaluations ───────────────────────────────┐ │
│ │ Eval: "Call center accuracy"  Score: 0.92     │ │
│ │ 8/10 passed  [Run Again] [View Details]       │ │
│ └──────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

---

## Dependencies To Add

```json
{
  "dependencies": {
    "lit": "^3.3.2",
    "@lit-labs/router": "^0.1.4",
    "@twind/core": "^1.1.3",
    "sigma": "^3.0.0",
    "graphology": "^0.25.4",
    "echarts": "^5.5.0",
    "monaco-editor": "^0.50.0",
    "@anthropic-ai/sdk": "^0.30.0"
  }
}
```

---

## What VOYANT Becomes After This

| Before | After |
|--------|-------|
| Backend powerhouse, terminal UI | Full product with world-class UI |
| 13 basic admin views | 18 specialized views with graph, DAG, editor |
| No visual builders | 4 visual builders (ontology, pipeline, scraper, actions) |
| No AI integration in UI | AI-powered SQL, search, agent builder |
| Hard to demo | Every view is a demo moment |
| "Interesting backend" | "This is better than Palantir" |

The key insight: **Palantir wins because of the demo. Databricks wins because of the UX. VOYANT will win because it has BOTH — powered by MCP tools that neither has.**

---

**Created:** 2026-09-07
**Status:** Ready for implementation
**First Sprint:** Foundation (Week 1-2)
