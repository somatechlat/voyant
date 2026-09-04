"""
Apache SkyWalking Distributed Tracing Integration (FR-24).

Provides OpenTelemetry-based tracing that exports to SkyWalking OAP server.
Instruments Temporal activities, HTTP requests, and database queries with
distributed trace context propagation.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from apps.core.config import get_settings

logger = logging.getLogger(__name__)

_tracer_provider = None
_tracer = None


def init_tracing() -> None:
    """
    Initialize OpenTelemetry tracing with SkyWalking OTLP exporter.

    Sets up the TracerProvider with OTLP gRPC exporter pointing to the
    SkyWalking OAP server's OTLP receiver. Adds resource attributes for
    service identification.
    """
    global _tracer_provider, _tracer

    settings = get_settings()
    otlp_endpoint = getattr(settings, "skywalking_otlp_endpoint", "")

    if not otlp_endpoint:
        logger.info("SkyWalking OTLP endpoint not configured, tracing disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create(
            {
                "service.name": "voyant",
                "service.version": "3.0.0",
                "service.instance.id": os.environ.get("HOSTNAME", "local"),
            }
        )

        _tracer_provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        _tracer_provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(_tracer_provider)
        _tracer = trace.get_tracer("voyant", "3.0.0")

        logger.info("SkyWalking tracing initialized: %s", otlp_endpoint)
    except ImportError:
        logger.warning("OpenTelemetry packages not installed, tracing disabled")
    except Exception as exc:
        logger.warning("Failed to initialize SkyWalking tracing: %s", exc)


def get_tracer():
    """
    Get the Voyant tracer instance.

    Returns a no-op tracer if tracing is not initialized, so callers
    can safely call get_tracer().start_span() without null checks.
    """
    if _tracer is not None:
        return _tracer

    try:
        from opentelemetry import trace

        return trace.get_tracer("voyant", "3.0.0")
    except ImportError:
        return _NoOpTracer()


def shutdown_tracing() -> None:
    """Flush pending spans and shut down the tracer provider."""
    global _tracer_provider
    if _tracer_provider is not None:
        try:
            _tracer_provider.shutdown()
            logger.info("SkyWalking tracing shut down")
        except Exception as exc:
            logger.warning("Error shutting down tracing: %s", exc)
        finally:
            _tracer_provider = None


class _NoOpTracer:
    """Fallback tracer when OpenTelemetry is not available."""

    def start_span(self, name: str, **kwargs: Any) -> _NoOpSpan:
        return _NoOpSpan(name)


class _NoOpSpan:
    """Fallback span that does nothing."""

    def __init__(self, name: str) -> None:
        self.name = name

    def __enter__(self) -> _NoOpSpan:
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_status(self, status: Any) -> None:
        pass

    def record_exception(self, exception: Exception) -> None:
        pass

    def end(self) -> None:
        pass
