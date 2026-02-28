"""Launcher module for django-mcp transport via Django ASGI application."""

import os

import uvicorn

from apps.core.config import get_settings


def main() -> None:
    """Run Voyant with django-mcp mounted at `/mcp`."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")
    settings = get_settings()
    host = settings.mcp_host
    port = settings.mcp_port
    uvicorn.run("voyant_project.asgi:application", host=host, port=port)


if __name__ == "__main__":
    main()
