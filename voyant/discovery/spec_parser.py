"""
Spec Parser: Module for Parsing OpenAPI/Swagger API Specifications.

This module provides a robust parser for OpenAPI (v3) and Swagger (v2)
specifications. It enables the Voyant Discovery Engine to ingest raw API
definitions and transform them into a standardized internal representation,
extracting key metadata such as API title, version, base URL, and a list
of available endpoints.
"""

import logging
from typing import Any, Dict
from urllib.parse import urlparse

import requests
import yaml

from voyant.discovery.models import ApiEndpoint, ApiSpec

logger = logging.getLogger(__name__)


class SpecParser:
    """
    A parser for processing OpenAPI (v3) and Swagger (v2) API specifications.

    This class handles fetching specifications from URLs and converting their
    raw JSON/YAML content into structured `ApiSpec` and `ApiEndpoint` objects.
    It includes logic for version detection, base URL determination, and
    heuristic-based authentication type inference.
    """

    def __init__(self):
        """Initializes the SpecParser."""
        pass

    def parse_from_url(self, url: str) -> ApiSpec:
        """
        Fetches an API specification from a given URL and parses its content.

        Args:
            url (str): The URL where the OpenAPI/Swagger specification can be accessed.

        Returns:
            ApiSpec: An `ApiSpec` object representing the parsed API specification.

        Raises:
            requests.exceptions.RequestException: If fetching the URL fails.
            ValueError: If the spec format is unknown or parsing fails.
            Exception: For other unexpected errors.
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data: Dict[str, Any]
            try:
                # Attempt to parse as JSON first.
                data = response.json()
            except ValueError:
                # If JSON parsing fails, attempt to parse as YAML.
                data = yaml.safe_load(response.text)

            return self.parse_spec(data, source_url=url)

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch API specification from {url}: {e}")
            raise ValueError(f"Failed to fetch specification: {e}") from e
        except (ValueError, yaml.YAMLError) as e:
            logger.error(f"Failed to parse API specification from {url}: {e}")
            raise ValueError(f"Invalid API specification format: {e}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred parsing spec from {url}: {e}")
            raise

    def parse_spec(self, data: Dict[str, Any], source_url: str = "") -> ApiSpec:
        """
        Parses a raw API specification dictionary into an `ApiSpec` model.

        This method extracts key information such as title, version, base URL,
        endpoints, and authentication type from the provided specification data.

        Args:
            data (Dict[str, Any]): The raw dictionary content of the OpenAPI/Swagger specification.
            source_url (str, optional): The URL from which the spec was fetched, used as a fallback
                                        for determining the base URL if not explicitly defined in the spec.

        Returns:
            ApiSpec: An `ApiSpec` object representing the parsed API specification.

        Raises:
            ValueError: If the spec format is unknown or required information is missing.
        """
        # Determine the OpenAPI/Swagger version.
        is_openapi_v3 = "openapi" in data
        is_swagger_v2 = "swagger" in data

        if not (is_openapi_v3 or is_swagger_v2):
            raise ValueError(
                "Unknown API specification format. Expected 'openapi' (v3) or 'swagger' (v2) key."
            )

        info = data.get("info", {})
        title = info.get("title", "Unknown API")
        version = info.get("version", "1.0")

        # Determine the base URL for the API endpoints.
        base_url = ""
        if is_openapi_v3:
            servers = data.get("servers", [])
            if servers and isinstance(servers, list) and servers[0]:
                base_url = servers[0].get("url", "")
        elif is_swagger_v2:
            host = data.get("host", "")
            base_path = data.get("basePath", "")
            schemes = data.get("schemes", ["https"])
            scheme = schemes[0] if schemes and isinstance(schemes, list) else "https"
            if host:
                base_url = f"{scheme}://{host}{base_path}"

        # Fallback to the source URL's domain if no base URL is explicitly defined in the spec.
        if not base_url and source_url:
            parsed = urlparse(source_url)
            if parsed.scheme and parsed.netloc:
                base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Parse Endpoints: Iterate through paths and methods to extract endpoint details.
        endpoints = []
        paths = data.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                # Filter for standard HTTP methods.
                if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                    continue

                endpoints.append(
                    ApiEndpoint(
                        path=path,
                        method=method.upper(),
                        summary=details.get("summary", ""),
                        parameters=details.get("parameters", []),
                        # Determine if authentication is required for the endpoint.
                        auth_required=bool(details.get("security", [])) or bool(data.get("security", [])),
                    )
                )

        # Detect Auth Type: Heuristic based on security schemes defined in the spec.
        auth_type = "none"
        security_schemes: Dict[str, Any] = {}
        if is_openapi_v3:
            components = data.get("components", {})
            security_schemes = components.get("securitySchemes", {})
        elif is_swagger_v2:
            security_schemes = data.get("securityDefinitions", {})

        if security_schemes:
            # For simplicity, we consider the first detected scheme.
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
            raw_spec=data,  # Store the original raw spec for debugging or advanced use.
        )
