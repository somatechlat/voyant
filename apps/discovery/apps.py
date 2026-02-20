"""Discovery app configuration."""

from django.apps import AppConfig


class DiscoveryConfig(AppConfig):
    """Configuration for the Discovery app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.discovery"
    verbose_name = "Service Discovery"
