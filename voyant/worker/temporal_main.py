import asyncio
import logging
import os
from temporalio.client import Client
from temporalio.worker import Worker

# Import Workflows and Activities
from voyant.workflows.ingest_workflow import IngestWorkflow
from voyant.activities.ingest_activities import IngestActivities

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_worker():
    temporal_host = os.getenv("TEMPORAL_HOST", "temporal:7233")
    task_queue = os.getenv("TEMPORAL_TASK_QUEUE", "voyant-tasks")
    
    logger.info(f"Connecting to Temporal server at {temporal_host}...")
    
    # Connect to client
    client = await Client.connect(temporal_host)
    
    logger.info(f"Starting worker on queue: {task_queue}")

    # Create worker
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[IngestWorkflow],
        activities=[IngestActivities().run_ingestion],
    )
    
    # Run worker
    await worker.run()

if __name__ == "__main__":
    asyncio.run(run_worker())
