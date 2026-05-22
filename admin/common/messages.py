"""
Centralized Messages & I18N Registry for Voyant.
Adheres to Vibe Coding Rule 11.
"""

from typing import Any, Dict

MESSAGES: Dict[str, str] = {
    # Core / Auth
    "ERR_AUTH_EXPIRED": "Authentication token has expired.",
    "ERR_AUTH_INVALID": "Invalid authentication token: {error}.",
    "ERR_AUTH_SIGNING_KEY": "Invalid authentication token: signing key not found.",
    "ERR_AUTH_MISSING": "Authentication required: No Bearer token provided.",
    "ERR_AUTH_DENIED_ROLE": "Access denied: Role '{role}' required.",
    "ERR_AUTH_DENIED_PERMISSION": "Access denied: Permission '{permission}' required.",
    "ERR_AUTH_KEYCLOAK_UNAVAILABLE": "Authentication service unavailable.",
    "ERR_AUTH_INTERNAL": "Authentication failed due to an internal error.",
    "ERR_AUTH_CROSS_REALM": "Authentication failed: cross-realm token rejected.",
    "ERR_AUTH_DENIED_REALM": "Access denied: Realm '{realm}' required.",
    "ERR_POLICY_INVALID": "Invalid policy context: {error}",
    "ERR_POLICY_DENIED": "Access denied by policy.",
    "ERR_POLICY_UNAVAILABLE": "Policy engine unavailable: {error}",
    # SQL / Trino
    "ERR_SQL_INVALID": "Query failed due to internal error: {error}",
    "ERR_SQL_TABLES": "Failed to list tables: {error}",
    "ERR_SQL_COLUMNS": "Failed to get columns for table '{table}': {error}",
    "ERR_TRINO_KEYWORD": "Forbidden SQL keyword detected: '{kw}'",
    # Search / Vector
    "ERR_SEARCH_EMBEDDING": "Failed to extract embedding from query",
    "ERR_SEARCH_INVALID": "Invalid query: {error}",
    "ERR_SEARCH_FAILED": "Search failed: {error}",
    "ERR_INDEX_EMBEDDING": "Failed to extract embedding from text",
    "ERR_INDEX_INVALID": "Invalid request: {error}",
    "ERR_INDEX_FAILED": "Indexing failed: {error}",
    "ERR_ITEM_NOT_FOUND": "Item not found: {item_id}",
    "ERR_ITEM_DENIED": "Access denied: item belongs to different tenant",
    "ERR_DELETE_FAILED": "Deletion failed: {error}",
    "ERR_RETRIEVAL_FAILED": "Retrieval failed: {error}",
    # Workflows / Jobs
    "ERR_JOB_NOT_FOUND": "Job {job_id} not found",
    "ERR_JOB_STATE": "Job {job_id} cannot be cancelled (status: {status})",
    "ERR_JOB_CANCEL_FAILED": "Failed to cancel job: {error}",
    "ERR_ARTIFACT_NOT_FOUND": "Artifact not found",
    "ERR_STORAGE_UNAVAILABLE": "Storage unavailable",
    "ERR_ARTIFACT_DOWNLOAD": "Artifact download failed: {error}",
    "ERR_PRESET_NOT_FOUND": "Preset not found",
    "ERR_KPI_TEMPLATE_NOT_FOUND": "KPI template not found",
    # Ingestion
    "ERR_SOURCE_NOT_FOUND": "Source {source_id} not found",
    "ERR_INGESTION_START_FAILED": "Failed to start ingestion: {error}",
    "ERR_AIRBYTE_UNSUPPORTED": "Unsupported HTTP method: {method}",
    # Discovery
    "ERR_ACCESS_DENIED": "Access to this resource is denied.",
    "ERR_SERVICE_REGISTER_FAILED": "Failed to register service: {error}",
    "ERR_SERVICE_LIST_FAILED": "Failed to list services: {error}",
    "ERR_SERVICE_NOT_FOUND": "Service not found",
    "ERR_SERVICE_RETR_FAILED": "Failed to retrieve service: {error}",
    "ERR_SCAN_FAILED": "Scan failed: {error}",
    "ERR_SPEC_FETCH_FAILED": "Failed to fetch specification: {error}",
    "ERR_SPEC_INVALID": "Invalid API specification format: {error}",
    # Governance
    "ERR_SCHEMA_NOT_FOUND": "Schema not found",
    "ERR_DATAHUB_UNAVAILABLE": "DataHub unavailable",
    "ERR_DATAHUB_QUERY_FAILED": "DataHub query failed",
    "ERR_INVALID_TIER": "Invalid tier: {tier}",
    # Validation Generic
    "ERR_VALIDATION": "Validation error: {error}",
    "ERR_SYSTEM": "System error: {error}",
    # Fallback
    "ERR_UNKNOWN": "An unexpected error occurred.",
}


def get_message(code: str, **kwargs: Any) -> str:
    """
    Retrieve an i18n-ready message string by code and interpolate arguments.
    """
    template = MESSAGES.get(code, code)
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
