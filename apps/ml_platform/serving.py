"""
Model Serving Engine — Inference runtime for ML model predictions.

Loads trained model artifacts from MinIO/object storage, keeps them in an
LRU cache, and routes real-time + batch prediction requests to the correct
deserialized model.

Supports: pickle (.pkl), joblib (.joblib), ONNX (.onnx) formats.
"""

from __future__ import annotations

import io
import logging
import threading
import time
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Max models kept in memory
# ---------------------------------------------------------------------------
MAX_CACHED_MODELS = 10


class _ModelCache:
    """Thread-safe LRU cache for loaded model objects."""

    def __init__(self, max_size: int = MAX_CACHED_MODELS) -> None:
        self._max_size = max_size
        self._cache: OrderedDict[str, tuple[Any, dict[str, Any]]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> tuple[Any, dict[str, Any]] | None:
        with self._lock:
            if key not in self._cache:
                return None
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return self._cache[key]

    def put(self, key: str, model: Any, meta: dict[str, Any]) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = (model, meta)
                return
            if len(self._cache) >= self._max_size:
                evicted_key, _ = self._cache.popitem(last=False)
                logger.info("Evicted model from cache: %s", evicted_key)
            self._cache[key] = (model, meta)

    def remove(self, key: str) -> bool:
        with self._lock:
            return self._cache.pop(key, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._cache.keys())


# ---------------------------------------------------------------------------
# Global singleton cache
# ---------------------------------------------------------------------------
_model_cache = _ModelCache()


def _detect_format(storage_path: str) -> str:
    """Infer serialization format from file extension."""
    ext = Path(storage_path).suffix.lower()
    fmt_map = {
        ".pkl": "pickle",
        ".pickle": "pickle",
        ".joblib": "joblib",
        ".onnx": "onnx",
    }
    return fmt_map.get(ext, "pickle")


def _deserialize_model(content: bytes, fmt: str) -> Any:
    """Deserialize a model artifact from raw bytes."""
    if fmt == "onnx":
        try:
            import onnxruntime as ort  # type: ignore[import-untyped]

            return ort.InferenceSession(io.BytesIO(content))
        except ImportError:
            raise RuntimeError(
                "onnxruntime is required to load ONNX models. "
                "Install it with: pip install onnxruntime"
            )

    if fmt == "joblib":
        try:
            import joblib  # type: ignore[import-untyped]

            return joblib.load(io.BytesIO(content))
        except ImportError:
            # Fall back to pickle if joblib not available
            import pickle

            return pickle.loads(content)  # noqa: S301

    # Default: pickle
    import pickle

    return pickle.loads(content)  # noqa: S301


def _run_prediction(model: Any, input_data: Any, fmt: str) -> Any:
    """Run a prediction on a loaded model, handling format differences."""
    if fmt == "onnx":
        try:
            import onnxruntime as ort  # type: ignore[import-untyped]

            if isinstance(model, ort.InferenceSession):
                input_name = model.get_inputs()[0].name
                outputs = model.run(None, {input_name: input_data})
                result = outputs[0]
                return result.tolist() if hasattr(result, "tolist") else result
        except ImportError:
            pass

    # sklearn-compatible models (pickle / joblib)
    if hasattr(model, "predict"):
        result = model.predict(input_data)
        return result.tolist() if hasattr(result, "tolist") else result
    if hasattr(model, "transform"):
        result = model.transform(input_data)
        return result.tolist() if hasattr(result, "tolist") else result

    raise RuntimeError(
        "Loaded model has no predict() or transform() method. "
        "Ensure the artifact is a valid ML model."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class ModelServingEngine:
    """
    Inference engine that loads models from object storage and serves predictions.

    Usage::

        engine = ModelServingEngine()
        result = engine.predict(endpoint_id="abc", input_data={"features": [1, 2, 3]})
    """

    # ── Loading ──────────────────────────────────────────────────────────

    def load_model(self, model_version_id: str) -> dict[str, Any]:
        """
        Load a model artifact from storage into the in-memory LRU cache.

        Steps:
        1. Look up ModelVersion to get ``storage_path``.
        2. Fetch raw bytes from the artifact store (MinIO / local FS).
        3. Detect format and deserialize.
        4. Cache the loaded model object.

        Returns:
            dict with ``model_version_id``, ``format``, ``loaded_at``, ``cache_size``.
        """
        from apps.ml_platform.models import ModelVersion

        mv = ModelVersion.objects.filter(id=model_version_id).first()
        if not mv:
            raise ValueError(f"ModelVersion {model_version_id} not found")

        storage_path = mv.storage_path
        if not storage_path:
            raise ValueError(
                f"ModelVersion {mv.id} has no storage_path — "
                "upload a model artifact before loading."
            )

        cache_key = str(mv.id)

        # Check cache first
        cached = _model_cache.get(cache_key)
        if cached is not None:
            logger.info("Model %s already in cache", cache_key)
            return {
                "model_version_id": cache_key,
                "format": cached[1].get("format", "unknown"),
                "loaded_at": cached[1].get("loaded_at"),
                "cache_size": _model_cache.size,
                "cache_hit": True,
            }

        # Fetch raw bytes from artifact store
        content = self._fetch_artifact_bytes(storage_path)
        if content is None:
            raise RuntimeError(
                f"Could not fetch model artifact from storage_path={storage_path}"
            )

        fmt = _detect_format(storage_path)
        model_obj = _deserialize_model(content, fmt)

        meta: dict[str, Any] = {
            "format": fmt,
            "storage_path": storage_path,
            "loaded_at": datetime.now(UTC).isoformat(),
            "model_version_id": cache_key,
        }
        _model_cache.put(cache_key, model_obj, meta)

        logger.info(
            "Loaded model %s (format=%s, %d bytes) — cache size: %d",
            cache_key, fmt, len(content), _model_cache.size,
        )
        return {
            "model_version_id": cache_key,
            "format": fmt,
            "loaded_at": meta["loaded_at"],
            "cache_size": _model_cache.size,
            "cache_hit": False,
        }

    def _fetch_artifact_bytes(self, storage_path: str) -> bytes | None:
        """
        Fetch artifact bytes from MinIO / object store / local filesystem.

        Supports:
        - Local file paths (``/path/to/model.pkl``)
        - ``minio://bucket/key`` URIs
        - Content-addressable store hash references
        """
        path = Path(storage_path)

        # 1. Local file
        if path.exists():
            return path.read_bytes()

        # 2. MinIO URI
        if storage_path.startswith("minio://"):
            return self._fetch_from_minio(storage_path)

        # 3. Try artifact store (content-addressable hash)
        try:
            from apps.core.lib.artifact_store import get_artifact_store

            store = get_artifact_store()
            content = store.retrieve(storage_path)
            if content is not None:
                return content
        except Exception:
            logger.debug("Artifact store lookup failed for %s", storage_path)

        # 4. Last resort: treat storage_path as a relative path
        alt = Path("./artifacts") / storage_path
        if alt.exists():
            return alt.read_bytes()

        return None

    def _fetch_from_minio(self, uri: str) -> bytes | None:
        """Fetch a model artifact from a MinIO URI (``minio://bucket/key``)."""
        try:
            # Parse URI: minio://bucket/key
            parts = uri.replace("minio://", "").split("/", 1)
            if len(parts) < 2:
                logger.error("Invalid MinIO URI: %s", uri)
                return None

            bucket, key = parts[0], parts[1]

            try:
                from minio import Minio  # type: ignore[import-untyped]
            except ImportError:
                logger.error("minio package not installed — cannot fetch %s", uri)
                return None

            from django.conf import settings as django_settings

            client = Minio(
                getattr(django_settings, "MINIO_ENDPOINT", "localhost:9000"),
                access_key=getattr(django_settings, "MINIO_ACCESS_KEY", "minioadmin"),
                secret_key=getattr(django_settings, "MINIO_SECRET_KEY", "minioadmin"),
                secure=getattr(django_settings, "MINIO_SECURE", False),
            )

            response = client.get_object(bucket, key)
            data = response.read()
            response.close()
            response.release_conn()
            return data

        except Exception:
            logger.exception("Failed to fetch from MinIO: %s", uri)
            return None

    # ── Prediction ───────────────────────────────────────────────────────

    def predict(self, endpoint_id: str, input_data: Any) -> dict[str, Any]:
        """
        Run a real-time prediction for a single input.

        Args:
            endpoint_id: UUID of the ``ModelEndpoint``.
            input_data: Input payload (list, dict, numpy array, etc.).

        Returns:
            dict with ``prediction``, ``endpoint_id``, ``model_version_id``,
            ``latency_ms``, ``timestamp``.
        """
        from apps.ml_platform.models import ModelEndpoint

        endpoint = ModelEndpoint.objects.filter(id=endpoint_id).first()
        if not endpoint:
            raise ValueError(f"Endpoint {endpoint_id} not found")
        if endpoint.status != ModelEndpoint.STATUS_ACTIVE:
            raise RuntimeError(f"Endpoint {endpoint.name} is not active (status={endpoint.status})")
        if not endpoint.model_version_id:
            raise RuntimeError(f"Endpoint {endpoint.name} has no model_version assigned")

        mv_id = str(endpoint.model_version_id)
        cache_key = mv_id

        # Ensure model is loaded
        cached = _model_cache.get(cache_key)
        if cached is None:
            self.load_model(mv_id)
            cached = _model_cache.get(cache_key)
            if cached is None:
                raise RuntimeError(f"Failed to load model {mv_id}")

        model_obj, meta = cached
        fmt = meta.get("format", "pickle")

        start = time.monotonic()
        try:
            prediction = _run_prediction(model_obj, input_data, fmt)
            latency_ms = (time.monotonic() - start) * 1000

            # Update endpoint counters
            self._update_endpoint_stats(endpoint, latency_ms, success=True)

            # Record serving metric asynchronously
            self._record_serving_metric(endpoint, latency_ms, success=True)

            return {
                "prediction": prediction,
                "endpoint_id": str(endpoint.id),
                "endpoint_name": endpoint.name,
                "model_version_id": mv_id,
                "latency_ms": round(latency_ms, 2),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        except Exception as exc:
            latency_ms = (time.monotonic() - start) * 1000
            self._update_endpoint_stats(endpoint, latency_ms, success=False)
            self._record_serving_metric(endpoint, latency_ms, success=False)
            raise RuntimeError(f"Prediction failed on endpoint {endpoint.name}: {exc}") from exc

    def batch_predict(
        self, endpoint_id: str, input_dataset: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Run batch predictions via a Temporal workflow.

        Submits a ``BatchPredictWorkflow`` to Temporal that fans out
        predictions across the dataset and aggregates results.

        Returns:
            dict with ``workflow_id``, ``run_id``, ``status``, ``dataset_size``.
        """
        import asyncio

        from apps.ml_platform.models import ModelEndpoint

        endpoint = ModelEndpoint.objects.filter(id=endpoint_id).first()
        if not endpoint:
            raise ValueError(f"Endpoint {endpoint_id} not found")

        workflow_id = f"batch-predict-{endpoint.name}-{int(time.time())}"

        async def _start_workflow() -> dict[str, str]:
            from apps.core.lib.temporal_client import get_temporal_client

            client = await get_temporal_client()
            result = await client.start_workflow(
                "BatchPredictWorkflow",
                {
                    "endpoint_id": str(endpoint.id),
                    "endpoint_name": endpoint.name,
                    "model_version_id": str(endpoint.model_version_id),
                    "input_dataset": input_dataset,
                },
                id=workflow_id,
                task_queue="voyant-main",
            )
            return {"workflow_id": workflow_id, "run_id": result.run_id}

        try:
            wf_info = asyncio.run(_start_workflow())
            return {
                **wf_info,
                "status": "submitted",
                "dataset_size": len(input_dataset),
                "endpoint_id": str(endpoint.id),
            }
        except Exception as exc:
            logger.exception("Failed to start batch predict workflow")
            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": str(exc),
                "dataset_size": len(input_dataset),
            }

    # ── Health Check ─────────────────────────────────────────────────────

    def health_check(self) -> dict[str, Any]:
        """
        Return health information about the serving engine.

        Includes: cached model count, model load status, last prediction info.
        """
        from apps.ml_platform.models import ServingMetric

        cached_models = _model_cache.keys()

        # Get latest serving metric for error rate / last prediction
        latest_metric = ServingMetric.objects.order_by("-timestamp").first()

        return {
            "status": "healthy",
            "cached_model_count": _model_cache.size,
            "max_cache_size": MAX_CACHED_MODELS,
            "cached_model_ids": cached_models,
            "last_prediction_at": (
                latest_metric.timestamp.isoformat() if latest_metric else None
            ),
            "current_error_rate": (
                latest_metric.error_rate if latest_metric else 0.0
            ),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def get_model_status(self, model_version_id: str) -> dict[str, Any]:
        """Check whether a specific model version is loaded."""
        cached = _model_cache.get(model_version_id)
        return {
            "model_version_id": model_version_id,
            "loaded": cached is not None,
            "meta": cached[1] if cached else None,
        }

    # ── Internal Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _update_endpoint_stats(
        endpoint: Any, latency_ms: float, success: bool
    ) -> None:
        """Update the ModelEndpoint's running counters."""
        try:
            endpoint.invocation_count += 1
            # Exponential moving average for latency
            alpha = 0.1
            endpoint.avg_latency_ms = (
                alpha * latency_ms + (1 - alpha) * endpoint.avg_latency_ms
            )
            endpoint.save(update_fields=["invocation_count", "avg_latency_ms", "updated_at"])
        except Exception:
            logger.debug("Failed to update endpoint stats", exc_info=True)

    @staticmethod
    def _record_serving_metric(
        endpoint: Any, latency_ms: float, success: bool
    ) -> None:
        """Record a serving metric data point (best-effort)."""
        try:
            from apps.ml_platform.models import ServingMetric

            # Aggregate into per-minute buckets
            now = datetime.now(UTC)
            bucket = now.replace(second=0, microsecond=0)

            metric, created = ServingMetric.objects.get_or_create(
                deployment=endpoint,
                timestamp=bucket,
                defaults={
                    "latency_p50": latency_ms,
                    "latency_p95": latency_ms,
                    "latency_p99": latency_ms,
                    "throughput_rps": 0.0,
                    "error_rate": 0.0 if success else 1.0,
                    "request_count": 1,
                },
            )
            if not created:
                metric.request_count += 1
                # Simple running p-approximations
                metric.latency_p50 = (metric.latency_p50 + latency_ms) / 2
                metric.latency_p95 = max(metric.latency_p95, latency_ms)
                metric.latency_p99 = max(metric.latency_p99, latency_ms)
                if not success:
                    metric.error_rate = (
                        metric.error_rate * (metric.request_count - 1) + 1.0
                    ) / metric.request_count
                metric.throughput_rps = metric.request_count / max(
                    (now - bucket).total_seconds(), 1.0
                )
                metric.save()
        except Exception:
            logger.debug("Failed to record serving metric", exc_info=True)


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------
_serving_engine: ModelServingEngine | None = None
_engine_lock = threading.Lock()


def get_serving_engine() -> ModelServingEngine:
    """Get or create the global ModelServingEngine singleton."""
    global _serving_engine
    if _serving_engine is None:
        with _engine_lock:
            if _serving_engine is None:
                _serving_engine = ModelServingEngine()
    return _serving_engine
