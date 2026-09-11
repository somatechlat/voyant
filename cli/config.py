"""Configuration and credential management for the Voyant CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_CONFIG_DIR = Path.home() / ".voyant"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
DEFAULT_CREDENTIALS_FILE = DEFAULT_CONFIG_DIR / "credentials.json"


def get_config_dir() -> Path:
    """Return the Voyant config directory, creating it if needed."""
    config_dir = Path(os.environ.get("VOYANT_CONFIG_DIR", str(DEFAULT_CONFIG_DIR)))
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_file() -> Path:
    return get_config_dir() / "config.json"


def get_credentials_file() -> Path:
    return get_config_dir() / "credentials.json"


def load_config() -> dict:
    """Load the CLI config file."""
    config_file = get_config_file()
    if config_file.exists():
        return json.loads(config_file.read_text())
    return {}


def save_config(config: dict) -> None:
    """Save the CLI config file."""
    config_file = get_config_file()
    config_file.write_text(json.dumps(config, indent=2))


def load_credentials() -> dict:
    """Load stored credentials."""
    cred_file = get_credentials_file()
    if cred_file.exists():
        return json.loads(cred_file.read_text())
    return {}


def save_credentials(credentials: dict) -> None:
    """Save credentials with restrictive permissions."""
    cred_file = get_credentials_file()
    cred_file.write_text(json.dumps(credentials, indent=2))
    # Restrict file permissions to owner only
    os.chmod(cred_file, 0o600)


def get_api_url() -> str:
    """Get the Voyant API base URL from config or environment."""
    config = load_config()
    return (
        os.environ.get("VOYANT_API_URL")
        or config.get("api_url")
        or "http://localhost:8000/v1"
    )


def get_tenant_id() -> str:
    """Get the current tenant ID from config or environment."""
    config = load_config()
    return (
        os.environ.get("VOYANT_TENANT_ID")
        or config.get("tenant_id")
        or "default"
    )


def get_auth_token() -> str | None:
    """Get the stored auth token."""
    creds = load_credentials()
    return creds.get("access_token") or os.environ.get("VOYANT_API_TOKEN")
