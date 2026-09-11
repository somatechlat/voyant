# Voyant v4.0 — UI/UX Deep Design Document

**Document ID:** VOYANT-UIUX-4.0.0
**Version:** 1.0.0
**Date:** 2026-09-09
**Status:** Active (Iteration 6/7)
**Compliance:** ISO/IEC 25010:2011 · WCAG 2.1 AA

---

## 1. Current Implementation — Every View, Every Component

### 1.1 View Inventory (13 Views)

| # | View | File | Routes | API Endpoints | Status | Known Bugs |
|---|------|------|--------|---------------|--------|------------|
| 1 | Login | `view-login.ts` | `/admin/login` | `/v1/auth/login` | **Fixed** | Login bypass gated behind VITE_ALLOW_LOCAL_LOGIN |
| 2 | Dashboard | `view-dashboard.ts` | `/admin` | `/v1/admin/status`, `/v1/admin/services` | **Fixed** | Services dict handling + circuit breaker mapping fixed |
| 3 | Jobs | `view-jobs.ts` | `/admin/jobs` | `/v1/admin/jobs`, `/v1/admin/jobs/{id}`, `/v1/admin/jobs/{id}/cancel`, `/v1/admin/jobs/{id}/reset` | **Fixed** | Job-create prefix fixed |
| 4 | Sources | `view-sources.ts` | `/admin/sources` | `/v1/admin/sources`, `/v1/admin/sources/{id}` | **Fixed** | connection_config now returned |
| 5 | Governance | `view-governance.ts` | `/admin/governance` | `/v1/admin/governance/policies`, `/v1/admin/governance/contracts`, `/v1/admin/governance/quotas` | Basic | Table-only, no visual editors |
| 6 | Capsules | `view-capsules.ts` | `/admin/capsules` | `/v1/admin/capsules`, `/v1/admin/capsules/{id}/activate`, `/v1/admin/capsules/{id}/suspend`, `/v1/admin/capsules/{id}/archive` | Basic | List view only |
| 7 | Ontology | `view-ontology.ts` | `/admin/ontology` | `/v1/admin/ontology/types`, `/v1/admin/ontology/links` | Partial | Table only, 4 dead action buttons, no graph/grid/detail |
| 8 | Audit | `view-audit.ts` | `/admin/audit` | `/v1/admin/audit` | Basic | Log viewer, no filtering |
| 9 | SQL | `view-sql.ts` | `/admin/sql` | `/v1/sql/query`, `/v1/sql/tables` | **Fixed** | TableInfo[] contract + rows type fixed |
| 10 | Search | `view-search.ts` | `/admin/search` | `/v1/admin/search/query`, `/v1/admin/search/index`, `/v1/admin/search/{id}` | Basic | Input + results, no semantic search |
| 11 | Scraper | `view-scraper.ts` | `/admin/scraper` | `/v1/scraper/templates`, `/v1/scrape/*` | Partial | 6 tabs, some wired, template status removed |
| 12 | Settings | `view-settings.ts` | `/admin/settings` | `/v1/admin/settings`, `/v1/admin/settings/{key}` | Basic | Config editor |
| 13 | Tenants | `view-tenants.ts` | `/admin/tenants` | `/v1/admin/tenants` | Basic | Tenant list |

### 1.2 Component Inventory (12 Components)

| # | Component | File | Purpose | Current Capabilities | Missing |
|---|-----------|------|---------|---------------------|---------|
| 1 | Layout | `saas-layout.ts` | Shell layout | Sidebar + topbar + content area | Responsive breakpoints |
| 2 | Sidebar | `saas-sidebar.ts` | Navigation | Route links, active state, icons | Collapsible, keyboard nav |
| 3 | Glass Modal | `saas-glass-modal.ts` | Modal dialog | Glass-morphism overlay | Focus trap, escape key |
| 4 | Infra Card | `saas-infra-card.ts` | Service status card | Status dot, name, port | Historical data |
| 5 | Stat Card | `saas-stat-card.ts` | Metric display | Number + label + trend | Sparkline, target line |
| 6 | Status Dot | `saas-status-dot.ts` | Status indicator | Color-coded dots | Tooltip, animation |
| 7 | Graph View | `voyant-graph-view.ts` | Sigma.js graph | Force-directed layout, nodes/edges | Click-to-expand, minimap, search, zoom controls |
| 8 | Chart | `voyant-chart.ts` | ECharts wrapper | Basic chart rendering | Multiple chart types, themes, responsive |
| 9 | Data Table | `voyant-data-table.ts` | Sortable table | Sort, filter, pagination | Column resize, row selection, export, virtual scroll |
| 10 | Detail Panel | `voyant-detail-panel.ts` | Slide-in panel | Basic detail display | Tabs, editable fields, actions |
| 11 | Metric Card | `voyant-metric-card.ts` | KPI card | Number display | Trend arrow, comparison, sparkline |
| 12 | Monaco Editor | `voyant-monaco-editor.ts` | Code editor | Basic Monaco wrapper | SQL autocomplete, Python autocomplete, minimap, multi-file |

### 1.3 Design System (Current)

```css
/* Brand */
--brand: #FF4D00;           /* Voyant orange */
--brand-light: #FF7A3D;
--brand-dark: #CC3D00;

/* Dark Mode (default) */
--bg-primary: #0A0A0A;
--bg-secondary: #141414;
--bg-tertiary: #1E1E1E;
--text-primary: #FAFAFA;
--text-secondary: #A0A0A0;
--border: #2A2A2A;

/* Status */
--success: #22C55E;
--warning: #F59E0B;
--error: #EF4444;
--info: #3B82F6;

/* Typography */
--font-display: 'Geist', sans-serif;
--font-body: 'Inter', sans-serif;
--font-mono: 'JetBrains Mono', monospace;

/* Layout */
--sidebar-width: 240px;
--sidebar-collapsed: 64px;
--content-max-width: 1920px;
--content-padding: 32px;
--card-min-width: 280px;
--card-gap: 16px;
--table-row-height: 40px;
--modal-max-width: 720px;

/* Border */
--radius: 8px;
--shadow: 0 4px 24px rgba(0,0,0,0.3);
```

---

## 2. Palantir Workshop — Screen-by-Screen Comparison

### 2.1 Palantir Screens vs Voyant Screens

| # | Palantir Screen | What It Does | Voyant Equivalent | Voyant Status | Voyant Improvement |
|---|----------------|-------------|-------------------|---------------|-------------------|
| 1 | **Ontology Manager** | Browse types, edit properties/links/actions/functions, schema diff | `view-ontology.ts` | **Partial** (table only) | MCP agent access, graph view, filter builder |
| 2 | **Object Explorer** | Search, filter builder, pivot table, compare, export | Part of `view-ontology.ts` | **Missing** (no pivot, no compare) | NL search via Intent Engine, agent-driven exploration |
| 3 | **Object Detail** | Editable properties, relationship graph, actions, timeline, comments | `voyant-detail-panel.ts` | **Basic** | Multi-hop link traversal, undo actions, audit diffs |
| 4 | **Pipeline Builder** | DAG canvas, node config, run history, scheduling | `view-pipelines.ts` | **Missing** | NL→pipeline via Intent Engine, Temporal durability |
| 5 | **Workshop** | Low-code app builder, component palette, drag-drop layout | No equivalent | **Missing** | Capsule Builder (agent-deployable recipes) |
| 6 | **Quiver** | Collaborative notebooks, cell editor, kernel management | No equivalent | **Missing** (deferred V4.1) | MCP integration, agent-generated cells |
| 7 | **AIP Logic Studio** | AI workflow builder, LLM config, tool picker | `view-agents.ts` | **Missing** | 67 MCP tools, deterministic execution |
| 8 | **AIP Agent Builder** | Agent definition, evaluation, deployment, monitoring | Part of `view-agents.ts` | **Missing** | AI judge evaluation, capsule integration |
| 9 | **Pipeline Operations** | Build history, health monitoring, alerts, resource usage | `view-jobs.ts` | **Basic** | Temporal replay, workflow visualization |

### 2.2 Palantir Strengths Voyant Must Match

| Palantir Feature | How They Do It | Voyant Approach |
|-----------------|---------------|-----------------|
| **Force-directed graph** | Custom WebGL renderer | HTML/SVG (ADR-004), WebGL only if 1k-node perf fails |
| **Filter builder** | Visual condition editor (field→op→value, AND/OR) | Same approach, but with NL filter via Intent Engine |
| **Pivot table** | Drag fields to rows/columns/values | Apache ECharts pivot or custom Lit component |
| **Action execution** | Parameter form → execute → undo | ActionType model with `previous_values` snapshot (already built) |
| **Function editor** | Monaco with type-aware autocomplete | Monaco wrapper with ontology schema autocomplete |
| **Real-time updates** | WebSocket subscriptions | Redis Pub/Sub + Django Channels (planned T4-16) |
| **Collaborative editing** | Multi-user cursors | Deferred (V4.1+) |

---

## 3. Databricks Workspace — Screen-by-Screen Comparison

### 3.1 Databricks Screens vs Voyant Screens

| # | Databricks Screen | What It Does | Voyant Equivalent | Voyant Status | Voyant Improvement |
|---|------------------|-------------|-------------------|---------------|-------------------|
| 1 | **Workspace** | File browser, notebook editor, collaboration, Git | No equivalent | **Missing** | Ontology-integrated workspace (files + data + agents) |
| 2 | **SQL Editor** | Monaco editor, schema browser, results, query history | `view-sql.ts` | **Basic** | NL→SQL via Intent Engine, ontology autocomplete |
| 3 | **Dashboard** | Widget palette, drag-drop, chart types, filters, auto-refresh | `view-dashboard.ts` | **Basic** | Agent-generated insights panel, WebSocket auto-refresh |
| 4 | **MLflow Experiments** | Experiment list, run comparison, run detail | `view-ml.ts` | **Missing** | Agent evaluations alongside ML runs |
| 5 | **Model Registry** | Model versions, stage transitions | Part of `view-ml.ts` | **Missing** | MCP tools for model lifecycle |
| 6 | **Model Serving** | Endpoint list, metrics, A/B testing | Part of `view-ml.ts` | **Missing** | Self-hosted serving, no vendor lock-in |
| 7 | **Unity Catalog** | 3-level hierarchy, permissions, lineage | `view-governance.ts` | **Basic** | Ontology graph > flat hierarchy, agent-level governance |
| 8 | **Genie** | NL chat → SQL → visualization | No equivalent | **Missing** | Intent Engine (not just SQL — scrape, analyze, build ontology) |
| 9 | **Lakeflow** | Pipeline editor, quality expectations, monitoring | No equivalent | **Missing** | Temporal-based pipelines, NL→DAG |
| 10 | **Agent Bricks** | Agent definition, tools, evaluation | `view-agents.ts` | **Missing** | 67 MCP tools, deterministic execution, capsule system |

### 3.2 Databricks Strengths Voyant Must Match

| Databricks Feature | How They Do It | Voyant Approach |
|-------------------|---------------|-----------------|
| **Monaco SQL editor** | Monaco + Unity Catalog autocomplete | Monaco + ontology schema autocomplete + NL→SQL |
| **Dashboard builder** | Drag-drop widgets, SQL-bound charts | Apache ECharts + drag-drop grid + WebSocket auto-refresh |
| **MLflow tracking** | Decorator-based experiment logging | MLflow-compatible REST API at `/api/2.0/mlflow/*` |
| **Model serving** | Managed endpoints with auto-scaling | Self-hosted endpoints via Temporal + Docker |
| **NL BI (Genie)** | LLM → SQL → table → chart | Intent Engine → structured plan → deterministic execution |
| **Data lineage** | Unity Catalog lineage graph | DataHub client + visual lineage graph |

---

## 4. Design System (v4.0 Target)

### 4.1 Color Palette

| Token | Dark Mode | Light Mode | Usage |
|-------|-----------|------------|-------|
| `brand` | `#FF6B2B` | `#FF4D00` | Primary actions, active states |
| `brand-subtle` | `#1A1008` | `#FFF3ED` | Brand-highlighted backgrounds |
| `ink` | `#FAFAFA` | `#050505` | Primary text |
| `ink-muted` | `#9CA3AF` | `#6B7280` | Secondary text |
| `surface` | `#0A0A0A` | `#F5F5F5` | Page background |
| `card` | `#141414` | `#FFFFFF` | Card/panel background |
| `card-hover` | `#1A1A1A` | `#FAFAFA` | Card hover |
| `border` | `#262626` | `#E5E7EB` | Borders, dividers |
| `success` | `#22C55E` | `#22C55E` | Success |
| `warning` | `#F59E0B` | `#F59E0B` | Warning |
| `danger` | `#EF4444` | `#EF4444` | Error, destructive |
| `info` | `#3B82F6` | `#3B82F6` | Information, links |

### 4.2 Typography

| Element | Font | Size | Weight | Line Height |
|---------|------|------|--------|-------------|
| Page title | Geist | 28px | 900 | 1.2 |
| Section title | Geist | 20px | 700 | 1.3 |
| Card title | Inter | 14px | 600 | 1.4 |
| Body | Inter | 13px | 400 | 1.5 |
| Caption | Inter | 11px | 400 | 1.4 |
| Code | JetBrains Mono | 12px | 400 | 1.6 |

### 4.3 Layout System

| Element | Specification |
|---------|--------------|
| Sidebar | 240px fixed, collapsible to 64px icons-only |
| Main content | Fluid, max-width 1920px, padding 32px |
| Card grid | CSS Grid, min-card-width 280px, gap 16px |
| Tables | Full-width, sticky header, row height 40px |
| Modals | Centered, max-width 720px, backdrop blur |
| Detail panels | 400px right slide-in |
| Command palette | Centered overlay, max-width 640px |

---

## 5. Component Library Design (v4.0)

### 5.1 voyant-graph-view (Graph Visualization)

| Spec | Value |
|------|-------|
| Technology | HTML/SVG (no external lib per ADR-004) |
| Layout algorithms | Force-directed (default), Hierarchical |
| Node representation | Circular, colored by category, sized by instance count (log scale) |
| Edge representation | Curved Bezier, labeled, arrowed, width by link count |
| Interactions | Click select, double-click expand, right-click context menu, hover tooltip, search highlight+zoom |
| Performance | <100ms 100 nodes, <500ms 1000 nodes |
| Controls | Zoom (scroll 0.1x-10x), pan (drag), minimap (160x120px), zoom-to-fit button |
| Export | PNG, SVG |

### 5.2 voyant-data-table (Data Table)

| Spec | Value |
|------|-------|
| Features | Sort (multi-column), filter (per-column), pagination, row selection, column resize |
| Export | CSV, JSON, Excel |
| Virtual scroll | Yes (for 10K+ rows) |
| Sticky header | Yes |
| Row actions | Edit, delete, view detail (per row) |
| Empty state | "No data" message with action button |
| Loading state | Skeleton rows |
| Keyboard | Arrow keys navigate, Enter selects, Escape deselects |

### 5.3 voyant-detail-panel (Detail Panel)

| Spec | Value |
|------|-------|
| Position | Right slide-in, 400px wide |
| Sections | Header, stats grid, properties, links, actions, audit trail |
| Interactions | Close (X button, Escape key), scroll, tabs |
| Editable fields | Inline edit with save/cancel |
| Actions | Button bar with confirmation for destructive actions |

### 5.4 voyant-monaco-editor (Code Editor)

| Spec | Value |
|------|-------|
| Languages | SQL (Trino syntax), Python, TypeScript, JSON |
| Features | Syntax highlighting, autocomplete (from ontology schema), error highlighting, minimap |
| Keybindings | Ctrl+Enter (run), Ctrl+S (save), Ctrl+/ (comment) |
| Output panel | Bottom panel for results/errors |

### 5.5 voyant-chart (Chart)

| Spec | Value |
|------|-------|
| Technology | Apache ECharts (Lit wrapper) |
| Chart types | Line, bar, pie, scatter, heatmap, gauge, radar, treemap |
| Features | Responsive, dark/light theme, tooltip, legend, zoom |
| Data binding | Direct data or API endpoint |

### 5.6 voyant-search-bar (Search)

| Spec | Value |
|------|-------|
| Modes | Semantic (Milvus), full-text (PostgreSQL), NL (Intent Engine) |
| Features | Type-ahead, result preview, category filter |
| Keyboard | Cmd+K global trigger, arrow keys navigate results, Enter selects |

### 5.7 voyant-dag-canvas (DAG Editor)

| Spec | Value |
|------|-------|
| Purpose | Pipeline builder, scraper workflow builder |
| Features | Drag nodes from palette, connect edges (click-drag), delete (backspace), undo/redo |
| Node types | Source, Transform, Filter, Validate, Export, Custom |
| Node config | Right panel (reuse voyant-detail-panel) |
| Validation | Cycle detection, missing connections |
| Export | JSON, PNG |

### 5.8 Additional Components

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| `voyant-metric-card` | KPI display | Number, label, trend arrow, sparkline, comparison |
| `voyant-timeline` | Event history | Timestamped events, expandable details, filter by type |
| `voyant-context-menu` | Right-click menu | Nested items, keyboard navigation, icons |
| `voyant-drag-drop` | Drag framework | Reorderable lists, drag between containers |
| `voyant-code-block` | Code display | Syntax highlighting, copy button, line numbers |
| `voyant-json-viewer` | JSON tree | Collapsible, searchable, copy path/value |

---

## 6. Page-by-Page Design (v4.0)

### 6.1 Dashboard (Home)

```
┌─────────────────────────────────────────────────────────────────┐
│ [Sidebar]  Dashboard                                [🔔] [👤]  │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│ │ 21      │ │ 67      │ │ 2,042   │ │ 12      │ │ 46      │  │
│ │Services │ │MCP Tools│ │Tests    │ │Ontology │ │Active   │  │
│ │  🟢 all │ │  live   │ │ passing │ │ Types   │ │ Agents  │  │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
│                                                                 │
│ ┌── Service Health ──────────────┐ ┌── Recent Activity ───────┐ │
│ │ 🟢 voyant_api    v3.0.0 :45000│ │ 2m ago  agent-xtrim ran  │ │
│ │ 🟢 voyant_worker v3.0.0 :45090│ │         voyant.sql query │ │
│ │ 🟢 voyant_milvus 2.4   :19530│ │ 5m ago  ingest job       │ │
│ │ 🟢 voyant_trino  434   :45080│ │         completed (1,247  │ │
│ │ 🟡 voyant_flink  1.18  :45082│ │         rows)             │ │
│ └────────────────────────────────┘ └──────────────────────────┘ │
│ ┌── Job Pipeline ─────────────────────────────────────────────┐ │
│ │ Running (3)  ████████░░  Queued (7)  ░░░░░░░░░░  Done (142)│ │
│ │ ▸ ingest: customers  ▸ profile: sales  ▸ analyze: inventory│ │
│ └─────────────────────────────────────────────────────────────┘ │
│ ┌── Agent Activity ─────────────┐ ┌── MCP Tool Usage ────────┐ │
│ │ Agent         Last Active     │ │ voyant.sql      ████     │ │
│ │ xtrim-demo    2m ago    34    │ │ voyant.search   ███      │ │
│ │ callcenter    15m ago   12    │ │ ontology.types  ██       │ │
│ └────────────────────────────────┘ └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```
**Components:** Stat Card ×5, Infra Card, Status Dot, Chart (bar), Timeline, Metric Card
**API:** `/v1/admin/status`, `/v1/admin/services`, `/v1/admin/jobs`, `/v1/admin/audit`

### 6.2 Ontology Explorer (5 View Modes)

**Components:** Graph View, Data Table, Detail Panel, Search Bar, Context Menu, Monaco Editor
**API:** `/v1/ontology/types`, `/v1/ontology/objects`, `/v1/ontology/links`, `/v1/ontology/interfaces`

| Mode | Purpose | Components |
|------|---------|------------|
| Graph | Visual knowledge graph | voyant-graph-view, voyant-search-bar, voyant-detail-panel |
| Table | Structured data grid | voyant-data-table (×4: types, instances, link types, links), voyant-detail-panel |
| Grid | Card-based overview | Type cards, voyant-detail-panel, voyant-metric-card |
| Code | Functions + actions | voyant-monaco-editor, voyant-code-block |
| Schema | Type hierarchy | Tree view, drag-drop type builder |

### 6.3 SQL Console

```
┌─────────────────────────────────────────────────────────────────┐
│ [Sidebar]  SQL Console                              [▶️] [📥]  │
├─────────────────────────────────────────────────────────────────┤
│ ┌── Monaco Editor ─────────────────────────────────────────────┐│
│ │ SELECT p.name, COUNT(c.id) as customers, SUM(p.price)       ││
│ │ FROM customers c JOIN plans p ON c.plan_id = p.id           ││
│ │ WHERE c.city = 'Quito' GROUP BY p.name ORDER BY customers   ││
│ └──────────────────────────────────────────────────────────────┘│
│ [▶️ Run] [📥 CSV] [📥 JSON]  │  3 rows │ 0.045s               │
│ ┌── Results Table ─────────────────────────────────────────────┐│
│ │ name          │ customers │ revenue                          ││
│ │ Essential     │ 847       │ $21,175                          ││
│ │ Advanced      │ 234       │ $4,475                           ││
│ └──────────────────────────────────────────────────────────────┘│
│ ┌── Schema Browser ────────────────────────────────────────────┐│
│ │ 📂 default                                                    ││
│ │   📋 customers (2,341 rows)                                   ││
│ │     ├ id        UUID                                          ││
│ │     ├ name      VARCHAR                                       ││
│ └──────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```
**Components:** Monaco Editor, Data Table, Search Bar
**API:** `/v1/sql/query`, `/v1/sql/tables`, `/v1/sql/columns`

### 6.4 Pipeline Builder

**Components:** DAG Canvas, Detail Panel, Data Table (run history)
**API:** `/v1/workflows/*` (planned)

### 6.5 Scraper Builder

**Components:** Browser Canvas, Data Table, Detail Panel, DAG Canvas
**API:** `/v1/scraper/templates`, `/v1/scrape/*`

### 6.6 Agent Control Center

**Components:** Data Table, Monaco Editor, Detail Panel, Search Bar
**API:** `/v1/ml/agents`, `/v1/ml/evaluations`, `/v1/mcp/tools` (planned)

### 6.7 MCP Playground

**Components:** Data Table, Monaco Editor, Detail Panel, Code Block, JSON Viewer
**API:** `/v1/mcp/tools`, `/v1/mcp/tools/{name}/invoke` (planned)

---

## 7. Navigation Architecture

```
Sidebar (always visible):
├── Dashboard          — system overview, health, metrics
├── Data
│   ├── Sources        — data source management
│   ├── SQL Console    — interactive SQL editor
│   └── Search         — semantic + full-text search
├── Ontology           — graph explorer, types, objects, links
├── Pipelines          — visual DAG builder, workflow editor
├── Scraper            — template browser, job monitor, visual builder
├── ML Platform        — experiments, models, agents, evaluations
├── Governance         — policies, RLS, masking, lineage, quotas
├── Capsules           — capsule registry, install, execute
├── Agents             — agent definitions, live sessions, MCP tools
├── Audit              — audit log, security events
└── Settings           — system config, LLM providers, tenants
```

**Keyboard shortcuts:**
- `Cmd+K` — Global command palette
- `Cmd+/` — Toggle sidebar
- `Cmd+B` — Toggle sidebar collapse
- `Escape` — Close modal/panel
- `Cmd+S` — Save current form
- `Cmd+Enter` — Run current query/action

---

## 8. Responsive Design

| Breakpoint | Layout |
|-----------|--------|
| ≥1920px | Full sidebar (240px), fluid content, 4-column card grid |
| 1280-1919px | Full sidebar, 3-column card grid |
| 768-1279px | Collapsed sidebar (64px), 2-column card grid |
| <768px | Hidden sidebar (hamburger menu), 1-column, stacked tables |

---

## 9. Accessibility (WCAG 2.1 AA)

| Requirement | Implementation |
|-------------|---------------|
| Color contrast | ≥4.5:1 for text, ≥3:1 for large text and UI components |
| Keyboard navigation | All interactive elements focusable, Tab order logical |
| Screen reader | ARIA labels on all interactive elements, role attributes |
| Focus management | Visible focus indicators, focus trap in modals |
| Motion | `prefers-reduced-motion` respected, no essential animation |
| Text scaling | Up to 200% zoom without loss of functionality |

---

## 10. Visualization Engine Architecture

*Sourced from Deep-Dive Module & Function Spec §6.2*

The Visualization Engine is the rendering backbone for all analytical UI in Voyant. It translates ontology queries into interactive charts, maps, and tables through a three-layer pipeline: Query Layer → Rendering Layer → Interaction Layer.

```
┌─────────────────────────────────────────────────────────────────┐
│              VISUALIZATION ENGINE ARCHITECTURE                   │
│                                                                  │
│  ┌─ QUERY LAYER ───────────────────────────────────────────┐    │
│  │                                                          │    │
│  │  User Interaction → Widget Config → Ontology Query       │    │
│  │       │                    │              │               │    │
│  │       ▼                    ▼              ▼               │    │
│  │  Filter/Drag/       Generate query   Execute against     │    │
│  │  Configure          spec (JSON)      Ontology objects    │    │
│  │                                                          │    │
│  │  Widget Query Spec Example:                              │    │
│  │  {                                                       │    │
│  │    "objectType": "Order",                                │    │
│  │    "select": ["order_date", "revenue"],                  │    │
│  │    "filter": [                                           │    │
│  │      { "property": "status", "eq": "completed" },       │    │
│  │      { "property": "order_date", "gte": "2026-01-01" }  │    │
│  │    ],                                                    │    │
│  │    "groupBy": {                                          │    │
│  │      "property": "order_date",                           │    │
│  │      "granularity": "month"                              │    │
│  │    },                                                    │    │
│  │    "aggregation": { "property": "revenue", "fn": "SUM" }│    │
│  │  }                                                       │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ RENDERING LAYER ──────────────────────────────────────┐     │
│  │                                                          │    │
│  │  Chart Library: Apache ECharts 5.x (primary)             │    │
│  │  Map Library: Leaflet + Mapbox GL                        │    │
│  │  Table: Custom virtual-scroll table component            │    │
│  │                                                          │    │
│  │  Rendering Pipeline:                                     │    │
│  │  1. Query result (JSON/Arrow) arrives                    │    │
│  │  2. Data transformer normalizes to chart-ready format    │    │
│  │  3. Chart config generator maps user selections to       │    │
│  │     ECharts option object                                │    │
│  │  4. ECharts renders with animation                       │    │
│  │  5. Interaction handlers registered (click, hover,       │    │
│  │     brush, zoom)                                         │    │
│  │  6. Cross-filter events emitted to dashboard bus         │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ CHART TYPE CATALOG (Complete) ────────────────────────┐    │
│  │                                                          │    │
│  │  BASIC:                                                  │    │
│  │  • Line Chart (single/multi series, area fill, stacked)  │    │
│  │  • Bar Chart (vertical, horizontal, stacked, grouped)    │    │
│  │  • Pie Chart                                             │    │
│  │  • Donut Chart                                           │    │
│  │  • Scatter Plot (with optional size/color dimensions)    │    │
│  │  • Bubble Chart                                          │    │
│  │  • Area Chart (stacked, percentage)                      │    │
│  │                                                          │    │
│  │  STATISTICAL:                                            │    │
│  │  • Box Plot (with outliers)                              │    │
│  │  • Histogram (configurable bin count)                    │    │
│  │  • Heatmap (2D density)                                  │    │
│  │  • Candlestick / OHLC                                    │    │
│  │  • Radar / Spider Chart                                  │    │
│  │  • Error Bar                                             │    │
│  │                                                          │    │
│  │  HIERARCHICAL:                                           │    │
│  │  • Treemap                                               │    │
│  │  • Sunburst                                              │    │
│  │  • Sankey Diagram                                        │    │
│  │  • Funnel Chart                                          │    │
│  │                                                          │    │
│  │  RELATIONAL:                                             │    │
│  │  • Network / Graph (node-link diagram)                   │    │
│  │  • Chord Diagram                                         │    │
│  │                                                          │    │
│  │  GEOGRAPHIC:                                             │    │
│  │  • Choropleth Map                                        │    │
│  │  • Bubble Map                                            │    │
│  │  • Heat Map (geographic)                                 │    │
│  │  • Point Map (with clustering)                           │    │
│  │  • Flow Map (origin-destination)                         │    │
│  │                                                          │    │
│  │  KPI / GAUGE:                                            │    │
│  │  • KPI Card (value + trend + comparison)                 │    │
│  │  • Gauge Chart                                           │    │
│  │  • Progress Bar                                          │    │
│  │  • Bullet Chart                                          │    │
│  │                                                          │    │
│  │  SPECIAL:                                                │    │
│  │  • Waterfall Chart                                       │    │
│  │  • Word Cloud                                            │    │
│  │  • Timeline / Gantt                                      │    │
│  │  • Sparkline (inline)                                    │    │
│  │  • Pareto Chart                                          │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 10.1 Chart Type Catalog Summary

| Category | Chart Types | Count |
|----------|------------|-------|
| Basic | Line, Bar, Pie, Donut, Scatter, Bubble, Area | 7 |
| Statistical | Box Plot, Histogram, Heatmap, Candlestick, Radar, Error Bar | 6 |
| Hierarchical | Treemap, Sunburst, Sankey, Funnel | 4 |
| Relational | Network/Graph, Chord | 2 |
| Geographic | Choropleth, Bubble Map, Heat Map, Point Map, Flow Map | 5 |
| KPI/Gauge | KPI Card, Gauge, Progress Bar, Bullet | 4 |
| Special | Waterfall, Word Cloud, Timeline/Gantt, Sparkline, Pareto | 5 |
| **Total** | | **33** |

---

## 11. Cross-Filtering Engine (Deep Specification)

*Sourced from Deep-Dive Module & Function Spec §6.2*

The Cross-Filtering Engine enables interactive dashboard exploration. When a user clicks a data point in one widget, the selection propagates as a filter to all other widgets on the same dashboard.

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ┌─ CROSS-FILTERING ENGINE ───────────────────────────────┐    │
│  │                                                          │    │
│  │  When user clicks a data point in Widget A:              │    │
│  │  1. Widget A emits cross-filter event:                   │    │
│  │     { source: "widget_a",                                │    │
│  │       filter: { property: "segment", value: "Premium" }} │    │
│  │  2. Dashboard event bus broadcasts to all widgets        │    │
│  │  3. Each widget checks if it has a matching filterable   │    │
│  │     dimension                                            │    │
│  │  4. Matching widgets apply the filter and re-query       │    │
│  │  5. Non-matching widgets remain unchanged                │    │
│  │  6. Visual indication shows which widgets are filtered   │    │
│  │                                                          │    │
│  │  Configuration per widget:                               │    │
│  │  crossFilterBindings: [                                  │    │
│  │    { dimension: "segment", accepts: ["segment"] },       │    │
│  │    { dimension: "region", accepts: ["region", "country"] }│   │
│  │  ]                                                       │    │
│  │  crossFilterMode: "BROADCAST" | "RECEIVE_ONLY" | "NONE" │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 11.1 Cross-Filter Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `BROADCAST` | Emits filter events AND receives them | Interactive charts (default) |
| `RECEIVE_ONLY` | Only receives filter events | Summary KPI cards |
| `NONE` | Ignores cross-filter events | Fixed reference charts |

### 11.2 Cross-Filter Event Flow

```
User clicks "Premium" segment in Widget A
  │
  ▼
Widget A emits: { source: "widget_a", filter: { segment: "Premium" } }
  │
  ▼
Dashboard Event Bus broadcasts to all widgets
  │
  ├──▶ Widget B (Revenue by Region) — has "segment" dimension → applies filter, re-queries
  ├──▶ Widget C (Orders over Time) — has "segment" dimension → applies filter, re-queries
  ├──▶ Widget D (KPI: Total Customers) — RECEIVE_ONLY mode → applies filter, re-queries
  └──▶ Widget E (Service Health) — NONE mode → no change
```

---

## 12. Drill-Down Engine (Deep Specification)

*Sourced from Deep-Dive Module & Function Spec §6.2*

The Drill-Down Engine enables hierarchical data exploration. Users can click on data points to zoom into finer granularity, and use a breadcrumb trail to navigate back up.

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ┌─ DRILL-DOWN ENGINE ────────────────────────────────────┐    │
│  │                                                          │    │
│  │  Hierarchies (configurable per dimension):               │    │
│  │  Time:     Year → Quarter → Month → Week → Day          │    │
│  │  Geography: Country → State → City → ZIP                │    │
│  │  Product:  Category → Subcategory → Product → SKU       │    │
│  │  Org:      Division → Department → Team → Individual    │    │
│  │                                                          │    │
│  │  Interaction:                                            │    │
│  │  • Click on a bar/point → drill down one level           │    │
│  │  • Breadcrumb trail shows current drill path             │    │
│  │  • Click breadcrumb to drill back up                     │    │
│  │  • Right-click → "Drill to detail" (show raw records)    │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 12.1 Predefined Hierarchies

| Hierarchy | Levels | Example Drill Path |
|-----------|--------|--------------------|
| **Time** | Year → Quarter → Month → Week → Day | 2026 → Q3 → September → Week 37 → Sept 10 |
| **Geography** | Country → State → City → ZIP | USA → California → San Francisco → 94102 |
| **Product** | Category → Subcategory → Product → SKU | Electronics → Laptops → MacBook Pro → MBP-16-M3 |
| **Organization** | Division → Department → Team → Individual | Engineering → Data → Platform → Alice |

### 12.2 Drill-Down Interaction Pattern

```
Initial view: Revenue by Year (bar chart)
  │
  │ User clicks "2026" bar
  ▼
Drill level 1: Revenue by Quarter for 2026
  Breadcrumb: [All Years] > [2026]
  │
  │ User clicks "Q3" bar
  ▼
Drill level 2: Revenue by Month for Q3 2026
  Breadcrumb: [All Years] > [2026] > [Q3]
  │
  │ User clicks breadcrumb "2026"
  ▼
Drill back up: Revenue by Quarter for 2026
  Breadcrumb: [All Years] > [2026]
  │
  │ User right-clicks "Q3" → "Drill to detail"
  ▼
Raw records view: All orders in Q3 2026
  Breadcrumb: [All Years] > [2026] > [Q3] > [Detail]
```

---

## 13. Analytical Paths (Contour-style)

*Sourced from Deep-Dive Module & Function Spec §6.2*

Analytical Paths enable users to explore data through a series of saved analytical steps, each building on the previous one — similar to Palantir Contour's approach. Paths act as a "breadcrumb trail" of analysis that can be named, shared, branched, and converted to dashboard widgets.

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ┌─ ANALYTICAL PATHS (Contour-style) ─────────────────────┐    │
│  │                                                          │    │
│  │  Concept: Users can explore data through a series of     │    │
│  │  analytical steps, each building on the previous one.    │    │
│  │  Like a "breadcrumb trail" of analysis.                  │    │
│  │                                                          │    │
│  │  Example Path:                                           │    │
│  │  Step 1: "All Orders" (5.8M rows)                       │    │
│  │  Step 2: Filter "region = West" (1.4M rows)             │    │
│  │  Step 3: Group by "product_category" → Bar chart         │    │
│  │  Step 4: Drill into "Electronics" (234K rows)            │    │
│  │  Step 5: Add "time" dimension → Trend line               │    │
│  │  Step 6: Compare with "East" region → Dual line chart    │    │
│  │                                                          │    │
│  │  Each step is saved and can be:                          │    │
│  │  • Named and shared with other users                     │    │
│  │  • Branched (explore alternative paths from any step)    │    │
│  │  • Converted to a dashboard widget                       │    │
│  │  • Exported as a report                                  │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 13.1 Analytical Path Operations

| Operation | Description | Example |
|-----------|-------------|---------|
| **Add Step** | Apply a filter, group, aggregation, or drill-down | Filter by region, then group by category |
| **Branch** | Fork from any step to explore alternative directions | At Step 3, branch to compare with "South" region |
| **Name** | Give a step or path a human-readable label | "Q3 Electronics Deep Dive" |
| **Share** | Share a path with other users (view or edit) | Share with Data Science team |
| **Convert to Widget** | Turn a path step into a pinned dashboard widget | Pin Step 5 (trend line) to the Sales Dashboard |
| **Export** | Export path results as CSV, PDF, or scheduled report | Weekly export of top-KPI path |
| **Undo / Backtrack** | Revert to a previous step | Go back from Step 5 to Step 3 |

### 13.2 Parameterized Analyses

Users can define parameters that make analyses reusable and shareable:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Parameters:                                                     │
│  • date_range: DateRange  (default: last 30 days)              │
│  • region: String[]       (default: ["All"])                    │
│  • min_revenue: Double    (default: 0)                          │
│  • compare_mode: Boolean  (default: false)                      │
│                                                                  │
│  These parameters appear as UI controls at the top of           │
│  the analysis and propagate to all queries.                     │
│                                                                  │
│  Can be shared as templates:                                     │
│  "Here's my regional sales analysis. Change the                 │
│   parameters to see your region."                                │
└─────────────────────────────────────────────────────────────────┘
```

### 13.3 Path Storage Schema

| Field | Type | Description |
|-------|------|-------------|
| `path_id` | UUID | Unique path identifier |
| `name` | VARCHAR(255) | User-defined path name |
| `description` | TEXT | Optional description |
| `owner_id` | UUID | Creator |
| `tenant_id` | VARCHAR(64) | Multi-tenant isolation |
| `steps` | JSONB | Ordered array of step definitions |
| `parameters` | JSONB | Parameterized variables (date_range, region, etc.) |
| `shared_with` | JSONB | List of user/team IDs with access |
| `is_template` | BOOLEAN | Whether this is a reusable template |
| `created_at` | TIMESTAMPTZ | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | Last modification timestamp |

---

**Created:** 2026-09-09
**Document ID:** VOYANT-UIUX-4.0.0
