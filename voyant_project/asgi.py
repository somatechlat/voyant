"""ASGI config for Voyant — HTTP + MCP + WebSocket."""

import os

from django.core.asgi import get_asgi_application
from django_mcp import mount_mcp_server

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")

# Get the Django ASGI application
django_asgi_app = get_asgi_application()

# MCP server mounted at /mcp
application = mount_mcp_server(django_http_app=django_asgi_app, mcp_base_path="/mcp")

# Add WebSocket support (requires django-channels)
try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.sessions import SessionMiddlewareStack

    # Merge with the visual scraper consumer route
    from django.urls import path

    # Import core WebSocket routes (ontology, jobs, agents, scraper subscriptions)
    from apps.core.routing import websocket_urlpatterns as core_ws_urls
    from apps.scraper.visual.consumer import ScraperConsumer

    all_websocket_urlpatterns = core_ws_urls + [
        path("ws/scraper/visual/", ScraperConsumer.as_asgi()),
    ]

    application = ProtocolTypeRouter({
        "http": application,
        "websocket": SessionMiddlewareStack(
            URLRouter(all_websocket_urlpatterns)
        ),
    })
except ImportError:
    pass  # channels not installed — HTTP-only mode
