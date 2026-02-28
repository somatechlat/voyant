"""
URI Parser Engine

Translates generic data protocol URIs into localized Airbyte connection configs.
Enforces the Zero Custom Logic rule by eliminating Agent-led database driver programming.
"""

import logging
from typing import Any, Dict
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class URIParser:
    """
    Deconstructs agnostic connection strings (e.g. postgresql://user:pass@host/db)
    to feed dynamically into Temporal/Airbyte sync functions.
    """

    # Maps generic URI schemes to predefined Voyant BUILTIN_CONNECTORS IDs
    SCHEME_TO_CONNECTOR = {
        "postgresql": "postgres",
        "postgres": "postgres",
        "mysql": "mysql",
        "s3": "s3",
        "gcs": "gcs",
        "snowflake": "snowflake",
        "bigquery": "bigquery",
    }

    @classmethod
    def parse_uri(cls, uri: str) -> Dict[str, Any]:
        """
        Parses a generic URI into discrete credential components matching
        the dynamic source schema.
        """
        if not uri or "://" not in uri:
            raise ValueError("Invalid URI format. Expected scheme://...")

        parsed = urlparse(uri)
        scheme = parsed.scheme.lower()

        connector_id = cls.SCHEME_TO_CONNECTOR.get(scheme)
        if not connector_id:
            raise ValueError(f"Unsupported generic URI scheme: {scheme}")

        logger.info(f"[URIParser] Parsed {scheme} generic URI successfully.")

        return {
            "connector_id": connector_id,
            "config": {
                "host": parsed.hostname,
                "port": parsed.port,
                "database": parsed.path.lstrip("/") if parsed.path else None,
                "user": parsed.username,
                "password": parsed.password,
            },
        }
