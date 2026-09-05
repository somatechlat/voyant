"""Intent Engine — Django app config."""

from django.apps import AppConfig


class IntentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.intent"
    verbose_name = "Intent Engine"
