# Voyant Ontology Engine — Software Requirements Specification

**Document ID:** VOY-SRS-ONTOLOGY-001
**Version:** 1.0
**Date:** 2026-07-20
**Status:** DRAFT
**Standard:** ISO/IEC/IEEE 29148:2018

---

## 1. Introduction

### 1.1 Purpose

This document specifies the requirements for the Voyant Ontology Engine — a semantic knowledge graph layer that connects Voyant's data assets to real-world entities. The Ontology Engine enables users to define object types, establish relationships, execute actions, and author custom business logic.

### 1.2 Scope

The Ontology Engine provides:

- **Object Type Management** — Define entity schemas with typed properties
- **Link Type Management** — Define relationships between object types
- **Object Instance Management** — Create, read, update, delete object instances
- **Link Instance Management** — Create and traverse relationships
- **Action Types** — Define write operations with side effects
- **Functions** — Author custom business logic in Python/TypeScript
- **Interfaces** — Polymorphic type definitions
- **Object Explorer** — Search, filter, compare, pivot across objects
- **Scenarios** — Branching for experimentation without affecting production data

### 1.3 Intended Audience

- Software Architects
- Backend Engineers
- Frontend Engineers
- QA Engineers
- Product Managers

---

## 2. Normative References

| Document | Description |
|----------|-------------|
| ISO/IEC/IEEE 29148:2018 | Software requirements engineering |
| ISO/IEC 25010:2023 | Software quality models |
| VOY-ARCH-001 | Voyant System Architecture |
| VOY-SRS-CORE-001 | Voyant Core Platform SRS |

---

## 3. Definitions

| Term | Definition |
|------|------------|
| **Object Type** | A schema definition representing a class of entities (e.g., Customer, Sensor, Transaction) |
| **Object Instance** | A specific occurrence of an object type (e.g., Customer #4521) |
| **Link Type** | A schema definition representing a relationship between two object types |
| **Link Instance** | A specific occurrence of a link type connecting two object instances |
| **Property** | A named, typed attribute on an object type or link type |
| **Action Type** | A definition of a write operation that mutates object state |
| **Function** | A unit of custom business logic executable within the Ontology |
| **Interface** | A type contract that multiple object types can implement |
| **Scenario** | An isolated branch of the Ontology for experimentation |
| **Namespace** | A tenant isolation boundary within the Ontology |

---

## 4. System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    VOYANT ONTOLOGY ENGINE                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │                  API Layer (Django Ninja)            │     │
│  │  /api/v2/ontology/object-types                      │     │
│  │  /api/v2/ontology/objects                           │     │
│  │  /api/v2/ontology/link-types                        │     │
│  │  /api/v2/ontology/links                             │     │
│  │  /api/v2/ontology/action-types                      │     │
│  │  /api/v2/ontology/functions                         │     │
│  │  /api/v2/ontology/interfaces                        │     │
│  │  /api/v2/ontology/scenarios                         │     │
│  └──────────────────────┬──────────────────────────────┘     │
│                         │                                      │
│  ┌──────────────────────┴──────────────────────────────┐     │
│  │                  Service Layer                        │     │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │     │
│  │  │ ObjectService │ │ LinkService  │ │ActionService │ │     │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ │     │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │     │
│  │  │FuncRuntime   │ │SearchService │ │ScenarioSvc   │ │     │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ │     │
│  └──────────────────────┬──────────────────────────────┘     │
│                         │                                      │
│  ┌──────────────────────┴──────────────────────────────┐     │
│  │                  Data Layer                            │     │
│  │  PostgreSQL (metadata) + Milvus (vector search)       │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │                  MCP Tools                            │     │
│  │  voyant.ontology.* — Agent-accessible operations      │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Functional Requirements

### 5.1 Object Type Management

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| ONT-F-001 | System shall allow creating object types with a name, description, and property definitions | Critical | 🔧 Planned |
| ONT-F-002 | System shall support property types: string, integer, float, boolean, date, timestamp, enum, array, map, struct, geopoint | Critical | 🔧 Planned |
| ONT-F-003 | System shall enforce required/optional constraints on properties | Critical | 🔧 Planned |
| ONT-F-004 | System shall support default values for properties | High | 🔧 Planned |
| ONT-F-005 | System shall support property validation rules (regex, range, custom) | High | 🔧 Planned |
| ONT-F-006 | System shall allow updating object type schemas with backward compatibility checks | High | 🔧 Planned |
| ONT-F-007 | System shall support soft-deletion of object types | Medium | 🔧 Planned |
| ONT-F-008 | System shall version object type schemas automatically | High | 🔧 Planned |

### 5.2 Object Instance Management

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| ONT-F-010 | System shall allow creating object instances from defined object types | Critical | 🔧 Planned |
| ONT-F-011 | System shall validate object properties against the object type schema on create/update | Critical | 🔧 Planned |
| ONT-F-012 | System shall support full CRUD operations on object instances | Critical | 🔧 Planned |
| ONT-F-013 | System shall support batch operations (create/update/delete 1000+ objects) | High | 🔧 Planned |
| ONT-F-014 | System shall support upsert operations (create or update) | High | 🔧 Planned |
| ONT-F-015 | System shall track creation/update timestamps and user attribution | High | 🔧 Planned |
| ONT-F-016 | System shall support soft-deletion with configurable retention | Medium | 🔧 Planned |
| ONT-F-017 | System shall support object versioning (optimistic concurrency) | High | 🔧 Planned |

### 5.3 Link Type Management

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| ONT-F-020 | System shall allow creating link types between object types | Critical | 🔧 Planned |
| ONT-F-021 | System shall support cardinality: one-to-one, one-to-many, many-to-many | Critical | 🔧 Planned |
| ONT-F-022 | System shall allow properties on link instances | High | 🔧 Planned |
| ONT-F-023 | System shall enforce referential integrity on link creation | High | 🔧 Planned |
| ONT-F-024 | System shall support cascading operations (delete source → handle targets) | Medium | 🔧 Planned |
| ONT-F-025 | System shall support inverse link navigation | High | 🔧 Planned |

### 5.4 Link Instance Management

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| ONT-F-030 | System shall allow creating link instances between object instances | Critical | 🔧 Planned |
| ONT-F-031 | System shall support traversing links in both directions | Critical | 🔧 Planned |
| ONT-F-032 | System shall support multi-hop traversal (A → B → C → D) | High | 🔧 Planned |
| ONT-F-033 | System shall support filtered traversal (follow links where condition) | High | 🔧 Planned |
| ONT-F-034 | System shall support link aggregation (count, sum, avg across linked objects) | Medium | 🔧 Planned |

### 5.5 Action Types

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| ONT-F-040 | System shall allow defining action types with input/output schemas | Critical | 🔧 Planned |
| ONT-F-041 | System shall support executing actions against object instances | Critical | 🔧 Planned |
| ONT-F-042 | System shall track action execution history with audit trail | Critical | 🔧 Planned |
| ONT-F-043 | System shall support side effects (send notification, call webhook, update external system) | High | 🔧 Planned |
| ONT-F-044 | System shall support rollback on action failure | High | 🔧 Planned |
| ONT-F-045 | System shall support action parameters with default values | High | 🔧 Planned |
| ONT-F-046 | System shall support conditional action execution (rules) | Medium | 🔧 Planned |
| ONT-F-047 | System shall support batch action execution | Medium | 🔧 Planned |

### 5.6 Functions

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| ONT-F-050 | System shall allow authoring functions in Python | Critical | 🔧 Planned |
| ONT-F-051 | System shall allow authoring functions in TypeScript | High | 🔧 Planned |
| ONT-F-052 | System shall execute functions in a sandboxed environment | Critical | 🔧 Planned |
| ONT-F-053 | System shall support function versioning | High | 🔧 Planned |
| ONT-F-054 | System shall support function parameters with type hints | High | 🔧 Planned |
| ONT-F-055 | System shall support functions that query object instances | High | 🔧 Planned |
| ONT-F-056 | System shall support functions that modify object instances | High | 🔧 Planned |
| ONT-F-057 | System shall support function composition (call other functions) | Medium | 🔧 Planned |
| ONT-F-058 | System shall support external API calls from functions | Medium | 🔧 Planned |

### 5.7 Interfaces

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| ONT-F-060 | System shall allow defining interfaces (type contracts) | High | 🔧 Planned |
| ONT-F-061 | System shall allow object types to implement multiple interfaces | High | 🔧 Planned |
| ONT-F-062 | System shall enforce interface contracts on implementing object types | High | 🔧 Planned |
| ONT-F-063 | System shall support polymorphic queries across interface implementations | Medium | 🔧 Planned |

### 5.8 Object Explorer

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| ONT-F-070 | System shall provide full-text search across all object instances | Critical | 🔧 Planned |
| ONT-F-071 | System shall support property-based filtering (equals, contains, gt, lt, in, between) | Critical | 🔧 Planned |
| ONT-F-072 | System shall support comparison of two object sets | High | 🔧 Planned |
| ONT-F-073 | System shall support pivot navigation (navigate from object to linked objects) | High | 🔧 Planned |
| ONT-F-074 | System shall support saved searches (named filters) | Medium | 🔧 Planned |
| ONT-F-075 | System shall support sorting by any property | High | 🔧 Planned |
| ONT-F-076 | System shall support pagination with cursor-based navigation | High | 🔧 Planned |
| ONT-F-077 | System shall support export of search results (CSV, JSON) | Medium | 🔧 Planned |

### 5.9 Scenarios

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| ONT-F-080 | System shall allow creating isolated scenarios (branches) | Medium | 🔧 Planned |
| ONT-F-081 | System shall allow modifications within a scenario without affecting production | Medium | 🔧 Planned |
| ONT-F-082 | System shall support merging scenarios back to production | Medium | 🔧 Planned |
| ONT-F-083 | System shall detect and report merge conflicts | Medium | 🔧 Planned |
| ONT-F-084 | System shall support scenario comparison (diff view) | Medium | 🔧 Planned |

---

## 6. Non-Functional Requirements

### 6.1 Performance

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| ONT-NF-001 | Object instance query response time (p95) | < 100ms | APM tracing |
| ONT-NF-002 | Object instance creation throughput | > 1000/sec | Load test |
| ONT-NF-003 | Link traversal depth (max hops) | 10+ | Query test |
| ONT-NF-004 | Concurrent object queries | > 500 | Stress test |
| ONT-NF-005 | Full-text search response time (p95) | < 200ms | APM tracing |
| ONT-NF-006 | Function execution timeout | < 30s | Runtime config |

### 6.2 Scalability

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| ONT-NF-010 | Total object instances per namespace | > 10M | Capacity test |
| ONT-NF-011 | Total object types per namespace | > 1000 | Capacity test |
| ONT-NF-012 | Total link instances per namespace | > 50M | Capacity test |
| ONT-NF-013 | Properties per object type | > 100 | Schema test |

### 6.3 Availability

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| ONT-NF-020 | System uptime | 99.9% | Monitoring |
| ONT-NF-021 | Recovery time objective (RTO) | < 1 hour | DR test |
| ONT-NF-022 | Recovery point objective (RPO) | < 5 minutes | Backup test |

### 6.4 Security

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| ONT-NF-030 | Authentication | OIDC/JWT | Security audit |
| ONT-NF-031 | Authorization | RBAC ( SpiceDB) | Security audit |
| ONT-NF-032 | Data encryption at rest | AES-256 | Security audit |
| ONT-NF-033 | Data encryption in transit | TLS 1.3 | Security audit |
| ONT-NF-034 | Audit logging | All mutations | Compliance audit |

---

## 7. Data Model

### 7.1 Entity Relationship Diagram

```
┌──────────────────────┐       ┌──────────────────────┐
│  ontology_object_    │       │  ontology_property   │
│  types               │       │                      │
├──────────────────────┤       ├──────────────────────┤
│ id (UUID, PK)        │──┐    │ id (UUID, PK)        │
│ namespace_id (UUID)  │  │    │ object_type_id (FK)  │
│ name (VARCHAR)       │  │    │ name (VARCHAR)       │
│ description (TEXT)   │  └───>│ property_type (ENUM) │
│ schema (JSONB)       │       │ required (BOOLEAN)   │
│ created_at (TS)      │       │ default_value (JSONB)│
│ updated_at (TS)      │       │ metadata (JSONB)     │
│ created_by (UUID)    │       └──────────────────────┘
│ version (INTEGER)    │
│ deleted_at (TS)      │
└──────────┬───────────┘
           │
           │ 1:N
           ▼
┌──────────────────────┐       ┌──────────────────────┐
│  ontology_objects    │       │  ontology_link_      │
│                      │       │  types               │
├──────────────────────┤       ├──────────────────────┤
│ id (UUID, PK)        │       │ id (UUID, PK)        │
│ object_type_id (FK)  │       │ name (VARCHAR)       │
│ properties (JSONB)   │       │ source_type_id (FK)  │
│ namespace_id (UUID)  │       │ target_type_id (FK)  │
│ created_at (TS)      │       │ cardinality (ENUM)   │
│ updated_at (TS)      │       │ properties (JSONB)   │
│ created_by (UUID)    │       │ metadata (JSONB)     │
│ version (INTEGER)    │       └──────────┬───────────┘
│ deleted_at (TS)      │                  │
└──────────┬───────────┘                  │ 1:N
           │                              ▼
           │ 1:N               ┌──────────────────────┐
           ▼                   │  ontology_links      │
┌──────────────────────┐       ├──────────────────────┤
│  ontology_action_    │       │ id (UUID, PK)        │
│  types               │       │ link_type_id (FK)    │
├──────────────────────┤       │ source_object_id (FK)│
│ id (UUID, PK)        │       │ target_object_id (FK)│
│ name (VARCHAR)       │       │ properties (JSONB)   │
│ description (TEXT)   │       │ created_at (TS)      │
│ input_schema (JSONB) │       └──────────────────────┘
│ output_schema (JSONB)│
│ function_id (FK)     │
│ side_effects (JSONB) │
│ metadata (JSONB)     │
└──────────────────────┘
           │
           │ N:1
           ▼
┌──────────────────────┐       ┌──────────────────────┐
│  ontology_functions  │       │  ontology_interfaces │
├──────────────────────┤       ├──────────────────────┤
│ id (UUID, PK)        │       │ id (UUID, PK)        │
│ name (VARCHAR)       │       │ name (VARCHAR)       │
│ language (ENUM)      │       │ description (TEXT)   │
│ code (TEXT)          │       │ schema (JSONB)       │
│ parameters (JSONB)   │       │ metadata (JSONB)     │
│ return_type (JSONB)  │       └──────────────────────┘
│ created_at (TS)      │
│ updated_at (TS)      │
│ version (INTEGER)    │
└──────────────────────┘
```

### 7.2 PostgreSQL Schema

```sql
-- Object Types
CREATE TABLE ontology_object_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace_id UUID NOT NULL REFERENCES namespaces(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    schema JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID NOT NULL REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    UNIQUE(namespace_id, name, deleted_at)
);

CREATE INDEX idx_object_types_namespace ON ontology_object_types(namespace_id);
CREATE INDEX idx_object_types_name ON ontology_object_types(name);

-- Properties
CREATE TABLE ontology_properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_type_id UUID NOT NULL REFERENCES ontology_object_types(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    property_type VARCHAR(50) NOT NULL,
    required BOOLEAN NOT NULL DEFAULT FALSE,
    default_value JSONB,
    validation_rules JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(object_type_id, name)
);

CREATE INDEX idx_properties_object_type ON ontology_properties(object_type_id);

-- Object Instances
CREATE TABLE ontology_objects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_type_id UUID NOT NULL REFERENCES ontology_object_types(id),
    namespace_id UUID NOT NULL REFERENCES namespaces(id),
    properties JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID NOT NULL REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_objects_type ON ontology_objects(object_type_id);
CREATE INDEX idx_objects_namespace ON ontology_objects(namespace_id);
CREATE INDEX idx_objects_properties ON ontology_objects USING GIN(properties);
CREATE INDEX idx_objects_created_at ON ontology_objects(created_at);

-- Link Types
CREATE TABLE ontology_link_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace_id UUID NOT NULL REFERENCES namespaces(id),
    name VARCHAR(255) NOT NULL,
    source_object_type_id UUID NOT NULL REFERENCES ontology_object_types(id),
    target_object_type_id UUID NOT NULL REFERENCES ontology_object_types(id),
    cardinality VARCHAR(20) NOT NULL CHECK (cardinality IN ('one_to_one', 'one_to_many', 'many_to_many')),
    properties JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(namespace_id, name, deleted_at)
);

CREATE INDEX idx_link_types_namespace ON ontology_link_types(namespace_id);
CREATE INDEX idx_link_types_source ON ontology_link_types(source_object_type_id);
CREATE INDEX idx_link_types_target ON ontology_link_types(target_object_type_id);

-- Links
CREATE TABLE ontology_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    link_type_id UUID NOT NULL REFERENCES ontology_link_types(id),
    source_object_id UUID NOT NULL REFERENCES ontology_objects(id) ON DELETE CASCADE,
    target_object_id UUID NOT NULL REFERENCES ontology_objects(id) ON DELETE CASCADE,
    properties JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(link_type_id, source_object_id, target_object_id)
);

CREATE INDEX idx_links_type ON ontology_links(link_type_id);
CREATE INDEX idx_links_source ON ontology_links(source_object_id);
CREATE INDEX idx_links_target ON ontology_links(target_object_id);

-- Action Types
CREATE TABLE ontology_action_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace_id UUID NOT NULL REFERENCES namespaces(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    input_schema JSONB NOT NULL,
    output_schema JSONB,
    function_id UUID,
    side_effects JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(namespace_id, name)
);

-- Action Executions (Audit Trail)
CREATE TABLE ontology_action_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type_id UUID NOT NULL REFERENCES ontology_action_types(id),
    object_id UUID REFERENCES ontology_objects(id),
    input_data JSONB NOT NULL,
    output_data JSONB,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'rolled_back')),
    executed_by UUID NOT NULL REFERENCES users(id),
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    duration_ms INTEGER
);

CREATE INDEX idx_action_executions_type ON ontology_action_executions(action_type_id);
CREATE INDEX idx_action_executions_object ON ontology_action_executions(object_id);
CREATE INDEX idx_action_executions_status ON ontology_action_executions(status);

-- Functions
CREATE TABLE ontology_functions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace_id UUID NOT NULL REFERENCES namespaces(id),
    name VARCHAR(255) NOT NULL,
    language VARCHAR(50) NOT NULL CHECK (language IN ('python', 'typescript')),
    code TEXT NOT NULL,
    parameters JSONB,
    return_type JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID NOT NULL REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    UNIQUE(namespace_id, name)
);

-- Interfaces
CREATE TABLE ontology_interfaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace_id UUID NOT NULL REFERENCES namespaces(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    schema JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(namespace_id, name)
);

-- Interface Implementations
CREATE TABLE ontology_interface_implementations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interface_id UUID NOT NULL REFERENCES ontology_interfaces(id) ON DELETE CASCADE,
    object_type_id UUID NOT NULL REFERENCES ontology_object_types(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(interface_id, object_type_id)
);
```

---

## 8. API Specification

### 8.1 Object Types

```
POST   /api/v2/ontology/object-types          Create object type
GET    /api/v2/ontology/object-types          List object types
GET    /api/v2/ontology/object-types/{id}     Get object type
PUT    /api/v2/ontology/object-types/{id}     Update object type
DELETE /api/v2/ontology/object-types/{id}     Delete object type
```

### 8.2 Object Instances

```
POST   /api/v2/ontology/objects               Create object
GET    /api/v2/ontology/objects               List objects (with filtering)
GET    /api/v2/ontology/objects/{id}          Get object
PUT    /api/v2/ontology/objects/{id}          Update object
DELETE /api/v2/ontology/objects/{id}          Delete object
POST   /api/v2/ontology/objects/batch         Batch create/update
```

### 8.3 Link Types

```
POST   /api/v2/ontology/link-types            Create link type
GET    /api/v2/ontology/link-types            List link types
GET    /api/v2/ontology/link-types/{id}       Get link type
PUT    /api/v2/ontology/link-types/{id}       Update link type
DELETE /api/v2/ontology/link-types/{id}       Delete link type
```

### 8.4 Links

```
POST   /api/v2/ontology/links                 Create link
GET    /api/v2/ontology/links                 List links
GET    /api/v2/ontology/links/{id}            Get link
DELETE /api/v2/ontology/links/{id}            Delete link
GET    /api/v2/ontology/objects/{id}/links    Get links for object
```

### 8.5 Action Types

```
POST   /api/v2/ontology/action-types          Create action type
GET    /api/v2/ontology/action-types          List action types
GET    /api/v2/ontology/action-types/{id}     Get action type
PUT    /api/v2/ontology/action-types/{id}     Update action type
POST   /api/v2/ontology/action-types/{id}/execute  Execute action
GET    /api/v2/ontology/action-types/{id}/executions  List executions
```

### 8.6 Functions

```
POST   /api/v2/ontology/functions             Create function
GET    /api/v2/ontology/functions             List functions
GET    /api/v2/ontology/functions/{id}        Get function
PUT    /api/v2/ontology/functions/{id}        Update function
POST   /api/v2/ontology/functions/{id}/execute  Execute function
```

### 8.7 Interfaces

```
POST   /api/v2/ontology/interfaces            Create interface
GET    /api/v2/ontology/interfaces            List interfaces
GET    /api/v2/ontology/interfaces/{id}       Get interface
PUT    /api/v2/ontology/interfaces/{id}       Update interface
POST   /api/v2/ontology/interfaces/{id}/implement  Implement interface
```

### 8.8 Object Explorer

```
GET    /api/v2/ontology/explore/search        Full-text search
GET    /api/v2/ontology/explore/filter        Filtered search
POST   /api/v2/ontology/explore/compare       Compare object sets
GET    /api/v2/ontology/explore/pivot/{objectId}  Navigate links
POST   /api/v2/ontology/explore/save          Save search
GET    /api/v2/ontology/explore/saved         List saved searches
```

---

## 9. MCP Tools

```python
# voyant.ontology — Agent-accessible Ontology operations

voyant.ontology.create_object_type    # Create object type
voyant.ontology.list_object_types     # List object types
voyant.ontology.create_object         # Create object instance
voyant.ontology.get_object            # Get object instance
voyant.ontology.update_object         # Update object instance
voyant.ontology.delete_object         # Delete object instance
voyant.ontology.create_link           # Create link between objects
voyant.ontology.get_links             # Get links for object
voyant.ontology.execute_action        # Execute action type
voyant.ontology.search_objects        # Search objects
voyant.ontology.compare_objects       # Compare object sets
```

---

## 10. Implementation Plan

### Phase 1: Core Engine (Months 1-3)

| Week | Task | Deliverable |
|------|------|-------------|
| 1-2 | Database schema + migrations | Schema deployed |
| 3-4 | Object type CRUD API | API endpoints |
| 5-6 | Object instance CRUD API | API endpoints |
| 7-8 | Link type + link instance API | API endpoints |
| 9-10 | Property validation | Validation system |
| 11-12 | Unit + integration tests | 90%+ coverage |

### Phase 2: Search & Actions (Months 4-6)

| Week | Task | Deliverable |
|------|------|-------------|
| 1-2 | Full-text search (PostgreSQL + Milvus) | Search API |
| 3-4 | Filtered search + pivot | Explorer API |
| 5-6 | Action type management | Action API |
| 7-8 | Action execution engine | Execution runtime |
| 9-10 | Function framework (Python sandbox) | Function runtime |
| 11-12 | Audit trail + testing | 90%+ coverage |

### Phase 3: Advanced Features (Months 7-9)

| Week | Task | Deliverable |
|------|------|-------------|
| 1-2 | Interface management | Interface API |
| 3-4 | Scenario branching | Scenario API |
| 5-6 | Batch operations | Batch API |
| 7-8 | MCP tool integration | MCP tools |
| 9-10 | Performance optimization | < 100ms p95 |
| 11-12 | Security hardening + audit | Security audit pass |

---

## 11. Test Strategy

### 11.1 Unit Tests

```python
# apps/ontology/tests/test_object_types.py

import pytest
from apps.ontology.services import ObjectService

@pytest.mark.django_db
class TestObjectService:
    def test_create_object_type(self):
        service = ObjectService(namespace_id="test-ns")
        obj_type = service.create_object_type(
            name="Customer",
            properties=[
                {"name": "email", "type": "string", "required": True},
                {"name": "name", "type": "string", "required": True},
                {"name": "age", "type": "integer", "required": False}
            ]
        )
        assert obj_type.name == "Customer"
        assert len(obj_type.properties) == 3
        
    def test_create_object_instance(self):
        service = ObjectService(namespace_id="test-ns")
        obj_type = service.create_object_type(name="Customer", properties=[])
        obj = service.create_object(
            object_type_id=obj_type.id,
            properties={"email": "test@example.com", "name": "John"}
        )
        assert obj.properties["email"] == "test@example.com"
        
    def test_validate_required_property(self):
        service = ObjectService(namespace_id="test-ns")
        obj_type = service.create_object_type(
            name="Customer",
            properties=[{"name": "email", "type": "string", "required": True}]
        )
        with pytest.raises(ValidationError):
            service.create_object(object_type_id=obj_type.id, properties={})
            
    def test_create_link(self):
        service = ObjectService(namespace_id="test-ns")
        customer_type = service.create_object_type(name="Customer", properties=[])
        order_type = service.create_object_type(name="Order", properties=[])
        link_type = service.create_link_type(
            name="placed_order",
            source_type_id=customer_type.id,
            target_type_id=order_type.id,
            cardinality="one_to_many"
        )
        customer = service.create_object(object_type_id=customer_type.id, properties={})
        order = service.create_object(object_type_id=order_type.id, properties={})
        link = service.create_link(
            link_type_id=link_type.id,
            source_id=customer.id,
            target_id=order.id
        )
        assert link.source_object_id == customer.id
```

### 11.2 Integration Tests

```python
# apps/ontology/tests/integration/test_ontology_flow.py

@pytest.mark.django_db(transaction=True)
class TestOntologyIntegration:
    def test_complete_ontology_flow(self):
        """Test full lifecycle: type → instance → link → action"""
        # 1. Create object types
        # 2. Create object instances
        # 3. Create link types
        # 4. Create links
        # 5. Search objects
        # 6. Traverse links
        # 7. Execute action
        # 8. Verify audit trail
        pass
```

### 11.3 Performance Tests

```python
# apps/ontology/tests/performance/test_query_performance.py

class TestQueryPerformance:
    def test_object_query_p95(self):
        """ONT-NF-001: Object query p95 < 100ms"""
        # Create 100K objects
        # Query with filters
        # Assert p95 < 100ms
        pass
        
    def test_batch_create_throughput(self):
        """ONT-NF-002: Batch create > 1000/sec"""
        # Create 10K objects in batch
        # Measure throughput
        # Assert > 1000/sec
        pass
```

---

## 12. Traceability Matrix

| Req ID | Design | Code | Test | Status |
|--------|--------|------|------|--------|
| ONT-F-001 | §5.1 | object_types.py | test_object_types.py | 🔧 Planned |
| ONT-F-002 | §5.1 | property_types.py | test_property_types.py | 🔧 Planned |
| ONT-F-010 | §5.2 | objects.py | test_objects.py | 🔧 Planned |
| ONT-F-020 | §5.3 | link_types.py | test_link_types.py | 🔧 Planned |
| ONT-F-030 | §5.4 | links.py | test_links.py | 🔧 Planned |
| ONT-F-040 | §5.5 | action_types.py | test_action_types.py | 🔧 Planned |
| ONT-F-050 | §5.6 | functions.py | test_functions.py | 🔧 Planned |
| ONT-F-060 | §5.7 | interfaces.py | test_interfaces.py | 🔧 Planned |
| ONT-F-070 | §5.8 | search.py | test_search.py | 🔧 Planned |
| ONT-F-080 | §5.9 | scenarios.py | test_scenarios.py | 🔧 Planned |

---

**Document Status:** DRAFT
**Last Updated:** 2026-07-20
**Next Review:** 2026-08-20
