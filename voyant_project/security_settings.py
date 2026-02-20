"""
Voyant Security Configuration Module.

This module provides security-specific configuration that can be enabled
in production environments to enhance security posture and meet compliance
requirements.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from apps.core.config import get_settings


class SecuritySettings(BaseSettings):
    """
    Security configuration for Voyant.

    These settings are designed to meet ISO/IEC 27001 security requirements
    and provide defense-in-depth security controls.
    """

    model_config = SettingsConfigDict(
        env_prefix="VOYANT_SECURITY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --------------------------------------------------------------------------
    # Authentication and Authorization
    # --------------------------------------------------------------------------
    jwt_algorithm: str = Field(
        default="RS256",
        description="JWT signing algorithm (RS256 recommended for production).",
    )
    jwt_expiration_hours: int = Field(
        default=8, description="JWT token expiration time in hours."
    )
    jwt_issuer: str = Field(
        default="voyant-api", description="JWT token issuer (iss claim)."
    )
    jwt_audience: str = Field(
        default="voyant-clients", description="JWT token audience (aud claim)."
    )

    # --------------------------------------------------------------------------
    # Security Headers
    # --------------------------------------------------------------------------
    security_enabled: bool = Field(
        default=True, description="Enable security headers and protections."
    )
    hsts_enabled: bool = Field(
        default=True, description="Enable HTTP Strict Transport Security."
    )
    hsts_max_age: int = Field(
        default=31536000, description="HSTS max age in seconds (1 year)."
    )
    hsts_include_subdomains: bool = Field(
        default=True, description="Include subdomains in HSTS policy."
    )
    hsts_preload: bool = Field(default=True, description="Enable HSTS preload.")
    content_security_policy: str = Field(
        default=(
            "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'"
        ),
        description="Content Security Policy header.",
    )
    x_frame_options: str = Field(
        default="DENY", description="X-Frame-Options header value."
    )
    x_content_type_options: str = Field(
        default="nosniff", description="X-Content-Type-Options header value."
    )
    referrer_policy: str = Field(
        default="strict-origin-when-cross-origin",
        description="Referrer-Policy header value.",
    )

    # --------------------------------------------------------------------------
    # Rate Limiting
    # --------------------------------------------------------------------------
    rate_limit_enabled: bool = Field(
        default=True, description="Enable rate limiting for API endpoints."
    )
    rate_limit_requests_per_minute: int = Field(
        default=60, description="Maximum requests per minute per client."
    )
    rate_limit_burst_size: int = Field(
        default=10, description="Maximum burst size for rate limiting."
    )
    rate_limit_window_seconds: int = Field(
        default=60, description="Rate limiting window in seconds."
    )

    # --------------------------------------------------------------------------
    # CORS Configuration
    # --------------------------------------------------------------------------
    cors_enabled: bool = Field(default=True, description="Enable CORS headers.")
    cors_allow_origins: List[str] = Field(
        default=["*"], description="List of allowed CORS origins."
    )
    cors_allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="List of allowed HTTP methods.",
    )
    cors_allow_headers: List[str] = Field(
        default=["*"], description="List of allowed HTTP headers."
    )
    cors_allow_credentials: bool = Field(
        default=True, description="Allow credentials in CORS requests."
    )
    cors_max_age: int = Field(default=3600, description="CORS max age in seconds.")

    # --------------------------------------------------------------------------
    # Database Security
    # --------------------------------------------------------------------------
    database_ssl_require: bool = Field(
        default=True, description="Require SSL for database connections."
    )
    database_ssl_cert: Optional[str] = Field(
        default=None, description="Path to SSL certificate for database connections."
    )
    database_ssl_key: Optional[str] = Field(
        default=None, description="Path to SSL key for database connections."
    )
    database_ssl_root_cert: Optional[str] = Field(
        default=None,
        description="Path to SSL root certificate for database connections.",
    )

    # --------------------------------------------------------------------------
    # Secrets Management
    # --------------------------------------------------------------------------
    secrets_backend: str = Field(
        default="env", description="Secrets backend: 'env', 'k8s', 'vault', 'file'."
    )
    secrets_vault_url: Optional[str] = Field(
        default=None, description="HashiCorp Vault URL."
    )
    secrets_vault_token: Optional[str] = Field(
        default=None, description="HashiCorp Vault token."
    )
    secrets_vault_mount_point: str = Field(
        default="voyant", description="Vault secrets mount point."
    )
    secrets_encryption_key: Optional[str] = Field(
        default=None, description="Fernet encryption key for file-based secrets."
    )

    # --------------------------------------------------------------------------
    # Audit Logging
    # --------------------------------------------------------------------------
    audit_log_enabled: bool = Field(
        default=True, description="Enable comprehensive audit logging."
    )
    audit_log_level: str = Field(
        default="INFO", description="Audit log level (DEBUG, INFO, WARNING, ERROR)."
    )
    audit_log_file: Optional[str] = Field(
        default="/var/log/voyant/audit.log", description="Path to audit log file."
    )
    audit_log_retention_days: int = Field(
        default=365, description="Audit log retention period in days."
    )
    audit_log_include_requests: bool = Field(
        default=True, description="Include HTTP requests in audit logs."
    )
    audit_log_include_responses: bool = Field(
        default=True, description="Include HTTP responses in audit logs."
    )
    audit_log_include_user_actions: bool = Field(
        default=True, description="Include user actions in audit logs."
    )

    # --------------------------------------------------------------------------
    # Security Monitoring
    # --------------------------------------------------------------------------
    security_monitoring_enabled: bool = Field(
        default=True, description="Enable security event monitoring."
    )
    security_monitoring_alerts: bool = Field(
        default=True, description="Enable security alert notifications."
    )
    security_monitoring_threshold_failed_logins: int = Field(
        default=5, description="Threshold for failed login alerts."
    )
    security_monitoring_threshold_suspicious_requests: int = Field(
        default=100, description="Threshold for suspicious request alerts."
    )
    security_monitoring_block_ip_on_failure: bool = Field(
        default=True, description="Block IP after failed login attempts."
    )
    security_monitoring_block_duration_minutes: int = Field(
        default=30, description="Duration of IP block in minutes."
    )

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v or []

    @field_validator("cors_allow_methods", mode="before")
    @classmethod
    def parse_cors_methods(cls, v):
        """Parse CORS methods from string or list."""
        if isinstance(v, str):
            return [method.strip() for method in v.split(",") if method.strip()]
        return v or []

    @field_validator("cors_allow_headers", mode="before")
    @classmethod
    def parse_cors_headers(cls, v):
        """Parse CORS headers from string or list."""
        if isinstance(v, str):
            return [header.strip() for header in v.split(",") if header.strip()]
        return v or []

    @field_validator("security_enabled")
    @classmethod
    def validate_security_enabled(cls, v):
        """Ensure security is enabled in production."""
        if get_settings().env == "production" and not v:
            raise ValueError("Security must be enabled in production")
        return v

    @field_validator("secrets_backend")
    @classmethod
    def validate_secrets_backend(cls, v, info: ValidationInfo):
        """Validate secrets backend configuration."""
        if v == "vault":
            vault_url = (
                info.data.get("secrets_vault_url") or get_settings().secrets_vault_url
            )
            if not vault_url:
                raise ValueError("Vault URL required when using vault backend")
        return v

    @field_validator("database_ssl_require")
    @classmethod
    def validate_database_ssl(cls, v, info: ValidationInfo):
        """Validate database SSL configuration."""
        if v and not info.data.get("database_ssl_cert"):
            import warnings

            warnings.warn(
                "Database SSL required but certificate not configured", UserWarning
            )
        return v

    def get_security_headers(self) -> dict:
        """
        Get security headers for HTTP responses.

        Returns:
            Dictionary of security headers.
        """
        headers = {}

        if self.security_enabled:
            # Content Security Policy
            headers["Content-Security-Policy"] = self.content_security_policy

            # X-Frame-Options
            headers["X-Frame-Options"] = self.x_frame_options

            # X-Content-Type-Options
            headers["X-Content-Type-Options"] = self.x_content_type_options

            # Referrer Policy
            headers["Referrer-Policy"] = self.referrer_policy

            # HSTS (if enabled)
            if self.hsts_enabled:
                hsts_value = f"max-age={self.hsts_max_age}"
                if self.hsts_include_subdomains:
                    hsts_value += "; includeSubDomains"
                if self.hsts_preload:
                    hsts_value += "; preload"
                headers["Strict-Transport-Security"] = hsts_value

        return headers

    def get_cors_headers(self) -> dict:
        """
        Get CORS headers for HTTP responses.

        Returns:
            Dictionary of CORS headers.
        """
        if not self.cors_enabled:
            return {}

        headers = {
            "Access-Control-Allow-Origin": ", ".join(self.cors_allow_origins),
            "Access-Control-Allow-Methods": ", ".join(self.cors_allow_methods),
            "Access-Control-Allow-Headers": ", ".join(self.cors_allow_headers),
            "Access-Control-Max-Age": str(self.cors_max_age),
        }

        if self.cors_allow_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"

        return headers


# Global security settings instance
security_settings = SecuritySettings()
