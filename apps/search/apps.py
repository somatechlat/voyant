"""Search app configuration."""

from django.apps import AppConfig


class SearchConfig(AppConfig):
    """Configuration for the Semantic Search Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.search"
    verbose_name = "Semantic Search"

    def ready(self) -> None:
        """Initialize app when Django starts."""
        pass
