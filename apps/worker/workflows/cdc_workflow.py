"""
CDC Workflow: Orchestrates PostgreSQL Change Data Capture via Temporal.

This workflow manages the full lifecycle of a CDC replication stream:
  1. Setup: creates the replication slot and publication if they do not exist.
  2. Main loop: listens for WAL changes, batches them, and processes each batch.
  3. Error handling: retries with exponential backoff on transient failures.
  4. Shutdown: cleanly closes the replication connection.
"""

from datetime import timedelta
from typing import Any

from temporalio import activity, workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError, CancelledError

with workflow.unsafe.imports_passed_through():
    pass


# =============================================================================
# Workflow
# =============================================================================


@workflow.defn
class CDCWorkflow:
    """
    Temporal workflow that drives a PostgreSQL CDC replication stream.

    Parameters (``params`` dict):
        cdc_connection_id: UUID of the ``CDCConnection`` model row.
        connection_string: psycopg2 DSN for the source database.
        replication_slot: Name of the PostgreSQL replication slot.
        publication_name: Name of the PostgreSQL publication.
        tables: List of tables to watch (empty = all).
        batch_size: Max events per processing batch.
        poll_interval: Seconds between idle polls.
        tenant_id: Tenant identifier for event storage.
        source_id: Source identifier.
    """

    @workflow.run
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the CDC workflow.

        The workflow loops indefinitely (until cancelled or until an
        unrecoverable error occurs), processing batches of change events.
        """
        cdc_connection_id = params["cdc_connection_id"]
        workflow.logger.info(f"CDCWorkflow started for connection {cdc_connection_id}")

        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=60),
            maximum_attempts=5,
            non_retryable_error_types=[
                "ValidationError",
                "AuthenticationError",
                "ApplicationError",
            ],
        )

        # ── Phase 1: Setup ──────────────────────────────────────────────
        setup_result = await workflow.execute_activity(
            "setup_replication",
            params,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=2),
                backoff_coefficient=2.0,
                maximum_interval=timedelta(seconds=30),
                maximum_attempts=3,
                non_retryable_error_types=["ValidationError", "ApplicationError"],
            ),
        )

        workflow.logger.info(
            f"CDC replication setup complete: {setup_result}"
        )

        # ── Phase 2: Main loop — stream & process batches ───────────────
        total_events = 0
        batch_count = 0

        try:
            while True:
                # Stream one batch of changes from the replication slot.
                batch_result = await workflow.execute_activity(
                    "stream_changes_batch",
                    {
                        **params,
                        "last_lsn": setup_result.get("last_lsn", ""),
                    },
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=retry_policy,
                    heartbeat_timeout=timedelta(seconds=30),
                )

                events = batch_result.get("events", [])
                if not events:
                    # No new changes — workflow may continue polling via
                    # the activity's own idle sleep, or we can signal
                    # completion for bounded CDC runs.
                    workflow.logger.debug("No new CDC events; sleeping…")
                    workflow.continue_as_new(params)
                    return {
                        "cdc_connection_id": cdc_connection_id,
                        "status": "idle",
                        "total_events": total_events,
                        "batches_processed": batch_count,
                    }

                # Process the batch: persist events and advance the
                # watermark.
                process_result = await workflow.execute_activity(
                    "process_changes",
                    {
                        "cdc_connection_id": cdc_connection_id,
                        "events": [e for e in events],
                        "tenant_id": params.get("tenant_id", ""),
                    },
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=retry_policy,
                )

                last_lsn = process_result.get("last_lsn", "")
                events_processed = process_result.get("events_processed", 0)
                total_events += events_processed
                batch_count += 1

                # Commit the checkpoint (advance watermark).
                await workflow.execute_activity(
                    "commit_checkpoint",
                    {
                        "cdc_connection_id": cdc_connection_id,
                        "last_lsn": last_lsn,
                        "total_events": total_events,
                    },
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=retry_policy,
                )

                # Update params with new LSN for next iteration.
                params["last_lsn"] = last_lsn

                workflow.logger.info(
                    f"CDC batch #{batch_count} processed: "
                    f"{events_processed} events, LSN={last_lsn}"
                )

        except CancelledError:
            workflow.logger.info(
                f"CDCWorkflow cancelled for connection {cdc_connection_id}"
            )
            await workflow.execute_activity(
                "teardown_cdc",
                {"cdc_connection_id": cdc_connection_id},
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
            return {
                "cdc_connection_id": cdc_connection_id,
                "status": "cancelled",
                "total_events": total_events,
                "batches_processed": batch_count,
            }

        except Exception as exc:
            workflow.logger.error(f"CDCWorkflow failed: {exc}")
            await workflow.execute_activity(
                "teardown_cdc",
                {"cdc_connection_id": cdc_connection_id},
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
            raise ApplicationError(f"CDC workflow failed: {exc}") from exc


# =============================================================================
# Activities
# =============================================================================


@activity.defn(name="setup_replication")
async def setup_replication(params: dict[str, Any]) -> dict[str, Any]:
    """
    Create the replication slot and publication if they do not exist.

    Returns:
        Dict with ``slot_created``, ``publication_created``, and ``last_lsn``.
    """
    from apps.ingestion.lib.cdc_service import CDCConfig, PostgreSQLCDCConnector

    config = CDCConfig(
        connection_string=params["connection_string"],
        replication_slot_name=params.get("replication_slot", "voyant_cdc_slot"),
        publication_name=params.get("publication_name", "voyant_cdc_pub"),
        tables=params.get("tables", []),
    )
    connector = PostgreSQLCDCConnector(config)
    result = connector.setup_replication()

    # Mark the CDC connection as running.
    cdc_id = params.get("cdc_connection_id")
    if cdc_id:
        try:

            conn = await _aget_cdc_connection(cdc_id)
            if conn:
                conn.status = "running"
                conn.replication_slot = config.replication_slot_name
                conn.publication_name = config.publication_name
                conn.error_message = ""
                await _asave_cdc_connection(conn)
        except Exception:  # noqa: BLE001
            activity.logger.warning("Could not update CDCConnection status", exc_info=True)

    result["last_lsn"] = ""
    return result


@activity.defn(name="stream_changes_batch")
async def stream_changes_batch(params: dict[str, Any]) -> dict[str, Any]:
    """
    Connect to the replication slot and stream one batch of changes.

    This activity blocks until a batch of events is available or a
    heartbeat timeout is reached.

    Returns:
        Dict with ``events`` (list of event dicts) and ``lsn``.
    """
    from apps.ingestion.lib.cdc_service import CDCConfig, PostgreSQLCDCConnector

    config = CDCConfig(
        connection_string=params["connection_string"],
        replication_slot_name=params.get("replication_slot", "voyant_cdc_slot"),
        publication_name=params.get("publication_name", "voyant_cdc_pub"),
        tables=params.get("tables", []),
        batch_size=params.get("batch_size", 1000),
        poll_interval=params.get("poll_interval", 1.0),
    )
    connector = PostgreSQLCDCConnector(config)
    connector.connect()

    collected: list[dict[str, Any]] = []
    max_batch = params.get("batch_size", 1000)

    def _on_batch(batch):
        for evt in batch:
            collected.append(evt.to_dict())
        # Stop after first batch
        connector.stop()

    try:
        connector.consume_stream(callback=_on_batch, batch_size=max_batch)
    except Exception:
        activity.logger.warning("stream_changes_batch error", exc_info=True)
    finally:
        connector.disconnect()

    return {"events": collected, "lsn": connector.get_last_lsn() or ""}


@activity.defn(name="process_changes")
async def process_changes(params: dict[str, Any]) -> dict[str, Any]:
    """
    Parse WAL entries and persist them as ``CDCChangeEvent`` rows.

    Returns:
        Dict with ``events_processed`` count and the ``last_lsn``.
    """
    from apps.ingestion.models import CDCChangeEvent

    events = params["events"]
    cdc_connection_id = params["cdc_connection_id"]
    tenant_id = params.get("tenant_id", "")
    last_lsn = ""

    objects = []
    for evt in events:
        objects.append(
            CDCChangeEvent(
                connection_id=cdc_connection_id,
                operation=evt["operation"],
                table_name=evt["table"],
                schema_name=evt["schema"],
                primary_key=evt.get("primary_key"),
                before_data=evt.get("before"),
                after_data=evt.get("after"),
                lsn=evt.get("lsn", ""),
                timestamp=evt["timestamp"],
                tenant_id=tenant_id,
            )
        )
        if evt.get("lsn"):
            last_lsn = evt["lsn"]

    # Bulk-create for efficiency.
    CDCChangeEvent.objects.bulk_create(objects, batch_size=500)

    # Update last_sync_at on the connection.
    if last_lsn:
        try:
            from apps.ingestion.models import CDCConnection

            CDCConnection.objects.filter(id=cdc_connection_id).update(
                last_lsn=last_lsn,
                last_sync_at=_utcnow(),
            )
        except Exception:  # noqa: BLE001
            activity.logger.warning("Could not update CDCConnection watermark", exc_info=True)

    return {"events_processed": len(objects), "last_lsn": last_lsn}


@activity.defn(name="commit_checkpoint")
async def commit_checkpoint(params: dict[str, Any]) -> dict[str, Any]:
    """
    Advance the CDC watermark in the database.

    Returns:
        Dict confirming the checkpoint was committed.
    """
    cdc_id = params["cdc_connection_id"]
    last_lsn = params["last_lsn"]

    from apps.ingestion.models import CDCConnection

    updated = CDCConnection.objects.filter(id=cdc_id).update(last_lsn=last_lsn)
    activity.logger.info(
        f"Checkpoint committed for CDC connection {cdc_id}: LSN={last_lsn}, "
        f"updated={updated}"
    )
    return {"committed": True, "last_lsn": last_lsn}


@activity.defn(name="teardown_cdc")
async def teardown_cdc(params: dict[str, Any]) -> dict[str, Any]:
    """
    Mark the CDC connection as stopped.

    Called on workflow cancellation or unrecoverable failure.
    """
    cdc_id = params["cdc_connection_id"]

    from apps.ingestion.models import CDCConnection

    try:
        CDCConnection.objects.filter(id=cdc_id).update(status="stopped")
    except Exception:  # noqa: BLE001
        activity.logger.warning("Could not update CDCConnection on teardown", exc_info=True)

    activity.logger.info(f"CDC connection {cdc_id} torn down")
    return {"torn_down": True}


# =============================================================================
# Helpers
# =============================================================================


def _utcnow():
    """Return a timezone-aware UTC now timestamp."""
    from django.utils import timezone

    return timezone.now()


async def _aget_cdc_connection(cdc_id: str):
    """Fetch a CDCConnection by primary key (sync ORM wrapped for async)."""
    from apps.ingestion.models import CDCConnection

    return CDCConnection.objects.filter(id=cdc_id).first()


async def _asave_cdc_connection(conn):
    """Save a CDCConnection instance (sync ORM wrapped for async)."""
    conn.save(update_fields=["status", "replication_slot", "publication_name", "error_message"])
