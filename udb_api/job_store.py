"""Job store abstraction supporting in-memory and Redis backends."""
from __future__ import annotations
from typing import Optional, Dict, Any
import json

try:  # optional import
    import redis  # type: ignore
except ImportError:  # pragma: no cover
    redis = None  # type: ignore

class BaseJobStore:
    def set(self, job_id: str, data: Dict[str, Any]): ...  # noqa: E701
    def get(self, job_id: str) -> Optional[Dict[str, Any]]: ...  # noqa: E701

class MemoryJobStore(BaseJobStore):
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
    def set(self, job_id: str, data: Dict[str, Any]):
        self._store[job_id] = data
    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(job_id)

class RedisJobStore(BaseJobStore):
    def __init__(self, url: str):
        if not redis:  # pragma: no cover
            raise RuntimeError("redis package not installed")
        self.client = redis.Redis.from_url(url)
    def set(self, job_id: str, data: Dict[str, Any]):
        self.client.set(job_id, json.dumps(data))
    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        raw = self.client.get(job_id)
        if not raw:
            return None
        return json.loads(raw)

_job_store: Optional[BaseJobStore] = None

def get_job_store(redis_url: Optional[str]) -> BaseJobStore:
    global _job_store
    if _job_store is not None:
        return _job_store
    if redis_url:
        try:
            _job_store = RedisJobStore(redis_url)
            return _job_store
        except Exception:
            pass
    _job_store = MemoryJobStore()
    return _job_store
