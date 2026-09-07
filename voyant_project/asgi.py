"""ASGI config for Voyant — HTTP + MCP + WebSocket (optional)."""

import os

from django.core.asgi import get_asgi_application
from django_mcp import mount_mcp_server

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")

# Get the Django ASGI application
django_asgi_app = get_asgi_application()

# MCP server mounted at /mcp
application = mount_mcp_server(django_http_app=django_asgi_app, mcp_base_path="/mcp")

# Try to add WebSocket support if channels is installed
try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.sessions import SessionMiddlewareStack
    from django.urls import path

    websocket_urlpatterns = [
        path("ws/scraper/", __import__("apps.scraper.visual.consumer", fromlist=["ScraperConsumer"]).ScraperConsumer.as_asgi()),
    ]

    application = ProtocolTypeRouter({
        "http": application,
        "websocket": SessionMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    })
except ImportError:
    pass  # channels not installed — HTTP-only mode
