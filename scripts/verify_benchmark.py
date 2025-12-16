"""
Verification Script

Triggers the BENCHMARK_MY_BRAND workflow on Temporal.
Requires 'docker-compose up -d temporal'
"""
import asyncio
import logging
from voyant.core.temporal_client import get_temporal_client
from voyant.workflows.benchmark_workflow import BenchmarkBrandWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify")

async def main():
    try:
        client = await get_temporal_client()
        
        logger.info("Triggering BENCHMARK_MY_BRAND...")
        
        handle = await client.start_workflow(
            BenchmarkBrandWorkflow.run,
            {
                "brand_source_id": "src_nike",
                "competitor_source_ids": ["src_adidas", "src_puma"],
                "metric": "revenue"
            },
            id="benchmark-test-001",
            task_queue="voyant-tasks",
        )

        logger.info(f"Workflow started. ID: {handle.id}, RunID: {handle.result_run_id}")
        logger.info("Waiting for result...")
        
        result = await handle.result()
        logger.info(f"Result: {result}")
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
