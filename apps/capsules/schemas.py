"""
Pydantic schemas for Capsule validation.

ISO/IEC 29148 compliant input/output contracts.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class CapsuleStatus(str, Enum):
    DRAFT = "draft"
    CERTIFIED = "certified"
    ACTIVE = "active"
    ARCHIVED = "archived"
    SUSPENDED = "suspended"


class CapsuleInstanceStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


class StepRetryPolicy(BaseModel):
    max_attempts: int = Field(default=3, ge=1, le=10)
    backoff_seconds: int = Field(default=5, ge=1, le=300)


class ExecutionStep(BaseModel):
    step_id: str = Field(..., min_length=1, max_length=128)
    action: str = Field(..., min_length=1, max_length=256)
    condition: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    inputs: Dict[str, str] = Field(default_factory=dict)
    outputs: Dict[str, str] = Field(default_factory=dict)
    retry_policy: StepRetryPolicy = Field(default_factory=StepRetryPolicy)
    timeout_seconds: int = Field(default=60, ge=1, le=3600)

    @field_validator("step_id")
    @classmethod
    def validate_step_id(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("step_id must be alphanumeric with _ or - only")
        return v


class ParameterSchema(BaseModel):
    type: str = Field(..., pattern=r"^(string|integer|number|boolean|array|object|daterange)$")
    required: bool = Field(default=False)
    default: Any = None
    description: str = Field(default="")
    options: Optional[List[Any]] = None


class RoleCaps(BaseModel):
    max_breadth: Optional[int] = Field(default=None, ge=1, le=100)
    max_depth: Optional[int] = Field(default=None, ge=1, le=10)
    allowed_actions: Optional[List[str]] = None
    blocked_actions: Optional[List[str]] = None


class AdminOverrideRule(BaseModel):
    audited: bool = True
    requires_justification: bool = True


class CapsuleRBAC(BaseModel):
    required_permission: str = Field(..., min_length=1)
    viewer_blocked: bool = True
    analyst_caps: Optional[RoleCaps] = None
    engineer_caps: Optional[RoleCaps] = None
    admin_override: Optional[AdminOverrideRule] = None


class CapsuleSoul(BaseModel):
    system_prompt: str = Field(default="")
    personality_traits: Dict[str, float] = Field(default_factory=dict)
    neuromodulator_baseline: Dict[str, float] = Field(default_factory=dict)


class CapsuleBody(BaseModel):
    capsule_type: str = Field(default="voyant.intelligence_recipe")
    capabilities_whitelist: List[str] = Field(default_factory=list)
    resource_limits: Dict[str, Any] = Field(default_factory=dict)
    json_schema: Dict[str, Any] = Field(default_factory=dict)
    config: Dict[str, Any] = Field(default_factory=dict)
    execution_graph: List[ExecutionStep] = Field(default_factory=list)
    parameters: Dict[str, ParameterSchema] = Field(default_factory=dict)
    rbac: CapsuleRBAC = Field(default_factory=lambda: CapsuleRBAC(required_permission="execute:research"))
    output_formats: List[str] = Field(default_factory=lambda: ["pdf", "markdown"])
    triggers: List[Dict[str, Any]] = Field(default_factory=list)

    @field_validator("output_formats")
    @classmethod
    def validate_output_formats(cls, v: List[str]) -> List[str]:
        allowed = {"pdf", "xlsx", "csv", "markdown", "parquet", "json"}
        invalid = set(v) - allowed
        if invalid:
            raise ValueError(f"Invalid output formats: {invalid}. Allowed: {allowed}")
        return v


class CapsuleGovernance(BaseModel):
    constitution_ref: Dict[str, Any] = Field(default_factory=dict)
    registry_signature: Optional[str] = None
    certified_at: Optional[str] = None


class CapsuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(default="1.0.0", max_length=50)
    description: str = Field(default="", max_length=5000)
    soul: CapsuleSoul = Field(default_factory=CapsuleSoul)
    body: CapsuleBody = Field(default_factory=CapsuleBody)

    class Config:
        extra = "forbid"


class CapsuleUpdateRequest(BaseModel):
    description: Optional[str] = None
    soul: Optional[CapsuleSoul] = None
    body: Optional[CapsuleBody] = None

    class Config:
        extra = "forbid"


class CapsuleRunRequest(BaseModel):
    installation_id: str = Field(..., min_length=1)
    parameter_values: Dict[str, Any] = Field(default_factory=dict)
    tenant_id: Optional[str] = None

    class Config:
        extra = "forbid"


class CapsuleInstallRequest(BaseModel):
    capsule_id: str = Field(..., min_length=1)
    parameter_overrides: Dict[str, Any] = Field(default_factory=dict)
    tenant_id: Optional[str] = None

    class Config:
        extra = "forbid"


class CapsuleResponse(BaseModel):
    id: str
    name: str
    version: str
    description: str
    status: str
    capsule_type: str
    created_at: str
    updated_at: str


class CapsuleInstanceResponse(BaseModel):
    id: str
    capsule_id: str
    capsule_name: str
    status: str
    job_urn: str
    triggered_by: str
    started_at: str
    completed_at: Optional[str] = None


class CapsuleExecutionResult(BaseModel):
    job_urn: str
    status: str
    dispatch_type: str
    message: str


class CapsuleDiscoverResponse(BaseModel):
    id: str
    name: str
    version: str
    description: str
    capsule_type: str
    parameters: Dict[str, ParameterSchema]
    rbac: CapsuleRBAC
    install_count: int


class ImportResult(BaseModel):
    success: bool
    capsule_id: Optional[str] = None
    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
