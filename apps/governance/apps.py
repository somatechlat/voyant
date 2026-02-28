"""Django app configuration for governance."""

from __future__ import annotations

from django.apps import AppConfig


class GovernanceConfig(AppConfig):
    """Configuration for the governance app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.governance"
    verbose_name = "Data Governance"
