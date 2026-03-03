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
        # Register all MCP tools at startup. All 3 modules must be imported to trigger
        # @mcp_app.tool decorator registrations. Split per Rule-245 from tools.py.
        from apps.mcp import tools_catalog as _t2  # noqa: F401
        from apps.mcp import tools_core as _t1  # noqa: F401
        from apps.mcp import tools_scrape as _t3  # noqa: F401
