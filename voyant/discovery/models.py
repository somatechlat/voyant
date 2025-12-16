"""
Discovery Models

Data models for the Discovery Engine.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class ApiEndpoint:
    path: str
    method: str
    summary: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    auth_required: bool = True

@dataclass
class ApiSpec:
    title: str
    version: str
    base_url: str
    endpoints: List[ApiEndpoint] = field(default_factory=list)
    auth_type: str = "unknown"
    raw_spec: Dict[str, Any] = field(default_factory=dict)
