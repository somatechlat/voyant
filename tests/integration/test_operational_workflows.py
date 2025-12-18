
import pytest
import os
import uuid
import logging
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from datetime import timedelta
from voyant.workflows.operational_workflows import DetectAnomaliesWorkflow
from voyant.activities.operational_activities import OperationalActivities
from voyant.core.ml_primitives import SKLEARN_AVAILABLE
import concurrent.futures

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
async def temporal_client_fixture():
    """
    Fixture that returns a (client, worker_handle) tuple.
    """
    # If TEMPORAL_HOST is set, we connect to real cluster (e.g. localhost:45233)
    # Otherwise we use the Time-Skipping Mock environment
    host = os.environ.get("TEMPORAL_HOST")
    namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
    
    if host:
        # REAL INFRASTRUCTURE (VIBE Compliant)
        logger.info(f"Connecting to REAL INFRASTRUCTURE at {host} (namespace: {namespace})")
        client = await Client.connect(host, namespace=namespace)
        yield client, None # No env to shutdown
    else:
        logger.info("Starting ephemeral TestEnvironment (Fake Infra)")
        async with await WorkflowEnvironment.start_time_skipping() as env:
            yield env.client, env

@pytest.mark.asyncio
@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
async def test_detect_anomalies_workflow_integration(temporal_client_fixture):
    """
    Test the full DetectAnomaliesWorkflow with real activity execution.
    Supports both Real Infra (Docker) and TestEnvironment.
    """
    client, env_handle = temporal_client_fixture
    activities = OperationalActivities()
    
    task_queue = f"test-queue-{uuid.uuid4()}" # Unique queue to avoid collision in real infra

    # Start Worker (needed for both real and test env to execute the code under test)
    # Even with real server, we need a local worker to run the Activity code we just modified
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[DetectAnomaliesWorkflow],
            activities=[activities.detect_anomalies],
            activity_executor=executor,
        ):
            # 1. Prepare Data
            data = [{"val": 10} for _ in range(20)] + [{"val": 1000}]
            
            # 2. Execute Workflow
            # Note: In real infra, wait for result might take longer
            logger.info(f"Executing workflow on queue {task_queue}")
            result = await client.execute_workflow(
                DetectAnomaliesWorkflow.run,
                {"data": data, "contamination": 0.1},
                id=f"test-anomaly-{uuid.uuid4()}",
                task_queue=task_queue,
            )
            
            # 3. Verify Results
            assert result is not None
            assert result["total_records"] == 21
            assert result["anomaly_count"] >= 1
            anomalies = result["anomalies"]
            assert any(r["val"] == 1000 for r in anomalies)

@pytest.mark.asyncio
@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
async def test_detect_anomalies_workflow_empty(temporal_client_fixture):
    """Test workflow behavior with empty data."""
    client, env_handle = temporal_client_fixture
    activities = OperationalActivities()
    task_queue = f"test-queue-{uuid.uuid4()}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[DetectAnomaliesWorkflow],
            activities=[activities.detect_anomalies],
            activity_executor=executor,
        ):
            with pytest.raises(Exception):
                await client.execute_workflow(
                    DetectAnomaliesWorkflow.run,
                    {"data": []},
                    id=f"test-anomaly-empty-{uuid.uuid4()}",
                    task_queue=task_queue,
                )
