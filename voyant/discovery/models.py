"""
Discovery Models: Data Structures for API and Service Discovery.

This module defines the core data models used within the Voyant Discovery Engine.
These dataclasses provide a standardized structure for representing information
about discovered APIs, including their endpoints, specifications, and authentication
details.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ApiEndpoint:
    """
    Represents a single API endpoint (path and method) of a discovered service.

    Attributes:
        path (str): The URL path of the endpoint (e.g., "/users/{id}").
        method (str): The HTTP method of the endpoint (e.g., "GET", "POST").
        summary (str): A brief summary or description of the endpoint's function.
        parameters (List[Dict[str, Any]]): A list of dictionaries describing the endpoint's parameters.
                                            Each dict typically includes 'name', 'in' (query, header, path), 'type', 'required'.
        auth_required (bool): Indicates whether authentication is required to access this endpoint.
    """

    path: str
    method: str
    summary: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    auth_required: bool = True


@dataclass
class ApiSpec:
    """
    Represents a parsed API specification, containing high-level information
    and a list of its endpoints.

    This acts as a standardized internal representation of an OpenAPI/Swagger
    specification.

    Attributes:
        title (str): The title of the API.
        version (str): The version of the API (e.g., "1.0.0").
        base_url (str): The base URL for the API endpoints.
        endpoints (List[ApiEndpoint]): A list of `ApiEndpoint` objects defined by the specification.
        auth_type (str): The type of authentication used by the API (e.g., "OAuth2", "Bearer", "API_KEY").
        raw_spec (Dict[str, Any]): The raw, unparsed dictionary representation of the original API specification.
    """

    title: str
    version: str
    base_url: str
    endpoints: List[ApiEndpoint] = field(default_factory=list)
    auth_type: str = "unknown"
    raw_spec: Dict[str, Any] = field(default_factory=dict)
