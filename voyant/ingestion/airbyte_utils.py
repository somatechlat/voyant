"""
Airbyte Configuration Generators

Helper utilities to generate Airbyte source configurations for various protocols.
Adheres to Vibe Coding Rules: Real schema structures based on Airbyte specs.
"""
from typing import Any, Dict, Optional

class AirbyteConfigGenerator:
    """Generates valid Airbyte source configurations."""
    
    @staticmethod
    def generate_postgres_config(
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        schemas: Optional[list[str]] = None,
        ssl_mode: str = "disable"
    ) -> Dict[str, Any]:
        """
        Generate source-postgres configuration.
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
                "ssl_mode": {
                    "mode": ssl_mode
                },
                "tunnel_method": {
                    "tunnel_method": "NO_TUNNEL"
                },
                "replication_method": {
                    "method": "Standard"
                }
            }
        }

    @staticmethod
    def generate_s3_config(
        bucket: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str,
        path_prefix: str = "",
        format_type: str = "csv"
    ) -> Dict[str, Any]:
        """
        Generate source-s3 configuration.
        """
        format_config = {}
        if format_type == "csv":
            format_config = {"filetype": "csv"}
        elif format_type == "parquet":
            format_config = {"filetype": "parquet"}
        elif format_type == "json":  # jsonl
             format_config = {"filetype": "jsonl"}
             
        return {
            "sourceType": "s3",
            "connectionConfiguration": {
                "bucket": bucket,
                "aws_access_key_id": aws_access_key_id,
                "aws_secret_access_key": aws_secret_access_key,
                "region_name": region_name,
                "path_prefix": path_prefix,
                "format": format_config,
                "provider": {
                    "storage": "S3"
                }
            }
        }

    @staticmethod
    def generate_rest_api_config(
        url: str,
        http_method: str = "GET",
        auth_type: str = "ApiKey", 
        auth_params: Optional[Dict[str, str]] = None,
        streams: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate source-declarative-manifest configuration (Low-code REST).
        This maps to Airbyte's Builder logic.
        """
        # Simplified generation for common patterns
        # In a real impl, this would construct the full YAML/JSON manifest for the Connector Builder
        
        manifest = {
            "version": "0.29.0",
            "type": "DeclarativeSource",
            "check": {
                "type": "CheckStream",
                "stream_names": [streams[0]["name"]] if streams else ["default_stream"]
            },
            "streams": streams or [],
            "spec": {
                "connection_specification": {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "object",
                    "required": [],
                    "properties": {}
                }
            }
        }
        
        # Inject Auth
        if auth_type == "ApiKey":
            manifest["auth"] = {
                 "type": "ApiKey",
                 "header": auth_params.get("header", "Authorization"),
                 "api_token": auth_params.get("api_key", "")
            }
        elif auth_type == "Bearer":
             manifest["auth"] = {
                 "type": "Bearer",
                 "api_token": auth_params.get("api_key", "")
             }

        return {
             "sourceType": "declarative-manifest",
             "connectionConfiguration": {
                 "manifest": manifest
             }
        }

    @staticmethod
    def generate_file_secure_config(
        url: str,
        file_format: str = "csv",
        provider_storage: str = "HTTPS",
        user_agent: bool = False
    ) -> Dict[str, Any]:
        """
        Generate source-file-secure configuration (HTTPS/Local).
        """
        return {
            "sourceType": "file-secure",
            "connectionConfiguration": {
                "url": url,
                "format": file_format,
                "provider": {
                    "storage": provider_storage,
                    "user_agent": user_agent
                }
            }
        }
