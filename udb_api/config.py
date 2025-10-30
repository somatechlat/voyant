"""Configuration loading utilities for UDB API."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration sourced from environment.

    NOTE: We intentionally do NOT wrap defaults in os.getenv so that tests which
    monkeypatch environment variables after import still influence new Settings()
    instances (since pydantic re-evaluates env on instantiation). For any value
    whose default differs from production we encode the default literal here and
    rely on env override when provided.
    """

    # pydantic-settings config: environment variables prefixed with UDB_
    model_config = SettingsConfigDict(env_prefix="UDB_", extra="ignore")

    # Core environment / infra
    environment: str = "dev"  # UDB_ENV
    airbyte_url: AnyHttpUrl = "http://airbyte-server:8001"  # AIRBYTE_URL
    airbyte_workspace_id: str | None = None  # AIRBYTE_WORKSPACE_ID
    duckdb_path: str = "data/warehouse.duckdb"  # DUCKDB_PATH (relative for portability)
    artifacts_root: str = "artifacts"  # ARTIFACTS_ROOT (relative for portability)
    redis_url: Optional[str] = None  # REDIS_URL
    kafka_brokers: Optional[str] = None  # KAFKA_BROKERS
    max_analysis_jobs: int = 2  # UDB_MAX_ANALYSIS_JOBS
    allowed_egress_domains: List[str] = []  # UDB_ALLOWED_EGRESS_DOMAINS
    tenant_header: str = "X-UDB-Tenant"  # UDB_TENANT_HEADER

    # Feature flags (bool env of 0/1 accepted by pydantic)
    enable_quality: bool = True
    enable_charts: bool = True
    enable_unstructured: bool = False
    enable_events: bool = False
    enable_tracing: bool = False
    enable_rbac: bool = True
    enable_narrative: bool = True
    metrics_mode: str = "full"  # off|basic|full (UDB_METRICS_MODE)
    enable_kestra: bool = False  # UDB_ENABLE_KESTRA
    kestra_base_url: Optional[str] = None  # UDB_KESTRA_BASE_URL
    kestra_api_token: Optional[str] = None  # UDB_KESTRA_API_TOKEN

    @field_validator("allowed_egress_domains", mode="before")
    @classmethod
    def parse_domains(cls, v):  # type: ignore
        env_v = os.getenv("UDB_ALLOWED_EGRESS_DOMAINS", "*")
        if env_v.strip() == "*":
            return ["*"]
        return [d.strip() for d in env_v.split(",") if d.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
