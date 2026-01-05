"""
Voyant Scraper - Django App Configuration.

This module defines the Django AppConfig for the `voyant.scraper` application.
It configures the application's metadata within the Django project.
"""

from django.apps import AppConfig


class ScraperConfig(AppConfig):
    """Django app config for the `voyant.scraper` module."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "voyant.scraper"
    label = "scraper"
    verbose_name = "Voyant DataScraper"

    def ready(self):
        """
        Initializes the application when Django starts.

        This method is a hook for performing startup tasks such as registering
        signals, performing checks, or loading configurations.
        """
        pass
