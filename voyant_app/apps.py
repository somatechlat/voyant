import logging

from django.apps import AppConfig


class VoyantAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "voyant_app"

    def ready(self) -> None:
        # Ensure django-mcp tools are registered at startup.
        try:
            import voyant_app.mcp_tools  # noqa: F401
        except Exception:
            logging.getLogger(__name__).exception("Failed to register django-mcp tools")
            raise
