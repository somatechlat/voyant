"""
OCTOPUS Dispatcher.

Routes OctopusRequest instances to the correct ARM executor,
enforcing SSRF validation, tenant quotas, circuit breakers,
and timeouts.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

from apps.core.lib.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    get_circuit_breaker,
)
from apps.core.lib.tenant_quotas import (
    QuotaExceededException,
    ResourceType,
    record_usage,
    require_quota,
)
from apps.scraper.octopus.schemas import OctopusARM, OctopusRequest, OctopusResult
from apps.scraper.security import SSRFError, URLValidationError, validate_url

logger = logging.getLogger(__name__)


def _get_arm_executors() -> (
    dict[OctopusARM, Callable[[OctopusRequest], Coroutine[Any, Any, OctopusResult]]]
):
    """
    Lazily load ARM executor modules.

    Isolates import-time side effects so that missing optional
    dependencies for one arm do not break the entire dispatcher.
    """
    executors: dict[
        OctopusARM,
        Callable[[OctopusRequest], Coroutine[Any, Any, OctopusResult]],
    ] = {}

    try:
        from apps.scraper.octopus.arms import arm_static

        executors[OctopusARM.STATIC] = arm_static.execute
    except Exception as exc:
        logger.warning("ARM static unavailable: %s", exc)

    try:
        from apps.scraper.octopus.arms import arm_dynamic

        executors[OctopusARM.DYNAMIC] = arm_dynamic.execute
    except Exception as exc:
        logger.warning("ARM dynamic unavailable: %s", exc)

    try:
        from apps.scraper.octopus.arms import arm_evasion

        executors[OctopusARM.EVASION] = arm_evasion.execute
    except Exception as exc:
        logger.warning("ARM evasion unavailable: %s", exc)

    try:
        from apps.scraper.octopus.arms import arm_crawl

        executors[OctopusARM.CRAWL] = arm_crawl.execute
    except Exception as exc:
        logger.warning("ARM crawl unavailable: %s", exc)

    try:
        from apps.scraper.octopus.arms import arm_api_intercept

        executors[OctopusARM.API_INTERCEPT] = arm_api_intercept.execute
    except Exception as exc:
        logger.warning("ARM api_intercept unavailable: %s", exc)

    try:
        from apps.scraper.octopus.arms import arm_document

        executors[OctopusARM.DOCUMENT] = arm_document.execute
    except Exception as exc:
        logger.warning("ARM document unavailable: %s", exc)

    try:
        from apps.scraper.octopus.arms import arm_ocr

        executors[OctopusARM.OCR] = arm_ocr.execute
    except Exception as exc:
        logger.warning("ARM ocr unavailable: %s", exc)

    try:
        from apps.scraper.octopus.arms import arm_transcribe

        executors[OctopusARM.TRANSCRIBE] = arm_transcribe.execute
    except Exception as exc:
        logger.warning("ARM transcribe unavailable: %s", exc)

    try:
        from apps.scraper.octopus.arms import arm_archive

        executors[OctopusARM.ARCHIVE] = arm_archive.execute
    except Exception as exc:
        logger.warning("ARM archive unavailable: %s", exc)

    return executors


class OctopusDispatcher:
    """
    Unified dispatcher for the OCTOPUS multi-arm scraping engine.

    Validates security constraints, checks tenant quotas, applies
    circuit breaker protection, and routes requests to the correct
    ARM executor.
    """

    def __init__(self) -> None:
        pass

    async def dispatch(self, request: OctopusRequest) -> OctopusResult:
        start = datetime.now(UTC)

        # SSRF validation
        try:
            validate_url(request.url)
        except (SSRFError, URLValidationError) as exc:
            logger.warning("SSRF blocked for %s: %s", request.url, exc)
            return self._error_result(request, start, "SSRF_BLOCKED", str(exc))

        # Tenant quota check
        try:
            require_quota(request.tenant_id, ResourceType.JOBS_PER_DAY, amount=1.0)
            require_quota(request.tenant_id, ResourceType.JOBS_CONCURRENT, amount=1.0)
        except QuotaExceededException as exc:
            logger.warning("Quota exceeded for tenant %s: %s", request.tenant_id, exc)
            return self._error_result(
                request, start, "QUOTA_EXCEEDED", exc.result.message
            )

        # Record usage before execution
        record_usage(
            request.tenant_id,
            ResourceType.JOBS_PER_DAY,
            amount=1.0,
            job_id=request.job_id,
        )
        record_usage(
            request.tenant_id,
            ResourceType.JOBS_CONCURRENT,
            amount=1.0,
            job_id=request.job_id,
        )

        # Resolve executor
        executors = _get_arm_executors()
        executor = executors.get(request.arm)
        if executor is None:
            return self._error_result(
                request,
                start,
                "ARM_UNAVAILABLE",
                f"ARM {request.arm.value} is not available",
            )

        # Circuit breaker
        cb_name = f"octopus_arm_{request.arm.value}"
        cb = get_circuit_breaker(cb_name)

        # Execute with circuit breaker and timeout
        try:
            result = await self._run_with_breaker(cb, executor, request)
        except CircuitBreakerOpenError as exc:
            return self._error_result(request, start, "CIRCUIT_BREAKER_OPEN", str(exc))
        except TimeoutError:
            return self._error_result(
                request,
                start,
                "TIMEOUT",
                f"Execution exceeded {request.timeout_seconds}s",
            )
        except Exception as exc:
            logger.exception(
                "ARM %s execution failed for %s",
                request.arm.value,
                request.url,
            )
            return self._error_result(request, start, "EXECUTION_ERROR", str(exc))

        # Store artifact on success
        if result.success:
            try:
                from apps.core.lib.artifact_store import store_artifact

                ref = store_artifact(
                    content=result.model_dump(mode="json"),
                    artifact_type="octopus_result",
                    metadata={
                        "arm": request.arm.value,
                        "tenant_id": request.tenant_id,
                        "job_id": request.job_id,
                        "url": request.url,
                    },
                )
                result.artifact_uri = ref.hash
                result.artifact_size_bytes = ref.size_bytes
            except Exception:
                logger.exception("Artifact storage failed for job %s", request.job_id)

        return result

    async def _run_with_breaker(
        self,
        cb: CircuitBreaker,
        executor: Callable[[OctopusRequest], Coroutine[Any, Any, OctopusResult]],
        request: OctopusRequest,
    ) -> OctopusResult:
        """Run executor under circuit breaker protection with timeout."""
        if cb.get_state() == CircuitState.OPEN:
            raise CircuitBreakerOpenError(f"Circuit breaker '{cb.name}' is OPEN")
        try:
            result = await asyncio.wait_for(
                executor(request), timeout=request.timeout_seconds
            )
            cb._on_success()
            return result
        except Exception:
            cb._on_failure()
            raise

    def _error_result(
        self,
        request: OctopusRequest,
        start: datetime,
        error_code: str,
        error_message: str,
    ) -> OctopusResult:
        """Construct a standardized failure result."""
        duration_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return OctopusResult(
            arm=request.arm.value,
            url=request.url,
            tenant_id=request.tenant_id,
            job_id=request.job_id,
            success=False,
            duration_ms=duration_ms,
            fetched_at=start.isoformat(),
            error_code=error_code,
            error_message=error_message,
        )
