"""
Voyant Temporal Worker

Main entrypoint for the Temporal worker process.
Registers all workflows and activities and listens on the configured task queue.
"""
import asyncio
import logging
import signal
from concurrent.futures import ThreadPoolExecutor

from temporalio.worker import Worker

from voyant.core.config import get_settings
from voyant.core.temporal_client import get_temporal_client

from voyant.workflows.ingest_workflow import IngestDataWorkflow
from voyant.workflows.profile_workflow import ProfileWorkflow
from voyant.workflows.analyze_workflow import AnalyzeWorkflow
from voyant.activities.ingest_activities import IngestActivities
from voyant.activities.profile_activities import ProfileActivities
from voyant.activities.analysis_activities import AnalysisActivities
from voyant.activities.generation_activities import GenerationActivities
from voyant.activities.kpi_activities import KPIActivities
from voyant.workflows.benchmark_workflow import BenchmarkBrandWorkflow
from voyant.activities.stats_activities import StatsActivities
from voyant.activities.ml_activities import MLActivities
from voyant.activities.discovery_activities import DiscoveryActivities
from voyant.activities.operational_activities import OperationalActivities
from voyant.workflows.operational_workflows import (
    DetectAnomaliesWorkflow,
    AnalyzeSentimentWorkflow,
    FixDataQualityWorkflow
)
from voyant.workflows.segmentation_workflow import SegmentCustomersWorkflow
from voyant.workflows.regression_workflow import LinearRegressionWorkflow

# DataScraper Module
from voyant.scraper.workflow import ScrapeWorkflow
from voyant.scraper.activities import ScrapeActivities

from voyant.core.monitoring import MetricsRegistry
from voyant.core.interceptors import MetricsInterceptor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("voyant.worker")

async def run_worker():
    """Run the Temporal worker."""
    settings = get_settings()
    
    # 0. Start Metrics Server
    metrics = MetricsRegistry()
    metrics.start_server(port=9090)
    
    # 1. Connect to Temporal
    try:
        client = await get_temporal_client()
    except Exception as e:
        logger.critical(f"Failed to start worker: {e}")
        return

    # 2. Define Workflows and Activities
    workflows = [
        IngestDataWorkflow, 
        ProfileWorkflow,
        AnalyzeWorkflow,
        BenchmarkBrandWorkflow,
        DetectAnomaliesWorkflow,
        AnalyzeSentimentWorkflow,
        FixDataQualityWorkflow,
        SegmentCustomersWorkflow,
        LinearRegressionWorkflow,
        ScrapeWorkflow,  # NEW: DataScraper workflow
    ]
    activities = [
        IngestActivities().run_ingestion, 
        IngestActivities().sync_airbyte,
        ProfileActivities().profile_data,
        AnalysisActivities().fetch_sample,
        AnalysisActivities().run_analyzers,
        GenerationActivities().run_generators,
        KPIActivities().run_kpis,
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
        # NEW: DataScraper activities
        ScrapeActivities().fetch_page,
        ScrapeActivities().extract_with_llm,
        ScrapeActivities().extract_basic,
        ScrapeActivities().process_ocr,
        ScrapeActivities().process_media,
        ScrapeActivities().store_artifact,
        ScrapeActivities().finalize_job,
    ]
    
    task_queue = settings.temporal_task_queue
    logger.info(f"Starting worker on queue: {task_queue}")

    # 3. Create Worker
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=workflows,
        activities=activities,
        interceptors=[MetricsInterceptor()]
    )

    # 4. Handle Shutdown Signals
    stop_event = asyncio.Event()

    def handle_signal():
        logger.info("Shutdown signal received...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    # 5. Run Worker
    try:
        await worker.run()
    except asyncio.CancelledError:
        logger.info("Worker cancelled.")
    except Exception as e:
        logger.error(f"Worker crashed: {e}")
    finally:
        logger.info("Worker shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        pass
