"""
Secrets Backend for Voyant

Pluggable secrets management supporting:
- env: Environment variables (DEV-LOCAL)
- k8s: Kubernetes Secrets (PROD)
- vault: HashiCorp Vault (HA-PROD)
"""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any, Dict, Optional

from voyant.core.config import get_settings

logger = logging.getLogger(__name__)


class SecretsBackend(ABC):
    """Abstract base for secrets backends."""
    
    @abstractmethod
    def get_secret(self, path: str) -> Optional[str]:
        pass
    
    @abstractmethod
    def get_database_credentials(self, db_name: str) -> Dict[str, Any]:
        pass


class EnvSecretsBackend(SecretsBackend):
    """DEV-LOCAL: Environment variables."""
    
    def get_secret(self, path: str) -> Optional[str]:
        env_key = path.upper().replace("/", "_").replace("-", "_")
        return os.environ.get(env_key)
    
    def get_database_credentials(self, db_name: str) -> Dict[str, Any]:
        prefix = db_name.upper()
        return {
            "host": os.environ.get(f"{prefix}_HOST", "localhost"),
            "port": int(os.environ.get(f"{prefix}_PORT", "5432")),
            "username": os.environ.get(f"{prefix}_USER", db_name),
            "password": os.environ.get(f"{prefix}_PASSWORD", ""),
            "database": os.environ.get(f"{prefix}_DB", db_name),
        }


class K8sSecretsBackend(SecretsBackend):
    """PROD: Kubernetes mounted secrets."""
    
    def __init__(self, root: str = "/var/run/secrets/voyant"):
        self.root = root
    
    def get_secret(self, path: str) -> Optional[str]:
        file_path = os.path.join(self.root, path)
        try:
            with open(file_path, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return None
    
    def get_database_credentials(self, db_name: str) -> Dict[str, Any]:
        base = f"database/{db_name}"
        return {
            "host": self.get_secret(f"{base}/host") or "localhost",
            "port": int(self.get_secret(f"{base}/port") or "5432"),
            "username": self.get_secret(f"{base}/username") or db_name,
            "password": self.get_secret(f"{base}/password") or "",
            "database": self.get_secret(f"{base}/database") or db_name,
        }


class VaultSecretsBackend(SecretsBackend):
    """HA-PROD: HashiCorp Vault."""
    
    def __init__(self):
        self.vault_addr = os.environ.get("VAULT_ADDR", "http://vault:8200")
        self._client = None
        self._init_client()
    
    def _init_client(self):
        try:
            import hvac
            token = os.environ.get("VAULT_TOKEN")
            role = os.environ.get("VAULT_ROLE")
            
            self._client = hvac.Client(url=self.vault_addr)
            
            if token:
                self._client.token = token
            elif role:
                jwt_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
                if os.path.exists(jwt_path):
                    with open(jwt_path) as f:
                        jwt = f.read()
                    self._client.auth.kubernetes.login(role=role, jwt=jwt)
                    
        except ImportError:
            logger.warning("hvac package not installed")
        except Exception as e:
            logger.error(f"Vault init failed: {e}")
    
    def get_secret(self, path: str) -> Optional[str]:
        if not self._client or not self._client.is_authenticated():
            return None
        try:
            secret = self._client.secrets.kv.v2.read_secret_version(path=path)
            return secret["data"]["data"].get("value")
        except Exception:
            return None
    
    def get_database_credentials(self, db_name: str) -> Dict[str, Any]:
        if not self._client or not self._client.is_authenticated():
            return {}
        try:
            creds = self._client.secrets.database.generate_credentials(name=db_name)
            return {
                "username": creds["data"]["username"],
                "password": creds["data"]["password"],
            }
        except Exception:
            return {
                "host": self.get_secret(f"database/{db_name}/host") or "localhost",
                "port": int(self.get_secret(f"database/{db_name}/port") or "5432"),
                "username": self.get_secret(f"database/{db_name}/username") or db_name,
                "password": self.get_secret(f"database/{db_name}/password") or "",
                "database": self.get_secret(f"database/{db_name}/database") or db_name,
            }


@lru_cache
def get_secrets_backend() -> SecretsBackend:
    """Get configured secrets backend."""
    settings = get_settings()
    backend_type = settings.secrets_backend.lower()
    
    if backend_type == "k8s":
        return K8sSecretsBackend()
    elif backend_type == "vault":
        return VaultSecretsBackend()
    else:
        return EnvSecretsBackend()


def get_secret(path: str) -> Optional[str]:
    """Convenience function to get a secret."""
    return get_secrets_backend().get_secret(path)
