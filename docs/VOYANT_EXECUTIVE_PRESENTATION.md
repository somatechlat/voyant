# VOYANT v4.0 — Executive Architecture Presentation
## Autonomous Data Intelligence for AI Agents

**Prepared for:** IT Leadership & Executive Review
**Date:** 2026-09-11
**Version:** 4.0.0
**Classification:** Internal

---

## 1. SYSTEM ACCESS — Login Credentials

### Dashboard URL
```
http://localhost:45001
```

### User Accounts (Keycloak Identity Provider)

| Role | Username | Password | Email | Access Level |
|------|----------|----------|-------|-------------|
| **System Admin** | `admin` | `admin` | admin@voyant.io | Full system access — all tenants, all modules, all settings |
| **Data Engineer** | `engineer` | `engineer` | engineer@voyant.io | Read all + write sources/jobs + execute SQL/pipelines + scraping |
| **Data Analyst** | `analyst` | `analyst` | analyst@voyant.io | Read all + execute SQL/presets + dashboards |

### Additional Service Ports

| Service | URL | Credentials |
|---------|-----|-------------|
| **API** | http://localhost:45000 | Bearer token via login |
| **Temporal UI** | http://localhost:45089 | No auth |
| **Keycloak Admin** | http://localhost:45180 | admin / *(see secrets)* |
| **Vault** | http://localhost:45820 | Token: `voyant-root-token` |
| **Trino** | http://localhost:45080 | No auth |
| **MinIO Console** | http://localhost:45901 | *(see secrets)* |
| **Flink UI** | http://localhost:45082 | No auth |
| **Milvus** | http://localhost:19530 | gRPC |
| **Elasticsearch** | http://localhost:45200 | No auth |
| **SearXNG** | http://localhost:45088 | No auth |

---

## 2. FULL SYSTEM ARCHITECTURE — Mermaid Diagram

### 2.1 High-Level Architecture

```mermaid
graph TB
    subgraph "External Users"
        HUMANS["👤 Human Users<br/>(Admin, Engineer, Analyst)"]
        AGENTS["🤖 AI Agents<br/>(MCP Protocol)"]
        EXTERNAL["🔌 External Systems<br/>(APIs, Webhooks)"]
    end

    subgraph "Presentation Layer"
        DASHBOARD["📊 Dashboard<br/>Lit 3 + Vite + Tailwind<br/>38 Views, 16 Components<br/>Port: 45001"]
        CLI["⌨️ CLI Tool<br/>Click-based<br/>voyant command"]
        SDK["📦 SDKs<br/>Python, TypeScript<br/>Go, Java"]
    end

    subgraph "API Gateway Layer"
        API["🚀 Voyant API<br/>Django 5 + Django Ninja<br/>~240 REST Endpoints<br/>Port: 45000"]
        MCP["🔧 MCP Server<br/>80 AI Agent Tools<br/>django-mcp at /mcp"]
        GQL["📊 GraphQL<br/>graphene-django<br/>at /graphql"]
        MLFLOW["🧪 MLflow API<br/>19 Compatible Endpoints<br/>at /api/2.0/mlflow/"]
        WS["🔌 WebSocket<br/>Django Channels<br/>Real-time Events"]
    end

    subgraph "Security Layer"
        KC["🔐 Keycloak<br/>JWT Authentication<br/>Port: 45180"]
        SPICE["🛡️ SpiceDB<br/>Fine-grained RBAC<br/>Port: 50051"]
        VAULT["🗝️ HashiCorp Vault<br/>Secrets Management<br/>Port: 45820"]
    end

    subgraph "Application Layer — 16 Modules"
        M1["M1 Connect<br/>Ingestion & Discovery"]
        M2["M2 Pipeline<br/>ETL & Temporal"]
        M3["M3 Catalog<br/>Ontology Engine"]
        M4["M4 Lakehouse<br/>Iceberg Storage"]
        M5["M5 Analyze<br/>SQL & Analytics"]
        M6["M6 ML<br/>Experiments & Serving"]
        M7["M7 Agent<br/>Intent & MCP"]
        M8["M8 Scrape<br/>9-Arm Octopus"]
        M9["M9 Shield<br/>Governance"]
        M10["M10 Workspace<br/>Collaboration"]
        M11["M11 Admin<br/>Operations"]
        M12["M12 API<br/>Gateway & SDKs"]
        M13["M13 Features<br/>Feature Store"]
        M14["M14 Notify<br/>Notifications"]
        M15["M15 Approve<br/>Workflows"]
        M16["M16 Validate<br/>Data Quality"]
    end

    subgraph "Orchestration Layer"
        TEMPORAL["⏱️ Temporal.io<br/>17 Workflows, 50+ Activities<br/>Durable & Replayable<br/>Port: 45233"]
        WORKER["⚙️ Temporal Worker<br/>Background Processing<br/>Port: 45090"]
    end

    subgraph "Data Layer"
        PG["🐘 PostgreSQL 16<br/>Metadata Store<br/>Port: 45432"]
        REDIS["⚡ Redis 7<br/>Cache, Sessions, Pub/Sub<br/>Port: 45379"]
        TRINO["🔍 Trino 434<br/>Distributed SQL<br/>Port: 45080"]
        MINIO["📦 MinIO<br/>Object Storage (S3)<br/>Port: 45900"]
        MILVUS["🧠 Milvus<br/>Vector Database<br/>Port: 19530"]
        KAFKA["📨 Apache Kafka<br/>Event Streaming<br/>Port: 45092"]
        ES["🔎 Elasticsearch<br/>Full-text Search<br/>Port: 45200"]
    end

    subgraph "Streaming Layer"
        FLINK["⚡ Apache Flink<br/>Real-time Analytics<br/>Port: 45082"]
    end

    subgraph "Anti-Bot Layer"
        BROWSERLESS["🌐 Browserless<br/>Chromium Pool<br/>Port: 45300"]
        FLARE["🔥 FlareSolverr<br/>Anti-bot Bypass<br/>Port: 45191"]
        SEARXNG["🔍 SearXNG<br/>Meta Search<br/>Port: 45088"]
    end

    HUMANS --> DASHBOARD
    AGENTS --> MCP
    EXTERNAL --> API
    DASHBOARD --> API
    CLI --> API
    SDK --> API
    API --> M1 & M2 & M3 & M4 & M5 & M6 & M7 & M8 & M9 & M10 & M11 & M12 & M13 & M14 & M15 & M16
    MCP --> M7
    GQL --> M3
    MLFLOW --> M6
    WS --> M10
    API --> KC & SPICE & VAULT
    M1 --> TEMPORAL
    M2 --> TEMPORAL
    M5 --> TEMPORAL
    M8 --> TEMPORAL
    TEMPORAL --> WORKER
    WORKER --> PG & REDIS & KAFKA & MINIO
    M3 --> TRINO
    M5 --> TRINO
    M4 --> MINIO
    M7 --> MILVUS
    M8 --> BROWSERLESS & FLARE & SEARXNG
    M9 --> ES
    KAFKA --> FLINK
```

### 2.2 Data Flow Architecture

```mermaid
flowchart LR
    subgraph "Data Sources"
        DB["Databases<br/>PostgreSQL, MySQL<br/>MongoDB, Snowflake"]
        FILES["Files<br/>CSV, JSON, Parquet<br/>PDF, Excel"]
        WEB["Web<br/>APIs, Scraping<br/>Deep Research"]
        STREAM["Streams<br/>Kafka, Kinesis<br/>Event Hubs"]
    end

    subgraph "Ingestion"
        CONNECT["Voyant Connect<br/>Airbyte + Direct<br/>CDC Support"]
    end

    subgraph "Processing"
        PIPELINE["Voyant Pipeline<br/>DAG Validation<br/>12 Transform Types"]
        TEMPORAL["Temporal<br/>Durable Workflows<br/>Retry & Replay"]
    end

    subgraph "Storage"
        ICEBERG["Apache Iceberg<br/>Lakehouse<br/>Time Travel"]
        PG["PostgreSQL<br/>Metadata"]
        MINIO["MinIO<br/>Artifacts"]
        MILVUS["Milvus<br/>Vectors"]
    end

    subgraph "Intelligence"
        ANALYZE["Voyant Analyze<br/>SQL, KPIs<br/>Anomaly Detection"]
        ML["Voyant ML<br/>Experiments<br/>Model Serving"]
        INTENT["Intent Engine<br/>NL → Plans<br/>LLM-Powered"]
    end

    subgraph "Output"
        DASH["Dashboards<br/>Charts, Tables<br/>Graph Views"]
        API_OUT["REST API<br/>240+ Endpoints"]
        MCP_OUT["MCP Tools<br/>80 Agent Tools"]
        EXPORT["Export<br/>CSV, JSON<br/>PDF, Excel"]
    end

    DB --> CONNECT
    FILES --> CONNECT
    WEB --> CONNECT
    STREAM --> CONNECT
    CONNECT --> PIPELINE
    PIPELINE --> TEMPORAL
    TEMPORAL --> ICEBERG & PG & MINIO
    ICEBERG --> ANALYZE
    MILVUS --> ANALYZE
    ANALYZE --> ML
    ML --> DASH
    INTENT --> API_OUT
    ANALYZE --> MCP_OUT
    ML --> EXPORT
```

### 2.3 Security Architecture

```mermaid
graph TB
    subgraph "Layer 1: Authentication"
        KC["Keycloak<br/>JWT Tokens<br/>Realm Isolation"]
        JWT["JWT Validation<br/>RS256 Signatures<br/>Token Refresh"]
    end

    subgraph "Layer 2: Authorization"
        SPICE["SpiceDB<br/>Relationship-Based<br/>Access Control"]
        RBAC["RBAC Middleware<br/>4 Roles: Admin<br/>Engineer, Analyst, Viewer"]
        POLICY["Governance Policies<br/>12 Rule Types<br/>Scope Matching"]
    end

    subgraph "Layer 3: Data Security"
        RLS["Row-Level Security<br/>SQL WHERE Injection<br/>Per-Tenant Filtering"]
        MASK["Column Masking<br/>6 Mask Types<br/>Role-Based"]
        ABAC["Attribute-Based<br/>Access Control<br/>Cell-Level Security"]
        AUDIT["Audit Log<br/>Immutable, Append-Only<br/>Full Event Trail"]
    end

    subgraph "Layer 4: Infrastructure Security"
        VAULT["HashiCorp Vault<br/>Secrets Management<br/>16 Secret Keys"]
        SSRF["SSRF Protection<br/>URL Validation<br/>Internal Block"]
        SQL_SEC["SQL Security<br/>Read-Only Enforcement<br/>28 Forbidden Keywords"]
        CORS["CORS<br/>Explicit Origins Only<br/>No Wildcards"]
    end

    KC --> JWT --> SPICE --> RBAC --> POLICY
    RLS --> MASK --> ABAC --> AUDIT
    VAULT --> SSRF --> SQL_SEC --> CORS
```

### 2.4 Module Architecture (16 Modules)

```mermaid
graph LR
    subgraph "Data Layer"
        M1["🔗 M1 Voyant Connect<br/>━━━━━━━━━━━━━<br/>Ingestion & Discovery<br/>Airbyte, CDC, File Upload<br/>23 Sources"]
        M4["🏗️ M4 Voyant Lakehouse<br/>━━━━━━━━━━━━━<br/>Iceberg Storage<br/>MinIO Artifacts<br/>Time Travel"]
    end

    subgraph "Processing Layer"
        M2["⚙️ M2 Voyant Pipeline<br/>━━━━━━━━━━━━━<br/>DAG Builder<br/>12 Transform Types<br/>Temporal Execution"]
        M5["📊 M5 Voyant Analyze<br/>━━━━━━━━━━━━━<br/>SQL Console (Trino)<br/>KPI Templates<br/>Anomaly Detection"]
        M8["🕷️ M8 Voyant Scrape<br/>━━━━━━━━━━━━━<br/>9-Arm Octopus Engine<br/>51 Templates<br/>CAPTCHA Solver"]
    end

    subgraph "Intelligence Layer"
        M3["🧠 M3 Voyant Catalog<br/>━━━━━━━━━━━━━<br/>22 Ontology Models<br/>Query Engine<br/>PII Detection"]
        M6["🤖 M6 Voyant ML<br/>━━━━━━━━━━━━━<br/>MLflow-Compatible<br/>Model Registry<br/>Drift Detection"]
        M7["🎯 M7 Voyant Agent<br/>━━━━━━━━━━━━━<br/>Intent Engine<br/>80 MCP Tools<br/>Capsule System"]
    end

    subgraph "Governance Layer"
        M9["🛡️ M9 Voyant Shield<br/>━━━━━━━━━━━━━<br/>RBAC, RLS, Masking<br/>GDPR, SOC2<br/>Data Lineage"]
        M15["✅ M15 Voyant Approve<br/>━━━━━━━━━━━━━<br/>Approval Workflows<br/>Action Gating<br/>Audit Trail"]
        M16["✔️ M16 Voyant Validate<br/>━━━━━━━━━━━━━<br/>Data Quality Rules<br/>Contracts<br/>Validation Framework"]
    end

    subgraph "Collaboration Layer"
        M10["👥 M10 Voyant Workspace<br/>━━━━━━━━━━━━━<br/>Workspaces<br/>Comments, Activity<br/>Asset Sharing"]
        M14["🔔 M14 Voyant Notify<br/>━━━━━━━━━━━━━<br/>In-App, Email, Slack<br/>Preferences<br/>Real-time WebSocket"]
    end

    subgraph "Operations Layer"
        M11["⚙️ M11 Voyant Admin<br/>━━━━━━━━━━━━━<br/>System Dashboard<br/>Tenant Management<br/>Health Monitoring"]
        M12["🚀 M12 Voyant API<br/>━━━━━━━━━━━━━<br/>240+ REST Endpoints<br/>4 SDKs, CLI<br/>GraphQL, MLflow"]
        M13["📈 M13 Voyant Features<br/>━━━━━━━━━━━━━<br/>Feature Store<br/>Online/Batch Serving<br/>Statistics"]
    end
```

### 2.5 Infrastructure Topology (20 Docker Services)

```mermaid
graph TB
    subgraph "voyant_cluster [Docker Network: voyant_cluster]"
        subgraph "Core Services"
            API["voyant_api<br/>Custom Python 3.11<br/>Port: 45000 → 8000<br/>1 CPU, 768MB"]
            WORKER["voyant_worker<br/>Temporal Worker<br/>Port: 45090 → 9090<br/>1 CPU, 512MB"]
            DASH["voyant_dashboard<br/>nginx + Lit SPA<br/>Port: 45001 → 80<br/>0.25 CPU, 128MB"]
        end

        subgraph "Data Infrastructure"
            PG["voyant_postgres<br/>PostgreSQL 16 Alpine<br/>Port: 45432 → 5432<br/>0.5 CPU, 512MB"]
            REDIS["voyant_redis<br/>Redis 7 Alpine<br/>Port: 45379 → 6379<br/>256MB"]
            KAFKA["voyant_kafka<br/>Apache Kafka 3.7<br/>Port: 45092 → 9092<br/>0.75 CPU, 768MB"]
            MINIO["voyant_minio<br/>MinIO S3-Compatible<br/>Port: 45900/45901<br/>0.5 CPU, 384MB"]
        end

        subgraph "Analytics"
            TRINO["voyant_trino<br/>Trino 434<br/>Port: 45080 → 8080<br/>1 CPU, 768MB"]
            MILVUS["voyant_milvus<br/>Milvus 2.4<br/>Port: 19530<br/>1 CPU, 1GB"]
            ETCD["voyant_etcd<br/>etcd 3.5<br/>0.5 CPU, 256MB"]
            ES["voyant_elasticsearch<br/>ES 7.17<br/>Port: 45200<br/>0.5 CPU, 512MB"]
        end

        subgraph "Workflow & Security"
            TEMPORAL["voyant_temporal<br/>Temporal 1.24<br/>Port: 45233<br/>0.5 CPU, 384MB"]
            TEMPORAL_UI["voyant_temporal_ui<br/>Temporal UI<br/>Port: 45089"]
            KEYCLOAK["voyant_keycloak<br/>Keycloak 23<br/>Port: 45180<br/>0.5 CPU, 384MB"]
            VAULT["voyant_vault<br/>Vault 1.15<br/>Port: 45820<br/>0.25 CPU, 256MB"]
            SPICEDB["voyant_spicedb<br/>SpiceDB<br/>Port: 50051<br/>0.25 CPU, 192MB"]
        end

        subgraph "Streaming & Anti-Bot"
            FLINK_JM["voyant_flink_jobmanager<br/>Flink 1.18<br/>Port: 45082<br/>0.5 CPU, 512MB"]
            FLINK_TM["voyant_flink_taskmanager<br/>Flink 1.18<br/>0.5 CPU, 512MB"]
            BROWSERLESS["voyant_browserless<br/>Chromium Pool<br/>Port: 45300<br/>0.5 CPU, 512MB"]
            FLARE["voyant_flaresolverr<br/>Anti-bot Bypass<br/>Port: 45191<br/>0.5 CPU, 256MB"]
            SEARXNG["voyant_searxng<br/>Meta Search<br/>Port: 45088<br/>0.25 CPU, 256MB"]
        end
    end

    API --> PG & REDIS & KAFKA & VAULT & KEYCLOAK & SPICEDB & TRINO & MILVUS & MINIO
    WORKER --> PG & REDIS & KAFKA & VAULT & TEMPORAL
    DASH --> API
    TEMPORAL --> PG
    MILVUS --> ETCD & MINIO
    FLINK_TM --> FLINK_JM
```

### 2.6 Technology Stack Summary

```mermaid
mindmap
  root((Voyant v4.0))
    Backend
      Django 5.0
      Django Ninja REST
      django-mcp
      Python 3.11+
    Frontend
      Lit 3 Web Components
      Vite 7.3
      Tailwind CSS
      Apache ECharts
      Monaco Editor
    Database
      PostgreSQL 16
      DuckDB
      Milvus 2.4
      Redis 7
    Orchestration
      Temporal.io
      Apache Kafka
      Apache Flink
    Security
      Keycloak JWT
      SpiceDB RBAC
      HashiCorp Vault
    Data
      Trino 434
      MinIO S3
      Apache Iceberg
      Elasticsearch
    Scraping
      Playwright
      Scrapy
      BeautifulSoup
      9-Arm Octopus
    ML
      scikit-learn
      MLflow Compatible
      Drift Detection
    DevOps
      Docker Compose
      Kubernetes
      Helm Charts
```

---

## 3. KEY METRICS

| Metric | Value |
|--------|-------|
| Python LOC | ~73,416 |
| TypeScript LOC | ~9,099 |
| Django Apps | 22 |
| REST Endpoints | ~240 |
| MCP Tools | 80 |
| Temporal Workflows | 17 |
| Test Functions | 2,203 (2,128 passing) |
| Playwright E2E | 84 tests (81 passing) |
| Docker Services | 20 |
| LLM Providers | 7 |
| Scraper Templates | 51 |
| Ontology Models | 22 |
| SDKs | 4 (Python, TypeScript, Go, Java) |
| SRS Completion | 87% (77/89) |

---

## 4. COMPETITIVE POSITION

| Capability | Palantir Foundry | Databricks | **Voyant v4.0** |
|-----------|-----------------|------------|-----------------|
| Ontology Engine | ✅ | ❌ | ✅ (22 models) |
| MCP Agent Protocol | ❌ | ❌ | ✅ (80 tools) |
| Web Scraping | ❌ | ❌ | ✅ (9-arm engine) |
| Self-Hosted | ❌ | ❌ | ✅ (Docker) |
| MLflow Compatible | ❌ | ✅ | ✅ (19 endpoints) |
| Visual Pipeline Builder | ✅ | ✅ | ✅ (DAG editor) |
| Real-time Streaming | ✅ | ✅ | ✅ (Flink + Kafka) |
| RBAC + RLS + Masking | ✅ | ✅ | ✅ (3-layer) |
| Open Source | ❌ | ❌ | ✅ (Apache 2.0) |
| Agent-First Design | ❌ | ❌ | ✅ (native) |

---

## 5. DEPLOYMENT

### Quick Start
```bash
cd infra/standalone
./scripts/bootstrap-env.sh
docker compose up -d
```

### Total Resource Requirements
- **CPU:** ~10 cores
- **RAM:** ~10 GB
- **Disk:** ~20 GB (including images)
- **Ports:** 45xxx range (no conflicts with local services)

---

*Document generated by Voyant Engineering — Ready for PPT conversion*
