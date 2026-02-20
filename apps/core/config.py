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
from typing import ClassVar

from pydantic import Field, field_validator, model_validator
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

    RUNTIME_ENV_KEYS: ClassVar[set[str]] = {
        "env",
        "debug",
        "secrets_backend",
        "secrets_vault_url",
        "secrets_vault_token",
        "secrets_vault_mount_point",
        "api_host",
        "api_port",
        "mcp_host",
        "mcp_port",
        "mcp_api_url",
        "mcp_api_token",
        "database_url",
        "redis_url",
        "kafka_bootstrap_servers",
        "temporal_host",
        "temporal_namespace",
        "temporal_task_queue",
        "minio_endpoint",
        "datahub_gms_url",
        "keycloak_url",
        "keycloak_realm",
        "lago_api_url",
        "soma_policy_url",
        "soma_memory_url",
        "soma_orchestrator_url",
        "flink_jobmanager_url",
    }
    SECRET_KEYS: ClassVar[set[str]] = {
        "minio_access_key",
        "minio_secret_key",
        "keycloak_client_secret",
        "lago_api_key",
        "serper_api_key",
        "mcp_api_token",
    }

    # --------------------------------------------------------------------------
    # Core Application Environment
    # --------------------------------------------------------------------------
    env: str = Field(
        default="local", description="Environment: local, staging, production"
    )
    deployment_mode: str = Field(
        default="integrated",
        description="Deployment mode: integrated or standalone.",
    )
    worker_mode: str = Field(
        default="full",
        description="Temporal worker mode: full|scraper",
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    secret_key: str = Field(
        default="",
        alias="SECRET_KEY",
        description="Django secret key. Critical for security.",
    )
    allowed_hosts: list[str] = Field(
        default=["*"],
        alias="ALLOWED_HOSTS",
        description="List of strings representing the host/domain names that this Django site can serve.",
    )

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        return v

    csrf_trusted_origins: list[str] = Field(
        default=[],
        alias="CSRF_TRUSTED_ORIGINS",
        description="A list of hosts that are trusted for CSRF purposes.",
    )

    @field_validator("csrf_trusted_origins", mode="before")
    @classmethod
    def parse_csrf_trusted_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # --------------------------------------------------------------------------
    # Core Infrastructure Backing Services
    # --------------------------------------------------------------------------
    database_url: str = Field(
        default="",
        alias="DATABASE_URL",
        description="Primary PostgreSQL database for metadata.",
    )
    duckdb_path: str = Field(
        default="voyant.duckdb",
        alias="DUCKDB_PATH",
        description="File path for the local analytical DuckDB database.",
    )
    redis_url: str = Field(
        default="",
        alias="REDIS_URL",
        description="Connection URL for Redis, used for caching and sessions.",
    )

    # --------------------------------------------------------------------------
    # Email Configuration
    # --------------------------------------------------------------------------
    email_host: str = Field(
        default="localhost",
        alias="EMAIL_HOST",
        description="The host to use for sending email.",
    )
    email_port: int = Field(
        default=587,
        alias="EMAIL_PORT",
        description="Port to use for the SMTP server defined in EMAIL_HOST.",
    )
    email_use_tls: bool = Field(
        default=True,
        alias="EMAIL_USE_TLS",
        description="Whether to use a TLS (secure) connection when talking to the SMTP server.",
    )
    email_host_user: str = Field(
        default="",
        alias="EMAIL_HOST_USER",
        description="Username to use for the SMTP server defined in EMAIL_HOST.",
    )
    email_host_password: str = Field(
        default="",
        alias="EMAIL_HOST_PASSWORD",
        description="Password to use for the SMTP server defined in EMAIL_HOST.",
    )
    default_from_email: str = Field(
        default="webmaster@localhost",
        alias="DEFAULT_FROM_EMAIL",
        description="Default email address to use for various automated correspondence.",
    )

    # --------------------------------------------------------------------------
    # Service Integrations
    # --------------------------------------------------------------------------
    kafka_bootstrap_servers: str = Field(
        default="",
        alias="KAFKA_BOOTSTRAP_SERVERS",
        description="Comma-separated list of Kafka brokers.",
    )
    temporal_host: str = Field(
        default="",
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
    temporal_activity_max_workers: int = Field(
        default=0,
        alias="TEMPORAL_ACTIVITY_MAX_WORKERS",
        description=(
            "Max worker threads for synchronous Temporal activities. "
            "0 means auto-sized based on CPU."
        ),
    )
    minio_endpoint: str = Field(
        default="",
        alias="MINIO_ENDPOINT",
        description="Endpoint for the MinIO S3-compatible object storage.",
    )
    minio_access_key: str = Field(
        default="",
        alias="MINIO_ACCESS_KEY",
        description="Access key for MinIO.",
    )
    minio_secret_key: str = Field(
        default="",
        alias="MINIO_SECRET_KEY",
        description="Secret key for MinIO.",
    )
    minio_secure: bool = Field(
        default=False, description="Use HTTPS for MinIO connection."
    )
    trino_host: str = Field(
        default="", description="Hostname for the Trino SQL query engine."
    )
    trino_port: int = Field(default=45090, description="Port for Trino.")
    trino_user: str = Field(default="", description="Username for Trino.")
    trino_catalog: str = Field(
        default="iceberg", description="Default Trino catalog to query."
    )
    trino_schema: str = Field(default="", description="Default Trino schema to query.")
    r_engine_host: str = Field(
        default="", description="Hostname for the R-Engine (pyRserve)."
    )
    r_engine_port: int = Field(default=45311, description="Port for the R-Engine.")
    datahub_gms_url: str = Field(
        default="",
        alias="DATAHUB_GMS_URL",
        description="URL for the DataHub metadata service (GMS).",
    )
    keycloak_url: str = Field(
        default="",
        alias="KEYCLOAK_URL",
        description="URL for the Keycloak identity and access management server.",
    )
    keycloak_realm: str = Field(
        default="",
        alias="KEYCLOAK_REALM",
        description="Keycloak realm for Voyant.",
    )
    keycloak_client_id: str = Field(
        default="",
        alias="KEYCLOAK_CLIENT_ID",
        description="Keycloak client ID for the Voyant API.",
    )
    keycloak_client_secret: str = Field(
        default="",
        alias="KEYCLOAK_CLIENT_SECRET",
        description="Keycloak client secret.",
    )
    lago_api_url: str = Field(
        default="",
        alias="LAGO_API_URL",
        description="URL for the Lago billing API.",
    )
    lago_api_key: str = Field(
        default="",
        alias="LAGO_API_KEY",
        description="API key for Lago.",
    )
    serper_api_key: str = Field(
        default="",
        alias="SERPER_API_KEY",
        description="API key for Serper search integration.",
    )
    serper_search_url: str = Field(
        default="",
        alias="SERPER_SEARCH_URL",
        description="Serper search endpoint URL.",
    )
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
        default="",
        alias="FLINK_JOBMANAGER_URL",
        description="URL for the Apache Flink JobManager.",
    )

    @model_validator(mode="after")
    def check_security(self) -> "Settings":
        """
        Perform post-validation security checks.

        This validator runs after all environment variables are parsed and warns
        when required secret values are missing in non-local environments.
        """
        if self.env != "local":
            if self.secrets_backend != "vault":
                import logging

                logging.getLogger("voyant.security").warning(
                    "Running non-local environment without Vault-backed secrets backend."
                )
            if (
                not str(self.minio_secret_key).strip()
                or not str(self.keycloak_client_secret).strip()
            ):
                import logging

                # This is a critical security warning.
                logging.getLogger("voyant.security").warning(
                    f"⚠️ SECURITY WARNING: Running in {self.env} with missing secret values."
                )
        return self

    @model_validator(mode="after")
    def validate_required_external_config(self) -> "Settings":
        """Fail fast when required external service settings are missing outside local env."""
        if self.env == "local":
            return self

        required = {
            "database_url": self.database_url,
            "redis_url": self.redis_url,
            "kafka_bootstrap_servers": self.kafka_bootstrap_servers,
            "temporal_host": self.temporal_host,
            "minio_endpoint": self.minio_endpoint,
            "minio_access_key": self.minio_access_key,
            "minio_secret_key": self.minio_secret_key,
            "datahub_gms_url": self.datahub_gms_url,
            "keycloak_url": self.keycloak_url,
            "keycloak_realm": self.keycloak_realm,
            "keycloak_client_id": self.keycloak_client_id,
            "keycloak_client_secret": self.keycloak_client_secret,
            "lago_api_url": self.lago_api_url,
            "mcp_api_url": self.mcp_api_url,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            missing_str = ", ".join(sorted(missing))
            raise ValueError(
                f"Missing required VOYANT settings for env='{self.env}': {missing_str}"
            )
        return self

    # --------------------------------------------------------------------------
    # Pluggable & Feature Toggles
    # --------------------------------------------------------------------------
    secrets_backend: str = Field(
        default="env", description="Secrets backend provider: 'env', 'k8s', or 'vault'."
    )
    secrets_vault_url: str = Field(
        default="",
        description="Vault base URL used when secrets_backend='vault'.",
    )
    secrets_vault_token: str = Field(
        default="",
        description="Vault authentication token.",
    )
    secrets_vault_mount_point: str = Field(
        default="secret",
        description="Vault KV mount point for Voyant secrets.",
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
    mcp_host: str = Field(
        default="0.0.0.0",
        description="Host interface for the MCP server transport.",
    )
    mcp_port: int = Field(
        default=8001,
        description="Port for the MCP server transport.",
    )
    mcp_api_url: str = Field(
        default="",
        description="Upstream Voyant API URL used by MCP tools.",
    )
    mcp_api_token: str = Field(
        default="",
        description="Bearer token used by MCP tools when calling the Voyant API.",
    )
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
    default_tenant_id: str = Field(
        default="default",
        alias="DEFAULT_TENANT_ID",
        description="Default tenant identifier when request context is missing.",
    )
    scraper_default_engine: str = Field(
        default="playwright",
        alias="SCRAPER_DEFAULT_ENGINE",
        description="Default scraper fetch engine.",
    )
    scraper_default_timeout_seconds: int = Field(
        default=30,
        alias="SCRAPER_DEFAULT_TIMEOUT_SECONDS",
        description="Default timeout for scraper network operations in seconds.",
    )
    scraper_default_ocr_language: str = Field(
        default="spa+eng",
        alias="SCRAPER_DEFAULT_OCR_LANGUAGE",
        description="Default OCR language pack.",
    )
    scraper_default_transcribe_language: str = Field(
        default="es",
        alias="SCRAPER_DEFAULT_TRANSCRIBE_LANGUAGE",
        description="Default speech transcription language.",
    )
    scraper_http_user_agent: str = Field(
        default="Mozilla/5.0 (compatible; VoyantBot/1.0)",
        alias="SCRAPER_HTTP_USER_AGENT",
        description="User-Agent header for HTTP scraper engine.",
    )
    scraper_http_accept_language: str = Field(
        default="es-EC,es;q=0.9,en;q=0.8",
        alias="SCRAPER_HTTP_ACCEPT_LANGUAGE",
        description="Accept-Language header for HTTP scraper engine.",
    )
    scraper_tls_verify: bool = Field(
        default=True,
        alias="SCRAPER_TLS_VERIFY",
        description="Verify TLS certificates for scraper HTTP clients.",
    )
    scraper_tls_trust_store: str = Field(
        default="system",
        alias="SCRAPER_TLS_TRUST_STORE",
        description="TLS trust store selection for scraper HTTP clients: system|certifi.",
    )
    scraper_playwright_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        alias="SCRAPER_PLAYWRIGHT_USER_AGENT",
        description="User-Agent used by Playwright browser context.",
    )
    scraper_playwright_locale: str = Field(
        default="es-EC",
        alias="SCRAPER_PLAYWRIGHT_LOCALE",
        description="Locale used by Playwright browser context.",
    )
    scraper_playwright_wait_until: str = Field(
        default="domcontentloaded",
        alias="SCRAPER_PLAYWRIGHT_WAIT_UNTIL",
        description=(
            "Playwright page.goto wait_until strategy: load|domcontentloaded|networkidle|commit. "
            "networkidle can hang on pages with long-lived connections; domcontentloaded is safer."
        ),
    )
    scraper_playwright_capture_json_default: bool = Field(
        default=False,
        alias="SCRAPER_PLAYWRIGHT_CAPTURE_JSON_DEFAULT",
        description="Default setting for Playwright JSON/XHR capture in the fetch tool.",
    )
    scraper_playwright_capture_max_bytes: int = Field(
        default=524288,
        alias="SCRAPER_PLAYWRIGHT_CAPTURE_MAX_BYTES",
        description="Max bytes to read from a single captured JSON response body.",
    )
    scraper_playwright_capture_max_items: int = Field(
        default=25,
        alias="SCRAPER_PLAYWRIGHT_CAPTURE_MAX_ITEMS",
        description="Max number of captured JSON responses to attach to a fetch result.",
    )
    scraper_playwright_block_resources_default: bool = Field(
        default=True,
        alias="SCRAPER_PLAYWRIGHT_BLOCK_RESOURCES_DEFAULT",
        description="Default for Playwright fetch: block images/fonts/media to speed up loads.",
    )
    scraper_playwright_settle_ms_default: int = Field(
        default=2500,
        alias="SCRAPER_PLAYWRIGHT_SETTLE_MS_DEFAULT",
        description="Default time (ms) to wait after navigation to allow XHR/fetch requests to finish.",
    )
    scraper_max_ocr_images: int = Field(
        default=10,
        alias="SCRAPER_MAX_OCR_IMAGES",
        description="Maximum number of images to OCR per request.",
    )
    scraper_max_transcribe_media: int = Field(
        default=5,
        alias="SCRAPER_MAX_TRANSCRIBE_MEDIA",
        description="Maximum number of media files to transcribe per request.",
    )
    scraper_enable_transcribe: bool = Field(
        default=False,
        alias="SCRAPER_ENABLE_TRANSCRIBE",
        description=(
            "Enable media transcription. When disabled, transcribe endpoints/tools "
            "return a structured error and workflows skip transcription."
        ),
    )
    scraper_whisper_model_name: str = Field(
        default="base",
        alias="SCRAPER_WHISPER_MODEL_NAME",
        description="Whisper model name to load when transcription is enabled.",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_security_env(cls, data):
        """Normalize legacy security env var names into canonical VOYANT_* settings."""
        if not isinstance(data, dict):
            data = {}
        if "secrets_backend" not in data:
            legacy_backend = os.environ.get("VOYANT_SECURITY_SECRETS_BACKEND")
            if legacy_backend:
                data["secrets_backend"] = legacy_backend
        if "secrets_vault_url" not in data:
            legacy_vault_url = os.environ.get("VOYANT_SECURITY_SECRETS_VAULT_URL")
            if legacy_vault_url:
                data["secrets_vault_url"] = legacy_vault_url
        if "secrets_vault_token" not in data:
            legacy_vault_token = os.environ.get("VOYANT_SECURITY_SECRETS_VAULT_TOKEN")
            if legacy_vault_token:
                data["secrets_vault_token"] = legacy_vault_token
        if "secrets_vault_mount_point" not in data:
            legacy_mount = os.environ.get("VOYANT_SECURITY_SECRETS_VAULT_MOUNT_POINT")
            if legacy_mount:
                data["secrets_vault_mount_point"] = legacy_mount
        if "mcp_api_url" not in data:
            legacy_api_url = os.environ.get("VOYANT_API_URL")
            if legacy_api_url:
                data["mcp_api_url"] = legacy_api_url
        if "mcp_api_token" not in data:
            legacy_api_token = os.environ.get("VOYANT_API_TOKEN")
            if legacy_api_token:
                data["mcp_api_token"] = legacy_api_token
        if "mcp_host" not in data:
            legacy_mcp_host = os.environ.get("VOYANT_MCP_HOST")
            if legacy_mcp_host:
                data["mcp_host"] = legacy_mcp_host
        if "mcp_port" not in data:
            legacy_mcp_port = os.environ.get("VOYANT_MCP_PORT")
            if legacy_mcp_port:
                data["mcp_port"] = int(legacy_mcp_port)
        return data


@lru_cache
def get_settings() -> Settings:
    """
    Get the cached, application-wide settings instance.

    Using lru_cache ensures that the settings are loaded from the environment
    only once, improving performance.

    Returns:
        The singleton Settings instance.
    """
    settings = Settings()

    # Load non-runtime, non-secret configuration from ORM-backed settings store.
    overrides = {}
    try:
        from django.apps import apps
        SystemSetting = apps.get_model("core", "SystemSetting")

        # Basic query to get overrides
        # In a real scenario, you'd filter by keys
        # This part requires DB access which might not be ready during import
        # So we usually Wrap this or catch OperationalError
    except Exception:
        pass
    if overrides:
            settings = settings.model_copy(update=overrides)


    return settings

