"""
Unit tests for apps.core.lib.skywalking — _NoOpTracer, _NoOpSpan,
get_tracer fallback, and shutdown_tracing.

Real no-op objects. No mocks.
"""


from apps.core.lib.skywalking import (
    _NoOpSpan,
    _NoOpTracer,
    get_tracer,
    shutdown_tracing,
)

# ── _NoOpSpan Tests ──────────────────────────────────────────────────────────


class TestNoOpSpan:
    def test_creation(self):
        span = _NoOpSpan("test-span")
        assert span.name == "test-span"

    def test_context_manager_enter(self):
        span = _NoOpSpan("ctx-span")
        result = span.__enter__()
        assert result is span

    def test_context_manager_exit(self):
        span = _NoOpSpan("ctx-span")
        # Should not raise
        span.__exit__(None, None, None)

    def test_context_manager_with_statement(self):
        with _NoOpSpan("with-span") as span:
            assert span.name == "with-span"

    def test_set_attribute_noop(self):
        span = _NoOpSpan("attr-span")
        # Should not raise
        span.set_attribute("key", "value")
        span.set_attribute("count", 42)

    def test_set_status_noop(self):
        span = _NoOpSpan("status-span")
        # Should not raise
        span.set_status("OK")

    def test_record_exception_noop(self):
        span = _NoOpSpan("exc-span")
        # Should not raise
        span.record_exception(ValueError("test error"))

    def test_end_noop(self):
        span = _NoOpSpan("end-span")
        # Should not raise
        span.end()


# ── _NoOpTracer Tests ────────────────────────────────────────────────────────


class TestNoOpTracer:
    def test_start_span_returns_noop_span(self):
        tracer = _NoOpTracer()
        span = tracer.start_span("my-operation")
        assert isinstance(span, _NoOpSpan)
        assert span.name == "my-operation"

    def test_start_span_with_kwargs(self):
        tracer = _NoOpTracer()
        span = tracer.start_span("op", attributes={"key": "val"})
        assert isinstance(span, _NoOpSpan)

    def test_multiple_spans_independent(self):
        tracer = _NoOpTracer()
        span1 = tracer.start_span("op1")
        span2 = tracer.start_span("op2")
        assert span1.name == "op1"
        assert span2.name == "op2"
        assert span1 is not span2


# ── get_tracer Tests ─────────────────────────────────────────────────────────


class TestGetTracer:
    def test_returns_tracer_when_not_initialized(self):
        """When _tracer is None, get_tracer should return a usable tracer."""
        import apps.core.lib.skywalking as sw_module

        original = sw_module._tracer
        try:
            sw_module._tracer = None
            tracer = get_tracer()
            # Should be usable — either a real OTel tracer or a NoOpTracer
            span = tracer.start_span("test")
            assert span is not None
            # Clean up span
            if hasattr(span, "end"):
                span.end()
        finally:
            sw_module._tracer = original

    def test_returns_initialized_tracer(self):
        """When _tracer is set, get_tracer should return it."""
        import apps.core.lib.skywalking as sw_module

        original = sw_module._tracer
        noop = _NoOpTracer()
        try:
            sw_module._tracer = noop
            result = get_tracer()
            assert result is noop
        finally:
            sw_module._tracer = original


# ── shutdown_tracing Tests ────────────────────────────────────────────────────


class TestShutdownTracing:
    def test_shutdown_when_not_initialized(self):
        """Shutdown should be safe when _tracer_provider is None."""
        import apps.core.lib.skywalking as sw_module

        original = sw_module._tracer_provider
        try:
            sw_module._tracer_provider = None
            # Should not raise
            shutdown_tracing()
            assert sw_module._tracer_provider is None
        finally:
            sw_module._tracer_provider = original

    def test_shutdown_clears_provider(self):
        """After shutdown, _tracer_provider should be None."""
        import apps.core.lib.skywalking as sw_module

        original_provider = sw_module._tracer_provider
        original_tracer = sw_module._tracer
        try:
            # Set a mock provider that has a shutdown method
            class FakeProvider:
                def __init__(self):
                    self.shutdown_called = False

                def shutdown(self):
                    self.shutdown_called = True

            fake = FakeProvider()
            sw_module._tracer_provider = fake
            shutdown_tracing()
            assert fake.shutdown_called is True
            assert sw_module._tracer_provider is None
        finally:
            sw_module._tracer_provider = original_provider
            sw_module._tracer = original_tracer

    def test_shutdown_handles_exception(self):
        """Shutdown should not raise even if provider.shutdown() fails."""
        import apps.core.lib.skywalking as sw_module

        original_provider = sw_module._tracer_provider
        try:

            class BadProvider:
                def shutdown(self):
                    raise RuntimeError("shutdown failed")

            sw_module._tracer_provider = BadProvider()
            # Should not raise
            shutdown_tracing()
            assert sw_module._tracer_provider is None
        finally:
            sw_module._tracer_provider = original_provider
