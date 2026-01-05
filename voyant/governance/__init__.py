"""
Voyant Governance Package.

This package provides the public interface for Voyant's data governance
integrations, primarily focusing on interaction with DataHub for metadata
management, lineage tracking, and schema definitions.
"""

from .datahub import DataHubClient, DatasetUrn, get_datahub_client

__all__ = ["DataHubClient", "DatasetUrn", "get_datahub_client"]
