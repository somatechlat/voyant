"""
Unit tests for apps.core.config — Settings field defaults, validators,
Docker secrets resolution, and configuration constraints.

Real Settings construction with environment variables. No mocks.
"""

import os
import tempfile

from apps.core.config import Settings, _resolve_docker_secrets, get_settings

# ── Settings Defaults ─────────────────────────────────────────────────────────


class TestSettingsDefaults:
    """Test that Settings fields have correct default values."""

    def test_env_default(self):
        s = Settings()
        assert s.env == "local"

    def test_deployment_mode_is_valid(self):
        s = Settings()
        # May be overridden by env vars in test environment
        assert s.deployment_mode in ("integrated", "standalone")

    def test_worker_mode_default(self):
        s = Settings()
        assert s.worker_mode == "full"

    def test_debug_default(self):
        s = Settings()
        assert s.debug is False

    def test_allowed_hosts_default(self):
        s = Settings()
        assert s.allowed_hosts == ["*"]

    def test_api_host_default(self):
        s = Settings()
        assert s.api_host == "0.0.0.0"

    def test_api_port_default(self):
        s = Settings()
        assert s.api_port == 8000

    def test_mcp_port_default(self):
        s = Settings()
        assert s.mcp_port == 8001

    def test_api_workers_default(self):
        s = Settings()
        assert s.api_workers == 4

    def test_max_query_rows_default(self):
        s = Settings()
        assert s.max_query_rows == 10000

    def test_max_upload_size_mb_default(self):
        s = Settings()
        assert s.max_upload_size_mb == 100

    def test_session_ttl_hours_default(self):
        s = Settings()
        assert s.session_ttl_hours == 8

    def test_session_idle_minutes_default(self):
        s = Settings()
        assert s.session_idle_minutes == 30

    def test_temporal_namespace_default(self):
        s = Settings()
        assert s.temporal_namespace == "default"

    def test_temporal_task_queue_default(self):
        s = Settings()
        assert s.temporal_task_queue == "voyant-tasks"

    def test_trino_port_default(self):
        # Check the class-level field default (env vars may override in Docker)
        field = Settings.model_fields["trino_port"]
        assert field.default == 45090

    def test_trino_catalog_default(self):
        s = Settings()
        assert s.trino_catalog == "iceberg"

    def test_milvus_host_default(self):
        # Check the class-level field default (env vars may override in Docker)
        field = Settings.model_fields["milvus_host"]
        assert field.default == "localhost"

    def test_milvus_port_default(self):
        s = Settings()
        assert s.milvus_port == 19530

    def test_milvus_db_name_default(self):
        s = Settings()
        assert s.milvus_db_name == "voyant"

    def test_milvus_auto_create_default(self):
        s = Settings()
        assert s.milvus_auto_create is True

    def test_r_engine_port_default(self):
        s = Settings()
        assert s.r_engine_port == 45311

    def test_spicedb_endpoint_is_set(self):
        s = Settings()
        # May be overridden by env vars (e.g., localhost:50051 in test env)
        assert s.spicedb_endpoint  # Should be non-empty
        assert ":50051" in s.spicedb_endpoint

    def test_spicedb_tls_default(self):
        s = Settings()
        assert s.spicedb_tls is False

    def test_db_backend_default(self):
        s = Settings()
        assert s.db_backend == "duckdb_local"

    def test_db_max_connections_default(self):
        s = Settings()
        assert s.db_max_connections == 10

    def test_db_connection_timeout_default(self):
        s = Settings()
        assert s.db_connection_timeout == 30

    def test_db_query_timeout_default(self):
        s = Settings()
        assert s.db_query_timeout == 300

    def test_enable_quality_default(self):
        s = Settings()
        assert s.enable_quality is True

    def test_enable_datahub_is_boolean(self):
        s = Settings()
        # May be overridden by env vars in test environment
        assert isinstance(s.enable_datahub, bool)

    def test_enable_mfa_default(self):
        s = Settings()
        assert s.enable_mfa is False

    def test_enable_charts_default(self):
        s = Settings()
        assert s.enable_charts is True

    def test_enable_narrative_default(self):
        s = Settings()
        assert s.enable_narrative is True

    def test_metrics_mode_default(self):
        s = Settings()
        assert s.metrics_mode in ("off", "basic", "full")

    def test_secrets_backend_is_valid(self):
        s = Settings()
        # In local/test env, 'env' is permitted; in production, must be 'vault' or 'k8s'
        assert s.secrets_backend in ("vault", "k8s", "env")

    def test_secrets_vault_mount_point_default(self):
        s = Settings()
        assert s.secrets_vault_mount_point == "secret"

    def test_email_defaults(self):
        s = Settings()
        assert s.email_host == "localhost"
        assert s.email_port == 587
        assert s.email_use_tls is True
        assert s.email_host_user == ""
        assert s.email_host_password == ""
        assert s.default_from_email == "webmaster@localhost"

    def test_minio_bucket_name_default(self):
        s = Settings()
        assert s.minio_bucket_name == "voyant-artifacts"

    def test_minio_secure_default(self):
        s = Settings()
        assert s.minio_secure is False

    def test_scraper_defaults(self):
        s = Settings()
        assert s.scraper_default_engine in ("playwright", "httpx", "scrapy")
        assert s.scraper_default_timeout_seconds > 0
        assert isinstance(s.scraper_allow_local_hosts, bool)
        assert isinstance(s.scraper_default_ocr_language, str)
        assert isinstance(s.scraper_tls_verify, bool)
        assert s.scraper_tls_trust_store in ("system", "certifi")

    def test_prune_defaults(self):
        s = Settings()
        assert s.prune_enabled is True
        assert s.prune_interval_seconds == 3600
        assert s.prune_max_job_age_days == 30
        assert s.prune_max_artifact_age_days == 30
        assert s.prune_max_artifacts_per_tenant == 1000
        assert s.prune_dry_run is False


# ── Validators ────────────────────────────────────────────────────────────────


class TestAllowedHostsValidator:
    """Test parse_allowed_hosts validator."""

    def test_comma_separated_string(self):
        result = Settings.parse_allowed_hosts("host1.com, host2.com, host3.com")
        assert result == ["host1.com", "host2.com", "host3.com"]

    def test_json_list_string(self):
        result = Settings.parse_allowed_hosts('["host1.com", "host2.com"]')
        assert result == ["host1.com", "host2.com"]

    def test_single_host(self):
        result = Settings.parse_allowed_hosts("localhost")
        assert result == ["localhost"]

    def test_list_passthrough(self):
        result = Settings.parse_allowed_hosts(["a", "b"])
        assert result == ["a", "b"]

    def test_empty_string(self):
        result = Settings.parse_allowed_hosts("")
        assert result == []

    def test_whitespace_handling(self):
        result = Settings.parse_allowed_hosts("  a ,  b  , c ")
        assert result == ["a", "b", "c"]

    def test_invalid_json_falls_back_to_csv(self):
        result = Settings.parse_allowed_hosts("[invalid json")
        assert result == ["[invalid json"]


class TestCSRFTrustedOriginsValidator:
    """Test parse_csrf_trusted_origins validator."""

    def test_comma_separated(self):
        result = Settings.parse_csrf_trusted_origins("https://a.com, https://b.com")
        assert result == ["https://a.com", "https://b.com"]

    def test_list_passthrough(self):
        result = Settings.parse_csrf_trusted_origins(["https://a.com"])
        assert result == ["https://a.com"]

    def test_empty_string(self):
        result = Settings.parse_csrf_trusted_origins("")
        assert result == []


# ── Docker Secrets Resolution ─────────────────────────────────────────────────


class TestDockerSecretsResolution:
    """Test _resolve_docker_secrets function."""

    def test_resolves_file_env_var(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("my-secret-value")
            f.flush()
            file_path = f.name

        base_key = "VOYANT_TEST_SECRET_RESOLVE"
        file_key = f"{base_key}_FILE"

        # Clean up
        original_base = os.environ.get(base_key)
        original_file = os.environ.get(file_key)
        try:
            os.environ[file_key] = file_path
            if base_key in os.environ:
                del os.environ[base_key]

            _resolve_docker_secrets()

            assert os.environ.get(base_key) == "my-secret-value"
        finally:
            if base_key in os.environ:
                del os.environ[base_key]
            if original_base is not None:
                os.environ[base_key] = original_base
            if original_file is not None:
                os.environ[file_key] = original_file
            elif file_key in os.environ:
                del os.environ[file_key]
            os.unlink(file_path)

    def test_explicit_env_var_takes_precedence(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("file-value")
            f.flush()
            file_path = f.name

        base_key = "VOYANT_TEST_PRECEDENCE"
        file_key = f"{base_key}_FILE"

        original_base = os.environ.get(base_key)
        original_file = os.environ.get(file_key)
        try:
            os.environ[base_key] = "explicit-value"
            os.environ[file_key] = file_path

            _resolve_docker_secrets()

            assert os.environ[base_key] == "explicit-value"
        finally:
            if original_base is not None:
                os.environ[base_key] = original_base
            elif base_key in os.environ:
                del os.environ[base_key]
            if original_file is not None:
                os.environ[file_key] = original_file
            elif file_key in os.environ:
                del os.environ[file_key]
            os.unlink(file_path)

    def test_nonexistent_file_skipped(self):
        base_key = "VOYANT_TEST_NONEXISTENT"
        file_key = f"{base_key}_FILE"

        original_base = os.environ.get(base_key)
        original_file = os.environ.get(file_key)
        try:
            os.environ[file_key] = "/nonexistent/path/secret.txt"
            if base_key in os.environ:
                del os.environ[base_key]

            _resolve_docker_secrets()

            assert base_key not in os.environ
        finally:
            if original_base is not None:
                os.environ[base_key] = original_base
            elif base_key in os.environ:
                del os.environ[base_key]
            if original_file is not None:
                os.environ[file_key] = original_file
            elif file_key in os.environ:
                del os.environ[file_key]

    def test_non_file_env_vars_ignored(self):
        """Only env vars ending with _FILE should be processed."""
        original = os.environ.get("VOYANT_SOME_SETTING")
        try:
            os.environ["VOYANT_SOME_SETTING"] = "value"
            _resolve_docker_secrets()
            assert os.environ["VOYANT_SOME_SETTING"] == "value"
        finally:
            if original is not None:
                os.environ["VOYANT_SOME_SETTING"] = original
            elif "VOYANT_SOME_SETTING" in os.environ:
                del os.environ["VOYANT_SOME_SETTING"]


# ── ClassVar Keys ─────────────────────────────────────────────────────────────


class TestSettingsClassVars:
    def test_runtime_env_keys_is_set(self):
        assert isinstance(Settings.RUNTIME_ENV_KEYS, set)
        assert "env" in Settings.RUNTIME_ENV_KEYS
        assert "debug" in Settings.RUNTIME_ENV_KEYS
        assert "database_url" in Settings.RUNTIME_ENV_KEYS
        assert "redis_url" in Settings.RUNTIME_ENV_KEYS
        assert "temporal_host" in Settings.RUNTIME_ENV_KEYS

    def test_secret_keys_is_set(self):
        assert isinstance(Settings.SECRET_KEYS, set)
        assert "minio_access_key" in Settings.SECRET_KEYS
        assert "minio_secret_key" in Settings.SECRET_KEYS
        assert "keycloak_client_secret" in Settings.SECRET_KEYS
        assert "serper_api_key" in Settings.SECRET_KEYS
        assert "spicedb_grpc_preshared_key" in Settings.SECRET_KEYS
        assert "motherduck_token" in Settings.SECRET_KEYS


# ── get_settings ──────────────────────────────────────────────────────────────


class TestGetSettings:
    def test_returns_settings_instance(self):
        s = get_settings()
        assert isinstance(s, Settings)

    def test_cached(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_model_config(self):
        s = Settings()
        assert s.model_config.get("env_prefix") == "VOYANT_"
        assert s.model_config.get("extra") == "ignore"


# ── OAuth Defaults ────────────────────────────────────────────────────────────


class TestOAuthDefaults:
    def test_oauth_google_default(self):
        s = Settings()
        assert s.oauth_google == {}

    def test_oauth_github_default(self):
        s = Settings()
        assert s.oauth_github == {}

    def test_oauth_microsoft_default(self):
        s = Settings()
        assert s.oauth_microsoft == {}

    def test_oauth_okta_default(self):
        s = Settings()
        assert s.oauth_okta == {}

    def test_oauth_generic_default(self):
        s = Settings()
        assert s.oauth_generic == {}
