"""ASGI config for Voyant — HTTP + MCP + WebSocket."""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.sessions import SessionMiddlewareStack
from django.core.asgi import get_asgi_application
from django.urls import path
from django_mcp import mount_mcp_server

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")

# Get the Django ASGI application
django_asgi_app = get_asgi_application()

# MCP server mounted at /mcp
application_with_mcp = mount_mcp_server(django_http_app=django_asgi_app, mcp_base_path="/mcp")

# WebSocket routing
websocket_urlpatterns = [
    path("ws/scraper/", __import__("apps.scraper.visual.consumer", fromlist=["ScraperConsumer"]).ScraperConsumer.as_asgi()),
]

# Full ASGI application with protocol routing
application = ProtocolTypeRouter({
    "http": application_with_mcp,
    "websocket": SessionMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
