"""
Unit tests for apps.core.lib.circuit_breaker — State machine logic.

Real in-memory state machine. No DB, no services.
"""

import time
import threading

import pytest

from apps.core.lib.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerState,
    CircuitState,
    get_circuit_breaker,
    reset_all,
)


@pytest.fixture(autouse=True)
def clean_registry():
    reset_all()
    yield
    reset_all()


class TestCircuitBreakerConfig:
    def test_default_config(self):
        cfg = CircuitBreakerConfig()
        assert cfg.failure_threshold == 5
        assert cfg.recovery_timeout == 60
        assert cfg.success_threshold == 2

    def test_custom_config(self):
        cfg = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=10, success_threshold=1)
        assert cfg.failure_threshold == 3
        assert cfg.recovery_timeout == 10
        assert cfg.success_threshold == 1


class TestCircuitBreakerStateMachine:
    def test_starts_closed(self):
        cb = CircuitBreaker("test")
        assert cb.get_state() == CircuitState.CLOSED

    def test_successful_call_stays_closed(self):
        cb = CircuitBreaker("test")
        result = cb.call(lambda: 42)
        assert result == 42
        assert cb.get_state() == CircuitState.CLOSED

    def test_failure_increments_count(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3))
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb._state.failure_count == 1

    def test_threshold_trips_open(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3))
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.get_state() == CircuitState.OPEN

    def test_open_circuit_raises(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=1))
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(lambda: "should not run")

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=5))
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        cb.call(lambda: "ok")
        assert cb._state.failure_count == 0

    def test_recovery_timeout_transitions_to_half_open(self):
        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1),
        )
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.get_state() == CircuitState.OPEN
        time.sleep(0.15)
        assert cb.get_state() == CircuitState.HALF_OPEN

    def test_half_open_success_closes(self):
        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1, success_threshold=1),
        )
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        time.sleep(0.15)
        cb.call(lambda: "ok")
        assert cb.get_state() == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1),
        )
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        time.sleep(0.15)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.get_state() == CircuitState.OPEN

    def test_manual_reset(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=1))
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.get_state() == CircuitState.OPEN
        cb.reset()
        assert cb.get_state() == CircuitState.CLOSED


class TestCircuitBreakerMetrics:
    def test_metrics_structure(self):
        cb = CircuitBreaker("test")
        metrics = cb.get_metrics()
        assert metrics["name"] == "test"
        assert metrics["state"] == "closed"
        assert metrics["failure_count"] == 0
        assert metrics["success_count"] == 0
        assert isinstance(metrics["transitions"], list)


class TestCircuitBreakerThreadSafety:
    def test_concurrent_calls(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=100))
        errors = []

        def worker():
            try:
                cb.call(lambda: 42)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert cb.get_state() == CircuitState.CLOSED


class TestCircuitBreakerRegistry:
    def test_singleton_per_name(self):
        cb1 = get_circuit_breaker("test-service")
        cb2 = get_circuit_breaker("test-service")
        assert cb1 is cb2

    def test_different_names_different_instances(self):
        cb1 = get_circuit_breaker("service-a")
        cb2 = get_circuit_breaker("service-b")
        assert cb1 is not cb2

    def test_reset_all(self):
        cb1 = get_circuit_breaker("svc-a", CircuitBreakerConfig(failure_threshold=1))
        cb2 = get_circuit_breaker("svc-b", CircuitBreakerConfig(failure_threshold=1))
        with pytest.raises(ValueError):
            cb1.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        with pytest.raises(ValueError):
            cb2.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        reset_all()
        assert cb1.get_state() == CircuitState.CLOSED
        assert cb2.get_state() == CircuitState.CLOSED
