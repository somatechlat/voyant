"""
Presets API Routes

Pre-built analytical workflows.
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from voyant.api.middleware import get_tenant_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/presets")


# =============================================================================
# Preset Definitions (from SRS Part 6)
# =============================================================================

PRESETS = {
    # Financial
    "financial.revenue_analysis": {
        "name": "Revenue Analysis",
        "category": "financial",
        "description": "Analyze revenue trends, growth rates, and segmentation",
        "parameters": ["date_column", "amount_column", "segment_columns"],
        "output_artifacts": ["profile", "kpi", "chart"],
    },
    "financial.expense_tracking": {
        "name": "Expense Tracking",
        "category": "financial",
        "description": "Track and categorize expenses with anomaly detection",
        "parameters": ["date_column", "amount_column", "category_column"],
        "output_artifacts": ["profile", "kpi", "chart"],
    },
    "financial.margin_analysis": {
        "name": "Margin Analysis",
        "category": "financial",
        "description": "Calculate and analyze profit margins",
        "parameters": ["revenue_column", "cost_column", "segment_columns"],
        "output_artifacts": ["kpi", "chart"],
    },
    
    # Customer
    "customer.churn_analysis": {
        "name": "Churn Analysis",
        "category": "customer",
        "description": "Analyze customer churn patterns",
        "parameters": ["customer_id", "event_date", "churn_indicator"],
        "output_artifacts": ["profile", "kpi", "model"],
    },
    "customer.segmentation": {
        "name": "Customer Segmentation",
        "category": "customer",
        "description": "RFM analysis and customer clustering",
        "parameters": ["customer_id", "transaction_date", "amount"],
        "output_artifacts": ["profile", "kpi", "chart"],
    },
    "customer.ltv_prediction": {
        "name": "LTV Prediction",
        "category": "customer",
        "description": "Predict customer lifetime value",
        "parameters": ["customer_id", "revenue_history"],
        "output_artifacts": ["kpi", "model"],
    },
    
    # Quality
    "quality.data_profiling": {
        "name": "Data Profiling",
        "category": "quality",
        "description": "Comprehensive data profiling with statistics",
        "parameters": ["sample_size"],
        "output_artifacts": ["profile"],
    },
    "quality.anomaly_detection": {
        "name": "Anomaly Detection",
        "category": "quality",
        "description": "Detect data anomalies and outliers",
        "parameters": ["numeric_columns", "threshold"],
        "output_artifacts": ["quality", "chart"],
    },
    "quality.schema_validation": {
        "name": "Schema Validation",
        "category": "quality",
        "description": "Validate data against expected schema",
        "parameters": ["expected_schema"],
        "output_artifacts": ["quality"],
    },
    
    # Operations
    "ops.inventory_analysis": {
        "name": "Inventory Analysis",
        "category": "operations",
        "description": "Analyze inventory levels and turnover",
        "parameters": ["product_id", "quantity", "date"],
        "output_artifacts": ["profile", "kpi", "chart"],
    },
    "ops.supply_chain": {
        "name": "Supply Chain Analysis",
        "category": "operations",
        "description": "Analyze supply chain performance",
        "parameters": ["supplier_id", "lead_time", "cost"],
        "output_artifacts": ["kpi", "chart"],
    },
}


# =============================================================================
# Models
# =============================================================================

class PresetInfo(BaseModel):
    name: str
    category: str
    description: str
    parameters: List[str]
    output_artifacts: List[str]


class PresetExecuteRequest(BaseModel):
    source_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class PresetExecuteResponse(BaseModel):
    job_id: str
    preset_name: str
    status: str
    created_at: str


# =============================================================================
# In-memory store
# =============================================================================

_preset_jobs: Dict[str, Dict[str, Any]] = {}


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=Dict[str, List[PresetInfo]])
async def list_presets(category: Optional[str] = None):
    """List available preset workflows."""
    presets = []
    
    for key, preset in PRESETS.items():
        if category and preset["category"] != category:
            continue
        presets.append(PresetInfo(
            name=key,
            category=preset["category"],
            description=preset["description"],
            parameters=preset["parameters"],
            output_artifacts=preset["output_artifacts"],
        ))
    
    # Group by category
    grouped = {}
    for p in presets:
        if p.category not in grouped:
            grouped[p.category] = []
        grouped[p.category].append(p)
    
    return grouped


@router.get("/{preset_name}", response_model=PresetInfo)
async def get_preset(preset_name: str):
    """Get preset details."""
    if preset_name not in PRESETS:
        raise HTTPException(status_code=404, detail=f"Preset not found: {preset_name}")
    
    preset = PRESETS[preset_name]
    return PresetInfo(
        name=preset_name,
        category=preset["category"],
        description=preset["description"],
        parameters=preset["parameters"],
        output_artifacts=preset["output_artifacts"],
    )


@router.post("/{preset_name}/execute", response_model=PresetExecuteResponse)
async def execute_preset(preset_name: str, request: PresetExecuteRequest):
    """Execute a preset workflow."""
    if preset_name not in PRESETS:
        raise HTTPException(status_code=404, detail=f"Preset not found: {preset_name}")
    
    job_id = str(uuid.uuid4())
    tenant_id = get_tenant_id()
    now = datetime.utcnow().isoformat()
    
    job = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "preset_name": preset_name,
        "source_id": request.source_id,
        "parameters": request.parameters,
        "status": "queued",
        "created_at": now,
    }
    
    _preset_jobs[job_id] = job
    logger.info(f"Queued preset {preset_name} as job {job_id}")
    
    return PresetExecuteResponse(
        job_id=job_id,
        preset_name=preset_name,
        status="queued",
        created_at=now,
    )


# =============================================================================
# KPI Templates Endpoints
# =============================================================================

from voyant.core.kpi_templates import (
    list_templates as _list_kpi_templates,
    get_template as _get_kpi_template,
    render_template as _render_kpi_template,
    get_categories as _get_kpi_categories,
)


class KPITemplateInfo(BaseModel):
    name: str
    category: str
    description: str
    required_columns: List[str]
    optional_columns: Dict[str, str] = Field(default_factory=dict)
    output_columns: List[str] = Field(default_factory=list)


class KPIRenderRequest(BaseModel):
    parameters: Dict[str, str]


class KPIRenderResponse(BaseModel):
    template_name: str
    sql: str


@router.get("/kpi-templates", response_model=List[KPITemplateInfo])
async def list_kpi_templates(category: Optional[str] = None):
    """
    List available KPI SQL templates.
    
    These templates provide standard SQL patterns for common KPI calculations
    that can be applied to any compatible dataset.
    
    Args:
        category: Optional filter by category (financial, customer, quality, etc.)
    """
    templates = _list_kpi_templates(category=category)
    return [KPITemplateInfo(**t) for t in templates]


@router.get("/kpi-templates/categories", response_model=List[str])
async def list_kpi_categories():
    """List available KPI template categories."""
    return _get_kpi_categories()


@router.get("/kpi-templates/{template_name}", response_model=KPITemplateInfo)
async def get_kpi_template(template_name: str):
    """Get details for a specific KPI template."""
    template = _get_kpi_template(template_name)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_name}")
    
    return KPITemplateInfo(
        name=template.name,
        category=template.category,
        description=template.description,
        required_columns=template.required_columns,
        optional_columns=template.optional_columns,
        output_columns=template.output_columns,
    )


@router.post("/kpi-templates/{template_name}/render", response_model=KPIRenderResponse)
async def render_kpi_template(template_name: str, request: KPIRenderRequest):
    """
    Render a KPI template with provided parameters.
    
    Returns the generated SQL query ready for execution.
    
    Args:
        template_name: Name of the template to render
        request: Parameters to substitute in the template (table names, column names)
    """
    try:
        sql = _render_kpi_template(template_name, request.parameters)
        return KPIRenderResponse(template_name=template_name, sql=sql)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

