"""Compatibility facade for security secrets APIs.

This module preserves the legacy sync interface while delegating all secret
storage operations to the centralized backend in `voyant.core.secrets`.
"""

from __future__ import annotations

import asyncio
import threading
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any, Dict, Optional

from apps.core.config import get_settings
from apps.core.lib.secrets import get_secret as core_get_secret


class SecretsBackend(ABC):
    """Synchronous compatibility interface for secrets access."""

    @abstractmethod
    def get_secret(self, path: str) -> Optional[str]:
        """Return a secret value by logical path."""

    @abstractmethod
    def get_database_credentials(self, db_name: str) -> Dict[str, Any]:
        """Return database credentials for the named database."""


class _CoreSecretsAdapter(SecretsBackend):
    """Sync adapter around the centralized async secrets backend."""

    @staticmethod
    def _run(coro):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        result: Dict[str, Any] = {}

        def _worker() -> None:
            try:
                result["value"] = asyncio.run(coro)
            except Exception as exc:  # pragma: no cover - passthrough
                result["error"] = exc

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        thread.join()

        if "error" in result:
            raise result["error"]
        return result.get("value")

    def get_secret(self, path: str) -> Optional[str]:
        return self._run(core_get_secret(path))

    def get_database_credentials(self, db_name: str) -> Dict[str, Any]:
        base = f"database/{db_name}"
        host = self.get_secret(f"{base}/host") or ""
        port_raw = self.get_secret(f"{base}/port") or ""
        username = self.get_secret(f"{base}/username") or ""
        password = self.get_secret(f"{base}/password") or ""
        database = self.get_secret(f"{base}/database") or ""
        try:
            port = int(port_raw)
        except (TypeError, ValueError):
            port = 0
        return {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "database": database,
        }


class EnvSecretsBackend(_CoreSecretsAdapter):
    """Compatibility class kept for API stability."""


class K8sSecretsBackend(_CoreSecretsAdapter):
    """Compatibility class kept for API stability."""


class VaultSecretsBackend(_CoreSecretsAdapter):
    """Compatibility class kept for API stability."""


@lru_cache
def get_secrets_backend() -> SecretsBackend:
    """Return a sync adapter selected by centralized settings."""
    backend_type = get_settings().secrets_backend.lower()
    if backend_type == "k8s":
        return K8sSecretsBackend()
    if backend_type == "vault":
        return VaultSecretsBackend()
    if backend_type == "env":
        return EnvSecretsBackend()
    return _CoreSecretsAdapter()


def get_secret(path: str) -> Optional[str]:
    """Convenience sync secret accessor."""
    return get_secrets_backend().get_secret(path)
