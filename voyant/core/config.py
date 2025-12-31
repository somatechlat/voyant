"""
Voyant Configuration

Single source of truth for all configuration.
Uses Pydantic Settings for environment variable parsing.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Voyant configuration from environment variables."""
    
    model_config = SettingsConfigDict(
        env_prefix="VOYANT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Environment
    env: str = Field(default="local", description="Environment: local, staging, production")
    debug: bool = Field(default=False)
    
    # Database (PostgreSQL)
    database_url: str = Field(
        default="postgresql://voyant:voyant@localhost:45432/voyant",
        alias="DATABASE_URL",
    )
    
    # DuckDB (Local Analytical DB)
    duckdb_path: str = Field(
        default="voyant.duckdb",
        alias="DUCKDB_PATH",
    )
    
    # Redis (Sessions & Cache)
    redis_url: str = Field(
        default="redis://:voyant@localhost:45379/0",
        alias="REDIS_URL",
    )
    
    # Kafka
    kafka_bootstrap_servers: str = Field(default="localhost:45092")

    # Temporal (Orchestration)
    temporal_host: str = Field(default="localhost:45233")
    temporal_namespace: str = Field(default="default")
    temporal_task_queue: str = Field(default="voyant-tasks")
    
    # MinIO (S3-compatible)
    minio_endpoint: str = Field(default="localhost:45900")
    minio_access_key: str = Field(default="voyant")
    minio_secret_key: str = Field(default="voyant123") # Dev default accepted for local
    minio_secure: bool = Field(default=False)
    
    # Trino (SQL Federation)
    trino_host: str = Field(default="localhost")
    trino_port: int = Field(default=45090)
    trino_user: str = Field(default="voyant")
    trino_catalog: str = Field(default="iceberg")
    trino_schema: str = Field(default="voyant")

    # R Engine (Statistical Analysis)
    r_engine_host: str = Field(default="localhost")
    r_engine_port: int = Field(default=45311)
    
    # DataHub
    datahub_gms_url: str = Field(default="http://localhost:45080")
    
    # Keycloak
    keycloak_url: str = Field(default="http://localhost:45180")
    keycloak_realm: str = Field(default="voyant")
    keycloak_client_id: str = Field(default="voyant-api")
    keycloak_client_secret: str = Field(default="voyant-api-secret")
    
    # Lago Billing
    lago_api_url: str = Field(default="http://localhost:45300")
    lago_api_key: str = Field(default="")

    # Soma Stack Integration
    soma_policy_url: str = Field(default="", alias="SOMA_POLICY_URL")
    soma_memory_url: str = Field(default="", alias="SOMA_MEMORY_URL")
    soma_orchestrator_url: str = Field(default="", alias="SOMA_ORCHESTRATOR_URL")
    
    @model_validator(mode='after')
    def check_security(self) -> 'Settings':
        if self.env != "local":
            defaults = ["voyant123", "voyant-api-secret", "voyant"]
            val_str = str(self.minio_secret_key)
            if val_str in defaults or self.keycloak_client_secret in defaults:
                import logging
                logging.getLogger("voyant.security").warning(
                    f"⚠️ SECURITY WARNING: Running in {self.env} with default secrets! Rotate immediately."
                )
        return self
    
    # Secrets Backend
    secrets_backend: str = Field(default="env", description="env, k8s, or vault")
    
    # Feature Flags
    enable_quality: bool = Field(default=True)
    enable_billing: bool = Field(default=True)
    enable_datahub: bool = Field(default=True)
    enable_mfa: bool = Field(default=False)
    enable_charts: bool = Field(default=True)
    enable_narrative: bool = Field(default=True)
    
    # Metrics Mode: off (no metrics), basic (core only), full (all metrics)
    metrics_mode: str = Field(
        default="full",
        description="Metrics registration mode: off, basic, or full"
    )
    
    # API Settings
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_workers: int = Field(default=4)
    
    # Limits
    max_query_rows: int = Field(default=10000)
    max_upload_size_mb: int = Field(default=100)
    session_ttl_hours: int = Field(default=8)
    session_idle_minutes: int = Field(default=30)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
