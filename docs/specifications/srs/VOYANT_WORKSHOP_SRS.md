# Voyant Workshop — Software Requirements Specification

**Document ID:** VOY-SRS-Workshop-001
**Version:** 1.0
**Date:** 2026-07-20
**Status:** DRAFT
**Classification:** Internal
**Standard:** ISO/IEC/IEEE 29148:2018

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [Specific Requirements](#3-specific-requirements)
4. [External Interface Requirements](#4-external-interface-requirements)
5. [Internal Interface Requirements](#5-internal-interface-requirements)
6. [Performance Requirements](#6-performance-requirements)
7. [Database Requirements](#7-database-requirements)
8. [Design Constraints](#8-design-constraints)
9. [Security Requirements](#9-security-requirements)
10. [Quality Attributes](#10-quality-attributes)
11. [Verification and Validation](#11-verification-and-validation)
12. [Appendices](#12-appendices)

---

## 1. Introduction

### 1.1 Purpose

This document specifies the software requirements for Voyant Workshop, a browser-based low-code application builder that enables users to create custom data applications, dashboards, and operational tools on top of Voyant's data platform. This SRS follows ISO/IEC/IEEE 29148:2018.

### 1.2 Scope

Voyant Workshop encompasses:

- **Widget Library** — 30+ reusable UI components (charts, tables, forms, maps)
- **Page Builder** — Drag-and-drop page layout system
- **Data Binding** — Connect widgets to Ontology objects, pipelines, and SQL
- **Action Integration** — Trigger Ontology actions from UI interactions
- **Custom Scripting** — Extend widgets with JavaScript/Python
- **Application Deployment** — Publish applications to end users
- **Multi-page Applications** — Navigation and routing
- **Theming** — Customizable visual styling

### 1.3 Definitions, Acronyms, Abbreviations

| Term | Definition |
|------|------------|
| **Application** | A deployed Workshop artifact accessible via URL |
| **Page** | A single screen within an application |
| **Widget** | A reusable UI component that displays data or captures input |
| **Module** | A container for pages and shared state |
| **Data Source** | An Ontology object type, pipeline output, or SQL query |
| **Action** | An Ontology action type triggered by UI events |
| **Binding** | A connection between a widget property and a data source |
| **Theme** | A set of visual styles applied to an application |

### 1.4 References

| Document | Description |
|----------|-------------|
| ISO/IEC/IEEE 29148:2018 | Requirements engineering |
| ISO/IEC 25010:2023 | Quality models |
| VOY-ARCH-001 | Voyant System Architecture |
| VOY-SRS-Core-001 | Voyant Core Platform SRS |
| VOY-SRS-Ontology-001 | Voyant Ontology Engine SRS |

### 1.5 Document Overview

Section 2 provides overall description. Section 3 specifies detailed functional requirements. Sections 4-7 cover interface, performance, database, and constraints. Sections 8-10 cover security, quality, and verification.

---

## 2. Overall Description

### 2.1 Product Perspective

Voyant Workshop sits on top of the Ontology Engine and Data Platform, consuming data from pipelines, objects, and SQL queries to present interactive applications to end users.

```
┌─────────────────────────────────────────────────────────────────┐
│                       VOYANT WORKSHOP                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │                  FRONTEND (React + TypeScript)            │     │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐  │     │
│  │  │  App Viewer    │ │  Page Builder  │ │  Widget       │  │     │
│  │  │  (Runtime)     │ │  (Designer)    │ │  Library      │  │     │
│  │  └───────────────┘ └───────────────┘ └───────────────┘  │     │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐  │     │
│  │  │  Data Binding  │ │  Action       │ │  Theme        │  │     │
│  │  │  Engine        │ │  Handler      │ │  Engine       │  │     │
│  │  └───────────────┘ └───────────────┘ └───────────────┘  │     │
│  └────────────────────────┬────────────────────────────────┘     │
│                           │                                        │
│  ┌────────────────────────┴────────────────────────────────┐     │
│  │                  API LAYER (Django Ninja)                 │     │
│  │  /api/v2/workshop/apps/*                                 │     │
│  │  /api/v2/workshop/pages/*                                │     │
│  │  /api/v2/workshop/widgets/*                              │     │
│  │  /api/v2/workshop/themes/*                               │     │
│  │  /api/v2/workshop/deployments/*                          │     │
│  └────────────────────────┬────────────────────────────────┘     │
│                           │                                        │
│  ┌────────────────────────┴────────────────────────────────┐     │
│  │                  INTEGRATION LAYER                        │     │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐  │     │
│  │  │  Ontology      │ │  Pipeline     │ │  SQL Engine   │  │     │
│  │  │  Engine        │ │  Engine       │ │  (Trino)      │  │     │
│  │  └───────────────┘ └───────────────┘ └───────────────┘  │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Product Functions

| Function | Description |
|----------|-------------|
| F-01 | Create, edit, and delete applications |
| F-02 | Build pages with drag-and-drop layout |
| F-03 | Add widgets from a library of 30+ components |
| F-04 | Bind widget properties to data sources |
| F-05 | Trigger actions from UI interactions |
| F-06 | Add custom JavaScript/Python scripting |
| F-07 | Apply themes for visual customization |
| F-08 | Deploy applications to end users |
| F-09 | Support multi-page applications with navigation |
| F-10 | Version control applications |

### 2.3 User Characteristics

| User Type | Skill Level | Description |
|-----------|-------------|-------------|
| Citizen Developer | Beginner | Builds simple dashboards and forms |
| Business Analyst | Intermediate | Creates analytical applications |
| Data Engineer | Advanced | Builds complex data-driven apps |
| Application Developer | Expert | Creates custom widgets and scripts |

### 2.4 Constraints

| ID | Constraint | Rationale |
|----|------------|-----------|
| CON-01 | Must run in modern browsers | Target platform |
| CON-02 | Must integrate with Ontology Engine | Data source |
| CON-03 | Must support responsive design | Multi-device |
| CON-04 | Must support custom widgets via plugin API | Extensibility |
| CON-05 | Must support 1000+ concurrent app users | Scalability |

---

## 3. Specific Requirements

### 3.1 Functional Requirements

#### 3.1.1 Application Management

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| WKS-F-001 | System shall allow creating applications with name, description, and icon | Critical | Core function |
| WKS-F-002 | System shall allow editing application properties | Critical | Core function |
| WKS-F-003 | System shall allow deleting applications with confirmation | Critical | Core function |
| WKS-F-004 | System shall list applications with filtering and search | High | Discovery |
| WKS-F-005 | System shall support application duplication | Medium | Productivity |
| WKS-F-006 | System shall support application templates | Medium | Productivity |
| WKS-F-007 | System shall track application creation/modification timestamps | High | Audit |
| WKS-F-008 | System shall support application metadata (tags, category) | Medium | Organization |

#### 3.1.2 Page Builder

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| WKS-F-010 | System shall provide drag-and-drop page layout editor | Critical | Core UI |
| WKS-F-011 | System shall support grid-based layout (12-column) | Critical | Layout |
| WKS-F-012 | System shall support free-form layout | Medium | Flexibility |
| WKS-F-013 | System shall support multi-page applications with navigation | Critical | Multi-page |
| WKS-F-014 | System shall support page duplication | Medium | Productivity |
| WKS-F-015 | System shall support page reordering via drag-and-drop | High | Organization |
| WKS-F-016 | System shall support responsive breakpoints (mobile, tablet, desktop) | High | Multi-device |
| WKS-F-017 | System shall support page-level permissions | High | Security |
| WKS-F-018 | System shall support page previews in different screen sizes | Medium | Testing |

#### 3.1.3 Widget Library

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| WKS-F-020 | System shall provide data table widget | Critical | Core widget |
| WKS-F-021 | System shall provide chart widgets (bar, line, pie, scatter, area) | Critical | Visualization |
| WKS-F-022 | System shall provide form widgets (text, number, date, select, checkbox) | Critical | Input |
| WKS-F-023 | System shall provide text/markdown widget | High | Content |
| WKS-F-024 | System shall provide image widget | Medium | Content |
| WKS-F-025 | System shall provide map widget (geospatial) | Medium | Specialized |
| WKS-F-026 | System shall provide KPI/metric widget | High | Analytics |
| WKS-F-027 | System shall provide gauge/progress widget | Medium | Analytics |
| WKS-F-028 | System shall provide tabs widget | High | Layout |
| WKS-F-029 | System shall provide accordion widget | Medium | Layout |
| WKS-F-030 | System shall provide modal/dialog widget | High | Interaction |
| WKS-F-031 | System shall provide navigation/menu widget | High | Navigation |
| WKS-F-032 | System shall provide breadcrumbs widget | Medium | Navigation |
| WKS-F-033 | System shall provide button widget | Critical | Interaction |
| WKS-F-034 | System shall provide icon widget | Medium | Content |
| WKS-F-035 | System shall provide divider widget | Low | Layout |
| WKS-F-036 | System shall provide spacer widget | Low | Layout |
| WKS-F-037 | System shall provide HTML embed widget | Medium | Extensibility |
| WKS-F-038 | System shall provide iframe widget | Low | Integration |
| WKS-F-039 | System shall provide custom widget plugin API | High | Extensibility |
| WKS-F-040 | Total widget count shall be >= 30 | High | Coverage |

#### 3.1.4 Data Binding

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| WKS-F-050 | System shall support binding widget properties to Ontology object types | Critical | Data integration |
| WKS-F-051 | System shall support binding widget properties to pipeline outputs | Critical | Data integration |
| WKS-F-052 | System shall support binding widget properties to SQL queries | High | Data integration |
| WKS-F-053 | System shall support binding to Ontology object instances | High | Object data |
| WKS-F-054 | System shall support binding to linked objects (traversal) | High | Relationship data |
| WKS-F-055 | System shall support filter parameters in bindings | Critical | Dynamic data |
| WKS-F-056 | System shall support aggregation in bindings | Medium | Analytics |
| WKS-F-057 | System shall support real-time data refresh | High | Live data |
| WKS-F-058 | System shall support data transformation in bindings | Medium | Flexibility |
| WKS-F-059 | System shall support parameterized queries | High | Reusability |
| WKS-F-060 | System shall support cross-widget data references | Medium | Interaction |

#### 3.1.5 Action Integration

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| WKS-F-070 | System shall allow triggering Ontology actions from button clicks | Critical | Write operations |
| WKS-F-071 | System shall support action parameter forms | High | Input |
| WKS-F-072 | System shall support action confirmation dialogs | High | Safety |
| WKS-F-073 | System shall support action result display | High | Feedback |
| WKS-F-074 | System shall support action chaining (sequence of actions) | Medium | Workflows |
| WKS-F-075 | System shall support action rollback display | Medium | Error handling |
| WKS-F-076 | System shall support bulk actions on selected rows | High | Efficiency |
| WKS-F-077 | System shall track action execution history | High | Audit |

#### 3.1.6 Custom Scripting

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| WKS-F-080 | System shall support JavaScript scripting in custom widgets | High | Extensibility |
| WKS-F-081 | System shall support Python scripting in custom widgets | Medium | Extensibility |
| WKS-F-082 | System shall execute scripts in sandboxed environment | Critical | Security |
| WKS-F-083 | System shall provide script editor with syntax highlighting | High | Usability |
| WKS-F-084 | System shall provide script debugging capabilities | Medium | Debugging |
| WKS-F-085 | System shall support script versioning | Medium | History |
| WKS-F-086 | System shall support script import/export | Medium | Portability |

#### 3.1.7 Theming

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| WKS-F-090 | System shall provide default theme | Critical | Out-of-box |
| WKS-F-091 | System shall support custom themes (colors, fonts, spacing) | High | Branding |
| WKS-F-092 | System shall support dark mode | High | User preference |
| WKS-F-093 | System shall support per-application theming | Medium | Customization |
| WKS-F-094 | System shall support theme import/export | Medium | Reusability |
| WKS-F-095 | System shall support responsive theme adjustments | High | Multi-device |

#### 3.1.8 Application Deployment

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| WKS-F-100 | System shall support deploying applications to production | Critical | Release |
| WKS-F-101 | System shall support application versioning | High | Release mgmt |
| WKS-F-102 | System shall support application rollback | High | Recovery |
| WKS-F-103 | System shall support application sharing (public/private) | High | Distribution |
| WKS-F-104 | System shall support application access control | Critical | Security |
| WKS-F-105 | System shall provide application analytics (views, usage) | Medium | Insights |
| WKS-F-106 | System shall support application embedding (iframe) | Medium | Integration |
| WKS-F-107 | System shall support custom domains | Low | Branding |

#### 3.1.9 Navigation

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| WKS-F-110 | System shall support sidebar navigation | Critical | Navigation |
| WKS-F-111 | System shall support top navigation bar | High | Navigation |
| WKS-F-112 | System shall support breadcrumb navigation | Medium | Navigation |
| WKS-F-113 | System shall support deep linking (URL to page) | High | Sharing |
| WKS-F-114 | System shall support navigation permissions | High | Security |
| WKS-F-115 | System shall support conditional navigation (role-based) | Medium | Personalization |

---

## 4. External Interface Requirements

### 4.1 User Interface

| ID | Requirement | Rationale |
|----|-------------|-----------|
| UI-001 | Designer interface shall be responsive | Multi-device |
| UI-002 | Viewer interface shall be fully responsive | End-user devices |
| UI-003 | Interface shall support keyboard shortcuts | Efficiency |
| UI-004 | Interface shall support drag-and-drop | Usability |
| UI-005 | Interface shall follow Voyant design system | Consistency |
| UI-006 | Interface shall support internationalization (i18n) | Global users |

### 4.2 Software Interface

| ID | Interface | Protocol | Direction |
|----|-----------|----------|-----------|
| SW-001 | Voyant API Gateway | HTTP/REST | Bidirectional |
| SW-002 | Ontology Engine | HTTP/REST | Read/Write |
| SW-003 | Pipeline Engine | HTTP/REST | Read |
| SW-004 | SQL Engine (Trino) | HTTP | Read |
| SW-005 | Voyant Metadata DB | TCP | Read/Write |
| SW-006 | Voyant Cache (Redis) | TCP | Read/Write |

### 4.3 Communication Interface

| ID | Requirement | Rationale |
|----|-------------|-----------|
| COM-001 | API shall use HTTPS (TLS 1.3) | Security |
| COM-002 | API shall use JSON for request/response | Standard |
| COM-003 | API shall support WebSocket for real-time updates | Responsiveness |
| COM-004 | API shall support Server-Sent Events for data streaming | Live data |

---

## 5. Internal Interface Requirements

### 5.1 Component Interfaces

```
┌─────────────┐     HTTP      ┌─────────────┐     SQL       ┌─────────────┐
│  App Viewer  │──────────────>│  API Layer   │──────────────>│  Ontology   │
│  (Runtime)   │<──────────────│  (Django)    │<──────────────│  Engine     │
└─────────────┘               └──────┬──────┘               └─────────────┘
                                     │
                                     │ HTTP
                                     ▼
                              ┌─────────────┐
                              │  Pipeline    │
                              │  Engine      │
                              └─────────────┘
```

### 5.2 Internal APIs

| Interface | Caller | Callee | Protocol |
|-----------|--------|--------|----------|
| App CRUD | API Layer | PostgreSQL | SQL |
| Widget Data | API Layer | Ontology Engine | HTTP |
| Widget Data | API Layer | Pipeline Engine | HTTP |
| Widget Data | API Layer | SQL Engine | HTTP |
| App Serving | CDN/API | MinIO | S3 |
| Cache | API Layer | Redis | TCP |

---

## 6. Performance Requirements

### 6.1 Response Time

| ID | Operation | Target (p95) | Measurement |
|----|-----------|--------------|-------------|
| PERF-001 | App load (initial) | < 3s | APM |
| PERF-002 | Page navigation | < 500ms | APM |
| PERF-003 | Widget render | < 500ms | APM |
| PERF-004 | Data fetch (widget) | < 1s | APM |
| PERF-005 | Action execution | < 2s | APM |
| PERF-006 | App save | < 1s | APM |
| PERF-007 | Theme apply | < 200ms | APM |

### 6.2 Throughput

| ID | Operation | Target | Measurement |
|----|-----------|--------|-------------|
| PERF-010 | Concurrent app viewers | > 1000 | Load test |
| PERF-011 | Concurrent designer sessions | > 50 | Load test |
| PERF-012 | Data points rendered | > 10,000 | Stress test |

### 6.3 Scalability

| ID | Metric | Target | Measurement |
|----|--------|--------|-------------|
| PERF-020 | Widgets per page | > 50 | Scale test |
| PERF-021 | Pages per application | > 20 | Scale test |
| PERF-022 | Total applications per tenant | > 500 | Capacity test |
| PERF-023 | Total data rows in table widget | > 100,000 | Scale test |

---

## 7. Database Requirements

### 7.1 Schema

```sql
-- Applications
CREATE TABLE workshop_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace_id UUID NOT NULL REFERENCES namespaces(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    theme_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID NOT NULL REFERENCES users(id),
    updated_by UUID NOT NULL REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    UNIQUE(namespace_id, name, deleted_at)
);

CREATE INDEX idx_apps_namespace ON workshop_applications(namespace_id);

-- Pages
CREATE TABLE workshop_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES workshop_applications(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    layout JSONB NOT NULL,
    is_homepage BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    permissions JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(application_id, slug)
);

CREATE INDEX idx_pages_application ON workshop_pages(application_id);

-- Widgets (stored as page content)
CREATE TABLE workshop_widgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id UUID NOT NULL REFERENCES workshop_pages(id) ON DELETE CASCADE,
    widget_type VARCHAR(100) NOT NULL,
    position JSONB NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}',
    data_binding JSONB,
    event_handlers JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_widgets_page ON workshop_widgets(page_id);

-- Themes
CREATE TABLE workshop_themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace_id UUID NOT NULL REFERENCES namespaces(id),
    name VARCHAR(255) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    colors JSONB NOT NULL,
    fonts JSONB NOT NULL,
    spacing JSONB NOT NULL,
    components JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(namespace_id, name)
);

-- Deployments
CREATE TABLE workshop_deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES workshop_applications(id),
    version INTEGER NOT NULL,
    deployed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deployed_by UUID NOT NULL REFERENCES users(id),
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'inactive', 'rolled_back')),
    configuration JSONB,
    UNIQUE(application_id, version)
);

CREATE INDEX idx_deployments_application ON workshop_deployments(application_id);
```

---

## 8. Design Constraints

### 8.1 Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | React 18 + TypeScript | Component model |
| Widget Framework | Custom widget system | Flexibility |
| Layout Engine | React Grid Layout | Proven grid system |
| Chart Library | Recharts | React-native charts |
| Map Library | Deck.gl | Geospatial visualization |
| Table Library | AG Grid | Enterprise data tables |
| Styling | Tailwind CSS + shadcn/ui | Design system |
| Build Tool | Vite | Fast builds |
| Backend | Django 5.0 + Django Ninja | Existing stack |
| Database | PostgreSQL 16 | Existing stack |

### 8.2 Widget Plugin API

```typescript
// Widget Plugin Interface
interface VoyantWidget {
  id: string;
  name: string;
  category: 'data' | 'visualization' | 'input' | 'layout' | 'content';
  icon: string;
  
  // Configuration schema
  schema: {
    properties: Record<string, WidgetPropertySchema>;
    events: string[];
    dataBindings: DataBindingSchema;
  };
  
  // Rendering
  render: (props: WidgetRenderProps) => React.ReactNode;
  
  // Data handling
  onData?: (data: DataSourceResult) => void;
  
  // Event handling
  onEvent?: (event: WidgetEvent) => void;
}

// Registration
VoyantWorkshop.registerWidget(MyCustomWidget);
```

---

## 9. Security Requirements

| ID | Requirement | Standard | Implementation |
|----|-------------|----------|----------------|
| SEC-001 | Authentication required for designer | ISO 27001 | OIDC/JWT |
| SEC-002 | Viewer authentication configurable per app | ISO 27001 | App settings |
| SEC-003 | Authorization enforced per page | ISO 27001 | SpiceDB |
| SEC-004 | Widget data access controlled | ISO 27001 | RBAC |
| SEC-005 | Custom scripts sandboxed | OWASP | iframe sandbox |
| SEC-006 | API communication encrypted | ISO 27001 | TLS 1.3 |
| SEC-007 | XSS prevention in widgets | OWASP | Input sanitization |
| SEC-008 | CSRF protection | OWASP | Token validation |
| SEC-009 | Content Security Policy | OWASP | CSP headers |
| SEC-010 | Audit logging for deployments | ISO 27001 | Audit trail |

---

## 10. Quality Attributes

### 10.1 Reliability

| ID | Requirement | Target |
|----|-------------|--------|
| REL-001 | App availability | 99.9% |
| REL-002 | MTBF | > 720 hours |
| REL-003 | MTTR | < 30 minutes |
| REL-004 | Data binding success rate | > 99.9% |

### 10.2 Usability

| ID | Requirement | Target |
|----|-------------|--------|
| USAB-001 | Time to create first app | < 10 minutes |
| USAB-002 | SUS score | > 80 |
| USAB-003 | Accessibility | WCAG 2.1 AA |
| USAB-004 | Time to add widget | < 30 seconds |
| USAB-005 | Time to bind data | < 1 minute |

### 10.3 Maintainability

| ID | Requirement | Target |
|----|-------------|--------|
| MAINT-001 | Code test coverage | > 90% |
| MAINT-002 | Widget API documentation | 100% |
| MAINT-003 | Example applications | 10+ |
| MAINT-004 | Onboarding time | < 1 week |

---

## 11. Verification and Validation

### 11.1 Acceptance Criteria

| ID | Criterion | Test Method | Pass Condition |
|----|-----------|-------------|----------------|
| AC-001 | App creation via designer | E2E test | App saved |
| AC-002 | Widget drag-and-drop | E2E test | Widget placed |
| AC-003 | Data binding works | E2E test | Data displays |
| AC-004 | Action triggers work | E2E test | Action executes |
| AC-005 | App deployment works | E2E test | App accessible |
| AC-006 | 1000 concurrent viewers | Load test | p95 < 3s |
| AC-007 | Mobile responsive | E2E test | Layout adapts |
| AC-008 | Custom widget loads | E2E test | Widget renders |

### 11.2 Test Traceability

| Requirement | Test Case | Script |
|-------------|-----------|--------|
| WKS-F-001 | TC-WKS-001 | test_app_creation.py |
| WKS-F-010 | TC-WKS-010 | test_page_builder.py |
| WKS-F-020 | TC-WKS-020 | test_widgets.py |
| WKS-F-050 | TC-WKS-050 | test_data_binding.py |
| WKS-F-070 | TC-WKS-070 | test_actions.py |
| WKS-F-100 | TC-WKS-100 | test_deployment.py |

---

## 12. Appendices

### Appendix A: Widget Catalog

| Category | Widget | Description |
|----------|--------|-------------|
| **Data** | Data Table | Sortable, filterable data grid |
| **Data** | List | Simple list display |
| **Data** | Detail View | Single record display |
| **Visualization** | Bar Chart | Vertical/horizontal bars |
| **Visualization** | Line Chart | Time series lines |
| **Visualization** | Pie Chart | Proportional data |
| **Visualization** | Scatter Plot | XY correlation |
| **Visualization** | Area Chart | Stacked areas |
| **Visualization** | KPI Card | Single metric display |
| **Visualization** | Gauge | Progress/ratio display |
| **Visualization** | Map | Geospatial data |
| **Visualization** | Heatmap | Matrix visualization |
| **Visualization** | Treemap | Hierarchical data |
| **Input** | Text Input | Single-line text |
| **Input** | Text Area | Multi-line text |
| **Input** | Number Input | Numeric value |
| **Input** | Date Picker | Date selection |
| **Input** | Select Dropdown | Option selection |
| **Input** | Multi-Select | Multiple options |
| **Input** | Checkbox | Boolean toggle |
| **Input** | Radio Group | Single selection |
| **Input** | Slider | Range selection |
| **Input** | File Upload | File selection |
| **Layout** | Tabs | Tabbed content |
| **Layout** | Accordion | Collapsible sections |
| **Layout** | Modal | Dialog overlay |
| **Layout** | Sidebar | Side navigation |
| **Content** | Text/Markdown | Rich text |
| **Content** | Image | Image display |
| **Content** | Icon | Icon display |
| **Content** | Divider | Visual separator |
| **Content** | HTML Embed | Custom HTML |
| **Navigation** | Button | Action trigger |
| **Navigation** | Breadcrumbs | Path navigation |
| **Navigation** | Menu | Navigation menu |
| **Total** | **35** | |

### Appendix B: Example Application Structure

```yaml
# Voyant Workshop Application Definition
application:
  name: sales-dashboard
  description: "Sales team performance dashboard"
  theme: corporate-blue

pages:
  - name: Overview
    slug: overview
    is_homepage: true
    layout:
      type: grid
      columns: 12
    widgets:
      - id: kpi-revenue
        type: kpi-card
        position: { x: 0, y: 0, w: 3, h: 2 }
        properties:
          title: "Total Revenue"
          format: currency
        dataBinding:
          source: ontology
          objectType: SalesOrder
          aggregation:
            function: sum
            column: total_amount

      - id: kpi-orders
        type: kpi-card
        position: { x: 3, y: 0, w: 3, h: 2 }
        properties:
          title: "Total Orders"
        dataBinding:
          source: ontology
          objectType: SalesOrder
          aggregation:
            function: count

      - id: chart-monthly
        type: line-chart
        position: { x: 0, y: 2, w: 8, h: 4 }
        properties:
          title: "Monthly Revenue"
          xAxis: month
          yAxis: revenue
        dataBinding:
          source: pipeline
          pipelineId: monthly-sales-metrics

      - id: table-top-customers
        type: data-table
        position: { x: 8, y: 2, w: 4, h: 4 }
        properties:
          title: "Top Customers"
          pageSize: 10
          sortable: true
        dataBinding:
          source: sql
          query: |
            SELECT customer_name, SUM(total) as revenue
            FROM sales_orders
            GROUP BY customer_name
            ORDER BY revenue DESC
            LIMIT 10

  - name: Customers
    slug: customers
    widgets:
      - id: table-customers
        type: data-table
        position: { x: 0, y: 0, w: 12, h: 6 }
        dataBinding:
          source: ontology
          objectType: Customer
          filters:
            - column: status
              operator: equals
              value: active
        eventHandlers:
          rowClick:
            action: navigate
            target: /customers/{id}

actions:
  - name: create-order
    type: ontology
    objectType: SalesOrder
    actionType: create_order
    confirmation: "Create new order for {customer_name}?"
    successMessage: "Order created successfully"
    errorMessage: "Failed to create order"

navigation:
  type: sidebar
  items:
    - label: Overview
      page: overview
      icon: dashboard
    - label: Customers
      page: customers
      icon: people
    - label: Orders
      page: orders
      icon: shopping_cart

permissions:
  viewer:
    pages: [overview, customers, orders]
  editor:
    pages: [overview, customers, orders]
    actions: [create-order]
  admin:
    pages: "*"
    actions: "*"
    designer: true
```

### Appendix C: Glossary

| Term | Definition |
|------|------------|
| **Application** | A deployed Workshop artifact |
| **Page** | A single screen in an application |
| **Widget** | A reusable UI component |
| **Module** | A container for pages |
| **Data Source** | Ontology, pipeline, or SQL query |
| **Action** | Ontology action triggered by UI |
| **Binding** | Widget property ↔ data source connection |
| **Theme** | Visual style configuration |
| **Deployment** | Published application version |
| **Designer** | Visual application builder interface |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-20 | Voyant Engineering | Initial release |

**Approval:**

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Engineering Manager | _________________ | ________ | _________ |
| Product Manager | _________________ | ________ | _________ |
| QA Manager | _________________ | ________ | _________ |

---

**Document Status:** DRAFT
**Classification:** Internal
**Retention:** 7 years
**Next Review:** 2026-08-20
