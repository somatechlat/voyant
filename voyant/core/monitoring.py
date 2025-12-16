"""
Monitoring Core

Prometheus metrics registry and setup.
Adheres to Vibe Coding Rules: Singleton pattern for global metrics.
"""
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import logging

logger = logging.getLogger(__name__)

class MetricsRegistry:
    """
    Central registry for Prometheus metrics.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetricsRegistry, cls).__new__(cls)
            cls._instance._init_metrics()
        return cls._instance

    def _init_metrics(self):
        # Activity Metrics
        self.activity_executions = Counter(
            'voyant_activity_executions_total',
            'Total number of activity executions',
            ['activity_type', 'status']
        )
        self.activity_duration = Histogram(
            'voyant_activity_duration_seconds',
            'Time spent executing activities',
            ['activity_type']
        )
        
        # Workflow Metrics
        self.workflow_executions = Counter(
            'voyant_workflow_executions_total',
            'Total number of workflow executions',
            ['workflow_type', 'status']
        )
        
        # Circuit Breaker Metrics
        self.circuit_breaker_state = Gauge(
            'voyant_circuit_breaker_state',
            'Current circuit breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)',
            ['service']
        )
        self.circuit_breaker_transitions = Counter(
            'voyant_circuit_breaker_transitions_total',
            'Circuit breaker state transitions',
            ['service', 'from_state', 'to_state']
        )
        self.circuit_breaker_failures = Counter(
            'voyant_circuit_breaker_failures_total',
            'Total failures recorded by circuit breaker',
            ['service']
        )


    def start_server(self, port: int = 9090):
        """Start Prometheus HTTP server."""
        try:
            start_http_server(port)
            logger.info(f"Prometheus metrics server started on port {port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            raise  # Re-raise to notify caller of failure
