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
