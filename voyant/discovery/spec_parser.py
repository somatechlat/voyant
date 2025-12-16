"""
Spec Parser

Parses OpenAPI/Swagger specifications.
Adheres to Vibe Coding Rules: Robust parsing logic.
"""
import logging
from typing import Any, Dict, Optional
import requests
import yaml
import json
from urllib.parse import urlparse

from voyant.discovery.models import ApiSpec, ApiEndpoint

logger = logging.getLogger(__name__)

class SpecParser:
    """
    Parses OpenAPI/Swagger specs (v2, v3).
    """

    def parse_from_url(self, url: str) -> ApiSpec:
        """
        Fetch and parse a spec from a URL.
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Try JSON first
            try:
                data = response.json()
            except ValueError:
                # Try YAML
                data = yaml.safe_load(response.text)
                
            return self.parse_spec(data, source_url=url)
            
        except Exception as e:
            logger.error(f"Failed to fetch spec from {url}: {e}")
            raise

    def parse_spec(self, data: Dict[str, Any], source_url: str = "") -> ApiSpec:
        """
        Parse raw spec dictionary into ApiSpec model.
        """
        # Detect version
        is_openapi_v3 = "openapi" in data
        is_swagger_v2 = "swagger" in data
        
        if not (is_openapi_v3 or is_swagger_v2):
             raise ValueError("Unknown spec format. Expected 'openapi' or 'swagger' key.")

        info = data.get("info", {})
        title = info.get("title", "Unknown API")
        version = info.get("version", "1.0")
        
        # Determine Base URL
        base_url = ""
        if is_openapi_v3:
            servers = data.get("servers", [])
            if servers:
                base_url = servers[0].get("url", "")
        elif is_swagger_v2:
            host = data.get("host", "")
            base_path = data.get("basePath", "")
            schemes = data.get("schemes", ["https"])
            scheme = schemes[0] if schemes else "https"
            if host:
                base_url = f"{scheme}://{host}{base_path}"
        
        if not base_url and source_url:
             # Fallback to source domain
             parsed = urlparse(source_url)
             base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Parse Endpoints
        endpoints = []
        paths = data.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                    continue
                    
                endpoints.append(ApiEndpoint(
                    path=path,
                    method=method.upper(),
                    summary=details.get("summary", ""),
                    parameters=details.get("parameters", []),
                    auth_required=bool(details.get("security", [])) or bool(data.get("security", []))
                ))

        # Detect Auth Type (Heuristic)
        auth_type = "none"
        security_schemes = {}
        if is_openapi_v3:
            components = data.get("components", {})
            security_schemes = components.get("securitySchemes", {})
        elif is_swagger_v2:
            security_schemes = data.get("securityDefinitions", {})
            
        if security_schemes:
            # Taking the first one found for simplicity in Phase 4 MVP
            first_scheme = list(security_schemes.values())[0]
            scheme_type = first_scheme.get("type", "").lower()
            if scheme_type == "apikey":
                auth_type = "ApiKey"
            elif scheme_type == "http" and first_scheme.get("scheme") == "bearer":
                auth_type = "Bearer"
            elif scheme_type == "oauth2":
                auth_type = "OAuth2"
            else:
                auth_type = scheme_type

        return ApiSpec(
            title=title,
            version=version,
            base_url=base_url,
            endpoints=endpoints,
            auth_type=auth_type,
            raw_spec=data
        )
