"""SQL app configuration."""

from django.apps import AppConfig


class SqlConfig(AppConfig):
    """Configuration for the SQL Query Execution Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sql"
    verbose_name = "SQL Query Execution"

    def ready(self) -> None:
        """Initialize app when Django starts."""
        pass
