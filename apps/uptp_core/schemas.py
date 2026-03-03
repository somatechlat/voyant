import logging
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TemplateCategory(str, Enum):
    """
    Implemented UPTP execution categories.

    Architect Mandate: ONLY categories with a real physical execution route
    in UPTPExecutionEngine.dispatch_execution() may be listed here.
    Non-implemented categories are removed until routes exist.

    Implemented:
        INGESTION  → IngestDataWorkflow / ScrapeWorkflow / DeepResearchWorkflow
        MATH       → SandboxWorkflow (Docker-isolated Python)
        RENDER     → PlotlyRenderer (charts) / PDFAssembler (documents)
    """

    INGESTION = "ingestion"
    MATH = "math"
    RENDER = "render"


class TemplateExecutionRequest(BaseModel):
    """
    The Single Universal Payload for the Data Box.
    Architect Mandate: The Agent MUST route all execution through this schema.
    Security Mandate: Strict typing prevents payload injection.
    """

    template_id: str = Field(
        ...,
        description="The exact identifier of the UPTP template "
        "(e.g., 'ingest.db.generic' or 'ml.predict.binary_classification').",
    )
    category: TemplateCategory = Field(
        ..., description="The operational layer this template belongs to."
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="The arbitrary, template-specific parameters defining the execution boundaries.",
    )
    tenant_id: str = Field(
        ..., description="CRITICAL: The isolated tenant context executing the template."
    )
    job_name: Optional[str] = Field(
        None, description="Optional human-readable alias for tracking."
    )

    class Config:
        extra = "forbid"  # Security: No undeclared fields permitted.
