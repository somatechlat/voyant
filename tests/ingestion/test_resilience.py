"""
Integration tests for Resilience and Circuit Breakers.
No mocks - testing real state machine behavior.
"""

import time

import pytest

from apps.core.lib.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
)


class TestResilienceIntegration:
    """
    Verifies the circuit breaker and resilience logic.
    """

    @pytest.fixture
    def breaker(self):
        # Use a low threshold and timeout for fast testing
        config = CircuitBreakerConfig(
            failure_threshold=3, recovery_timeout=2, success_threshold=1
        )
        return CircuitBreaker("test-resilience", config)

    def test_circuit_breaker_tripping(self, breaker):
        """Verify that the breaker trips after N failures."""

        def failing_func():
            raise ValueError("Service failure")

        # 1. First 2 failures (threshold is 3)
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)
            assert breaker.get_state() == CircuitState.CLOSED

        # 2. 3rd failure trips the breaker
        with pytest.raises(ValueError):
            breaker.call(failing_func)

        assert breaker.get_state() == CircuitState.OPEN

        # 3. Subsequent call should fast-fail with CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError) as exc:
            breaker.call(failing_func)
        assert "is OPEN" in str(exc.value)

    def test_circuit_breaker_recovery(self, breaker):
        """Verify that the breaker recovers after timeout."""

        def failing_func():
            raise ValueError("Service failure")

        def success_func():
            return "ok"

        # 1. Trip the breaker
        for _ in range(3):
            with pytest.raises(ValueError):
                breaker.call(failing_func)
        assert breaker.get_state() == CircuitState.OPEN

        # 2. Wait for recovery timeout (2s)
        time.sleep(2.1)

        # 3. Next call should be HALF_OPEN and allowed to probe
        # On success, it should CLOSE the breaker (success_threshold=1)
        result = breaker.call(success_func)
        assert result == "ok"
        assert breaker.get_state() == CircuitState.CLOSED

    def test_circuit_breaker_half_open_failure(self, breaker):
        """Verify that a failure in HALF_OPEN immediately re-opens the breaker."""

        def failing_func():
            raise ValueError("Service failure")

        # 1. Trip the breaker
        for _ in range(3):
            with pytest.raises(ValueError):
                breaker.call(failing_func)
        assert breaker.get_state() == CircuitState.OPEN

        # 2. Wait for recovery timeout
        time.sleep(2.1)

        # 3. Fail during HALF_OPEN
        with pytest.raises(ValueError):
            breaker.call(failing_func)

        # Should be OPEN again immediately
        assert breaker.get_state() == CircuitState.OPEN
