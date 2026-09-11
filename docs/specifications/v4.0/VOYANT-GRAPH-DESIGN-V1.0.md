# Voyant v4.0 — Ontology Graph Designer
## Software Requirements Specification (SRS)

**Document ID:** VOYANT-SRS-GRAPH-DESIGNER-4.0.0
**Version:** 1.0.0
**Date:** 2026-09-09
**Classification:** Internal — Engineering
**Status:** Draft for Review
**Standard:** ISO/IEC/IEEE 29148:2018
**Parent Spec:** VOYANT-SRS-4.0.0 §3.1 (Ontology Engine), §3.5 (UI/UX)
**Compliance:** ISO/IEC 25010:2011 · WCAG 2.1 AA

---

## 1. Introduction

### 1.1 Purpose

This SRS defines the complete functional and non-functional requirements for the Voyant Ontology Graph Designer — the visual interface where users design, explore, and operate on the knowledge graph that powers the entire Voyant platform.

### 1.2 Scope

The Graph Designer is the **single pane of glass** for the Voyant Ontology. It replaces the current basic graph view (662 lines, viewer-only) with a full-featured visual designer that enables:

- Visual schema design (create/edit object types, properties, links)
- Knowledge graph exploration (traverse, search, filter)
- Action execution (trigger actions on objects from the graph)
- Real-time collaboration (see changes from other users/agents)

### 1.3 Definitions

| Term | Definition |
|------|-----------|
| **Node** | A visual representation of an Object Type in the graph |
| **Edge** | A visual representation of a Link Type between two Object Types |
| **Canvas** | The main area where nodes and edges are rendered |
| **Palette** | A sidebar containing draggable elements (node types, link types) |
| **Inspector** | A right-side panel showing details of the selected element |
| **Layout** | An algorithm that positions nodes on the canvas |
| **Zoom** | Scaling the canvas view in/out |
| **Pan** | Moving the viewport across the canvas |

### 1.4 References

| Ref | Document | Version |
|-----|----------|---------|
| REF-01 | VOYANT-SRS-4.0.0 | 4.0.1 |
| REF-02 | VOYANT-ONTOLOGY-VIEWER-SPEC-1.0 | 1.0.0 |
| REF-03 | ISO/IEC/IEEE 29148:2018 | 2018 |
| REF-04 | ISO/IEC 25010:2011 | 2011 |
| REF-05 | WCAG 2.1 AA | 2018 |
| REF-06 | Lit 3 Documentation | 3.x |
| REF-07 | Palantir Foundry Ontology (public docs) | 2024 |

---

## 2. System Overview

### 2.1 System Context

The Graph Designer operates within the Voyant Ontology module:

```
┌─────────────────────────────────────────────────────────────┐
│                    VOYANT PLATFORM                           │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐    │
│  │  AI Agents  │    │   Human     │    │  External    │    │
│  │  (MCP)      │    │   Users     │    │  Systems     │    │
│  └──────┬──────┘    └──────┬──────┘    └──────┬───────┘    │
│         │                  │                   │             │
│         ▼                  ▼                   ▼             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              REST API + MCP Tools                     │   │
│  └──────────────────────────┬───────────────────────────┘   │
│                             │                                │
│  ┌──────────────────────────▼───────────────────────────┐   │
│  │              ONTOLOGY ENGINE (Backend)                 │   │
│  │  models.py · services.py · api.py · validators.py     │   │
│  │  action_executor.py · function_runner.py               │   │
│  │  query_engine.py · time_travel.py                      │   │
│  └──────────────────────────┬───────────────────────────┘   │
│                             │                                │
│  ┌──────────────────────────▼───────────────────────────┐   │
│  │              GRAPH DESIGNER (Frontend)                 │   │
│  │  view-ontology.ts · voyant-graph-view.ts              │   │
│  │  voyant-data-table.ts · voyant-detail-panel.ts        │   │
│  │  voyant-monaco-editor.ts · voyant-pivot-table.ts      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 User Classes

| Actor | Capabilities | Technical Level |
|-------|-------------|-----------------|
| **Data Engineer** | Create/edit types, properties, links, actions, functions | High |
| **Data Analyst** | Browse ontology, search objects, explore relationships | Medium |
| **Application Developer** | Build applications using ontology APIs, define actions/functions | High |
| **AI Agent** | Query ontology, execute actions, traverse links via MCP tools | N/A |
| **Governance Officer** | Audit data lineage, enforce policies, classify sensitivity | Medium |

---

## 3. Functional Requirements

### 3.1 Graph View (Visual Explorer)

| FR-ID | Requirement | Priority | Status |
|-------|-------------|----------|--------|
| FR-GRAPH-001 | System SHALL render Object Types as circular nodes with type-specific colors | Must | DONE |
| FR-GRAPH-002 | System SHALL render Link Types as curved Bezier edges with labels and arrowheads | Must | DONE |
| FR-GRAPH-003 | System SHALL support force-directed layout (Coulomb repulsion + Hooke attraction + center gravity) | Must | DONE |
| FR-GRAPH-004 | System SHALL support hierarchical (top-down tree) layout | Must | DONE |
| FR-GRAPH-005 | System SHALL support zoom (0.1x to 10x) via mouse wheel | Must | DONE |
| FR-GRAPH-006 | System SHALL support pan via click-drag on empty space | Must | DONE |
| FR-GRAPH-007 | System SHALL display a minimap (160x120px) in bottom-right corner | Must | DONE |
| FR-GRAPH-008 | System SHALL support click-to-select a node (highlight connected edges) | Must | DONE |
| FR-GRAPH-009 | System SHALL support double-click-to-expand (load linked types from API) | Must | DONE |
| FR-GRAPH-010 | System SHALL support right-click context menu (View Objects, Create Object, Edit Type, Delete Type, Execute Action) | Must | DONE |
| FR-GRAPH-011 | System SHALL support hover tooltip (type name, instance count, property count) | Must | DONE |
| FR-GRAPH-012 | System SHALL support search (type-ahead, highlight matching nodes, dim others) | Must | DONE |
| FR-GRAPH-013 | System SHALL support drag-to-reposition nodes | Should | DONE |
| FR-GRAPH-014 | System SHALL support multi-select (Shift+click or lasso) | Should | DONE |
| FR-GRAPH-015 | System SHALL support edge creation by dragging from output port to input port | Should | DONE |
| FR-GRAPH-016 | System SHALL support export to PNG/SVG | Should | DONE |
| FR-GRAPH-017 | System SHALL pause physics simulation when tab is not visible | Must | DONE |
| FR-GRAPH-018 | System SHALL render 100 nodes in <100ms, 1000 nodes in <500ms | Must | DONE |

### 3.2 Table View (Data Grid)

| FR-ID | Requirement | Priority | Status |
|-------|-------------|----------|--------|
| FR-TABLE-001 | System SHALL display Object Types in a sortable table (name, description, properties count, instances count, version, created) | Must | DONE |
| FR-TABLE-002 | System SHALL display Object Instances with dynamic columns from property definitions | Must | DONE |
| FR-TABLE-003 | System SHALL display Link Types (name, source type, target type, cardinality, instances count) | Must | DONE |
| FR-TABLE-004 | System SHALL display Link Instances (source object, target object, properties, created) | Must | DONE |
| FR-TABLE-005 | System SHALL support sub-tabs for each table type | Must | DONE |
| FR-TABLE-006 | System SHALL support CSV/JSON export of any table | Must | DONE |
| FR-TABLE-007 | System SHALL support filter by any column | Should | DONE |

### 3.3 Grid View (Card Layout)

| FR-ID | Requirement | Priority | Status |
|-------|-------------|----------|--------|
| FR-GRID-001 | System SHALL display Object Types as cards (name, description, property count, instance count, link badges) | Must | DONE |
| FR-GRID-002 | System SHALL support click-to-open detail panel | Must | DONE |
| FR-GRID-003 | System SHALL support hover-to-highlight with type color | Must | DONE |
| FR-GRID-004 | System SHALL support drag-to-create-link between cards | Should | NOT BUILT |

### 3.4 Detail Panel (Inspector)

| FR-ID | Requirement | Priority | Status |
|-------|-------------|----------|--------|
| FR-DETAIL-001 | System SHALL display Type Detail (header, stats grid, properties table, link types, actions) | Must | DONE |
| FR-DETAIL-002 | System SHALL display Object Instance Detail (editable properties, links, actions, audit trail) | Must | DONE |
| FR-DETAIL-003 | System SHALL support tabbed navigation (Overview, Actions, Functions) | Must | DONE |
| FR-DETAIL-004 | System SHALL support inline property editing with save/cancel | Must | DONE |
| FR-DETAIL-005 | System SHALL support link navigation (click link → navigate to linked object) | Must | DONE |
| FR-DETAIL-006 | System SHALL display audit trail with diffs (old value → new value) | Should | DONE |

### 3.5 Type Builder (Schema Designer)

| FR-ID | Requirement | Priority | Status |
|-------|-------------|----------|--------|
| FR-BUILDER-001 | System SHALL provide a form to create new Object Types (name, description) | Must | DONE |
| FR-BUILDER-002 | System SHALL support adding properties with all 11 types (string, integer, float, boolean, date, timestamp, enum, array, map, struct, geopoint) | Must | DONE |
| FR-BUILDER-003 | System SHALL support configuring property validation (required, default, regex, min, max) | Must | DONE |
| FR-BUILDER-004 | System SHALL show JSON schema preview | Must | DONE |
| FR-BUILDER-005 | System SHALL submit to POST /v1/ontology/types | Must | DONE |
| FR-BUILDER-006 | System SHALL support editing existing types | Must | DONE |

### 3.6 Link Type Builder

| FR-ID | Requirement | Priority | Status |
|-------|-------------|----------|--------|
| FR-LINK-001 | System SHALL provide a form to create Link Types (name, source type, target type, cardinality) | Must | DONE |
| FR-LINK-002 | System SHALL support cardinality selection (1:1, 1:N, M:N) | Must | DONE |
| FR-LINK-003 | System SHALL submit to POST /v1/ontology/links | Must | DONE |

### 3.7 Action Builder

| FR-ID | Requirement | Priority | Status |
|-------|-------------|----------|--------|
| FR-ACTION-001 | System SHALL provide a visual form for Action Types (name, description, parameters, rules, side effects) | Must | DONE |
| FR-ACTION-002 | System SHALL support adding parameters (name, type, required, default) | Must | DONE |
| FR-ACTION-003 | System SHALL support adding rules (condition→action) | Must | DONE |
| FR-ACTION-004 | System SHALL support adding side effects (webhook, notification, audit_log) | Must | DONE |
| FR-ACTION-005 | System SHALL support undo rule configuration | Should | DONE |
| FR-ACTION-006 | System SHALL support test button (run against sample object) | Should | DONE |

### 3.8 Function Editor

| FR-ID | Requirement | Priority | Status |
|-------|-------------|----------|--------|
| FR-FUNC-001 | System SHALL provide Monaco editor for Python/TypeScript code | Must | DONE |
| FR-FUNC-002 | System SHALL support language selector (Python, TypeScript) | Must | DONE |
| FR-FUNC-003 | System SHALL support Ctrl+Enter to run function | Must | DONE |
| FR-FUNC-004 | System SHALL display output panel (stdout, stderr, return value) | Must | DONE |
| FR-FUNC-005 | System SHALL support input/output schema configuration | Must | DONE |
| FR-FUNC-006 | System SHALL submit to POST /v1/ontology/functions | Must | DONE |
| FR-FUNC-007 | System SHALL support editing existing functions | Must | DONE |

### 3.9 Filter Builder

| FR-ID | Requirement | Priority | Status |
|-------|-------------|----------|--------|
| FR-FILTER-001 | System SHALL provide a visual condition editor (field, operator, value) | Must | DONE |
| FR-FILTER-002 | System SHALL support operators: =, !=, >, <, >=, <=, contains, starts_with, ends_with | Must | DONE |
| FR-FILTER-003 | System SHALL support AND/OR grouping | Must | DONE |
| FR-FILTER-004 | System SHALL apply filter to current view (table/grid/graph) | Must | DONE |
| FR-FILTER-005 | System SHALL support clearing all filters | Must | DONE |

### 3.10 Search

| FR-ID | Requirement | Priority | Status |
|-------|-------------|----------|--------|
| FR-SEARCH-001 | System SHALL provide a search input that filters across all views | Must | DONE |
| FR-SEARCH-002 | System SHALL support search by type name, property name, object value | Must | DONE |
| FR-SEARCH-003 | System SHALL highlight matching nodes in graph view | Must | DONE |
| FR-SEARCH-004 | System SHALL dim non-matching nodes in graph view | Must | DONE |

### 3.11 Edit Instance

| FR-ID | Requirement | Priority | Status |
|-------|-------------|----------|--------|
| FR-EDIT-001 | System SHALL provide a modal for editing object instance properties | Must | DONE |
| FR-EDIT-002 | System SHALL support editing all property types with appropriate input controls | Must | DONE |
| FR-EDIT-003 | System SHALL submit to PUT /v1/ontology/objects/{id} | Must | DONE |
| FR-EDIT-004 | System SHALL display validation errors inline | Must | DONE |
| FR-EDIT-005 | System SHALL support cancel without saving | Must | DONE |

---

## 4. Non-Functional Requirements

### 4.1 Performance

| NFR-ID | Requirement | Target |
|--------|-------------|--------|
| NFR-PERF-001 | Graph render 100 nodes | <100ms |
| NFR-PERF-002 | Graph render 1000 nodes | <500ms |
| NFR-PERF-003 | Zoom/pan latency | <16ms (60fps) |
| NFR-PERF-004 | Search latency | <100ms |
| NFR-PERF-005 | Layout computation (1000 nodes) | <1s |
| NFR-PERF-006 | Table view load (1000 rows) | <500ms |
| NFR-PERF-007 | Detail panel open | <200ms |

### 4.2 Accessibility

| NFR-ID | Requirement | Target |
|--------|-------------|--------|
| NFR-ACC-001 | Keyboard navigation for all interactive elements | WCAG 2.1 AA |
| NFR-ACC-002 | ARIA labels on all buttons and controls | WCAG 2.1 AA |
| NFR-ACC-003 | Color contrast ratio >= 4.5:1 | WCAG 2.1 AA |
| NFR-ACC-004 | Screen reader support for graph nodes | WCAG 2.1 AA |
| NFR-ACC-005 | Focus management for modals | WCAG 2.1 AA |

### 4.3 Security

| NFR-ID | Requirement | Target |
|--------|-------------|--------|
| NFR-SEC-001 | All API calls authenticated via JWT | Required |
| NFR-SEC-002 | RBAC enforced on all ontology operations | Required |
| NFR-SEC-003 | Tenant isolation on all queries | Required |
| NFR-SEC-004 | Input validation on all form submissions | Required |

### 4.4 Compatibility

| NFR-ID | Requirement | Target |
|--------|-------------|--------|
| NFR-COMP-001 | Chrome 100+ | Required |
| NFR-COMP-002 | Firefox 100+ | Required |
| NFR-COMP-003 | Safari 16+ | Required |
| NFR-COMP-004 | Edge 100+ | Required |
| NFR-COMP-005 | Minimum resolution 1280x720 | Required |

---

## 5. Data Model

### 5.1 Backend Models (from `apps/ontology/models.py`)

| Model | Fields | Relationships |
|-------|--------|---------------|
| ObjectType | name, description, version, deleted_at, backing_dataset, primary_key_column | has_many Property, has_many LinkType (source/target) |
| Property | object_type(FK), name, property_type(11 choices), required, default_value, validation_rules | belongs_to ObjectType |
| Object | object_type(FK), properties(JSON), version, deleted_at | belongs_to ObjectType |
| LinkType | name, source_type(FK), target_type(FK), cardinality, properties_schema, inverse_name | has_many Link |
| Link | link_type(FK), source_object(FK), target_object(FK), properties, deleted_at | belongs_to LinkType |
| Interface | name, description, required_properties, optional_properties, implementing_types(M2M) | many_to_many ObjectType |
| StructType | name, description, fields(JSON), version | — |
| SharedProperty | name, property_type, default_value, validation_rules, used_by_types(M2M) | many_to_many ObjectType |
| ValueType | name, base_type, constraints(JSON), version | — |
| ActionType | name, status, parameters(JSON), rules(JSON), side_effects(JSON), undoable, undo_rules, requires_approval | belongs_to ObjectType |
| Function | name, status, language, source_code, entry_point, input_schema, output_schema, timeout, memory_limit | belongs_to ObjectType |
| ActionExecution | action_type(FK), target_object(FK), params(JSON), previous_values(JSON), changes(JSON), status | belongs_to ActionType |

### 5.2 Frontend State (from `view-ontology.ts`)

| State Variable | Type | Purpose |
|---------------|------|---------|
| types | ObjectType[] | All loaded object types |
| links | LinkType[] | All loaded link types |
| objectInstances | ObjectInstance[] | Instances for selected type |
| linkInstances | LinkInstance[] | Link instances |
| loading | boolean | Global loading state |
| view | 'table' \| 'grid' \| 'graph' \| 'builders' | Active view mode |
| tableSubTab | 'object-types' \| 'object-instances' \| 'link-types' \| 'link-instances' | Active table tab |
| searchQuery | string | Current search filter |
| detailTarget | DetailTarget | Selected object/type for detail panel |
| detailOpen | boolean | Detail panel visibility |
| detailPanelTab | 'overview' \| 'actions' \| 'functions' | Detail panel tab |
| filterBuilderOpen | boolean | Filter builder visibility |
| typeBuilderOpen | boolean | Type builder modal visibility |
| actionBuilderOpen | boolean | Action builder modal visibility |
| functionEditorOpen | boolean | Function editor modal visibility |
| editInstanceOpen | boolean | Edit instance modal visibility |

---

## 6. API Endpoints

### 6.1 Ontology API (from `apps/ontology/api.py`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | /ontology/types | List all object types | read:ontology |
| POST | /ontology/types | Create object type | write:ontology |
| GET | /ontology/types/{id} | Get type with properties | read:ontology |
| PUT | /ontology/types/{id} | Update object type | write:ontology |
| DELETE | /ontology/types/{id} | Delete object type | write:ontology |
| GET | /ontology/objects | List objects (with filtering) | read:ontology |
| POST | /ontology/objects | Create object | write:ontology |
| GET | /ontology/objects/{id} | Get object with links | read:ontology |
| PUT | /ontology/objects/{id} | Update object | write:ontology |
| DELETE | /ontology/objects/{id} | Delete object | write:ontology |
| POST | /ontology/objects/batch | Batch create objects | write:ontology |
| GET | /ontology/links | List links | read:ontology |
| POST | /ontology/links | Create link | write:ontology |
| DELETE | /ontology/links/{id} | Delete link | write:ontology |
| GET | /ontology/links/types | List link types | read:ontology |
| POST | /ontology/links/types | Create link type | write:ontology |
| POST | /ontology/actions | Create action type | write:ontology |
| POST | /ontology/actions/{id}/execute | Execute action | write:ontology |
| POST | /ontology/functions | Create function | write:ontology |
| POST | /ontology/functions/{id}/run | Run function | write:ontology |
| POST | /ontology/objects/{type}/aggregate | Aggregation query | read:ontology |
| POST | /ontology/interfaces/{id}/query | Interface query | read:ontology |
| GET | /ontology/datasets/{id}/versions | List versions | read:ontology |
| GET | /ontology/datasets/{id}/diff | Diff versions | read:ontology |
| POST | /ontology/pii/detect | Detect PII | read:ontology |
| GET | /ontology/quality/{id} | Get quality score | read:ontology |

---

## 7. Screen Specifications

### 7.1 Main Layout (Three-Panel)

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Sidebar]  Ontology Explorer                           [🔍] [⚙️]   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──[Table]──[Grid]──[Graph]──[Builders]──┐                        │
│  └────────────────────────────────────────┘                        │
│                                                                     │
│  ┌── Search ───────────────────────────┐ ┌── Metrics Bar ───────┐ │
│  │ [🔍 Search types, objects...]       │ │ 7 types │ 6 links    │ │
│  └─────────────────────────────────────┘ │ 44 props │ 31 objs   │ │
│                                           └──────────────────────┘ │
│  ┌── Main Canvas ──────────────────────┐ ┌── Detail Panel ──────┐ │
│  │                                      │ │                       │ │
│  │  (Table | Grid | Graph | Builders)   │ │  (slides in on click) │ │
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
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 Graph View Wireframe

```
┌─────────────────────────────────────────────────────────────────────┐
│ [🔍 Search graph...]  [Force ▼] [−] [+] [⊞ Fit] [📋 Export]       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│       ┌──────────┐         ┌──────────┐                            │
│       │ Customer │ ──────→ │  Plan    │                            │
│       │ ● 2,341  │ subscribes│ ● 8    │                            │
│       └──────────┘  _to    └──────────┘                            │
│            │                    │                                    │
│            │ has_service        │ has_streaming                     │
│            ▼                    ▼                                    │
│       ┌──────────┐         ┌──────────┐                            │
│       │ Service  │ ──────→ │Streaming │                            │
│       │ ● 5,127  │ includes│ ● 12    │                            │
│       └──────────┘         └──────────┘                            │
│                                                                     │
│  ┌─ Legend ──────────────────┐  ┌─ Minimap ─────┐                 │
│  │ ○ Object Type            │  │  ▪▪▪▪▪▪▪▪▪▪  │                 │
│  │ ─ Link Type              │  │  ▪▪▪▪▪▪▪▪▪▪  │                 │
│  │ ● Instance (count)       │  │  ▪▪▪▪▪▪▪▪▪▪  │                 │
│  └──────────────────────────┘  └───────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.3 Builders Tab Wireframe

```
┌─────────────────────────────────────────────────────────────────────┐
│ Builders                                                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ 🔍 Filter    │  │ ➕ Type      │  │ ⚡ Action    │             │
│  │    Builder   │  │    Builder   │  │    Builder   │             │
│  │              │  │              │  │              │             │
│  │ Visual       │  │ Create new   │  │ Define       │             │
│  │ condition    │  │ Object Type  │  │ operations   │             │
│  │ editor with  │  │ with 11      │  │ with params, │             │
│  │ AND/OR logic │  │ property     │  │ rules, side  │             │
│  │              │  │ types        │  │ effects      │             │
│  │ [Open]       │  │ [Open]       │  │ [Open]       │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                     │
│  ┌──────────────┐                                                  │
│  │ 💻 Function  │                                                  │
│  │    Editor    │                                                  │
│  │              │                                                  │
│  │ Monaco       │                                                  │
│  │ editor for   │                                                  │
│  │ Python/TS    │                                                  │
│  │ functions    │                                                  │
│  │              │                                                  │
│  │ [Open]       │                                                  │
│  └──────────────┘                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 8. Missing Features (Not Yet Built)

| FR-ID | Feature | Priority | Effort | Module |
|-------|---------|----------|--------|--------|
| FR-GRAPH-013 | Drag-to-reposition nodes | Should | 1wk | voyant-graph-view.ts |
| FR-GRAPH-014 | Multi-select (Shift+click or lasso) | Should | 0.5wk | voyant-graph-view.ts |
| FR-GRAPH-015 | Edge creation by dragging from port to port | Should | 1wk | voyant-graph-view.ts |
| FR-GRAPH-016 | Export to PNG/SVG | Should | 0.5wk | voyant-graph-view.ts |
| FR-GRID-004 | Drag-to-create-link between grid cards | Should | 0.5wk | view-ontology.ts |

---

## 9. Acceptance Criteria

| AC-ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-001 | Graph renders all types and links | Playwright: check node count = types.length |
| AC-002 | Table shows all types with correct columns | Playwright: check table headers match spec |
| AC-003 | Grid shows all type cards | Playwright: check card count = types.length |
| AC-004 | Detail panel opens on click | Playwright: click node → panel appears |
| AC-005 | Search finds and highlights nodes | Playwright: search "Cliente" → node highlighted |
| AC-006 | Create object via form | API: POST /ontology/objects → 201 |
| AC-007 | Execute action via UI | API: POST /ontology/actions/{id}/execute → 200 |
| AC-008 | Export to CSV | Download file → verify content |
| AC-009 | All MCP tools respond | curl each tool endpoint → 200 |
| AC-010 | Performance: 100 nodes <100ms | Benchmark test |

---

**END OF DOCUMENT**
