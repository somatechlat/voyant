"""Launcher module for django-mcp transport via Django ASGI application."""

import os

from apps.core.config import get_settings


def main() -> None:
    """Run Voyant with django-mcp mounted at `/mcp`."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")
    settings = get_settings()
    host = settings.mcp_host
    port = settings.mcp_port
    from daphne.endpoints import build_endpoint_description_strings
    from daphne.server import Server

    endpoints = build_endpoint_description_strings(host=host, port=port)
    Server(
        application="voyant_project.asgi:application",
        endpoints=endpoints,
    ).run()


if __name__ == "__main__":
    main()
