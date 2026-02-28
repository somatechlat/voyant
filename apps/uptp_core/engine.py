import logging
import uuid
from typing import Any, Dict

from django.conf import settings
from django.core.exceptions import ValidationError

from apps.core.api_utils import run_async
from apps.core.lib.temporal_client import get_temporal_client
from apps.uptp_core.schemas import TemplateExecutionRequest

logger = logging.getLogger(__name__)


class UPTPExecutionEngine:
    """
    The Central Dispatcher for the Universal Parametric Template Pattern.
    Performance Engineer Mandate: This class ONLY routes; it does not block.
    Real Execution Mandate: This delegates solely to physical Temporal queues and Render pipelines.
    """

    @staticmethod
    def dispatch_execution(request: TemplateExecutionRequest) -> Dict[str, Any]:
        """
        Translates the Agent's generic request into the physical Temporal workflow
        or synchronous DuckDB/Plotly execution natively mapped.
        """
        logger.info(
            f"[UPTP/DISPATCH] Triggering {request.template_id} for {request.tenant_id}"
        )

        if not request.template_id:
            raise ValidationError(
                "A valid template_id must be provided to the UPTP Engine."
            )

        job_uuid = uuid.uuid4().hex
        execution_urn = (
            f"urn:voyant:job:{request.tenant_id}:{request.template_id}:{job_uuid}"
        )

        client = run_async(get_temporal_client)

        if request.category == "ingestion":
            if request.template_id == "ingest.web.deep_research":
                # Route natively to Autonomous Deep Research Loop
                from apps.scraper.deep_research_workflow import DeepResearchWorkflow

                run_async(
                    client.start_workflow,
                    DeepResearchWorkflow.run,
                    {
                        "topic": request.params.get("topic"),
                        "max_urls": request.params.get("max_urls", 10),
                        "tenant_id": request.tenant_id,
                        "job_id": execution_urn,
                    },
                    id=execution_urn,
                    task_queue=settings.temporal_task_queue,
                )
                dispatch_status = "temporal_deep_research_started"
            elif request.template_id == "ingest.web.archive":
                # Route natively to Playwright Scraper Engine
                from apps.scraper.workflow import ScrapeWorkflow

                run_async(
                    client.start_workflow,
                    ScrapeWorkflow.run,
                    {
                        "url": request.params.get("url"),
                        "tenant_id": request.tenant_id,
                        "job_id": execution_urn,
                    },
                    id=execution_urn,
                    task_queue=settings.temporal_task_queue,
                )
                dispatch_status = "temporal_scrape_workflow_started"
            else:
                # Default generic database routing
                from apps.worker.workflows.ingest_workflow import IngestDataWorkflow

                run_async(
                    client.start_workflow,
                    IngestDataWorkflow.run,
                    {
                        "generic_uri": request.params.get("generic_uri"),
                        "tenant_id": request.tenant_id,
                        "job_id": execution_urn,
                    },
                    id=execution_urn,
                    task_queue=settings.temporal_task_queue,
                )
                dispatch_status = "temporal_ingest_workflow_started"

        elif request.category == "math":
            # Map natively to mathematical sandbox orchestrator
            from apps.worker.workflows.sandbox_workflow import SandboxWorkflow

            run_async(
                client.start_workflow,
                SandboxWorkflow.run,
                {
                    "script": request.params.get("script"),
                    "dependencies": request.params.get("dependencies", []),
                    "tenant_id": request.tenant_id,
                    "job_id": execution_urn,
                },
                id=execution_urn,
                task_queue=settings.temporal_task_queue,
            )
            dispatch_status = "temporal_sandbox_workflow_started"

        elif request.category == "render":
            # Route natively to synchronous engines
            if "chart" in request.template_id:
                import pandas as pd

                from apps.services.visualize.plotly_engine import PlotlyRenderer

                df = pd.DataFrame(request.params.get("data", []))
                if "bar" in request.template_id:
                    result_uri = PlotlyRenderer.render_bar_comparison(
                        df,
                        x_col=request.params.get("x_col"),
                        y_col=request.params.get("y_col"),
                        tenant_id=request.tenant_id,
                    )
                elif "time_series" in request.template_id:
                    result_uri = PlotlyRenderer.render_time_series(
                        df,
                        date_col=request.params.get("date_col"),
                        value_col=request.params.get("value_col"),
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
                from apps.services.reporting.pdf_engine import PDFAssembler

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
            "message": f"Successfully routed natively to Physical execution engine for {request.category.value}.",
        }
