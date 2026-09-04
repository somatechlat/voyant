# Dashboard and Scripts Module

> **Source date**: 2026-09-04
> **Files examined**: `dashboard/`, `scripts/`

## Overview

The dashboard and scripts module covers two non-server components:

1. **Dashboard** (`dashboard/`) — A client-side web UI built with Lit + Vite + Tailwind CSS
2. **Scripts** (`scripts/`) — Development, operations, verification, and example scripts

---

## Dashboard (`dashboard/`)

### Technology Stack

| Component | Technology | Version |
|---|---|---|
| Framework | Lit (Web Components) | ^3.3.2 |
| Router | @lit-labs/router | ^0.1.4 |
| CSS | @twind/core (Tailwind-in-JS) | ^1.1.3 |
| Build | Vite | ^7.3.0 |
| Runtime | Bun | Latest |
| Language | TypeScript | ^5 |

### Configuration

**`package.json`**: Private module, ESM (`"type": "module"`). Entry point `index.ts`.

**`vite.config.ts`**: Dev server on port 3000 (host `0.0.0.0`), build output to `dist/`.

**`Dockerfile`**: Container build for production deployment.

**`nginx.conf`**: Nginx configuration for serving the built dashboard.

### Source Structure

```
dashboard/src/
├── main.ts                    # Application entry point
├── styles/                    # CSS/style definitions
├── components/
│   ├── saas-glass-modal.ts    # Glassmorphism modal component
│   ├── saas-infra-card.ts     # Infrastructure card component
│   ├── saas-layout.ts         # Layout wrapper component
│   └── saas-status-dot.ts     # Status indicator dot component
└── views/
    ├── view-login.ts          # Login page view
    └── view-voyant-setup.ts   # Voyant setup wizard view
```

### Components

| Component | File | Description |
|---|---|---|
| `saas-glass-modal` | `saas-glass-modal.ts` | Modal dialog with glassmorphism styling |
| `saas-infra-card` | `saas-infra-card.ts` | Card component for infrastructure status display |
| `saas-layout` | `saas-layout.ts` | Page layout wrapper |
| `saas-status-dot` | `saas-status-dot.ts` | Visual status indicator (dot) |

### Views

| View | File | Description |
|---|---|---|
| Login | `view-login.ts` | Authentication/login page |
| Voyant Setup | `view-voyant-setup.ts` | Initial setup wizard for Voyant configuration |

### Build and Deployment

```bash
# Development
cd dashboard && bun install && bun run dev

# Production build
cd dashboard && bun run build  # outputs to dist/

# Docker
docker build -f dashboard/Dockerfile .
```

---

## Scripts (`scripts/`)

### Directory Structure

```
scripts/
├── README.md
├── dev/                  # Development scripts
│   ├── dev.sh            # Development server launcher
│   └── wait-for-stack.sh # Wait for dependencies to be ready
├── ops/                  # Operations scripts
│   ├── debug_imports.py  # Debug Python import issues
│   └── deploy_spicedb_schema.py  # Deploy SpiceDB authorization schema
├── verification/         # Integration verification scripts
│   ├── verify_benchmark.py       # Verify benchmark workflow
│   ├── verify_circuit_breakers.py # Verify circuit breaker patterns
│   ├── verify_cleaning.py        # Verify data cleaning operations
│   ├── verify_discovery.py       # Verify service discovery
│   ├── verify_ml.py              # Verify ML pipeline
│   ├── verify_observability.py   # Verify observability setup
│   ├── verify_operational.py     # Verify operational workflows
│   └── verify_vault.py           # Verify Vault secrets integration
├── sql/                  # SQL initialization
│   └── init-db.sql       # Database initialization script
└── examples/             # Example scripts
    ├── example_compras_publicas.py  # Public procurement scraping example
    ├── example_mcp_deep_archive.py  # MCP deep archive example
    ├── example_search_ai.py         # AI search example
    ├── patiotuerca_crawl.py         # PatioTuercа crawling example
    └── patiotuerca/                 # PatioTuercа data directory
```

### Development Scripts (`scripts/dev/`)

| Script | Description |
|---|---|
| `dev.sh` | Starts the development server stack |
| `wait-for-stack.sh` | Waits for infrastructure dependencies (DB, Redis, Temporal, etc.) to become available before starting the application |

### Operations Scripts (`scripts/ops/`)

| Script | Description |
|---|---|
| `debug_imports.py` | Diagnostic tool for debugging Python import chain issues |
| `deploy_spicedb_schema.py` | Deploys the SpiceDB authorization schema (relations, permissions) |

### Verification Scripts (`scripts/verification/`)

Automated verification scripts for validating subsystem integration:

| Script | Target |
|---|---|
| `verify_benchmark.py` | Benchmark workflow execution |
| `verify_circuit_breakers.py` | Circuit breaker pattern implementation |
| `verify_cleaning.py` | Data cleaning pipeline |
| `verify_discovery.py` | Service discovery subsystem |
| `verify_ml.py` | Machine learning pipeline |
| `verify_observability.py` | Observability stack (metrics, logging, tracing) |
| `verify_operational.py` | Operational workflows (anomaly detection, sentiment, etc.) |
| `verify_vault.py` | HashiCorp Vault secrets integration |

### SQL Scripts (`scripts/sql/`)

| Script | Description |
|---|---|
| `init-db.sql` | Database initialization DDL |

### Example Scripts (`scripts/examples/`)

| Script | Description |
|---|---|
| `example_compras_publicas.py` | Scraping example for public procurement data |
| `example_mcp_deep_archive.py` | MCP tool usage for deep archival scraping |
| `example_search_ai.py` | AI-powered search example |
| `patiotuerca_crawl.py` | Web crawling example for PatioTuercа site |

---

## Dependencies

### Dashboard
- **Lit** — Web Components framework
- **Vite** — Build tool and dev server
- **Bun** — JavaScript runtime and package manager
- **Tailwind (via @twind/core)** — Utility-first CSS
- **nginx** — Production serving

### Scripts
- **Python** — All verification and ops scripts
- **Bash** — Dev and wait scripts
- **SpiceDB** — Authorization schema deployment
- **HashiCorp Vault** — Secrets verification
