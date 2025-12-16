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
from voyant.activities.ingest_activities import IngestActivities
from voyant.workflows.benchmark_workflow import BenchmarkBrandWorkflow
from voyant.activities.stats_activities import StatsActivities

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("voyant.worker")

async def run_worker():
    """Run the Temporal worker."""
    settings = get_settings()
    
    # 1. Connect to Temporal
    try:
        client = await get_temporal_client()
    except Exception as e:
        logger.critical(f"Failed to start worker: {e}")
        return

    # 2. Define Workflows and Activities
    workflows = [IngestDataWorkflow, BenchmarkBrandWorkflow]
    activities = [
        IngestActivities().run_ingestion, 
        IngestActivities().sync_airbyte,
        StatsActivities().calculate_market_share,
        StatsActivities().perform_hypothesis_test,
        StatsActivities().describe_distribution,
        StatsActivities().calculate_correlation,
        StatsActivities().fit_distribution
    ]
    
    task_queue = settings.temporal_task_queue
    logger.info(f"Starting worker listening on queue: '{task_queue}'")

    # 3. Create Worker
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=workflows,
        activities=activities,
        # Optimize for production
        max_concurrent_activities=100,
        max_concurrent_workflow_task_executions=50,
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
