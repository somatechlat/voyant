# VOYANT Ontology Viewer & Designer — Full Specification

**Document ID:** VOYANT-ONTOLOGY-VIEWER-SPEC-1.0
**Version:** 1.0.0
**Date:** 2026-09-08
**Standard:** ISO/IEC 29148:2018 (Requirements) · ISO/IEC 25010 (Quality) · ISO/IEC 42010 (Architecture)
**Status:** Draft for Review

---

## 1. Executive Summary

The Ontology Viewer & Designer is the central interface for VOYANT's knowledge graph. It is the single screen where humans and agents define, explore, and operate on the data model that powers everything else — SQL queries, semantic search, scraper extraction, ML features, governance policies, and agent reasoning.

This document defines every screen, every interaction, every data flow, and every quality requirement for building a production-grade ontology interface that surpasses Palantir Foundry's Workshop, Neo4j Bloom, and Databricks' Unity Catalog.

---

## 2. What Is an Ontology and Why Does It Need a Viewer

### 2.1 Definition

An ontology is a formal description of a domain — the **types of things** that exist, their **properties**, and the **relationships** between them. In VOYANT:

- **Object Types** = classes (Cliente, Plan, Servicio)
- **Properties** = attributes (nombre: string, precio: float)
- **Link Types** = relationships (subscribes_to, has_service)
- **Objects** = instances (Juan Navarro, Plan Essential 300M)
- **Links** = instance relationships (Juan subscribes_to Essential)

### 2.2 Why a Viewer/Designer Is Critical

| Stakeholder | Need |
|-------------|------|
| **Data Engineer** | Define types, validate schemas, manage migrations |
| **Business Analyst** | Explore data relationships, find insights, build queries |
| **AI Agent** | Query the ontology to reason about data, generate SQL, traverse graphs |
| **Governance Officer** | Audit data lineage, enforce policies, classify sensitivity |
| **Developer** | Build actions, functions, workflows on top of ontology types |

The viewer is the **single pane of glass** where all these roles interact with the knowledge graph.

---

## 3. Industry Benchmarking

### 3.1 Palantir Foundry Ontology

**What they do well:**
- Object Explorer: search, filter, pivot, compare across types
- Graph visualization: force-directed layout with type-colored nodes
- Action Builder: visual configuration of parameters, rules, side effects
- Function Editor: Monaco code editor with type-aware autocomplete
- Timeline View: temporal data visualization
- Map View: geospatial overlay with clustering
- Real-time collaboration: multiple users editing simultaneously

**What they lack:**
- No MCP/agent-native access (human-only UI)
- No self-hosted option (cloud-only)
- No open ontology standard (proprietary format)

### 3.2 Neo4j Bloom

**What they do well:**
- Immersive graph exploration with natural language search
- Perspective-based views (different lenses on the same graph)
- Node/edge styling by properties
- Expand-on-click traversal
- Dark canvas with glowing nodes

**What they lack:**
- No ontology type system (just raw graph)
- No action/function framework
- No governance layer

### 3.3 Protégé (Stanford)

**What they do well:**
- OWL/RDF standard ontology editing
- Class hierarchy with inheritance
- Property restrictions and cardinality
- Reasoning and inference
- Plugin ecosystem

**What they lack:**
- No graph visualization (tree-only)
- No real-time data instances
- No action framework
- Academic-only, not production-ready

### 3.4 What VOYANT Must Combine

VOYANT must take:
- **Palantir's** depth (actions, functions, explorer, real-time)
- **Neo4j's** graph immersion (force-directed, expand-on-click, styling)
- **Protégé's** rigor (type system, validation, reasoning)
- **Plus**: MCP agent access (unique — no competitor has this)

---

## 4. Screen Architecture

### 4.1 Main Layout (Three-Panel)

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Sidebar]  Ontology Explorer                   [🔍] [⚙️] [👤]     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──[Graph]──[Table]──[Grid]──[Code]──┐                            │
│  └────────────────────────────────────┘                            │
│                                                                     │
│  ┌── Main Canvas ──────────────────────┐ ┌── Detail Panel ───────┐ │
│  │                                      │ │                       │ │
│  │  (Graph | Table | Grid | Code view)  │ │  (slides in on click) │ │
│  │                                      │ │                       │ │
│  │                                      │ │  Type: Cliente        │ │
│  │                                      │ │  10 properties        │ │
│  │                                      │ │  120 instances        │ │
│  │                                      │ │  6 link types         │ │
│  │                                      │ │                       │ │
│  │                                      │ │  [View Objects]       │ │
│  │                                      │ │  [Create Object]      │ │
│  │                                      │ │  [Execute Action]     │ │
│  │                                      │ │  [Run Function]       │ │
│  │                                      │ │  [Edit Type]          │ │
│  │                                      │ │  [Delete Type]        │ │
│  └──────────────────────────────────────┘ └───────────────────────┘ │
│                                                                     │
│  ┌── Metrics Bar ──────────────────────────────────────────────────┐ │
│  │ 7 types │ 6 links │ 44 properties │ 31 instances │ 3 zonas    │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Five View Modes

| Mode | Purpose | Interaction |
|------|---------|-------------|
| **Graph** | Visual knowledge graph exploration | Click nodes, expand neighbors, zoom, pan, search |
| **Table** | Structured data grid for types, objects, links | Sort, filter, export, inline edit |
| **Grid** | Card-based overview with metrics | Click cards for detail, drag to create links |
| **Code** | Monaco editor for functions, actions, queries | Syntax highlighting, autocomplete, run |
| **Schema** | Type hierarchy tree with inheritance | Drag-drop to restructure, visual validation |

---

## 5. Graph View — Detailed Specification

### 5.1 Visual Design

**Node representation:**
- Circular nodes with type-specific colors (brand palette)
- Size proportional to instance count (logarithmic scale)
- Label: type name (bold, 12px Inter)
- Sublabel: instance count (10px, muted)
- Icon: type-specific icon (optional, top-left of node)

**Edge representation:**
- Curved lines (Bezier) between connected nodes
- Label: link type name (9px, muted, positioned at midpoint)
- Arrowhead: directional indicator
- Color: lighter shade of source node color
- Width: proportional to link instance count (1-4px)

**Canvas:**
- Background: #FAFAFA (light) or #0A0A0A (dark)
- Dot grid pattern (subtle, 20px spacing)
- Minimap: bottom-right corner (160x120px)
- Zoom: scroll wheel (0.1x to 10x)
- Pan: click-drag on empty space
- Select: click on node/edge
- Multi-select: Shift+click or lasso

### 5.2 Interactions

| Action | Result |
|--------|--------|
| **Click node** | Select node, open detail panel, highlight connected edges |
| **Double-click node** | Expand neighbors (load linked types and instances) |
| **Right-click node** | Context menu: View Objects, Create Object, Edit Type, Delete Type, Execute Action |
| **Click edge** | Select edge, show link type details in panel |
| **Hover node** | Tooltip with type name, instance count, property count |
| **Search** | Type-ahead search, highlight matching nodes, zoom to result |
| **Filter** | Filter by type category, instance count range, property existence |
| **Layout** | Toggle: force-directed, hierarchical, circular, grid |

### 5.3 Graph Algorithms

| Algorithm | Purpose |
|-----------|---------|
| **Force-directed** (default) | Natural clustering, minimizes edge crossings |
| **Hierarchical** | Top-down tree for inheritance/containment |
| **Circular** | Equal spacing for overview |
| **Grid** | Alphabetical排列 for comparison |
| **Community detection** | Highlight clusters of related types |
| **Centrality** | Size nodes by betweenness/degree centrality |

### 5.4 Performance Requirements

| Metric | Target |
|--------|--------|
| Render100 nodes | <100ms |
| Render1000 nodes | <500ms |
| Render10000 nodes | <2s (with WebGL) |
| Zoom/pan latency | <16ms (60fps) |
| Search latency | <100ms |
| Layout computation | <1s for1000 nodes |

---

## 6. Table View — Detailed Specification

### 6.1 Object Types Table

| Column | Sortable | Filterable | Actions |
|--------|----------|------------|---------|
| Name | ✓ | ✓ (text search) | Click → detail panel |
| Description | ✓ | ✓ | |
| Properties | ✓ (count) | ✓ (range) | |
| Instances | ✓ (count) | ✓ (range) | |
| Version | ✓ | | |
| Created | ✓ | ✓ (date range) | |
| Actions | | | Edit, Delete, Export |

### 6.2 Object Instances Table

When viewing instances of a specific type:

| Column | Type | Sortable | Filterable |
|--------|------|----------|------------|
| ID | UUID | ✓ | |
| [Dynamic columns] | Per property definition | ✓ | ✓ |
| Version | Integer | ✓ | |
| Created | Timestamp | ✓ | ✓ (date range) |
| Actions | | | Edit, Delete, View Links |

**Dynamic columns** are generated from the type's property definitions. For Cliente:
- nombre (string), cedula (string), email (string), ciudad (string), plan (string), monto_mensual (float), estado (string)

### 6.3 Link Types Table

| Column | Sortable | Filterable |
|--------|----------|------------|
| Name | ✓ | ✓ |
| Source Type | ✓ | ✓ |
| Target Type | ✓ | ✓ |
| Cardinality | ✓ | ✓ |
| Instances | ✓ (count) | ✓ (range) |
| Actions | | Edit, Delete |

### 6.4 Link Instances Table

When viewing links of a specific type:

| Column | Sortable | Filterable |
|--------|----------|------------|
| Source Object | ✓ | ✓ |
| Target Object | ✓ | ✓ |
| Properties | | |
| Created | ✓ | ✓ |
| Actions | | Delete |

### 6.5 Export Formats

| Format | Scope |
|--------|-------|
| CSV | Current view (filtered/sorted) |
| Excel | Current view with formatting |
| JSON | Full objects with nested relationships |
| Parquet | For ML pipelines |

---

## 7. Grid View — Detailed Specification

### 7.1 Type Cards

Each object type displayed as a card:

```
┌─────────────────────────────────────────┐
│ 📐 Cliente                         v1   │
│ Cliente de servicios de telecomunic...  │
│                                          │
│  10 properties  ·  120 instances         │
│  6 linked types                          │
│                                          │
│  [🔗subscribes_to] [🔗has_service]      │
│  [🔗raised_ticket] [🔗billed_for]       │
└─────────────────────────────────────────┘
```

**Card interactions:**
- Click → opens detail panel
- Hover → border highlights with type color
- Drag → creates link between types (visual link builder)

### 7.2 Metrics Bar

Horizontal bar at top showing:
- Total types (count)
- Total link types (count)
- Total properties (count)
- Total instances (count)
- Health score (validation pass rate)

---

## 8. Detail Panel — Detailed Specification

### 8.1 Type Detail

Slides in from right (400px wide). Sections:

**Header:**
- Type name (24px, bold)
- Description (14px, muted)
- Version badge
- Edit button

**Stats Grid (2x2):**
- Properties count
- Instances count
- Link types count
- Last modified

**Properties Section:**
- Table of all properties: name, type, required, default, validation
- Add Property button
- Inline edit for each property
- Drag to reorder

**Link Types Section:**
- List of connected link types
- Source → Target direction
- Cardinality badge
- Instance count

**Actions Section:**
- View Objects → switches to table view filtered by this type
- Create Object → opens object creation form
- Execute Action → lists available action types
- Run Function → lists available functions
- Edit Type → inline edit form
- Delete Type → confirmation dialog

### 8.2 Object Instance Detail

**Header:**
- Object ID (monospace, muted)
- Type name badge
- Version badge

**Properties Section:**
- Editable form for all properties
- Validation errors inline
- Save/Cancel buttons

**Links Section:**
- Outgoing links: target objects with link type
- Incoming links: source objects with link type
- Add Link button
- Delete Link button

**Actions Section:**
- Available actions for this object type
- Execute with parameter form
- Undo button (if action is undoable)

**Audit Trail:**
- History of changes to this object
- Who changed what, when
- Diff view (old value → new value)

---

## 9. Code View — Detailed Specification

### 9.1 Function Editor

Monaco Editor with:
- Python/TypeScript syntax highlighting
- Type-aware autocomplete (from ontology schema)
- Error highlighting (inline)
- Run button (Ctrl+Enter)
- Output panel (stdout, stderr, return value)
- Version history

### 9.2 Action Editor

Visual form builder for action definitions:
- Parameter list (add/remove/reorder)
- Rule builder (condition → action)
- Side effect configuration (webhook URL, notification channel)
- Undo rule configuration
- Test button (run against sample object)

### 9.3 Query Editor

SQL editor with:
- Trino SQL syntax
- Schema autocomplete (from ontology)
- Results table
- Export button
- Query history

---

## 10. Schema View — Detailed Specification

### 10.1 Type Hierarchy Tree

Tree view showing:
- Root types (no parent)
- Child types (inheritance)
- Interface implementations
- Struct type compositions

### 10.2 Visual Type Builder

Drag-and-drop interface for creating types:
- Property palette (string, int, float, bool, date, etc.)
- Drop onto type canvas
- Configure validation rules visually
- Preview JSON schema
- Generate migration

---

## 11. Agent Integration (MCP)

### 11.1 MCP Tools for Ontology

| Tool | Purpose |
|------|---------|
| `voyant.ontology.types.list` | List all object types |
| `voyant.ontology.types.get` | Get type with properties |
| `voyant.ontology.types.create` | Create new type |
| `voyant.ontology.objects.list` | List instances |
| `voyant.ontology.objects.create` | Create instance |
| `voyant.ontology.objects.get` | Get instance with links |
| `voyant.ontology.objects.update` | Update instance |
| `voyant.ontology.objects.batch_create` | Bulk create |
| `voyant.ontology.links.create` | Create link |
| `voyant.ontology.links.delete` | Delete link |
| `voyant.ontology.traverse` | Multi-hop graph traversal |
| `voyant.ontology.interfaces.list` | List interfaces |
| `voyant.ontology.actions.execute` | Execute action on object |
| `voyant.ontology.functions.run` | Run function |

### 11.2 Agent Workflows

**Scenario 1: Agent discovers new data source**
1. Agent calls `voyant.discover` → detects PostgreSQL
2. Agent calls `voyant.connect` → registers source
3. Agent calls `voyant.ingest` → loads data
4. Agent calls `voyant.ontology.types.create` → creates type from schema
5. Agent calls `voyant.ontology.objects.batch_create` → loads instances
6. Agent calls `voyant.vector.index` → indexes for semantic search

**Scenario 2: Agent answers user question**
1. User asks "How many customers in Quito?"
2. Agent calls `voyant.ontology.types.get` → gets Cliente schema
3. Agent generates SQL: `SELECT COUNT(*) FROM xtrim_clientes WHERE ciudad = 'Quito'`
4. Agent calls `voyant.sql` → executes query
5. Agent returns: "14 customers in Quito"

**Scenario 3: Agent traverses relationships**
1. User asks "What plan does Juan Navarro have?"
2. Agent calls `voyant.ontology.objects.list` → finds Juan
3. Agent calls `voyant.ontology.traverse` → follows subscribes_to link
4. Agent returns: "Juan Navarro is on the Advanced 500M plan ($19.13/mo)"

---

## 12. Data Model (Backend)

### 12.1 Existing Models (12 total)

| Model | Fields | Status |
|-------|--------|--------|
| ObjectType | name, description, version, deleted_at | ✓ Complete |
| Property | object_type(FK), name, property_type, required, default_value, validation_rules | ✓ Complete |
| Object | object_type(FK), properties(JSON), version, deleted_at | ✓ Complete |
| LinkType | name, source_type(FK), target_type(FK), cardinality, properties_schema | ✓ Complete |
| Link | link_type(FK), source_object(FK), target_object(FK), properties, deleted_at | ✓ Complete |
| Interface | name, description, required_properties, optional_properties, implementing_types(M2M) | ✓ Complete |
| StructType | name, description, fields(JSON), version | ✓ Complete |
| SharedProperty | name, property_type, default_value, validation_rules, used_by_types(M2M) | ✓ Complete |
| ValueType | name, base_type, constraints, is_system, version | ✓ Complete |
| ActionType | name, status, parameters(JSON), rules(JSON), side_effects(JSON), undoable, undo_rules | ✓ Complete |
| Function | name, status, language, source_code, entry_point, input_schema, output_schema | ✓ Complete |
| ActionExecution | action_type(FK), target_object(FK), params, previous_values, changes, status | ✓ Complete |

### 12.2 API Endpoints (51 total)

Full CRUD for all12 models plus batch operations, upsert, and traversal.

---

## 13. Quality Requirements (ISO/IEC 25010)

| Characteristic | Requirement | Verification |
|---------------|-------------|-------------|
| **Functional Suitability** | All CRUD operations complete, all view modes functional | Test suite:200+ tests |
| **Performance Efficiency** | Graph render <100ms (100 nodes), search <100ms | Benchmark tests |
| **Compatibility** | Works on Chrome, Firefox, Safari, Edge | Cross-browser tests |
| **Usability** | Keyboard navigation, screen reader support, WCAG2.1 AA | Accessibility audit |
| **Reliability** | Graceful degradation when services unavailable | Fault injection tests |
| **Security** | JWT auth, RBAC, tenant isolation, input validation | Security test suite |
| **Maintainability** | Component-based Lit3 architecture, <100 lines per function | Code review |
| **Portability** | Runs in Docker, K8s, bare metal | Deployment tests |

---

## 14. Implementation Phases

### Phase 1: Foundation (Week1)
- [ ] Graph view with force-directed layout (HTML/SVG, no external lib)
- [ ] Table view with sort/filter/export
- [ ] Grid view with cards
- [ ] Detail panel with properties and links
- [ ] Metrics bar

### Phase 2: Interactions (Week2)
- [ ] Click-to-select nodes and edges
- [ ] Double-click to expand neighbors
- [ ] Search with highlight and zoom
- [ ] Filter by type, count, properties
- [ ] Context menu (right-click)

### Phase 3: Editing (Week3)
- [ ] Inline property edit
- [ ] Object creation form
- [ ] Link creation form
- [ ] Type creation wizard
- [ ] Validation error display

### Phase 4: Code Integration (Week4)
- [ ] Monaco editor for functions
- [ ] Action builder (visual)
- [ ] Query editor (SQL)
- [ ] Run button with output panel

### Phase 5: Advanced (Week5-6)
- [ ] Schema view (type hierarchy tree)
- [ ] Visual type builder (drag-drop)
- [ ] Graph algorithms (community detection, centrality)
- [ ] Export to JSON/CSV/Excel
- [ ] Dark mode

---

## 15. File Structure

```
dashboard/src/
├── components/
│   ├── voyant-graph-view.ts        # HTML/SVG graph (no external lib)
│   ├── voyant-data-table.ts        # Sort/filter/export table
│   ├── voyant-detail-panel.ts      # Slide-in detail panel
│   ├── voyant-code-editor.ts       # Monaco wrapper
│   ├── voyant-metric-card.ts       # KPI card
│   ├── voyant-search-bar.ts        # Global search
│   └── voyant-context-menu.ts      # Right-click menu
├── views/
│   └── view-ontology.ts            # Main ontology page
├── lib/
│   ├── graph-layout.ts             # Layout algorithms
│   └── ontology-api.ts             # API client
└── styles/
    └── globals.css                 # Design system
```

---

## 16. Acceptance Criteria

| Criterion | Test |
|-----------|------|
| Graph renders all types and links | Playwright: check node count = types.length |
| Table shows all types with correct columns | Playwright: check table headers match spec |
| Grid shows all type cards | Playwright: check card count = types.length |
| Detail panel opens on click | Playwright: click node → panel appears |
| Search finds and highlights nodes | Playwright: search "Cliente" → node highlighted |
| Create object via form | API: POST /ontology/objects →201 |
| Execute action via UI | API: POST /ontology/actions/{id}/execute →200 |
| Export to CSV | Download file → verify content |
| All MCP tools respond | curl each tool endpoint →200 |
| Performance:100 nodes <100ms | Benchmark test |

---

**Document prepared by:** VOYANT Engineering
**Review required before implementation begins**
