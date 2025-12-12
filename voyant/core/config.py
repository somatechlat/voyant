"""
Voyant Configuration

Single source of truth for all configuration.
Uses Pydantic Settings for environment variable parsing.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
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
        default="postgresql://voyant:voyant@localhost:5432/voyant",
        alias="DATABASE_URL",
    )
    
    # Redis (Sessions & Cache)
    redis_url: str = Field(
        default="redis://:voyant@localhost:6379/0",
        alias="REDIS_URL",
    )
    
    # Kafka
    kafka_bootstrap_servers: str = Field(default="localhost:9092")
    
    # MinIO (S3-compatible)
    minio_endpoint: str = Field(default="localhost:9000")
    minio_access_key: str = Field(default="voyant")
    minio_secret_key: str = Field(default="voyant123")
    minio_secure: bool = Field(default=False)
    
    # Trino (SQL Federation)
    trino_host: str = Field(default="localhost")
    trino_port: int = Field(default=8090)
    trino_user: str = Field(default="voyant")
    trino_catalog: str = Field(default="iceberg")
    trino_schema: str = Field(default="voyant")
    
    # DataHub
    datahub_gms_url: str = Field(default="http://localhost:8080")
    
    # Keycloak
    keycloak_url: str = Field(default="http://localhost:8180")
    keycloak_realm: str = Field(default="voyant")
    keycloak_client_id: str = Field(default="voyant-api")
    keycloak_client_secret: str = Field(default="voyant-api-secret")
    
    # Lago Billing
    lago_api_url: str = Field(default="http://localhost:3000")
    lago_api_key: str = Field(default="")
    
    # Secrets Backend
    secrets_backend: str = Field(default="env", description="env, k8s, or vault")
    
    # Feature Flags
    enable_quality: bool = Field(default=True)
    enable_billing: bool = Field(default=True)
    enable_datahub: bool = Field(default=True)
    enable_mfa: bool = Field(default=False)
    
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
