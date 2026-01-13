"""
Voyant Temporal Worker: Main Entrypoint for Workflow and Activity Execution.

This module serves as the primary entry point for the Temporal worker process.
It is responsible for:
1.  Initializing the connection to the Temporal cluster.
2.  Registering all defined workflows and activities, making them available for execution.
3.  Starting the worker to poll tasks from a specified task queue.
4.  Handling graceful shutdown signals.

The worker is crucial for executing the business logic orchestrated by Temporal workflows.
"""

import asyncio
import logging
import signal
from concurrent.futures import ThreadPoolExecutor # Unused import, can be removed.

from temporalio.worker import Worker

from voyant.core.config import get_settings
from voyant.core.temporal_client import get_temporal_client

from voyant.workflows.ingest_workflow import IngestDataWorkflow
from voyant.workflows.profile_workflow import ProfileWorkflow
from voyant.workflows.analyze_workflow import AnalyzeWorkflow
from voyant.workflows.quality_workflow import QualityWorkflow
from voyant.activities.ingest_activities import IngestActivities
from voyant.activities.profile_activities import ProfileActivities
from voyant.activities.analysis_activities import AnalysisActivities
from voyant.activities.generation_activities import GenerationActivities
from voyant.activities.kpi_activities import KPIActivities
from voyant.activities.quality_activities import QualityActivities
from voyant.workflows.benchmark_workflow import BenchmarkBrandWorkflow
from voyant.activities.stats_activities import StatsActivities
from voyant.activities.ml_activities import MLActivities
from voyant.activities.discovery_activities import DiscoveryActivities
from voyant.activities.operational_activities import OperationalActivities
from voyant.workflows.operational_workflows import (
    DetectAnomaliesWorkflow,
    AnalyzeSentimentWorkflow,
    FixDataQualityWorkflow,
)
from voyant.workflows.segmentation_workflow import SegmentCustomersWorkflow
from voyant.workflows.regression_workflow import LinearRegressionWorkflow

# DataScraper Module
from voyant.scraper.workflow import ScrapeWorkflow
from voyant.scraper.activities import ScrapeActivities

# Streaming Module (Apache Flink Integration - FR-21)
from voyant.streaming.workflow import StreamingJobWorkflow
from voyant.streaming.activities import StreamingActivities

from voyant.core.monitoring import MetricsRegistry
from voyant.core.interceptors import MetricsInterceptor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("voyant.worker")


async def run_worker():
    """
    Runs the Temporal worker process.

    This function performs the following steps:
    1.  Initializes a Prometheus metrics server for observability.
    2.  Establishes a connection to the Temporal cluster.
    3.  Registers all application workflows and activities with the worker.
    4.  Configures signal handlers for graceful shutdown.
    5.  Starts the worker to poll tasks from the configured task queue.

    Raises:
        Exception: If the worker fails to connect to Temporal or crashes during execution.
    """
    settings = get_settings()

    # 0. Start Metrics Server for Prometheus exposition.
    metrics = MetricsRegistry()
    metrics.start_server(port=9090)

    # 1. Connect to the Temporal Cluster.
    try:
        client = await get_temporal_client()
    except Exception as e:
        logger.critical(f"Failed to connect to Temporal cluster: {e}")
        return

    # 2. Define and Register Workflows and Activities.
    # All workflows and activities must be registered with the worker
    # so Temporal knows how to execute them.
    workflows = [
        IngestDataWorkflow,
        ProfileWorkflow,
        AnalyzeWorkflow,
        QualityWorkflow,
        BenchmarkBrandWorkflow,
        DetectAnomaliesWorkflow,
        AnalyzeSentimentWorkflow,
        FixDataQualityWorkflow,
        SegmentCustomersWorkflow,
        LinearRegressionWorkflow,
        ScrapeWorkflow,
        StreamingJobWorkflow,  # Flink Integration (FR-21)
    ]
    activities = [
        IngestActivities().run_ingestion,
        IngestActivities().sync_airbyte,
        ProfileActivities().profile_data,
        AnalysisActivities().fetch_sample,
        AnalysisActivities().run_analyzers,
        GenerationActivities().run_generators,
        KPIActivities().run_kpis,
        QualityActivities().fetch_sample,
        QualityActivities().run_quality_checks,
        StatsActivities().calculate_market_share,
        StatsActivities().perform_hypothesis_test,
        StatsActivities().describe_distribution,
        StatsActivities().calculate_correlation,
        StatsActivities().fit_distribution,
        MLActivities().cluster_data,
        MLActivities().train_classifier_model,
        MLActivities().forecast_time_series,
        MLActivities().train_regression_model,
        DiscoveryActivities().search_for_apis,
        DiscoveryActivities().scan_spec_url,
        OperationalActivities().detect_anomalies,
        OperationalActivities().analyze_sentiment_batch,
        OperationalActivities().fix_data_quality,
        OperationalActivities().clean_data,
        # DataScraper activities (Pure Execution)
        ScrapeActivities().fetch_page,
        ScrapeActivities().extract_data,
        ScrapeActivities().process_ocr,
        ScrapeActivities().transcribe_media,
        ScrapeActivities().parse_pdf,
        ScrapeActivities().store_artifact,
        ScrapeActivities().finalize_job,
        # Streaming activities (Flink - FR-21)
        StreamingActivities().get_cluster_overview,
        StreamingActivities().list_running_jobs,
        StreamingActivities().submit_streaming_job,
    ]

    task_queue = settings.temporal_task_queue
    logger.info(f"Starting worker and listening on task queue: {task_queue}")

    # 3. Create the Temporal Worker instance.
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=workflows,
        activities=activities,
        interceptors=[MetricsInterceptor()], # Interceptors for cross-cutting concerns like metrics.
    )

    # 4. Handle Shutdown Signals for graceful termination.
    stop_event = asyncio.Event()

    def handle_signal():
        """Callback to set the stop event when a shutdown signal is received."""
        logger.info("Shutdown signal received. Initiating graceful worker shutdown.")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    # 5. Run the Worker, awaiting its completion or a shutdown signal.
    try:
        await worker.run()
    except asyncio.CancelledError:
        logger.info("Temporal worker run was cancelled (e.g., via shutdown signal).")
    except Exception as e:
        logger.critical(f"Temporal worker crashed unexpectedly: {e}", exc_info=True)
    finally:
        logger.info("Temporal worker shutdown complete.")


async def main():
    """
    Main entry point for the Voyant Temporal worker application.

    This function initializes basic logging and runs the asynchronous `run_worker`
    function, handling keyboard interrupts for graceful exit during development.
    """
    try:
        await run_worker()
    except KeyboardInterrupt:
        logger.info("Worker process interrupted by user (Ctrl+C). Exiting.")
