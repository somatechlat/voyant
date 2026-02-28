"""Core app configuration."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuration for the Core Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Voyant Core"

    def ready(self) -> None:
        """
        Perform initialization when Django starts.

        This method is called once Django has loaded all apps.
        Use it to register signals, perform startup checks, etc.
        """
        # Register MCP tools at startup so django-mcp exposes a stable tool surface.
        from apps.mcp import tools as _mcp_tools  # noqa: F401
