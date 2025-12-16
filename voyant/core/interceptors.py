"""
Temporal Interceptors

Interceptors to capture metrics and logging for Workflows and Activities.
Adheres to Vibe Coding Rules: detailed observability via Interceptor pattern.
"""
import logging
import time
from typing import Any, Callable

from temporalio import activity
from temporalio.worker import ActivityInboundInterceptor, Interceptor

from voyant.core.monitoring import MetricsRegistry

logger = logging.getLogger(__name__)

class MetricsInterceptor(Interceptor):
    def activity_inbound_interceptor(self, next_interceptor: ActivityInboundInterceptor) -> ActivityInboundInterceptor:
        return MetricsActivityInboundInterceptor(next_interceptor)

class MetricsActivityInboundInterceptor(ActivityInboundInterceptor):
    def __init__(self, next_interceptor: ActivityInboundInterceptor):
        super().__init__(next_interceptor)
        self.metrics = MetricsRegistry()

    async def execute_activity(self, input: activity.ExecuteActivityInput) -> Any:
        activity_type = input.activity_type
        start_time = time.perf_counter()
        status = "success"
        
        try:
            return await super().execute_activity(input)
        except Exception:
            status = "failed"
            raise
        finally:
            duration = time.perf_counter() - start_time
            self.metrics.activity_executions.labels(activity_type=activity_type, status=status).inc()
            self.metrics.activity_duration.labels(activity_type=activity_type).observe(duration)
