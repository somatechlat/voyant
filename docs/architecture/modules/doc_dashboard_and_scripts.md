# Voyant Documentation: Frontend Dashboard & Scripts (`dashboard/`, `scripts/`)

## 1. Overview
This module covers the "human-facing" elements of Voyant. These consist of a modern web application for interactive data monitoring, and a suite of Python utility scripts for system verification.

## 2. File-by-File Breakdown

### `dashboard/`
The web user interface. True to **Rule 9 (UI Framework Policy)**, there is absolutely zero Alpine.js in this directory. The entire interface is built using Lit 3 Web Components.

*   **`package.json` & `vite.config.ts`:** Built using `vite` and leverages `lit` and `@lit-labs/router`. Styling is managed using `@twind/core` (Tailwind-in-JS) ensuring scoped styling across Shadow DOMs.
*   **`index.html` & `src/main.ts`:** The entry points. `index.html` sets up standard SaaS tailwind configuration via CDN. `main.ts` mounts the root `<voyant-app-root>` Component using `LitElement`.
*   **`src/components/` (e.g., `saas-infra-card.ts`, `saas-glass-modal.ts`):** Reusable UI elements strictly extending `LitElement`. They utilize Shadow DOM encapsulation and reactive properties `@property()`.
*   **`src/views/` (e.g., `view-login.ts`, `view-voyant-setup.ts`):** Route-level components mapping state to visual layouts, utilizing `@lit-labs/router` for client-side navigation.

### `scripts/`
A collection of operations and verification utilities, focused heavily on confirming Temporal orchestration and system health.

*   **`verify_*.py` (e.g., `verify_benchmark.py`, `verify_ml.py`, `verify_operational.py`):**
    *   These scripts act as standalone Python clients that import `get_temporal_client`.
    *   They are executed manually (e.g., `python scripts/verify_benchmark.py`).
    *   They physically dispatch asynchronous tasks (e.g., `BenchmarkBrandWorkflow.run`) directly to the `"voyant-tasks"` Temporal queue.
    *   They `await handle.result()` blocking until the microservice cluster resolves the requested pipeline block, making them highly effective integration tests.
*   **`init-db.sql`:** The master bootstrapping script for the Postgres database, establishing critical extensions (like `pgcrypto`) required for UUID primary keys and vector support.
*   **`wait-for-stack.sh` & `dev.sh`:** Bash orchestration scripts primarily aimed at local Docker-Compose environment hydration, waiting for Trino and PostgreSQL to accept connections before booting Django.

## 3. Core Principles Reflected
*   **Lit Component Purism:** The dashboard adheres faithfully to the mandate forbidding Alpine.js, maintaining clean encapsulation using standard Web Components.
*   **Verification-by-Execution:** The `scripts` emphasize verifying business logic by physically running the Temporal queues rather than relying solely on mock-driven unit tests.
