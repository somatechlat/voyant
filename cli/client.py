"""HTTP client wrapper for Voyant API calls."""

from __future__ import annotations

import json
import sys
from typing import Any

import httpx

from cli.config import get_api_url, get_auth_token, get_tenant_id


class VoyantClient:
    """HTTP client for the Voyant API."""

    def __init__(self, base_url: str | None = None, token: str | None = None, tenant_id: str | None = None):
        self.base_url = (base_url or get_api_url()).rstrip("/")
        self.token = token or get_auth_token()
        self.tenant_id = tenant_id or get_tenant_id()

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Tenant-ID": self.tenant_id,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> httpx.Response:
        """Make an HTTP request to the Voyant API."""
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.request(
                    method,
                    url,
                    headers=self._headers(),
                    json=json_body,
                    params=params,
                )
                return response
        except httpx.ConnectError:
            print(f"Error: Cannot connect to Voyant API at {self.base_url}", file=sys.stderr)
            sys.exit(1)
        except httpx.TimeoutException:
            print(f"Error: Request timed out after {timeout}s", file=sys.stderr)
            sys.exit(1)

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("DELETE", path, **kwargs)


def format_output(data: Any, output_format: str = "table") -> str:
    """Format data for CLI output."""
    if output_format == "json":
        return json.dumps(data, indent=2)

    if isinstance(data, list) and data and isinstance(data[0], dict):
        # Table format
        headers = list(data[0].keys())
        lines = []
        # Header
        widths = {h: len(h) for h in headers}
        for row in data:
            for h in headers:
                widths[h] = max(widths[h], len(str(row.get(h, ""))))
        header_line = "  ".join(h.ljust(widths[h]) for h in headers)
        separator = "  ".join("-" * widths[h] for h in headers)
        lines.append(header_line)
        lines.append(separator)
        for row in data:
            line = "  ".join(str(row.get(h, "")).ljust(widths[h]) for h in headers)
            lines.append(line)
        return "\n".join(lines)

    if isinstance(data, dict):
        lines = [f"{k}: {v}" for k, v in data.items()]
        return "\n".join(lines)

    return str(data)


def handle_response(response: httpx.Response, output_format: str = "table") -> Any:
    """Handle API response, printing errors and returning data."""
    if response.status_code >= 400:
        try:
            detail = response.json()
            msg = detail.get("detail", detail.get("message", str(detail)))
        except Exception:
            msg = response.text
        print(f"Error ({response.status_code}): {msg}", file=sys.stderr)
        sys.exit(1)

    if response.status_code == 204 or not response.content:
        return None

    data = response.json()
    return data
