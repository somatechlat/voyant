"""
Unit tests for apps.core.views — health, ready, status_view, version_view,
and _run_with_timeout.

Real Django JsonResponse objects. No mocks.
"""

import time
from concurrent.futures import TimeoutError as FuturesTimeoutError

import pytest
from django.http import HttpRequest, JsonResponse

from apps.core.views import _run_with_timeout, health, ready, status_view, version_view


# ── Helpers ───────────────────────────────────────────────────────────────────


def _dummy_request():
    """Create a minimal Django HttpRequest."""
    return HttpRequest()


# ── health view ───────────────────────────────────────────────────────────────


class TestHealthView:
    def test_returns_200(self):
        resp = health(_dummy_request())
        assert resp.status_code == 200

    def test_returns_json(self):
        resp = health(_dummy_request())
        assert isinstance(resp, JsonResponse)

    def test_contains_status(self):
        resp = health(_dummy_request())
        import json
        data = json.loads(resp.content)
        assert data["status"] == "healthy"

    def test_contains_version(self):
        resp = health(_dummy_request())
        import json
        data = json.loads(resp.content)
        assert data["version"] == "3.0.0"

    def test_contains_timestamp(self):
        resp = health(_dummy_request())
        import json
        data = json.loads(resp.content)
        assert "timestamp" in data
        assert data["timestamp"].endswith("Z")


# ── version_view ─────────────────────────────────────────────────────────────


class TestVersionView:
    def test_returns_200(self):
        resp = version_view(_dummy_request())
        assert resp.status_code == 200

    def test_returns_json(self):
        resp = version_view(_dummy_request())
        assert isinstance(resp, JsonResponse)

    def test_contains_version_info(self):
        resp = version_view(_dummy_request())
        import json
        data = json.loads(resp.content)
        assert "current_version" in data
        assert "supported_versions" in data
        assert "default_version" in data
        assert data["current_version"] == "v1"


# ── _run_with_timeout ────────────────────────────────────────────────────────


class TestRunWithTimeout:
    def test_returns_result(self):
        result = _run_with_timeout(lambda: 42, 5.0)
        assert result == 42

    def test_returns_string(self):
        result = _run_with_timeout(lambda: "hello", 5.0)
        assert result == "hello"

    def test_raises_on_timeout(self):
        def slow():
            time.sleep(10)
            return "done"

        with pytest.raises(FuturesTimeoutError):
            _run_with_timeout(slow, 0.1)

    def test_propagates_exception(self):
        def failing():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            _run_with_timeout(failing, 5.0)

    def test_fast_function_completes(self):
        def fast():
            return sum(range(100))

        result = _run_with_timeout(fast, 1.0)
        assert result == 4950


# ── ready view ────────────────────────────────────────────────────────────────


class TestReadyView:
    def test_returns_json(self):
        resp = ready(_dummy_request())
        assert isinstance(resp, JsonResponse)

    def test_contains_status(self):
        resp = ready(_dummy_request())
        import json
        data = json.loads(resp.content)
        assert "status" in data
        assert data["status"] in ("ready", "not_ready")

    def test_contains_checks(self):
        resp = ready(_dummy_request())
        import json
        data = json.loads(resp.content)
        assert "checks" in data
        assert isinstance(data["checks"], dict)

    def test_contains_timestamp(self):
        resp = ready(_dummy_request())
        import json
        data = json.loads(resp.content)
        assert "timestamp" in data
        assert data["timestamp"].endswith("Z")

    def test_duckdb_check_present(self):
        resp = ready(_dummy_request())
        import json
        data = json.loads(resp.content)
        assert "duckdb" in data["checks"]

    def test_circuit_breakers_check_present(self):
        resp = ready(_dummy_request())
        import json
        data = json.loads(resp.content)
        assert "circuit_breakers" in data["checks"]


# ── status_view ──────────────────────────────────────────────────────────────


class TestStatusView:
    def test_returns_200(self):
        resp = status_view(_dummy_request())
        assert resp.status_code == 200

    def test_returns_json(self):
        resp = status_view(_dummy_request())
        assert isinstance(resp, JsonResponse)

    def test_contains_version(self):
        resp = status_view(_dummy_request())
        import json
        data = json.loads(resp.content)
        assert data["version"] == "3.0.0"

    def test_contains_timestamp(self):
        resp = status_view(_dummy_request())
        import json
        data = json.loads(resp.content)
        assert "timestamp" in data

    def test_contains_environment(self):
        resp = status_view(_dummy_request())
        import json
        data = json.loads(resp.content)
        assert "environment" in data

    def test_contains_services(self):
        resp = status_view(_dummy_request())
        import json
        data = json.loads(resp.content)
        assert "services" in data
        assert isinstance(data["services"], dict)

    def test_contains_circuit_breakers(self):
        resp = status_view(_dummy_request())
        import json
        data = json.loads(resp.content)
        assert "circuit_breakers" in data
        assert isinstance(data["circuit_breakers"], dict)
