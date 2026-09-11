import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from django.core.exceptions import ValidationError

from apps.core.api_utils import run_async
from apps.core.config import get_settings
from apps.core.lib.temporal_client import get_temporal_client
from apps.uptp_core.schemas import TemplateExecutionRequest

logger = logging.getLogger(__name__)

# Non-blocking thread pool for Temporal workflow dispatch.
# Prevents Gunicorn sync workers from blocking on async Temporal client setup.
_temporal_dispatch_pool = ThreadPoolExecutor(
    max_workers=10, thread_name_prefix="uptp_dispatch"
)


def _dispatch_workflow(workflow_cls, args: dict, execution_urn: str) -> None:
    """Fire-and-forget Temporal workflow dispatch (runs in background thread)."""

    def _run():
        try:
            client = run_async(get_temporal_client)
            run_async(
                client.start_workflow,
                workflow_cls.run,
                args,
                id=execution_urn,
                task_queue=get_settings().temporal_task_queue,
            )
            logger.info("Dispatched workflow %s", execution_urn)
        except Exception as exc:
            logger.error("Workflow dispatch failed for %s: %s", execution_urn, exc)

    _temporal_dispatch_pool.submit(_run)


class UPTPExecutionEngine:
    """
    Central dispatcher for the Universal Parametric Template Pattern.

    Routes incoming execution requests to physical Temporal workflows or
    synchronous DuckDB/Plotly render pipelines. Temporal dispatches are
    fire-and-forget via a background thread pool to avoid blocking sync
    Django workers.
    """

    @staticmethod
    def dispatch_execution(request: TemplateExecutionRequest) -> dict[str, Any]:
        """
        Translates the Agent's generic request into the physical Temporal workflow
        or synchronous DuckDB/Plotly execution natively mapped.
        """
        logger.info(
            "[UPTP/DISPATCH] Triggering %s for %s",
            request.template_id,
            request.tenant_id,
        )

        if not request.template_id:
            raise ValidationError(
                "A valid template_id must be provided to the UPTP Engine."
            )

        job_uuid = uuid.uuid4().hex
        execution_urn = (
            f"urn:voyant:job:{request.tenant_id}:{request.template_id}:{job_uuid}"
        )

        if request.category == "ingestion":
            if request.template_id == "ingest.web.deep_research":
                from apps.scraper.deep_research_workflow import DeepResearchWorkflow

                _dispatch_workflow(
                    DeepResearchWorkflow,
                    {
                        "topic": request.params.get("topic"),
                        "max_urls": request.params.get("max_urls", 10),
                        "tenant_id": request.tenant_id,
                        "job_id": execution_urn,
                    },
                    execution_urn,
                )
                dispatch_status = "temporal_deep_research_started"
            elif request.template_id == "ingest.web.archive":
                from apps.scraper.workflow import ScrapeWorkflow

                _dispatch_workflow(
                    ScrapeWorkflow,
                    {
                        "url": request.params.get("url"),
                        "tenant_id": request.tenant_id,
                        "job_id": execution_urn,
                    },
                    execution_urn,
                )
                dispatch_status = "temporal_scrape_workflow_started"
            else:
                from apps.worker.workflows.ingest_workflow import IngestDataWorkflow

                _dispatch_workflow(
                    IngestDataWorkflow,
                    {
                        "generic_uri": request.params.get("generic_uri"),
                        "tenant_id": request.tenant_id,
                        "job_id": execution_urn,
                    },
                    execution_urn,
                )
                dispatch_status = "temporal_ingest_workflow_started"

        elif request.category == "math":
            from apps.worker.workflows.sandbox_workflow import SandboxWorkflow

            _dispatch_workflow(
                SandboxWorkflow,
                {
                    "script": request.params.get("script"),
                    "dependencies": request.params.get("dependencies", []),
                    "tenant_id": request.tenant_id,
                    "job_id": execution_urn,
                },
                execution_urn,
            )
            dispatch_status = "temporal_sandbox_workflow_started"

        elif request.category == "capsule":
            from apps.capsules.services.capsule_execution import CapsuleExecutionService

            capsule_id = request.params.get("capsule_id") or ""
            parameter_values = request.params.get("parameter_values", {})
            installation_id = request.params.get("installation_id")
            session_id = request.params.get("session_id", "")

            service = CapsuleExecutionService()
            if installation_id:
                run_result = service.run_capsule(
                    installation_id=installation_id,
                    parameter_values=parameter_values,
                    tenant_id=request.tenant_id,
                    session_id=session_id,
                )
            else:
                run_result = service.run_capsule_by_id(
                    capsule_id=capsule_id,
                    parameter_values=parameter_values,
                    tenant_id=request.tenant_id,
                    session_id=session_id,
                )

            if run_result.get("workflow_id"):
                dispatch_status = "temporal_capsule_workflow_started"
            else:
                dispatch_status = "sync_capsule_executed"
            return {
                "status": "accepted",
                "dispatch_type": dispatch_status,
                "job_urn": run_result.get("job_urn", execution_urn),
                "instance_id": run_result.get("instance_id"),
                "message": "Capsule execution dispatched.",
            }

        elif request.category == "render":
            # Route natively to synchronous engines
            if "chart" in request.template_id:
                import pandas as pd

                from apps.core.lib.plotly_engine import PlotlyRenderer

                df = pd.DataFrame(request.params.get("data", []))
                if "bar" in request.template_id:
                    result_uri = PlotlyRenderer.render_bar_comparison(
                        df,
                        x_col=request.params.get("x_col") or "",
                        y_col=request.params.get("y_col") or "",
                        tenant_id=request.tenant_id,
                    )
                elif "time_series" in request.template_id:
                    result_uri = PlotlyRenderer.render_time_series(
                        df,
                        date_col=request.params.get("date_col") or "",
                        value_col=request.params.get("value_col") or "",
                        tenant_id=request.tenant_id,
                    )
                else:
                    raise ValueError(
                        f"Unsupported chart template: {request.template_id}"
                    )

                return {
                    "status": "success",
                    "artifact_uri": result_uri,
                    "job_urn": execution_urn,
                }

            elif "document" in request.template_id:
                from apps.core.lib.pdf_engine import PDFAssembler

                template_name = request.template_id.split(".")[
                    -1
                ]  # e.g. 'benchmark' -> 'benchmark.html'

                result_uri = PDFAssembler.compile_pdf(
                    template_name=template_name,
                    params=request.params,
                    tenant_id=request.tenant_id,
                )
                return {
                    "status": "success",
                    "artifact_uri": result_uri,
                    "job_urn": execution_urn,
                }

            dispatch_status = "sync_render_executed"
        else:
            raise ValueError(
                f"Category {request.category} lacks a defined physical execution route."
            )

        return {
            "status": "accepted",
            "dispatch_type": dispatch_status,
            "job_urn": execution_urn,
            "message": (
                f"Successfully routed natively to Physical"
                f" execution engine for {request.category.value}."
            ),
        }
