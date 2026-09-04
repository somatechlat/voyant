"""Voyant Admin Panel — Django app config."""

from django.apps import AppConfig


class AdminPanelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admin_panel"
    verbose_name = "Voyant Admin Panel"
