"""Launcher module for django-mcp transport via Django ASGI application."""

import os

import uvicorn



def main() -> None:
    """Run Voyant with django-mcp mounted at `/mcp`."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")
    host = os.environ.get("VOYANT_MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("VOYANT_MCP_PORT", "8001"))
    uvicorn.run("voyant_project.asgi:application", host=host, port=port)


if __name__ == "__main__":
    main()
