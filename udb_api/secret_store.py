"""Simple secret store abstraction (in-memory + optional file persistence)."""
from __future__ import annotations

import json
import os
import threading
from base64 import urlsafe_b64encode
from typing import Any, Dict, Optional

_lock = threading.RLock()


class SecretStore:
    def __init__(self, root_path: Optional[str] = None, key: Optional[str] = None):
        self.root_path = root_path
        self._mem: Dict[str, Dict[str, Any]] = {}
        if self.root_path:
            os.makedirs(self.root_path, exist_ok=True)
        self._fernet = None
        if key:
            try:
                from cryptography.fernet import Fernet  # type: ignore
                # Derive base64 key if short
                if len(key) < 32:
                    padded = (key * 32)[:32].encode()
                    key_b64 = urlsafe_b64encode(padded)
                else:
                    # assume already base64-like or usable
                    key_b64 = key.encode()
                self._fernet = Fernet(key_b64)
            except Exception:
                self._fernet = None

    def _tenant_file(self, tenant: str) -> Optional[str]:
        if not self.root_path:
            return None
        return os.path.join(self.root_path, f"{tenant}.json")

    def _load_tenant(self, tenant: str) -> Dict[str, Any]:
        if tenant in self._mem:
            return self._mem[tenant]
        data: Dict[str, Any] = {}
        path = self._tenant_file(tenant)
        if path and os.path.isfile(path):
            try:
                with open(path, "r") as f:
                    raw = f.read()
                    if self._fernet:
                        from cryptography.fernet import InvalidToken  # type: ignore
                        try:
                            raw = self._fernet.decrypt(raw.encode()).decode()
                        except InvalidToken:
                            raw = "{}"
                    data = json.loads(raw)
            except Exception:
                data = {}
        self._mem[tenant] = data
        return data

    def _persist(self, tenant: str):
        path = self._tenant_file(tenant)
        if not path:
            return
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            serialized = json.dumps(self._mem[tenant])
            if self._fernet:
                serialized = self._fernet.encrypt(serialized.encode()).decode()
            f.write(serialized)
        os.replace(tmp, path)

    def set_secret(self, tenant: str, key: str, value: Any):
        with _lock:
            data = self._load_tenant(tenant)
            data[key] = value
            self._persist(tenant)

    def get_secret(self, tenant: str, key: str) -> Optional[Any]:
        with _lock:
            data = self._load_tenant(tenant)
            return data.get(key)

    def list_secrets(self, tenant: str) -> Dict[str, Any]:
        with _lock:
            return dict(self._load_tenant(tenant))


_singleton: Optional[SecretStore] = None


def get_secret_store() -> SecretStore:
    global _singleton
    if _singleton is None:
        root = os.getenv("UDB_SECRET_STORE_PATH")
        key = os.getenv("UDB_SECRET_KEY")
        _singleton = SecretStore(root, key)
    return _singleton
