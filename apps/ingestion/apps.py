"""Ingestion app configuration."""

from django.apps import AppConfig


class IngestionConfig(AppConfig):
    """Configuration for the Data Ingestion Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ingestion"
    verbose_name = "Data Ingestion"

    def ready(self) -> None:
        """Initialize app when Django starts."""
        pass
