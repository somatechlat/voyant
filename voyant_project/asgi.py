"""ASGI config for Voyant."""

import os

from django.core.asgi import get_asgi_application
from django_mcp import mount_mcp_server

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")

# Get the Django ASGI application
django_asgi_app = get_asgi_application()

# Mount MCP server at /mcp endpoint
# This allows AI agents to connect to MCP tools via HTTP/SSE
application = mount_mcp_server(
    django_http_app=django_asgi_app,
    mcp_base_path="/mcp"
)
