"""GraphQL view — serves the /graphql endpoint with depth limiting."""

from __future__ import annotations

import json
import logging
from typing import Any

from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger("voyant.graphql")


@method_decorator(csrf_exempt, name="dispatch")
class GraphQLView(View):
    """Django view serving the GraphQL endpoint.

    Supports:
    - POST with JSON body: ``{"query": "...", "variables": {...}}``
    - GET with query params (for GraphiQL/IDE introspection)
    - Depth limiting (max 10 levels)
    """

    MAX_DEPTH = 10

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        return self._handle(request)

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        # Simple GET handler for IDE/playground support
        query = request.GET.get("query", "")
        variables_str = request.GET.get("variables", "{}")
        try:
            variables = json.loads(variables_str) if variables_str else {}
        except json.JSONDecodeError:
            variables = {}
        return self._execute(request, query, variables)

    def _handle(self, request: HttpRequest) -> JsonResponse:
        """Parse request body and execute the GraphQL query."""
        try:
            body = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({"errors": [{"message": "Invalid JSON body"}]}, status=400)

        query = body.get("query", "")
        variables = body.get("variables", {})
        operation_name = body.get("operationName")

        if not query:
            return JsonResponse(
                {"errors": [{"message": "No query provided"}]}, status=400
            )

        return self._execute(request, query, variables, operation_name)

    def _execute(
        self,
        request: HttpRequest,
        query: str,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
    ) -> JsonResponse:
        """Execute a GraphQL query against the schema."""
        from apps.graphql.schema import _enforce_depth_limit, get_schema

        # Depth limiting
        try:
            _enforce_depth_limit(query, self.MAX_DEPTH)
        except ValueError as exc:
            return JsonResponse(
                {"errors": [{"message": str(exc)}]}, status=400
            )

        schema = get_schema()

        # Inject tenant_id into context for tenant-scoped queries
        from apps.core.middleware import get_tenant_id

        context = type("GraphQLContext", (), {"META": request.META})()
        try:
            context.tenant_id = get_tenant_id(request)
        except Exception:
            context.tenant_id = "default"

        result = schema.execute(
            query,
            variables=variables or {},
            operation_name=operation_name,
            context_value=context,
        )

        response: dict[str, Any] = {}

        if result.errors:
            response["errors"] = [
                {
                    "message": str(err.message),
                    "locations": (
                        [{"line": loc.line, "column": loc.column} for loc in err.locations]
                        if err.locations
                        else []
                    ),
                    "path": list(err.path) if err.path else [],
                }
                for err in result.errors
            ]

        if result.data is not None:
            response["data"] = result.data

        status = 200 if not result.errors or result.data else 400
        return JsonResponse(response, status=status, safe=False)
