"""
Circuit breaker pattern implementation.

State machine: CLOSED → OPEN → HALF_OPEN → CLOSED.
"""

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(StrEnum):

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """
    Configuration for the behavior of a CircuitBreaker instance.

    Attributes:
        failure_threshold: Number of consecutive failures required to trip the breaker (open).
        recovery_timeout: Seconds to wait in the OPEN state before transitioning to HALF_OPEN.
        success_threshold: Number of consecutive successes in HALF_OPEN required to close the breaker.
    """

    failure_threshold: int = 5
    recovery_timeout: int = 60
    success_threshold: int = 2


@dataclass
class CircuitBreakerState:
    """Tracks the internal state of a CircuitBreaker instance."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    opened_at: float = 0.0


class CircuitBreaker:
    """
    A thread-safe implementation of the Circuit Breaker pattern.

    This class monitors failures in wrapped function calls. When the number of
    failures exceeds a threshold, it "trips" or "opens" the circuit and
    fast-fails subsequent calls. After a configured timeout, it enters a
    "half-open" state to probe the service's health before fully closing.

    QA Engineer: Thread-safe for use in multi-threaded applications (e.g., web servers).
    Performance Engineer: O(1) state check on the critical path, minimal overhead.
    """

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        """
        Initialize a new Circuit Breaker.

        Args:
            name: A unique name for this circuit breaker, used for logging and metrics.
            config: An optional configuration object. If not provided, defaults are used.
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState()
        self._lock = threading.Lock()
        self._state_transitions: list[tuple[str, str, float]] = []

        logger.info(
            f"Circuit breaker '{name}' initialized: "
            f"threshold={self.config.failure_threshold}, "
            f"timeout={self.config.recovery_timeout}s"
        )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection.

        This is the primary method for using the circuit breaker. It wraps the
        function call, checking the breaker's state before execution and updating
        it based on the outcome.

        Analyst: This is a critical path that affects all external service calls.

        Args:
            func: The function to execute.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            The result of the wrapped function if it succeeds.

        Raises:
            CircuitBreakerOpenError: If the circuit is in the OPEN state.
            Exception: Any exception raised by the wrapped function.
        """
        with self._lock:
            current_state = self._get_current_state()

            if current_state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN (service failing)"
                )
            # In HALF_OPEN or CLOSED state, proceed to execute the call.

        # Execute the function outside the lock to prevent blocking other threads.
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _get_current_state(self) -> CircuitState:
        """
        Determine the current state of the breaker, applying time-based logic.

        Performance Engineer: This method involves no I/O, only pure computation.
        """
        if self._state.state == CircuitState.OPEN:
            # If the recovery timeout has passed, transition to HALF_OPEN to
            # allow a probe call.
            time_since_open = time.time() - self._state.opened_at
            if time_since_open >= self.config.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)

        return self._state.state

    def record_success(self) -> None:
        """Record a successful call externally (e.g., from outside the call() wrapper)."""
        self._on_success()

    def record_failure(self) -> None:
        """Record a failed call externally (e.g., from outside the call() wrapper)."""
        self._on_failure()

    def _on_success(self):
        """Update state upon a successful call."""
        with self._lock:
            if self._state.state == CircuitState.HALF_OPEN:
                # If in HALF_OPEN, a success increments the success counter.
                self._state.success_count += 1
                if self._state.success_count >= self.config.success_threshold:
                    # If the success threshold is met, close the circuit.
                    self._transition_to(CircuitState.CLOSED)
                    self._state.failure_count = 0
                    self._state.success_count = 0
            elif self._state.state == CircuitState.CLOSED:
                # If already closed, a success simply resets any intermittent failures.
                self._state.failure_count = 0

    def _on_failure(self):
        """Update state upon a failed call."""
        with self._lock:
            self._state.last_failure_time = time.time()

            if self._state.state == CircuitState.HALF_OPEN:
                # A failure during HALF_OPEN immediately trips the breaker back to OPEN.
                self._transition_to(CircuitState.OPEN)
                self._state.opened_at = time.time()
                self._state.success_count = 0
            elif self._state.state == CircuitState.CLOSED:
                # A failure during CLOSED increments the failure counter.
                self._state.failure_count += 1
                if self._state.failure_count >= self.config.failure_threshold:
                    # If the failure threshold is met, trip the circuit to OPEN.
                    self._transition_to(CircuitState.OPEN)
                    self._state.opened_at = time.time()

    def _transition_to(self, new_state: CircuitState):
        """
        Transition the circuit breaker to a new state and log the event.

        ISO Documenter: All state transitions are logged for audibility and monitoring.
        """
        old_state = self._state.state
        if old_state != new_state:
            self._state.state = new_state
            self._state_transitions.append(
                (old_state.value, new_state.value, time.time())
            )
            logger.warning(
                f"Circuit breaker '{self.name}': {old_state.value} → {new_state.value}"
            )

    def reset(self):
        """
        Manually reset the circuit breaker to its default CLOSED state.

        UX Consultant: This provides a crucial override for operators to force
        a service to be considered healthy after manual intervention.
        """
        with self._lock:
            old_state = self._state.state
            self._state = CircuitBreakerState()
            logger.info(
                f"Circuit breaker '{self.name}' manually reset from {old_state.value}"
            )

    def get_state(self) -> CircuitState:
        """Get the current, real-time state of the circuit breaker."""
        with self._lock:
            return self._get_current_state()

    def get_metrics(self) -> dict:
        """
        Get a snapshot of the circuit breaker's metrics for monitoring.

        Performance Engineer: This exposes internal state for SRE dashboards (e.g., Prometheus).
        """
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.state.value,
                "failure_count": self._state.failure_count,
                "success_count": self._state.success_count,
                "transitions": self._state_transitions[-10:],  # Last 10 transitions
            }


class CircuitBreakerOpenError(Exception):
    """
    Raised when a call is attempted while the circuit breaker is in the OPEN state.

    Security Auditor: Exception message is generic and leaks no sensitive internal details.
    """

    pass


# Global registry of all named circuit breakers.
_circuit_breakers: dict[str, CircuitBreaker] = {}
_registry_lock = threading.Lock()


def get_circuit_breaker(
    name: str, config: CircuitBreakerConfig | None = None
) -> CircuitBreaker:
    """
    Factory function to get or create a named CircuitBreaker instance.

    This ensures that all calls for a given service name share the same
    circuit breaker instance (Singleton pattern per name).

    Analyst: Using a singleton per service name is critical for accurate health tracking.

    Args:
        name: The unique name of the service being protected (e.g., "rserve", "datahub").
        config: Optional configuration. Only used on the first creation of the breaker.

    Returns:
        The singleton CircuitBreaker instance for the given name.
    """
    with _registry_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(name, config)
        return _circuit_breakers[name]


def reset_all():
    """Reset all registered circuit breakers to their default state. For testing only."""
    with _registry_lock:
        for cb in _circuit_breakers.values():
            cb.reset()
