# VOYANT Dashboard v4.0 — UI/UX Development Plan

## Design Philosophy

**"Palantir's depth, Databricks' clarity, VOYANT's agent-native intelligence."**

Dark-first, data-dense, agent-aware. Every screen works for both humans AND shows what agents are doing in real-time.

---

## Design System

### Color Palette

| Token | Light Mode | Dark Mode | Usage |
|-------|-----------|-----------|-------|
| `brand` | `#FF4D00` | `#FF6B2B` | Primary actions, active states, accent |
| `brand-subtle` | `#FFF3ED` | `#1A1008` | Backgrounds for brand-highlighted items |
| `ink` | `#050505` | `#FAFAFA` | Primary text |
| `ink-muted` | `#6B7280` | `#9CA3AF` | Secondary text |
| `surface` | `#F5F5F5` | `#0A0A0A` | Page background |
| `card` | `#FFFFFF` | `#141414` | Card/panel background |
| `card-hover` | `#FAFAFA` | `#1A1A1A` | Card hover state |
| `border` | `#E5E7EB` | `#262626` | Borders, dividers |
| `success` | `#22C55E` | `#22C55E` | Success states, healthy |
| `warning` | `#F59E0B` | `#F59E0B` | Warning states |
| `danger` | `#EF4444` | `#EF4444` | Error states, destructive |
| `info` | `#3B82F6` | `#3B82F6` | Information, links |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Page title | Geist | 28px | 900 |
| Section title | Geist | 20px | 700 |
| Card title | Inter | 14px | 600 |
| Body | Inter | 13px | 400 |
| Caption | Inter | 11px | 400 |
| Code | JetBrains Mono | 12px | 400 |

### Layout Grid

- **Sidebar**: 240px fixed, collapsible to 64px icons-only
- **Main content**: fluid, max-width1920px, padding32px
- **Card grid**: CSS Grid, min-card-width280px, gap16px
- **Tables**: full-width, sticky header, row height40px
- **Modals**: centered, max-width720px, backdrop blur

---

## Navigation Architecture

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

---

## Page-by-Page Mockups

### 1. Dashboard (Home)

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Sidebar]  Dashboard                                    [🔔] [👤]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│  │ 21      │ │ 59      │ │ 2,042   │ │ 12      │ │ 46      │      │
│  │Services │ │MCP Tools│ │Tests    │ │Ontology │ │Active   │      │
│  │  🟢 all │ │  live   │ │ passing │ │ Types   │ │ Agents  │      │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘      │
│                                                                     │
│  ┌─── Service Health ──────────────┐ ┌─── Recent Activity ───────┐ │
│  │ 🟢 voyant_api    v3.0.0  :45000│ │ 2m ago  agent-xtrim ran   │ │
│  │ 🟢 voyant_worker v3.0.0  :45090│ │         voyant.sql query  │ │
│  │ 🟢 voyant_milvus 2.4.17 :19530│ │ 5m ago  ingest job        │ │
│  │ 🟢 voyant_trino  434    :45080│ │         completed (1,247   │ │
│  │ 🟡 voyant_flink  1.18   :45082│ │         rows)              │ │
│  │ 🟢 voyant_vault  1.15   :45820│ │ 12m ago ontology.type      │ │
│  │ 🟢 voyant_kafka  3.7    :45092│ │         created: Customer  │ │
│  │ 🟢 voyant_temporal 1.24 :45233│ │ 1h ago  scrape job         │ │
│  └────────────────────────────────┘ │         5 pages fetched    │ │
│                                      └────────────────────────────┘ │
│  ┌─── Job Pipeline ──────────────────────────────────────────────┐ │
│  │  Running (3)  ████████░░  Queued (7)  ░░░░░░░░░░  Done (142) │ │
│  │  ▸ ingest: customers  ▸ profile: sales  ▸ analyze: inventory │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─── Agent Activity ─────────────────┐ ┌─── MCP Tool Usage ────┐ │
│  │ Agent          Last Active  Calls  │ │ voyant.sql      ████  │ │
│  │ xtrim-demo     2m ago       34     │ │ voyant.search   ███   │ │
│  │ callcenter     15m ago      12     │ │ ontology.types  ██    │ │
│  │ gerente        1h ago       8      │ │ scrape.fetch    █     │ │
│  └────────────────────────────────────┘ └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 2. Ontology Explorer (Graph View)

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Sidebar]  Ontology Explorer                            [🔍] [⚙️]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─[Graph]─[Table]─[Grid]──┐  ┌─ Search ontology... ──────────┐   │
│                            │  └────────────────────────────────┘   │
│  ┌── Graph Canvas ──────────────────────────────────────────────┐  │
│  │                                                              │  │
│  │      ┌──────────┐         ┌──────────┐                      │  │
│  │      │ Customer │ ──────→ │  Plan    │                      │  │
│  │      │ ● 2,341  │ subscribes_to│ ● 8  │                      │  │
│  │      └──────────┘         └──────────┘                      │  │
│  │           │                    │                             │  │
│  │           │ has_service        │ has_streaming               │  │
│  │           ▼                    ▼                             │  │
│  │      ┌──────────┐         ┌──────────┐                      │  │
│  │      │ Service  │ ──────→ │Streaming │                      │  │
│  │      │ ● 5,127  │ includes│ ● 12     │                      │  │
│  │      └──────────┘         └──────────┘                      │  │
│  │                                                              │  │
│  │  ┌─ Legend ──────────────────┐  ┌─ Minimap ─────┐           │  │
│  │  │ ○ Object Type            │  │  ▪▪▪▪▪▪▪▪▪▪  │           │  │
│  │  │ ─ Link Type              │  │  ▪▪▪▪▪▪▪▪▪▪  │           │  │
│  │  │ ● Instance (count)       │  │  ▪▪▪▪▪▪▪▪▪▪  │           │  │
│  │  └──────────────────────────┘  └───────────────┘           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌── Detail Panel (right slide) ─────────────────────────────────┐ │
│  │ Customer (Object Type)                          v3            │ │
│  │ ───────────────────────────────────────────────────────────── │ │
│  │ Properties:                                                     │ │
│  │   name        string   required                                │ │
│  │   email       string   required                                │ │
│  │   plan_id     string   → Plan                                  │ │
│  │   created_at  timestamp                                        │ │
│  │                                                                 │ │
│  │ Links:                                                          │ │
│  │   → subscribes_to → Plan (1:N)                                 │ │
│  │   → has_service → Service (1:N)                                │ │
│  │                                                                 │ │
│  │ Instances: 2,341  │  Actions: 3  │  Functions: 2              │ │
│  │                                                                 │ │
│  │ [View Objects] [Create Object] [Execute Action] [Run Function] │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 3. Pipeline Builder (DAG Editor)

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Sidebar]  Pipeline Builder                             [▶️] [💾]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─ Pipeline: Customer Analytics ────── [Edit] [Run] [Schedule] ─┐ │
│  │ Status: ● Idle  │  Last run: 2h ago  │  Duration: 4m 23s     │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─ Node Palette ──┐  ┌── DAG Canvas ────────────────────────────┐ │
│  │                  │  │                                          │ │
│  │ 📥 Source        │  │  ┌─────────┐    ┌─────────┐              │ │
│  │  ├ PostgreSQL    │  │  │ 📥 Postgres──→│ 🔄 Transform│          │ │
│  │  ├ S3 File       │  │  │ Source   │    │ Clean    │              │ │
│  │  └ API           │  │  └─────────┘    └────┬────┘              │ │
│  │                  │  │                       │                    │ │
│  │ 🔄 Transform     │  │                       ▼                    │ │
│  │  ├ Clean         │  │                 ┌─────────┐              │ │
│  │  ├ Filter        │  │                 │ 🔍 Quality│              │ │
│  │  ├ Aggregate     │  │                 │ Check    │              │ │
│  │  └ Join          │  │                 └────┬────┘              │ │
│  │                  │  │                      │                    │ │
│  │ 🔍 Validate      │  │               ┌──────┴──────┐           │ │
│  │  ├ Quality       │  │               ▼              ▼           │ │
│  │  └ Schema        │  │         ┌─────────┐  ┌─────────┐        │ │
│  │                  │  │         │ ✅ Pass  │  │ ❌ Fail  │        │ │
│  │ 📤 Export        │  │         │ Store    │  │ Alert   │        │ │
│  │  ├ Database      │  │         └─────────┘  └─────────┘        │ │
│  │  ├ File          │  │                                          │ │
│  │  └ Webhook       │  └──────────────────────────────────────────┘ │
│  └──────────────────┘                                               │
│                                                                     │
│  ┌── Run History ────────────────────────────────────────────────┐  │
│  │ Run ID    Status    Duration  Started        Rows    │         │  │
│  │ #142      ✅ Done   4m 23s   2h ago         1,247   │ [View]  │  │
│  │ #141      ❌ Failed 1m 02s   5h ago         —       │ [Retry] │  │
│  │ #140      ✅ Done   4m 11s   1d ago         1,230   │ [View]  │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 4. Dashboard Builder

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Sidebar]  Dashboard Builder                            [+] [💾]   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─ Widget Palette ──┐  ┌── Canvas (drag-drop grid) ─────────────┐ │
│  │                    │  │                                        │ │
│  │ 📊 Chart           │  │ ┌──────────────┐ ┌──────────────┐     │ │
│  │  ├ Line            │  │ │ Customers    │ │ Revenue      │     │ │
│  │  ├ Bar             │  │ │    2,341     │ │   $45,230    │     │ │
│  │  ├ Pie             │  │ │  +12% ↑      │ │  +8.3% ↑    │     │ │
│  │  └ Scatter         │  │ └──────────────┘ └──────────────┘     │ │
│  │                    │  │                                        │ │
│  │ 📈 Metric          │  │ ┌─────────────────────────────────┐   │ │
│  │  ├ KPI Card        │  │ │ 📊 Revenue by Plan              │   │ │
│  │  ├ Counter         │  │ │                                 │   │ │
│  │  └ Gauge           │  │ │  ████████████  Essential 42%   │   │ │
│  │                    │  │ │  ██████████    Advanced  28%   │   │ │
│  │ 📋 Table           │  │ │  ████████      Supreme   18%   │   │ │
│  │  ├ Data Table      │  │ │  ████           Prime    12%   │   │ │
│  │  └ Pivot Table     │  │ └─────────────────────────────────┘   │ │
│  │                    │  │                                        │ │
│  │ 🗺️ Map             │  │ ┌────────────────┐ ┌──────────────┐   │ │
│  │ 🕸️ Graph           │  │ │ 🗺️ Coverage Map │ │ 📋 Recent    │   │ │
│  │ 📝 Text            │  │ │ Ecuador        │ │ Transactions │   │ │
│  │                    │  │ │ ● Quito 85K    │ │ ──────────── │   │ │
│  └────────────────────┘  │ │ ● Guayaquil   │ │ $25 Essential│   │ │
│                          │ └────────────────┘ └──────────────┘   │ │
│                          └────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 5. Agent Control Center

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Sidebar]  Agents                                       [+] [🔔]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─[Definitions]─[Live Sessions]─[MCP Tools]─[Evaluations]───────┐ │
│                                                                     │
│  ┌── Agent Definitions ──────────────────────────────────────────┐ │
│  │ Name            Model           Tools  Status  │ Actions      │ │
│  │ xtrim-demo      gpt-oss-120b    12     🟢 Active│ [Edit][Test] │ │
│  │ callcenter      gpt-oss-120b    8      🟢 Active│ [Edit][Test] │ │
│  │ gerente         gpt-oss-120b    15     🟢 Active│ [Edit][Test] │ │
│  │ data-analyst    mimo-v2.5-pro   20     🟡 Draft │ [Edit][Test] │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌── Live MCP Sessions ──────────────────────────────────────────┐ │
│  │ Session ID       Agent         Last Tool Call    Status       │ │
│  │ a1b2c3d4        xtrim-demo    voyant.sql 2m ago  🟢 Active   │ │
│  │ e5f6g7h8        callcenter    search 15m ago     🟡 Idle      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌── MCP Tool Registry (59 tools) ───────────────────────────────┐ │
│  │ Category        Tools  Last Used        │ [Test] [Docs]       │ │
│  │ Data Ops        11     2m ago           │ voyant.sql          │ │
│  │ Catalog         27     15m ago          │ voyant.sources      │ │
│  │ Scraper          7     1h ago           │ scrape.fetch        │ │
│  │ Ontology        14     30m ago          │ ontology.types      │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 6. SQL Console

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Sidebar]  SQL Console                                  [▶️] [📥]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌── Monaco Editor ──────────────────────────────────────────────┐ │
│  │ SELECT p.name AS plan, COUNT(c.id) AS customers,             │ │
│  │        SUM(p.price) AS revenue                               │ │
│  │ FROM customers c                                              │ │
│  │ JOIN plans p ON c.plan_id = p.id                             │ │
│  │ WHERE c.city = 'Quito'                                       │ │
│  │ GROUP BY p.name                                              │ │
│  │ ORDER BY revenue DESC;                                       │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  [▶️ Run] [📥 Export CSV] [📥 Export JSON]  │  3 rows │ 0.045s    │
│                                                                     │
│  ┌── Results Table ──────────────────────────────────────────────┐ │
│  │ plan          │ customers │ revenue                           │ │
│  │ ──────────────┼───────────┼───────────                        │ │
│  │ Essential     │ 847       │ $21,175                           │ │
│  │ Advanced      │ 234       │ $4,475                            │ │
│  │ Supreme       │ 166       │ $5,644                            │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌── Schema Browser ─────────────────────────────────────────────┐ │
│  │ 📂 default                                                    │ │
│  │   📋 customers (2,341 rows)                                   │ │
│  │     ├ id        UUID                                          │ │
│  │     ├ name      VARCHAR                                       │ │
│  │     ├ email     VARCHAR                                       │ │
│  │     ├ city      VARCHAR                                       │ │
│  │     └ plan_id   UUID                                          │ │
│  │   📋 plans (8 rows)                                           │ │
│  │   📋 services (5,127 rows)                                    │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## New Components to Build

### Core Components (reusable)

| Component | Description | Priority |
|-----------|-------------|----------|
| `voyant-graph-view` | Sigma.js force-directed graph with zoom, pan, click-to-expand | P0 |
| `voyant-dag-canvas` | Custom DAG editor with drag-drop nodes, connection lines | P0 |
| `voyant-monaco-editor` | Monaco Editor wrapper for SQL/code editing | P0 |
| `voyant-chart` | Apache ECharts wrapper (line, bar, pie, scatter, gauge) | P0 |
| `voyant-data-table` | Full-featured table with sort, filter, pagination, export | P0 |
| `voyant-detail-panel` | Slide-in panel for object/resource details | P0 |
| `voyant-search-bar` | Global search with semantic + full-text + filters | P0 |
| `voyant-status-badge` | Status indicator with color-coded dots | P1 |
| `voyant-timeline` | Timeline view for audit events, job history | P1 |
| `voyant-map` | Leaflet map for geospatial data | P1 |
| `voyant-drag-drop` | Drag-and-drop framework for builders | P1 |
| `voyant-code-block` | Syntax-highlighted code display | P1 |
| `voyant-json-viewer` | Collapsible JSON tree viewer | P1 |
| `voyant-metric-card` | KPI metric with trend indicator | P1 |

### Page Views (new)

| View | Route | Description | Priority |
|------|-------|-------------|----------|
| `view-pipelines` | `/admin/pipelines` | DAG builder + run history | P0 |
| `view-agents` | `/admin/agents` | Agent control center | P0 |
| `view-ml` | `/admin/ml` | ML experiments, models, serving | P1 |
| `view-lineage` | `/admin/lineage` | Data lineage graph | P1 |

### Page Views (upgrade existing)

| View | Current | Upgrade To | Priority |
|------|---------|-----------|----------|
| `view-ontology` | Basic card grid | Graph view + table + grid + detail panel | P0 |
| `view-dashboard` | Basic stats | Full dashboard with charts, health, activity | P0 |
| `view-sql` | Basic textarea | Monaco editor + schema browser + results table | P0 |
| `view-scraper` | Basic list | Template browser + job monitor + visual builder | P1 |
| `view-search` | Basic input | Semantic search with filters + result cards | P1 |
| `view-governance` | Basic table | Policy builder + RLS visualizer + lineage | P1 |

---

## Dependencies to Install

```json
{
  "dependencies": {
    "sigma": "^3.0.0",
    "graphology": "^0.25.4",
    "echarts": "^5.5.0",
    "monaco-editor": "^0.47.0",
    "leaflet": "^1.9.4"
  },
  "devDependencies": {
    "@types/leaflet": "^1.9.8"
  }
}
```

---

## Development Sprints

### Sprint A: Foundation (Week 1)
- [ ] Install dependencies (sigma, echarts, monaco, leaflet)
- [ ] Create `voyant-graph-view` component (Sigma.js)
- [ ] Create `voyant-chart` component (ECharts)
- [ ] Create `voyant-monaco-editor` component
- [ ] Create `voyant-data-table` component
- [ ] Create `voyant-detail-panel` component
- [ ] Update design system (dark mode, new tokens)

### Sprint B: Ontology Explorer (Week 2)
- [ ] Graph view: force-directed layout of object types as nodes
- [ ] Graph view: link types as labeled edges
- [ ] Click-to-expand: show instances on node click
- [ ] Search-highlight: find and zoom to nodes
- [ ] Detail panel: show type properties, links, instances
- [ ] Table view: sortable, filterable data grid
- [ ] Grid view: card layout with metrics

### Sprint C: SQL Console + Dashboard (Week 3)
- [ ] Monaco editor with SQL syntax highlighting
- [ ] Autocomplete from Trino schema
- [ ] Results table with sort, filter, export
- [ ] Schema browser (tree view of tables/columns)
- [ ] Dashboard builder: drag-drop grid layout
- [ ] Chart widgets: line, bar, pie, gauge, metric card
- [ ] Table widget with live data binding

### Sprint D: Pipeline Builder (Week 4)
- [ ] DAG canvas: custom Lit canvas with SVG connections
- [ ] Node palette: source, transform, validate, export nodes
- [ ] Drag-drop from palette to canvas
- [ ] Connection drawing between nodes
- [ ] Pipeline execution via Temporal
- [ ] Run history table with status, duration, logs
- [ ] Pipeline save/load as JSON

### Sprint E: Agent Center + ML (Week 5)
- [ ] Agent definition CRUD with prompt editor
- [ ] Live MCP session monitor
- [ ] MCP tool registry browser with test capability
- [ ] Evaluation runner with test case editor
- [ ] ML experiment browser
- [ ] Model registry with version/stage management
- [ ] Serving endpoint monitor

### Sprint F: Polish + Advanced (Week 6)
- [ ] Scraper visual builder (reuse DAG canvas)
- [ ] Data lineage graph view
- [ ] Map view for geospatial data
- [ ] Timeline view for audit events
- [ ] Dark mode toggle
- [ ] Responsive design (mobile sidebar collapse)
- [ ] Keyboard shortcuts
- [ ] Global command palette (Cmd+K)

---

## File Structure

```
dashboard/src/
├── components/
│   ├── voyant-graph-view.ts       # Sigma.js graph
│   ├── voyant-dag-canvas.ts       # DAG editor
│   ├── voyant-monaco-editor.ts    # Monaco wrapper
│   ├── voyant-chart.ts            # ECharts wrapper
│   ├── voyant-data-table.ts       # Feature-rich table
│   ├── voyant-detail-panel.ts     # Slide-in detail panel
│   ├── voyant-search-bar.ts       # Global search
│   ├── voyant-metric-card.ts      # KPI card
│   ├── voyant-timeline.ts         # Timeline view
│   ├── voyant-map.ts              # Leaflet map
│   ├── voyant-code-block.ts       # Code display
│   ├── voyant-json-viewer.ts      # JSON tree
│   ├── saas-sidebar.ts            # (upgrade)
│   ├── saas-layout.ts             # (upgrade)
│   ├── saas-stat-card.ts          # (existing)
│   ├── saas-glass-modal.ts        # (existing)
│   ├── saas-infra-card.ts         # (existing)
│   └── saas-status-dot.ts         # (existing)
├── views/
│   ├── view-dashboard.ts          # (upgrade)
│   ├── view-ontology.ts           # (upgrade to graph)
│   ├── view-sql.ts                # (upgrade to Monaco)
│   ├── view-scraper.ts            # (upgrade)
│   ├── view-search.ts             # (upgrade)
│   ├── view-governance.ts         # (upgrade)
│   ├── view-pipelines.ts          # NEW
│   ├── view-agents.ts             # NEW
│   ├── view-ml.ts                 # NEW
│   ├── view-lineage.ts            # NEW
│   ├── view-jobs.ts               # (existing)
│   ├── view-sources.ts            # (existing)
│   ├── view-capsules.ts           # (existing)
│   ├── view-audit.ts              # (existing)
│   ├── view-settings.ts           # (existing)
│   ├── view-tenants.ts            # (existing)
│   └── view-login.ts              # (existing)
├── lib/
│   ├── api.ts                     # (existing)
│   ├── router.ts                  # (existing)
│   ├── graph-layout.ts            # NEW: graph layout algorithms
│   ├── chart-themes.ts            # NEW: ECharts theme config
│   └── monaco-config.ts           # NEW: Monaco editor config
├── styles/
│   └── globals.css                # (upgrade with dark mode)
├── main.ts                        # (upgrade with new routes)
└── index.ts                       # (existing)
```
