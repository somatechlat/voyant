"""Django settings for Voyant."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# --- Helper Functions ---


def _get_env(name: str, default: str = "") -> str:
    """
    Safely retrieve and strip an environment variable.

    Args:
        name: The name of the environment variable.
        default: The default value to use if the variable is not set.

    Returns:
        The stripped value of the environment variable or the default.
    """
    return os.environ.get(name, default).strip()


def _parse_database_url(url: str) -> dict[str, str | int]:
    """
    Parse a PostgreSQL database URL into a Django DATABASES dictionary.

    Args:
        url: The database URL string (e.g., "postgresql://user:pass@host:port/db").

    Returns:
        A dictionary compatible with Django's DATABASES setting.

    Raises:
        RuntimeError: If the URL scheme is not 'postgres' or 'postgresql'.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("postgres", "postgresql"):
        raise RuntimeError(f"Unsupported DATABASE_URL scheme: {parsed.scheme}")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "",
        "PORT": parsed.port or 5432,
    }


# --- Core Security Settings ---
# SECURITY WARNING: The following settings have insecure defaults suitable for
# development only. These MUST be overridden with secure values in production.

# SECURITY WARNING: Keep the secret key used in production secret!
SECRET_KEY = _get_env("VOYANT_SECRET_KEY", "voyant-insecure-dev-key")

# SECURITY WARNING: Don't run with debug turned on in production!
DEBUG = _get_env("VOYANT_DEBUG", "false").lower() in ("1", "true", "yes")

# SECURITY WARNING: Set to the specific hostnames/domains of your server in production.
# '*' is insecure and should not be used in a production environment.
ALLOWED_HOSTS = [h for h in _get_env("VOYANT_ALLOWED_HOSTS", "*").split(",") if h]


# --- Application Definition ---

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "corsheaders",  # For handling Cross-Origin Resource Sharing
    "ninja",  # For building the REST API
    # Internal apps
    "voyant_app",  # Core Voyant application, models, and API logic
    "voyant.scraper",  # Data scraping module and models
    "mcp_server",  # Django MCP Server
]

# --- Middleware Configuration ---
# The order of middleware is critical.
# See: https://docs.djangoproject.com/en/stable/topics/http/middleware/
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # Must be high in the list
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Custom Voyant middleware. Order is important for request processing.
    "voyant.api.middleware.RequestIdMiddleware",  # Adds a unique ID to each request.
    "voyant.api.middleware.TenantMiddleware",  # Identifies the tenant for the request.
    "voyant.api.middleware.SomaContextMiddleware",  # Injects agent context if available.
    "voyant.api.middleware.APIVersionMiddleware",  # Handles API versioning.
]

ROOT_URLCONF = "voyant_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "voyant_project.wsgi.application"
ASGI_APPLICATION = "voyant_project.asgi.application"


# --- Database Configuration ---
# https://docs.djangoproject.com/en/stable/ref/settings/#databases
# Database connection is configured via a single DATABASE_URL environment variable.
DATABASE_URL = _get_env(
    "DATABASE_URL", "postgresql://voyant:voyant@localhost:45432/voyant"
)
DATABASES = {"default": _parse_database_url(DATABASE_URL)}


# --- Internationalization ---
# https://docs.djangoproject.com/en/stable/topics/i18n/
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# --- Static files (CSS, JavaScript, Images) ---
# https://docs.djangoproject.com/en/stable/howto/static-files/
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Cross-Origin Resource Sharing (CORS) Settings ---
# SECURITY WARNING: Allowing all origins ('*') is insecure. In production,
# this should be a specific list of frontend domains.
CORS_ALLOW_ALL_ORIGINS = _get_env("CORS_ORIGINS", "*") == "*"
if not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = [
        origin for origin in _get_env("CORS_ORIGINS", "").split(",") if origin
    ]

# --- Cross-Site Request Forgery (CSRF) Settings ---
# A list of hosts that are trusted for CSRF purposes.
CSRF_TRUSTED_ORIGINS = [
    origin for origin in _get_env("CSRF_TRUSTED_ORIGINS", "").split(",") if origin
]
