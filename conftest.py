"""
Root conftest.py - Pytest configuration that runs before Django settings are loaded.

This file is loaded by pytest before any other conftest.py files, allowing us to
set environment variables before Django settings are imported.
"""

import os

# Configure environment variables BEFORE Django settings are loaded
# This runs at module import time, before pytest-django tries to load settings
os.environ.setdefault("VOYANT_ENV", "test")
os.environ.setdefault(
    "DATABASE_URL", "postgresql://voyant:voyant@localhost:45432/voyant_test"
)
os.environ.setdefault("REDIS_URL", "redis://:voyant@localhost:45379/1")
os.environ.setdefault(
    "VOYANT_SECRET_KEY",
    "test-secret-key-for-testing-only-min-50-chars-long-django-security",
)
os.environ.setdefault("VOYANT_DEBUG", "false")
os.environ.setdefault("VOYANT_SECURITY_ENABLED", "false")
os.environ.setdefault("VOYANT_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")

# Load .env file for additional configuration (but don't override test settings)
from dotenv import load_dotenv

load_dotenv(override=False)
