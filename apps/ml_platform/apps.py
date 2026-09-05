"""ML Platform — Django app config."""

from django.apps import AppConfig


class MlPlatformConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ml_platform"
    verbose_name = "ML Platform"
