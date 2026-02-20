"""
Airbyte Configuration Generators: Utilities for Airbyte Source Configurations.

This module provides helper utilities to programmatically generate valid Airbyte
source configurations for various data sources (e.g., PostgreSQL, S3, REST APIs,
secure files). These generators simplify the process of setting up new data
ingestion pipelines by abstracting the complexities of Airbyte's connection
configuration JSON schemas.
"""

from typing import Any, Dict, List, Optional


class AirbyteConfigGenerator:
    """
    A utility class containing static methods to generate valid Airbyte source configurations.

    These methods produce dictionary structures that conform to Airbyte's expected
    connection configuration format for different source types.
    """

    @staticmethod
    def generate_postgres_config(
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        schemas: Optional[list[str]] = None,
        ssl_mode: str = "disable",
    ) -> Dict[str, Any]:
        """
        Generates a configuration dictionary for an Airbyte PostgreSQL source.

        Args:
            host (str): The hostname or IP address of the PostgreSQL server.
            port (int): The port number of the PostgreSQL server.
            database (str): The name of the database to connect to.
            username (str): The username for PostgreSQL authentication.
            password (str): The password for PostgreSQL authentication.
            schemas (Optional[list[str]]): A list of schemas to include in the sync. Defaults to ["public"].
            ssl_mode (str): The SSL mode for the connection (e.g., "disable", "require", "verify-full").

        Returns:
            Dict[str, Any]: A dictionary representing the Airbyte source configuration for PostgreSQL.
        """
        return {
            "sourceType": "postgres",
            "connectionConfiguration": {
                "host": host,
                "port": port,
                "database": database,
                "username": username,
                "password": password,
                "schemas": schemas or ["public"],
                "ssl_mode": {"mode": ssl_mode},
                "tunnel_method": {"tunnel_method": "NO_TUNNEL"},
                "replication_method": {"method": "Standard"},
            },
        }

    @staticmethod
    def generate_s3_config(
        bucket: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str,
        path_prefix: str = "",
        format_type: str = "csv",
    ) -> Dict[str, Any]:
        """
        Generates a configuration dictionary for an Airbyte S3 source.

        Args:
            bucket (str): The name of the S3 bucket.
            aws_access_key_id (str): The AWS access key ID.
            aws_secret_access_key (str): The AWS secret access key.
            region_name (str): The AWS region where the bucket is located.
            path_prefix (str, optional): A prefix to filter objects within the bucket. Defaults to "".
            format_type (str, optional): The format of the files in the S3 bucket (e.g., "csv", "parquet", "jsonl").

        Returns:
            Dict[str, Any]: A dictionary representing the Airbyte source configuration for S3.
        """
        format_config = {}
        if format_type == "csv":
            format_config = {"filetype": "csv"}
        elif format_type == "parquet":
            format_config = {"filetype": "parquet"}
        elif format_type == "jsonl":
            format_config = {"filetype": "jsonl"}
        else:
            # Default to CSV or raise error for unsupported format
            format_config = {"filetype": "csv"}

        return {
            "sourceType": "s3",
            "connectionConfiguration": {
                "bucket": bucket,
                "aws_access_key_id": aws_access_key_id,
                "aws_secret_access_key": aws_secret_access_key,
                "region_name": region_name,
                "path_prefix": path_prefix,
                "format": format_config,
                "provider": {"storage": "S3"},
            },
        }

    @staticmethod
    def generate_rest_api_config(
        url: str,
        http_method: str = "GET",
        auth_type: str = "ApiKey",
        auth_params: Optional[Dict[str, str]] = None,
        streams: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generates a configuration dictionary for an Airbyte Declarative Manifest source (Low-code REST API).

        This method constructs a basic declarative manifest for connecting to a REST API,
        including authentication details.

        Args:
            url (str): The base URL of the REST API.
            http_method (str, optional): The HTTP method to use for requests (e.g., "GET", "POST"). Defaults to "GET".
            auth_type (str, optional): The type of authentication (e.g., "ApiKey", "Bearer").
            auth_params (Optional[Dict[str, str]]): A dictionary of authentication parameters
                                                     (e.g., {"header": "Authorization", "api_key": "YOUR_KEY"}).
            streams (Optional[List[Dict[str, Any]]]): A list of stream configurations.

        Returns:
            Dict[str, Any]: A dictionary representing the Airbyte source configuration for a REST API.
        """
        # This is a simplified generation for common patterns.
        # In a full implementation, this would construct a more comprehensive YAML/JSON manifest for the Airbyte Connector Builder.
        manifest = {
            "version": "0.29.0",
            "type": "DeclarativeSource",
            "check": {
                "type": "CheckStream",
                "stream_names": [streams[0]["name"]] if streams else ["default_stream"],
            },
            "streams": streams or [],
            "spec": {
                "connection_specification": {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "object",
                    "required": [],
                    "properties": {},
                }
            },
        }

        # Inject Authentication Configuration.
        if auth_type == "ApiKey":
            manifest["auth"] = {
                "type": "ApiKey",
                "header": auth_params.get("header", "Authorization"),
                "api_token": auth_params.get("api_key", ""),
            }
        elif auth_type == "Bearer":
            manifest["auth"] = {
                "type": "Bearer",
                "api_token": auth_params.get("api_key", ""),
            }

        return {
            "sourceType": "declarative-manifest",
            "connectionConfiguration": {"manifest": manifest},
        }

    @staticmethod
    def generate_file_secure_config(
        url: str,
        file_format: str = "csv",
        provider_storage: str = "HTTPS",
        user_agent: bool = False,
    ) -> Dict[str, Any]:
        """
        Generates a configuration dictionary for an Airbyte File-Secure source.

        This is used for ingesting files from secure locations accessible via URL (e.g., HTTPS).

        Args:
            url (str): The URL of the file to ingest.
            file_format (str, optional): The format of the file (e.g., "csv", "jsonl", "parquet").
            provider_storage (str, optional): The storage provider (e.g., "HTTPS", "S3", "GCS"). Defaults to "HTTPS".
            user_agent (bool, optional): Whether to include a User-Agent header in the request.

        Returns:
            Dict[str, Any]: A dictionary representing the Airbyte source configuration for a secure file.
        """
        return {
            "sourceType": "file-secure",
            "connectionConfiguration": {
                "url": url,
                "format": file_format,
                "provider": {"storage": provider_storage, "user_agent": user_agent},
            },
        }
