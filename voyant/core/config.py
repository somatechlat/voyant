"""
Voyant Configuration Management.

This module provides a single, typed, and validated source of truth for all
application configuration. It uses `pydantic-settings` to load configuration
from environment variables and/or a .env file, ensuring that all settings
are present and correctly typed before the application starts.

The `get_settings()` function is the cached entrypoint for accessing configuration
throughout the application.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Voyant configuration model, parsed from environment variables.

    Defines all application settings with types, defaults, and descriptions.
    The `VOYANT_` prefix is automatically applied to all environment variables.
    """

    model_config = SettingsConfigDict(
        env_prefix="VOYANT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from the environment
    )

    # --------------------------------------------------------------------------
    # Core Application Environment
    # --------------------------------------------------------------------------
    env: str = Field(
        default="local", description="Environment: local, staging, production"
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    # --------------------------------------------------------------------------
    # Core Infrastructure Backing Services
    # --------------------------------------------------------------------------
    database_url: str = Field(
        default="postgresql://voyant:voyant@localhost:45432/voyant",
        alias="DATABASE_URL",
        description="Primary PostgreSQL database for metadata.",
    )
    duckdb_path: str = Field(
        default="voyant.duckdb",
        alias="DUCKDB_PATH",
        description="File path for the local analytical DuckDB database.",
    )
    redis_url: str = Field(
        default="redis://:voyant@localhost:45379/0",
        alias="REDIS_URL",
        description="Connection URL for Redis, used for caching and sessions.",
    )

    # --------------------------------------------------------------------------
    # Service Integrations
    # --------------------------------------------------------------------------
    kafka_bootstrap_servers: str = Field(
        default="localhost:45092", description="Comma-separated list of Kafka brokers."
    )
    temporal_host: str = Field(
        default="localhost:45233",
        alias="TEMPORAL_HOST",
        description="Host and port for the Temporal workflow orchestration engine.",
    )
    temporal_namespace: str = Field(
        default="default", description="Temporal namespace to operate in."
    )
    temporal_task_queue: str = Field(
        default="voyant-tasks",
        alias="TEMPORAL_TASK_QUEUE",
        description="The task queue Voyant workers will listen on.",
    )
    minio_endpoint: str = Field(
        default="localhost:45900",
        description="Endpoint for the MinIO S3-compatible object storage.",
    )
    minio_access_key: str = Field(
        default="voyant", description="Access key for MinIO."
    )
    minio_secret_key: str = Field(
        default="voyant123",
        description="Secret key for MinIO. Dev default accepted for local.",
    )
    minio_secure: bool = Field(
        default=False, description="Use HTTPS for MinIO connection."
    )
    trino_host: str = Field(
        default="localhost", description="Hostname for the Trino SQL query engine."
    )
    trino_port: int = Field(default=45090, description="Port for Trino.")
    trino_user: str = Field(default="voyant", description="Username for Trino.")
    trino_catalog: str = Field(
        default="iceberg", description="Default Trino catalog to query."
    )
    trino_schema: str = Field(
        default="voyant", description="Default Trino schema to query."
    )
    r_engine_host: str = Field(
        default="localhost", description="Hostname for the R-Engine (pyRserve)."
    )
    r_engine_port: int = Field(
        default=45311, description="Port for the R-Engine."
    )
    datahub_gms_url: str = Field(
        default="http://localhost:45080",
        description="URL for the DataHub metadata service (GMS).",
    )
    keycloak_url: str = Field(
        default="http://localhost:45180",
        description="URL for the Keycloak identity and access management server.",
    )
    keycloak_realm: str = Field(
        default="voyant", description="Keycloak realm for Voyant."
    )
    keycloak_client_id: str = Field(
        default="voyant-api", description="Keycloak client ID for the Voyant API."
    )
    keycloak_client_secret: str = Field(
        default="voyant-api-secret", description="Keycloak client secret."
    )
    lago_api_url: str = Field(
        default="http://localhost:45300", description="URL for the Lago billing API."
    )
    lago_api_key: str = Field(default="", description="API key for Lago.")
    soma_policy_url: str = Field(
        default="",
        alias="SOMA_POLICY_URL",
        description="URL for the Soma Policy Engine.",
    )
    soma_memory_url: str = Field(
        default="",
        alias="SOMA_MEMORY_URL",
        description="URL for the Soma Memory Gateway.",
    )
    soma_orchestrator_url: str = Field(
        default="",
        alias="SOMA_ORCHESTRATOR_URL",
        description="URL for the Soma Orchestrator.",
    )
    flink_jobmanager_url: str = Field(
        default="http://voyant_flink_jobmanager:8081",
        alias="FLINK_JOBMANAGER_URL",
        description="URL for the Apache Flink JobManager.",
    )

    @model_validator(mode="after")
    def check_security(self) -> "Settings":
        """
        Perform post-validation security checks.

        This validator runs after all environment variables are parsed and warns
        the user if insecure default secrets are being used in a non-local environment.
        """
        if self.env != "local":
            defaults = ["voyant123", "voyant-api-secret", "voyant"]
            val_str = str(self.minio_secret_key)
            if val_str in defaults or self.keycloak_client_secret in defaults:
                import logging

                # This is a critical security warning.
                logging.getLogger("voyant.security").warning(
                    f"⚠️ SECURITY WARNING: Running in {self.env} with default secrets! Rotate immediately."
                )
        return self

    # --------------------------------------------------------------------------
    # Pluggable & Feature Toggles
    # --------------------------------------------------------------------------
    secrets_backend: str = Field(
        default="env", description="Secrets backend provider: 'env', 'k8s', or 'vault'."
    )
    enable_quality: bool = Field(
        default=True, description="Enable data quality checks and endpoints."
    )
    enable_billing: bool = Field(
        default=True, description="Enable billing integration and usage tracking."
    )
    enable_datahub: bool = Field(
        default=True, description="Enable DataHub integration for governance."
    )
    enable_mfa: bool = Field(
        default=False, description="Enable Multi-Factor Authentication requirements."
    )
    enable_charts: bool = Field(
        default=True, description="Enable chart generation capabilities."
    )
    enable_narrative: bool = Field(
        default=True, description="Enable narrative generation capabilities."
    )
    metrics_mode: str = Field(
        default="full",
        description="Metrics registration mode: 'off', 'basic', or 'full'.",
    )

    # --------------------------------------------------------------------------
    # API & Application Limits
    # --------------------------------------------------------------------------
    api_host: str = Field(default="0.0.0.0", description="Host for the API server.")
    api_port: int = Field(default=8000, description="Port for the API server.")
    api_workers: int = Field(
        default=4, description="Number of worker processes for the API server."
    )
    max_query_rows: int = Field(
        default=10000, description="Maximum number of rows to return from a SQL query."
    )
    max_upload_size_mb: int = Field(
        default=100, description="Maximum size for file uploads in megabytes."
    )
    session_ttl_hours: int = Field(
        default=8, description="Maximum session lifetime in hours."
    )
    session_idle_minutes: int = Field(
        default=30, description="Session idle timeout in minutes."
    )


@lru_cache
def get_settings() -> Settings:
    """
    Get the cached, application-wide settings instance.

    Using lru_cache ensures that the settings are loaded from the environment
    only once, improving performance.

    Returns:
        The singleton Settings instance.
    """
    return Settings()
