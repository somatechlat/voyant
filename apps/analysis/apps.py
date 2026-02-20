"""Analysis app configuration."""

from django.apps import AppConfig


class AnalysisConfig(AppConfig):
    """Configuration for the Statistical Analysis Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analysis"
    verbose_name = "Statistical Analysis"

    def ready(self) -> None:
        """Initialize app when Django starts."""
        pass
