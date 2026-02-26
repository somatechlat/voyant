# Voyant Documentation: Streaming & Workers (`apps/streaming`, `apps/worker`)

## 1. Overview
These modules constitute the asynchronous execution plane of Voyant.
- `apps/worker` houses the Temporal worker process that polls for jobs and executes registered workflows/activities.
- `apps/streaming` provides the Apache Flink integration for continuous, real-time analytics.

## 2. File-by-File Breakdown

### `apps/worker/worker_main.py`
This is the main entry point (`async def main()`) for starting the Temporal worker process.
*   **Startup Sequence:**
    1.  Calls `django.setup()` ensuring that the ORM is fully hydrated before the worker starts polling. This is critical because Temporal workers run in a plain Python process outside of the WSGI/ASGI server.
    2.  Spins up a Prometheus metrics server (`MetricsRegistry().start_server(port=9090)`).
    3.  Connects to the Temporal cluster using `get_temporal_client()`.
*   **Worker Modes & Registration:**
    *   Examines `settings.worker_mode`.
    *   If `mode == "scraper"`, it isolates execution exclusively to `ScrapeWorkflow` and `ScrapeActivities` to prevent sandbox violations from heavier libraries (like ML/Trino).
    *   Otherwise, it registers the massive default suite of workflows (Ingest, Profile, Analyze, Quality, Benchmark, Sentiment, Streaming) and their corresponding activities.
*   **Thread Pooling:** Initializes a bounded `ThreadPoolExecutor` (max 32 or `cpu_count * 5`) for executing synchronous activities safely within Python's execution model.
*   **Execution & Shutdown:** Wraps `worker.run()` with strict signal handling (`SIGINT`, `SIGTERM`) for graceful shutdown of long-running operations.

### `apps/streaming/flink_client.py`
A robust Python wrapper around the Apache Flink JobManager REST API.
*   **`FlinkClient`:** Points to `settings.flink_jobmanager_url`.
*   **Cluster Management (`get_overview`, `list_jobs`):** Synchronous HTTP requests (via `httpx`) to inspect the cluster health and running jobs.
*   **Job Submission (`upload_jar`, `submit_jar`):** Handles the physical upload of pre-compiled JAR files to the Flink cluster and triggers their execution with specific entry classes and arguments, returning the designated `jobid`.

### `apps/streaming/workflow.py`
The Temporal bridge that orchestrates the Flink client.
*   **`StreamingJobWorkflow`:**
    *   Idempotent and stateless ("Orchestrator pattern").
    *   Executes activity `get_cluster_overview` to ensure Flink is healthy.
    *   Executes activity `submit_streaming_job` passing the requested configuration (e.g., source Kafka topic, sink Kafka topic, job type).

## 3. Core Principles Reflected
*   **Strict Isolation:** The `worker_main.py` clearly segregates the `scraper` worker mode from the general analytics worker mode, preventing noisy neighbor problems and ensuring sandbox compatibility.
*   **Orchestration vs. Execution:** The Temporal workflow in `apps/streaming/workflow.py` does not run any heavy lifting itself. It purely delegates to the stateful `FlinkClient` inside isolated, retryable activities.
