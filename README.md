# Voyant v3.0.0 - Autonomous Data Intelligence for AI Agents

## Document Information
- **Document ID:** VOYANT-README-3.0.0
- **Status:** Active Development
- **Version:** 3.0.0
- **Last Updated:** 2026-01-12
- **Compliance:** ISO/IEC 25010 Software Quality Standards

## Executive Summary

Voyant is an autonomous data intelligence service designed specifically for AI agents, providing end-to-end data discovery, ingestion, profiling, quality analysis, and predictive capabilities through REST APIs and Model Context Protocol (MCP) tools. The system operates as a Django-based microservice with Temporal workflow orchestration and integrates seamlessly with modern data stacks including Apache Iceberg, Trino, and the SomaAgentHub orchestration platform.

## System Architecture

### Core Technology Stack
- **Web Framework:** Django 5.0 with Django Ninja REST API
- **Workflow Engine:** Temporal.io for reliable orchestration
- **Database:** PostgreSQL for metadata persistence
- **Object Storage:** MinIO for artifact management
- **Query Engine:** Trino for distributed SQL analytics
- **Authentication:** Keycloak JWT integration
- **Message Queue:** Kafka for event-driven operations
- **Containerization:** Docker Compose development environment

### Service Integration Architecture
```
┌─────────────────────────────────────────────────────────────┐
│ SomaAgentHub - Gateway/Orchestrator/Policy/Memory Services │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────┐
│          Voyant v3.0.0 - Data Intelligence Service           │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │   REST API     │ │   MCP Server    │ │  Temporal Workflows │ │
│ │ (Django Ninja) │ │ (Tool Registry) │ │ (Ingest/Profile/Analyze) │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────┐
│                External Data Ecosystem                       │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│ │ Airbyte │ │   NiFi   │ │  DataHub│ │   Iceberg│ │  Apache │   │
│ │ Connectors│ │ Flows   │ │Governance│ │Lakehouse│ │  Stack  │   │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Agent-First Data Intelligence
- **One-Call Analyze:** Complete data analysis pipeline from source to artifacts
- **MCP Tool Integration:** 15+ tools for agent orchestration
- **Pure Execution:** DataScraper module for web scraping without LLM integration

### 2. Data Ingestion & Processing
- **Multi-Source Connectors:** Airbyte integration for batch sync
- **Direct Ingestion:** File-to-DuckDB, file-to-Iceberg pipelines
- **Document Processing:** PDF, HTML, OCR, and media transcription
- **Stream Processing:** Apache Flink for real-time analytics

### 3. Analytics & Intelligence
- **Exploratory Data Analysis:** Adaptive sampling and profiling
- **Quality Assessment:** Rule-based and Evidently integration
- **Predictive Analytics:** Regression, forecasting, anomaly detection
- **KPI Generation:** SQL-based metric computation

### 4. Governance & Security
- **Multi-Tenant Isolation:** Tenant-scoped data and operations
- **Policy Enforcement:** Apache Ranger integration planned
- **Lineage Tracking:** DataHub metadata governance
- **Audit Logging:** Comprehensive event tracking

### 5. Soma Stack Integration
- **Agent Orchestration:** Native support for SomaAgentHub workflows
- **Policy Integration:** Real-time decision making via Policy Engine
- **Memory Integration:** Analysis summary persistence and recall
- **Distributed Tracing:** SkyWalking integration for observability

## API Documentation

### REST API Endpoints
- Health & Status: `/health`, `/ready`, `/status`
- Source Management: `/v1/sources/*`
- Job Execution: `/v1/jobs/ingest`, `/v1/jobs/profile`, `/v1/jobs/quality`
- Analysis Pipeline: `/v1/analyze` (one-call endpoint)
- SQL Query: `/v1/sql/query`, `/v1/sql/tables`
- Artifacts: `/v1/artifacts/*`
- Governance: `/v1/governance/*`
- Discovery: `/v1/discovery/*`

### MCP Tools Available
- `voyant.discover` - Auto-detect data source types
- `voyant.connect` - Establish data connections
- `voyant.ingest` - Trigger data ingestion
- `voyant.profile` - Generate data profiles
- `voyant.quality` - Run quality checks
- `voyant.analyze` - End-to-end analysis
- `voyant.kpi` - Execute KPI queries
- `voyant.status` - Check job status
- `voyant.artifact` - Retrieve artifacts
- `voyant.sql_query` - Execute SQL queries
- `voyant.search` - Search data catalog
- `voyant.lineage` - Get data lineage

Plus DataScraper tools:
- `scrape.fetch`, `scrape.extract`, `scrape.ocr`, `scrape.parse_pdf`, `scrape.transcribe`

## Development Setup

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL, Redis, Kafka, Temporal services

### Quick Start
```bash
# Clone repository
git clone https://github.com/somatech/voyant.git
cd voyant

# Install dependencies
pip install -r requirements.txt

# Start development environment
docker-compose up -d

# Run application
python manage.py runserver
```

### Configuration
All configuration is managed through environment variables with `VOYANT_` prefix. Key settings include:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/voyant

# External Services
TEMPORAL_HOST=localhost:7233
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
MINIO_ENDPOINT=localhost:9000

# Authentication
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_CLIENT_ID=voyant-api
```

## Deployment

### Docker Compose
```bash
docker-compose -f docker-compose.yml up -d
```

### Production Considerations
- Use secure secrets management (not default values)
- Configure proper CORS and SSL settings
- Implement rate limiting and authentication
- Set up monitoring and logging infrastructure
- Configure backup and disaster recovery

## Quality & Compliance

### Current Status
- **Code Quality:** 13% test coverage (needs improvement)
- **Security:** JWT authentication implemented, tenant isolation enforced
- **Performance:** Circuit breakers and retry policies for external calls
- **Reliability:** Temporal workflows with retry mechanisms
- **Documentation:** ISO-compliant documentation standards

### Development Standards
- **Code Style:** Black formatter, Ruff linter
- **Type Checking:** MyPy for static analysis
- **Testing:** pytest framework with async support
- **Documentation:** Comprehensive docstrings and API docs

## Integration Capabilities

### Data Sources Supported
- Database connectors via Airbyte (PostgreSQL, MySQL, etc.)
- File ingestion (CSV, JSON, Parquet)
- Web scraping with DataScraper module
- Stream processing via Apache Flink
- Document processing (PDF, HTML, media)

### Output Formats
- Analysis artifacts (JSON, CSV, Parquet)
- Visualizations and charts
- Narrative summaries
- SQL query results
- Lineage graphs

### Integration Patterns
- **SomaAgentHub Native:** Full integration with orchestration workflows
- **REST API:** Standard HTTP/JSON interface
- **MCP Tools:** Agent-first tool integration
- **Event-Driven:** Kafka-based event emission
- **Batch Processing:** Temporal workflow orchestration

## Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch
3. Implement changes with tests
4. Update documentation
5. Submit pull request

### Code Quality Requirements
- All new code must include comprehensive tests
- Documentation must be updated for new features
- Security considerations must be addressed
- Performance impact must be evaluated

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

## Support

For technical support, bug reports, or feature requests, please:
1. Check the existing issues on GitHub
2. Create a new issue with detailed description
3. Include environment information and reproduction steps

## Roadmap

### Current Development Focus
- M1: One-call analyze pipeline completion
- M2: Persistence and real connector integration
- M3: Quality and predictive workflows
- M4: Security and observability hardening
- M5: Production deployment and testing

### Future Enhancements
- Apache Iceberg lakehouse integration
- Apache Ranger policy enforcement
- Apache Atlas metadata governance
- Apache SkyWalking distributed tracing
- Apache NiFi dataflow integration
- Apache Superset BI integration
- Apache Druid/Pinot OLAP support
- Apache Tika document processing
- Apache Flink streaming analytics

---

**Voyant** - Autonomous Data Intelligence for AI Agents  
*Building the future of data-driven AI systems*