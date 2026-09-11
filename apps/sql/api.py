import logging
import uuid
from typing import Any

from ninja import Field, Router, Schema
from ninja.errors import HttpError

from admin.common.messages import get_message
from apps.core.api_utils import auth_guard
from apps.core.lib.trino import get_trino_client
from apps.core.security.auth import get_optional_user, require_permission

logger = logging.getLogger(__name__)
sql_router = Router(tags=["sql"], auth=require_permission("execute:sql"))


# ---------------------------------------------------------------------------
# Saved-Query schemas
# ---------------------------------------------------------------------------


class SavedQueryIn(Schema):
    """Payload for creating / updating a saved query."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("", description="Optional description")
    query_text: str = Field(..., min_length=1)
    language: str = Field("sql")
    parameters: dict[str, Any] | None = Field(default=dict)
    is_public: bool = Field(False)


class SavedQueryOut(Schema):
    """Representation of a saved query returned to the client."""

    id: str
    name: str
    description: str
    query_text: str
    language: str
    parameters: dict[str, Any] | None
    is_public: bool
    shared_with: list[str] = Field(default_factory=list)
    created_by: str
    created_at: Any
    updated_at: Any


class ShareRequest(Schema):
    """Payload for sharing a saved query with users or a workspace."""

    workspace_id: str | None = None
    user_ids: list[str] = Field(default_factory=list)
    message: str = ""


# ---------------------------------------------------------------------------
# Saved-Query CRUD endpoints
# ---------------------------------------------------------------------------


def _user_id(request) -> str:
    """Return the current user's id string (falls back to 'anonymous')."""
    user = get_optional_user(request)
    return user.user_id if user else "anonymous"


@sql_router.get(
    "/saved",
    response=list[SavedQueryOut],
    summary="List Saved Queries",
    auth=auth_guard,
)
def list_saved_queries(request):
    """Return saved queries belonging to the current user, shared with them, or public."""
    from django.db.models import Q

    from apps.sql.models import SavedQuery

    uid = _user_id(request)
    qs = SavedQuery.objects.filter(
        Q(created_by=uid) | Q(is_public=True) | Q(shared_with__contains=uid)
    )
    return [
        SavedQueryOut(
            id=str(q.id),
            name=q.name,
            description=q.description,
            query_text=q.query_text,
            language=q.language,
            parameters=q.parameters,
            is_public=q.is_public,
            shared_with=q.shared_with or [],
            created_by=q.created_by,
            created_at=q.created_at,
            updated_at=q.updated_at,
        )
        for q in qs
    ]


@sql_router.post(
    "/saved",
    response=SavedQueryOut,
    summary="Save a Query",
    auth=auth_guard,
)
def create_saved_query(request, payload: SavedQueryIn):
    """Persist a new saved query."""
    from apps.sql.models import SavedQuery

    uid = _user_id(request)
    user = get_optional_user(request)
    tenant_id = getattr(user, "tenant_id", "default") if user else "default"
    realm = getattr(user, "realm", "default") if user else "default"

    sq = SavedQuery.objects.create(
        name=payload.name,
        description=payload.description,
        query_text=payload.query_text,
        language=payload.language,
        parameters=payload.parameters,
        is_public=payload.is_public,
        created_by=uid,
        tenant_id=tenant_id,
        realm=realm,
    )
    return SavedQueryOut(
        id=str(sq.id),
        name=sq.name,
        description=sq.description,
        query_text=sq.query_text,
        language=sq.language,
        parameters=sq.parameters,
        is_public=sq.is_public,
        created_by=sq.created_by,
        created_at=sq.created_at,
        updated_at=sq.updated_at,
    )


@sql_router.get(
    "/saved/{query_id}",
    response=SavedQueryOut,
    summary="Get Saved Query",
    auth=auth_guard,
)
def get_saved_query(request, query_id: str):
    """Retrieve a single saved query by id."""
    from apps.sql.models import SavedQuery

    uid = _user_id(request)
    try:
        sq = SavedQuery.objects.get(
            id=uuid.UUID(query_id),
        )
    except SavedQuery.DoesNotExist:
        raise HttpError(404, get_message("ERR_NOT_FOUND", resource="saved query"))
    except ValueError:
        raise HttpError(400, "Invalid query id")

    if not sq.is_public and sq.created_by != uid:
        raise HttpError(404, get_message("ERR_NOT_FOUND", resource="saved query"))

    return SavedQueryOut(
        id=str(sq.id),
        name=sq.name,
        description=sq.description,
        query_text=sq.query_text,
        language=sq.language,
        parameters=sq.parameters,
        is_public=sq.is_public,
        created_by=sq.created_by,
        created_at=sq.created_at,
        updated_at=sq.updated_at,
    )


@sql_router.put(
    "/saved/{query_id}",
    response=SavedQueryOut,
    summary="Update Saved Query",
    auth=auth_guard,
)
def update_saved_query(request, query_id: str, payload: SavedQueryIn):
    """Update an existing saved query (owner only)."""
    from apps.sql.models import SavedQuery

    uid = _user_id(request)
    try:
        sq = SavedQuery.objects.get(
            id=uuid.UUID(query_id),
            created_by=uid,
        )
    except SavedQuery.DoesNotExist:
        raise HttpError(404, get_message("ERR_NOT_FOUND", resource="saved query"))
    except ValueError:
        raise HttpError(400, "Invalid query id")

    for field in ("name", "description", "query_text", "language", "parameters", "is_public"):
        setattr(sq, field, getattr(payload, field))
    sq.save()

    return SavedQueryOut(
        id=str(sq.id),
        name=sq.name,
        description=sq.description,
        query_text=sq.query_text,
        language=sq.language,
        parameters=sq.parameters,
        is_public=sq.is_public,
        created_by=sq.created_by,
        created_at=sq.created_at,
        updated_at=sq.updated_at,
    )


@sql_router.delete(
    "/saved/{query_id}",
    response={204: None},
    summary="Delete Saved Query",
    auth=auth_guard,
)
def delete_saved_query(request, query_id: str):
    """Delete a saved query (owner only)."""
    from apps.sql.models import SavedQuery

    uid = _user_id(request)
    try:
        sq = SavedQuery.objects.get(
            id=uuid.UUID(query_id),
            created_by=uid,
        )
    except SavedQuery.DoesNotExist:
        raise HttpError(404, get_message("ERR_NOT_FOUND", resource="saved query"))
    except ValueError:
        raise HttpError(400, "Invalid query id")

    sq.delete()
    return 204, None


@sql_router.post(
    "/saved/{query_id}/share",
    response=dict[str, Any],
    summary="Share Saved Query",
    auth=auth_guard,
)
def share_saved_query(request, query_id: str, payload: ShareRequest):
    """Share a saved query with specific users or make it public via workspace."""
    from apps.sql.models import SavedQuery

    uid = _user_id(request)
    try:
        sq = SavedQuery.objects.get(id=uuid.UUID(query_id), created_by=uid)
    except SavedQuery.DoesNotExist:
        raise HttpError(404, get_message("ERR_NOT_FOUND", resource="saved query"))
    except ValueError:
        raise HttpError(400, "Invalid query id")

    updated_fields: list[str] = []
    shared_with = list(sq.shared_with or [])

    if payload.user_ids:
        for user_id in payload.user_ids:
            if user_id not in shared_with:
                shared_with.append(user_id)
        sq.shared_with = shared_with
        updated_fields.append("shared_with")

    if payload.workspace_id:
        sq.is_public = True
        updated_fields.append("is_public")

    if updated_fields:
        sq.save(update_fields=updated_fields)

    return {
        "status": "shared",
        "query_id": str(sq.id),
        "shared_with": sq.shared_with,
        "is_public": sq.is_public,
        "workspace_id": payload.workspace_id,
    }


class SqlRequest(Schema):
    """Request schema for executing an ad-hoc SQL query."""

    sql: str = Field(
        ...,
        description="The SQL query string to execute. Only SELECT queries are permitted.",
    )
    limit: int = Field(
        1000,
        ge=1,
        le=10000,
        description="The maximum number of rows to return from the query.",
    )
    parameters: dict[str, Any] | None = Field(
        None,
        description=(
            "Optional parameters to pass to the SQL query (e.g., for parameterized queries)."
        ),
    )


class SqlResponse(Schema):
    """Response schema for the result of an executed SQL query."""

    columns: list[str] = Field(
        ..., description="A list of column names returned by the query."
    )
    rows: list[list[Any]] = Field(
        ...,
        description="A list of lists, where each inner list represents a row of data.",
    )
    row_count: int = Field(..., description="The total number of rows returned.")
    truncated: bool = Field(
        ...,
        description="True if the result set was truncated due to the specified limit.",
    )
    execution_time_ms: int = Field(
        ..., description="The time taken to execute the query in milliseconds."
    )
    query_id: str | None = Field(
        None, description="The unique ID assigned to the query by the Trino engine."
    )


@sql_router.post(
    "/query", response=SqlResponse, summary="Execute Ad-Hoc SQL Query", auth=auth_guard
)
def execute_sql(request, payload: SqlRequest):
    """
    Executes an ad-hoc SQL query against the Trino engine for the current tenant.

    This endpoint strictly enforces a read-only policy via the underlying `TrinoClient`
    to prevent any data modification or destructive operations.
    """
    # Security: Tenant validation and SQL query safety are handled by underlying TrinoClient.
    try:
        client = get_trino_client()
        result = client.execute(
            payload.sql, limit=payload.limit, parameters=payload.parameters
        )
        return SqlResponse(
            columns=result.columns,
            rows=result.rows,
            row_count=result.row_count,
            truncated=result.truncated,
            execution_time_ms=result.execution_time_ms,
            query_id=result.query_id,
        )
    except ValueError as exc:
        raise HttpError(400, get_message("ERR_VALIDATION", error=str(exc))) from exc
    except RuntimeError as exc:
        raise HttpError(503, get_message("ERR_SYSTEM", error=str(exc))) from exc
    except Exception as exc:
        logger.exception("SQL execution failed")
        raise HttpError(500, get_message("ERR_SQL_INVALID", error=str(exc))) from exc


@sql_router.get(
    "/tables",
    response=dict[str, Any],
    summary="List Available Tables",
    auth=auth_guard,
)
def list_tables(request, schema: str | None = None):
    """
    Retrieves a list of all tables accessible via the Trino engine for the current tenant.
    """
    try:
        client = get_trino_client()
        tables = client.get_tables(schema)
        return {"tables": tables, "schema": schema or client.schema}
    except Exception as exc:
        logger.exception("Failed to list tables")
        raise HttpError(500, get_message("ERR_SQL_TABLES", error=str(exc))) from exc


@sql_router.get(
    "/tables/{table}/columns",
    response=dict[str, Any],
    summary="Get Table Columns",
    auth=auth_guard,
)
def get_columns(request, table: str, schema: str | None = None):
    """
    Retrieves the column details for a specific table accessible via the Trino engine.
    """
    try:
        client = get_trino_client()
        columns = client.get_columns(table, schema)
        return {"table": table, "columns": columns}
    except Exception as exc:
        logger.exception("Failed to get columns for table '%s'", table)
        raise HttpError(
            500, get_message("ERR_SQL_COLUMNS", table=table, error=str(exc))
        ) from exc
