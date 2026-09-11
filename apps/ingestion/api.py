"""
Ingestion API Endpoints.

Provides REST endpoints for managing Airbyte source/destination provisioning
and data ingestion operations.
"""

from __future__ import annotations

import logging
from typing import Any

from ninja import Field, Router, Schema
from ninja.errors import HttpError

from admin.common.messages import get_message
from apps.core.api_utils import apply_policy, run_async
from apps.core.config import get_settings
from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission
from apps.discovery.models import Source

logger = logging.getLogger(__name__)
settings = get_settings()

ingestion_router = Router(tags=["ingestion"], auth=require_permission("read:*"))


# =============================================================================
# Schemas
# =============================================================================


class ConnectSourceRequest(Schema):
    """Request to provision an Airbyte source connector."""

    source_id: str = Field(..., description="Voyant source ID from discovery")
    source_definition_id: str = Field(
        ..., description="Airbyte source definition (connector) ID"
    )
    connection_config: dict[str, Any] = Field(
        ..., description="Source-specific configuration (host, port, auth, etc.)"
    )
    destination_definition_id: str | None = Field(
        None, description="Optional Airbyte destination definition ID"
    )
    destination_config: dict[str, Any] | None = Field(
        None, description="Optional destination-specific configuration"
    )


class ConnectSourceResponse(Schema):
    """Response after provisioning an Airbyte source."""

    source_id: str
    airbyte_source_id: str
    status: str
    airbyte_destination_id: str | None = None
    destination_status: str | None = None


class ProvisionDestinationRequest(Schema):
    """Request to provision an Airbyte destination connector."""

    workspace_id: str = Field("default", description="Airbyte workspace / tenant ID")
    destination_definition_id: str = Field(
        ..., description="Airbyte destination definition ID"
    )
    name: str = Field(..., description="Human-readable destination name")
    connection_config: dict[str, Any] = Field(
        ..., description="Destination-specific configuration"
    )


class ProvisionDestinationResponse(Schema):
    """Response after provisioning an Airbyte destination."""

    destination_id: str
    name: str
    workspace_id: str
    destination_definition_id: str
    status: str


# =============================================================================
# Endpoints
# =============================================================================


@ingestion_router.post(
    "/connect",
    response=ConnectSourceResponse,
    auth=require_permission("write:sources"),
)
def connect_source(request, payload: ConnectSourceRequest):
    """
    Provision an Airbyte source (and optionally a destination) for a Voyant source.

    This endpoint wires the Airbyte connect/provision flow:
    1. Validates the source exists and belongs to the tenant.
    2. Provisions the Airbyte source connector.
    3. Optionally provisions a destination and creates a connection.
    4. Updates the Source status to 'connected'.
    """
    tenant_id = get_tenant_id(request)

    # Validate source exists and belongs to this tenant
    source = Source.objects.filter(id=payload.source_id).first()
    if not source:
        raise HttpError(
            404, get_message("ERR_SOURCE_NOT_FOUND", source_id=payload.source_id)
        )
    if source.tenant_id != tenant_id:
        raise HttpError(403, get_message("ERR_ACCESS_DENIED"))

    apply_policy(
        "connect_source",
        f"voyant connect source_id={payload.source_id}",
        {"source_id": payload.source_id, "tenant_id": tenant_id},
    )

    try:
        from apps.ingestion.lib.airbyte_client import get_airbyte_client

        client = get_airbyte_client()

        # Provision the source
        source_result = run_async(
            client.connect_source,
            workspace_id=tenant_id,
            source_definition_id=payload.source_definition_id,
            name=source.name,
            connection_config=payload.connection_config,
        )

        airbyte_source_id = source_result.get("source_id", "")

        response = ConnectSourceResponse(
            source_id=payload.source_id,
            airbyte_source_id=airbyte_source_id,
            status="connected",
        )

        # Optionally provision destination
        if payload.destination_definition_id:
            dest_config = payload.destination_config or {}
            dest_result = run_async(
                client.provision_destination,
                workspace_id=tenant_id,
                destination_definition_id=payload.destination_definition_id,
                name=f"dest-{source.name}",
                connection_config=dest_config,
            )
            response.airbyte_destination_id = dest_result.get("destination_id", "")
            response.destination_status = "provisioned"

        # Update source status
        source.status = "connected"
        source.save(update_fields=["status"])

        logger.info(
            f"Source {payload.source_id} connected via Airbyte: "
            f"airbyte_source_id={airbyte_source_id}"
        )

        return response

    except Exception as exc:
        logger.exception(f"Failed to connect source {payload.source_id}")
        source.status = "error"
        source.save(update_fields=["status"])
        raise HttpError(500, get_message("ERR_SYSTEM", error=str(exc))) from exc


@ingestion_router.post(
    "/provision-destination",
    response=ProvisionDestinationResponse,
    auth=require_permission("write:sources"),
)
def provision_destination(request, payload: ProvisionDestinationRequest):
    """
    Provision a standalone Airbyte destination connector.

    Creates a destination in Airbyte (e.g. DuckDB, Postgres) that can be
    used as a target for data synchronization connections.
    """
    tenant_id = get_tenant_id(request)

    apply_policy(
        "provision_destination",
        f"voyant provision destination name={payload.name}",
        {"tenant_id": tenant_id},
    )

    try:
        from apps.ingestion.lib.airbyte_client import get_airbyte_client

        client = get_airbyte_client()

        result = run_async(
            client.provision_destination,
            workspace_id=payload.workspace_id,
            destination_definition_id=payload.destination_definition_id,
            name=payload.name,
            connection_config=payload.connection_config,
        )

        return ProvisionDestinationResponse(
            destination_id=result.get("destination_id", ""),
            name=result.get("name", payload.name),
            workspace_id=result.get("workspace_id", payload.workspace_id),
            destination_definition_id=result.get(
                "destination_definition_id", payload.destination_definition_id
            ),
            status=result.get("status", "provisioned"),
        )

    except Exception as exc:
        logger.exception("Failed to provision destination")
        raise HttpError(500, get_message("ERR_SYSTEM", error=str(exc))) from exc


# =============================================================================
# CDC (Change Data Capture) Schemas
# =============================================================================


class CDCStartRequest(Schema):
    """Request to start CDC for a source."""

    source_id: str = Field(..., description="Voyant source ID")
    connection_string: str = Field(
        ..., description="PostgreSQL connection string for the source database"
    )
    replication_slot: str = Field(
        "voyant_cdc_slot", description="Name of the replication slot"
    )
    publication_name: str = Field(
        "voyant_cdc_pub", description="Name of the publication"
    )
    tables: list[str] = Field(
        default_factory=list, description="Tables to monitor (empty = all)"
    )
    batch_size: int = Field(1000, description="Max events per processing batch")
    poll_interval: float = Field(1.0, description="Seconds between idle polls")


class CDCStartResponse(Schema):
    """Response after starting CDC."""

    cdc_connection_id: str
    source_id: str
    status: str
    replication_slot: str
    publication_name: str


class CDCStopRequest(Schema):
    """Request to stop a running CDC stream."""

    cdc_connection_id: str = Field(..., description="CDC connection ID to stop")


class CDCStopResponse(Schema):
    """Response after stopping CDC."""

    cdc_connection_id: str
    status: str


class CDCStatusResponse(Schema):
    """Current CDC connection status."""

    cdc_connection_id: str
    source_id: str
    status: str
    replication_slot: str
    publication_name: str
    last_lsn: str
    last_sync_at: str | None
    total_events: int
    error_message: str


class CDCEventSchema(Schema):
    """A single CDC change event."""

    id: str
    operation: str
    table_name: str
    schema_name: str
    primary_key: Any | None = None
    before_data: dict[str, Any] | None = None
    after_data: dict[str, Any] | None = None
    lsn: str
    timestamp: str
    created_at: str


class CDCEventListResponse(Schema):
    """Paginated list of CDC change events."""

    events: list[CDCEventSchema]
    total: int
    cdc_connection_id: str


# =============================================================================
# CDC Endpoints
# =============================================================================


@ingestion_router.post(
    "/cdc/start",
    response=CDCStartResponse,
    auth=require_permission("write:sources"),
)
def start_cdc(request, payload: CDCStartRequest):
    """
    Start a CDC (Change Data Capture) stream for a PostgreSQL source.

    Creates a CDCConnection record, sets up the replication slot and
    publication, and launches a Temporal workflow to stream changes.
    """
    tenant_id = get_tenant_id(request)

    source = Source.objects.filter(id=payload.source_id).first()
    if not source:
        raise HttpError(
            404, get_message("ERR_SOURCE_NOT_FOUND", source_id=payload.source_id)
        )
    if source.tenant_id != tenant_id:
        raise HttpError(403, get_message("ERR_ACCESS_DENIED"))

    apply_policy(
        "start_cdc",
        f"voyant cdc start source_id={payload.source_id}",
        {"source_id": payload.source_id, "tenant_id": tenant_id},
    )

    try:
        from apps.ingestion.models import CDCConnection

        # Check for an existing active CDC connection.
        existing = CDCConnection.objects.filter(
            source_id=payload.source_id,
            status__in=["created", "starting", "running"],
            tenant_id=tenant_id,
        ).first()
        if existing:
            raise HttpError(
                409,
                f"CDC already active for source {payload.source_id}: "
                f"connection {existing.id} ({existing.status})",
            )

        # Create the CDC connection record.
        cdc_conn = CDCConnection.objects.create(
            source_id=payload.source_id,
            replication_slot=payload.replication_slot,
            publication_name=payload.publication_name,
            tables=payload.tables,
            status="starting",
            config={
                "connection_string": payload.connection_string,
                "batch_size": payload.batch_size,
                "poll_interval": payload.poll_interval,
            },
            tenant_id=tenant_id,
        )

        # Launch the Temporal workflow.
        from temporalio.client import Client

        from apps.core.api_utils import run_async

        async def _start_workflow():
            client = await Client.connect("localhost:7233")
            wf = await client.start_workflow(
                "CDCWorkflow",
                {
                    "cdc_connection_id": str(cdc_conn.id),
                    "connection_string": payload.connection_string,
                    "replication_slot": payload.replication_slot,
                    "publication_name": payload.publication_name,
                    "tables": payload.tables,
                    "batch_size": payload.batch_size,
                    "poll_interval": payload.poll_interval,
                    "tenant_id": tenant_id,
                    "source_id": payload.source_id,
                },
                id=f"cdc-{cdc_conn.id}",
                task_queue="voyant-worker",
            )
            return wf.result_run_id

        run_async(_start_workflow)

        cdc_conn.workflow_instance_id = f"cdc-{cdc_conn.id}"
        cdc_conn.save(update_fields=["workflow_instance_id"])

        logger.info(
            "CDC started for source %s: connection=%s, workflow=%s",
            payload.source_id,
            cdc_conn.id,
            cdc_conn.workflow_instance_id,
        )

        return CDCStartResponse(
            cdc_connection_id=str(cdc_conn.id),
            source_id=payload.source_id,
            status="starting",
            replication_slot=payload.replication_slot,
            publication_name=payload.publication_name,
        )

    except HttpError:
        raise
    except Exception as exc:
        logger.exception(f"Failed to start CDC for source {payload.source_id}")
        raise HttpError(500, get_message("ERR_SYSTEM", error=str(exc))) from exc


@ingestion_router.post(
    "/cdc/stop",
    response=CDCStopResponse,
    auth=require_permission("write:sources"),
)
def stop_cdc(request, payload: CDCStopRequest):
    """
    Stop a running CDC stream.

    Cancels the associated Temporal workflow and updates the CDC
    connection status to ``stopped``.
    """
    tenant_id = get_tenant_id(request)

    from apps.ingestion.models import CDCConnection

    cdc_conn = CDCConnection.objects.filter(
        id=payload.cdc_connection_id, tenant_id=tenant_id
    ).first()
    if not cdc_conn:
        raise HttpError(404, f"CDC connection {payload.cdc_connection_id} not found")

    apply_policy(
        "stop_cdc",
        f"voyant cdc stop connection_id={payload.cdc_connection_id}",
        {"cdc_connection_id": payload.cdc_connection_id, "tenant_id": tenant_id},
    )

    try:
        from apps.core.api_utils import run_async

        if cdc_conn.workflow_instance_id:
            async def _cancel_workflow():
                from temporalio.client import Client

                client = await Client.connect("localhost:7233")
                handle = client.get_workflow_handle(cdc_conn.workflow_instance_id)
                await handle.cancel()

            run_async(_cancel_workflow)

        cdc_conn.status = "stopped"
        cdc_conn.save(update_fields=["status"])

        logger.info("CDC stopped for connection %s", payload.cdc_connection_id)

        return CDCStopResponse(
            cdc_connection_id=payload.cdc_connection_id,
            status="stopped",
        )

    except Exception as exc:
        logger.exception(
            f"Failed to stop CDC connection {payload.cdc_connection_id}"
        )
        raise HttpError(500, get_message("ERR_SYSTEM", error=str(exc))) from exc


@ingestion_router.get(
    "/cdc/status",
    response=CDCStatusResponse,
    auth=require_permission("read:*"),
)
def get_cdc_status(request, cdc_connection_id: str):
    """
    Retrieve the current status of a CDC connection.

    Returns the connection status, last LSN watermark, last sync time,
    total events processed, and any error message.
    """
    tenant_id = get_tenant_id(request)

    from apps.ingestion.models import CDCChangeEvent, CDCConnection

    cdc_conn = CDCConnection.objects.filter(
        id=cdc_connection_id, tenant_id=tenant_id
    ).first()
    if not cdc_conn:
        raise HttpError(404, f"CDC connection {cdc_connection_id} not found")

    total_events = CDCChangeEvent.objects.filter(
        connection_id=cdc_connection_id
    ).count()

    return CDCStatusResponse(
        cdc_connection_id=str(cdc_conn.id),
        source_id=str(cdc_conn.source_id),
        status=cdc_conn.status,
        replication_slot=cdc_conn.replication_slot,
        publication_name=cdc_conn.publication_name,
        last_lsn=cdc_conn.last_lsn,
        last_sync_at=cdc_conn.last_sync_at.isoformat() if cdc_conn.last_sync_at else None,
        total_events=total_events,
        error_message=cdc_conn.error_message,
    )


@ingestion_router.get(
    "/cdc/events",
    response=CDCEventListResponse,
    auth=require_permission("read:*"),
)
def list_cdc_events(
    request,
    cdc_connection_id: str,
    table_name: str | None = None,
    operation: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List recent CDC change events for a connection.

    Supports optional filtering by table name and operation type.
    Results are ordered by timestamp descending (most recent first).
    """
    tenant_id = get_tenant_id(request)

    from apps.ingestion.models import CDCChangeEvent, CDCConnection

    cdc_conn = CDCConnection.objects.filter(
        id=cdc_connection_id, tenant_id=tenant_id
    ).first()
    if not cdc_conn:
        raise HttpError(404, f"CDC connection {cdc_connection_id} not found")

    qs = CDCChangeEvent.objects.filter(
        connection_id=cdc_connection_id, tenant_id=tenant_id
    )

    if table_name:
        qs = qs.filter(table_name=table_name)
    if operation:
        qs = qs.filter(operation=operation.upper())

    total = qs.count()
    events_qs = qs[offset : offset + limit]

    events = [
        CDCEventSchema(
            id=str(evt.id),
            operation=evt.operation,
            table_name=evt.table_name,
            schema_name=evt.schema_name,
            primary_key=evt.primary_key,
            before_data=evt.before_data,
            after_data=evt.after_data,
            lsn=evt.lsn,
            timestamp=evt.timestamp.isoformat(),
            created_at=evt.created_at.isoformat(),
        )
        for evt in events_qs
    ]

    return CDCEventListResponse(
        events=events,
        total=total,
        cdc_connection_id=cdc_connection_id,
    )
