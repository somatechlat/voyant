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
    source_definition_id: str = Field(..., description="Airbyte source definition (connector) ID")
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
    destination_definition_id: str = Field(..., description="Airbyte destination definition ID")
    name: str = Field(..., description="Human-readable destination name")
    connection_config: dict[str, Any] = Field(..., description="Destination-specific configuration")


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
        raise HttpError(404, get_message("ERR_SOURCE_NOT_FOUND", source_id=payload.source_id))
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
