"""
Ontology test conftest — registers the ontology app for Django model loading.

apps.ontology is not in the default INSTALLED_APPS, so we add it here
before any ontology model imports occur during test collection.
"""

import django
from django.apps import apps
from django.conf import settings

if "apps.ontology" not in settings.INSTALLED_APPS:
    settings.INSTALLED_APPS = list(settings.INSTALLED_APPS) + ["apps.ontology"]

# Force Django to set up the newly added app
if not apps.ready:
    django.setup()
else:
    # Apps already set up — manually configure the new one
    try:
        apps.get_app_config("ontology")
    except LookupError:
        apps.populate(settings.INSTALLED_APPS)
