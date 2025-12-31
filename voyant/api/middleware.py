"""
API Middleware for Django.

Request ID, Tenant, Soma context, and API Version handling.
"""
from __future__ import annotations

import re
import uuid
from contextvars import ContextVar
from typing import Optional

from django.http import JsonResponse

# Context variables for request-scoped data
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="default")
api_version_var: ContextVar[str] = ContextVar("api_version", default="v1")
soma_session_id_var: ContextVar[str] = ContextVar("soma_session_id", default="")
soma_user_id_var: ContextVar[str] = ContextVar("soma_user_id", default="")
traceparent_var: ContextVar[str] = ContextVar("traceparent", default="")
authorization_var: ContextVar[str] = ContextVar("authorization", default="")

SUPPORTED_VERSIONS = ["v1"]
DEFAULT_VERSION = "v1"
CURRENT_VERSION = "v1"

VERSION_PATTERN = re.compile(r"application/vnd\.voyant\.v(\d+)\+json")


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(request_id)
        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant_id = request.headers.get("X-Tenant-ID", "default")
        tenant_id_var.set(tenant_id)
        return self.get_response(request)


class SomaContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        soma_session_id_var.set(request.headers.get("X-Soma-Session-ID", ""))
        soma_user_id_var.set(request.headers.get("X-User-ID", ""))
        traceparent_var.set(request.headers.get("traceparent", ""))
        authorization_var.set(request.headers.get("Authorization", ""))
        return self.get_response(request)


class APIVersionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in ("/health", "/ready", "/healthz", "/readyz"):
            return self.get_response(request)

        version = self._extract_version(request)
        if version and f"v{version}" not in SUPPORTED_VERSIONS:
            return JsonResponse(
                {
                    "error": "Not Acceptable",
                    "message": f"API version v{version} is not supported",
                    "supported_versions": SUPPORTED_VERSIONS,
                    "current_version": CURRENT_VERSION,
                },
                status=406,
                headers={"X-API-Version": CURRENT_VERSION},
            )

        api_version = f"v{version}" if version else DEFAULT_VERSION
        api_version_var.set(api_version)
        response = self.get_response(request)
        response["X-API-Version"] = api_version
        return response

    def _extract_version(self, request) -> Optional[str]:
        if header_version := request.headers.get("X-API-Version"):
            return header_version.lstrip("v")

        accept = request.headers.get("Accept", "")
        match = VERSION_PATTERN.search(accept)
        if match:
            return match.group(1)
        return None


def get_request_id() -> str:
    return request_id_var.get()


def get_tenant_id() -> str:
    return tenant_id_var.get()


def get_api_version() -> str:
    return api_version_var.get()


def get_soma_session_id() -> str:
    return soma_session_id_var.get()


def get_soma_user_id() -> str:
    return soma_user_id_var.get()


def get_traceparent() -> str:
    return traceparent_var.get()


def get_authorization() -> str:
    return authorization_var.get()


def get_version_info() -> dict:
    return {
        "current_version": CURRENT_VERSION,
        "supported_versions": SUPPORTED_VERSIONS,
        "default_version": DEFAULT_VERSION,
        "accept_format": "application/vnd.voyant.{version}+json",
    }
