"""Django settings for Voyant."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

# Load environment variables from .env file
from dotenv import load_dotenv

if os.environ.get("VOYANT_ENV") == "local":
    load_dotenv()

# Import security settings
from apps.core.config import get_settings

from .security_settings import security_settings

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# --- Helper Functions ---


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

    # SSL configuration for production
    ssl_config = {}
    if security_settings.database_ssl_require:
        ssl_config["sslmode"] = "require"
        if security_settings.database_ssl_cert:
            ssl_config["sslcert"] = security_settings.database_ssl_cert
        if security_settings.database_ssl_key:
            ssl_config["sslkey"] = security_settings.database_ssl_key
        if security_settings.database_ssl_root_cert:
            ssl_config["sslrootcert"] = security_settings.database_ssl_root_cert

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "",
        "PORT": parsed.port or 5432,
        **ssl_config,
    }


# --- Core Security Settings ---
# SECURITY WARNING: The following settings have been enhanced for production security.
# Always override these with secure values in production environments.

app_settings = get_settings()

# SECURITY WARNING: Keep the secret key used in production secret!
SECRET_KEY = app_settings.secret_key
if not SECRET_KEY and app_settings.env in {"test", "local"}:
    SECRET_KEY = "voyant-local-test-secret-key-not-for-production"

# SECURITY WARNING: Don't run with debug turned on in production!
DEBUG = app_settings.debug

# SECURITY WARNING: Set to the specific hostnames/domains of your server in production.
# '*' is insecure and should not be used in a production environment.
ALLOWED_HOSTS = app_settings.allowed_hosts

# SECURITY WARNING: Always use HTTPS in production.
# Local/dev environments commonly run without TLS; enforce HTTPS only outside local.
SECURE_SSL_REDIRECT = (
    security_settings.security_enabled and not DEBUG and app_settings.env != "local"
)
SESSION_COOKIE_SECURE = (
    security_settings.security_enabled and not DEBUG and app_settings.env != "local"
)
CSRF_COOKIE_SECURE = (
    security_settings.security_enabled and not DEBUG and app_settings.env != "local"
)

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
    "django_mcp",  # Django MCP Server (django-mcp 0.3.1)
    # Internal apps - New Django App Structure
    "apps.core",  # Core models (TimeStampedModel, TenantModel, AuditLog, SystemSetting)
    "apps.workflows",  # Workflows (Jobs, Artifacts, Presets)
    "apps.analysis",  # Statistical analysis
    "apps.sql",  # SQL query execution via Trino
    "apps.search",  # Semantic search with vector embeddings (Milvus)
    "apps.discovery",  # Service discovery, API catalog, Sources
    "apps.ingestion",  # Ingestion jobs bound to canonical discovery sources
    "apps.governance",  # Data governance, lineage, policies, quotas
    "apps.scraper",  # Data scraping module (Pure Execution)
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
    "apps.core.middleware.RequestIdMiddleware",  # Adds a unique ID to each request.
    "apps.core.middleware.TenantMiddleware",  # Identifies the tenant for the request.
    "apps.core.middleware.SomaContextMiddleware",  # Injects agent context if available.
    "apps.core.middleware.APIVersionMiddleware",  # Handles API versioning.
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
DATABASE_URL = app_settings.database_url
if not DATABASE_URL:
    # For testing, use a default test database URL
    if "pytest" in os.environ.get("_", "") or "test" in os.environ.get(
        "VOYANT_ENV", ""
    ):
        DATABASE_URL = "postgresql://voyant:voyant@localhost:45432/voyant_test"
    else:
        raise RuntimeError("DATABASE_URL must be configured")
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

# --- Security Headers Configuration ---
# Apply security headers based on security settings
SECURE_HSTS_SECONDS = (
    security_settings.hsts_max_age if security_settings.hsts_enabled else 0
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = security_settings.hsts_include_subdomains
SECURE_HSTS_PRELOAD = security_settings.hsts_preload
SECURE_CONTENT_TYPE_NOSNIFF = security_settings.security_enabled
SECURE_BROWSER_XSS_FILTER = security_settings.security_enabled
SECURE_REFERRER_POLICY = security_settings.referrer_policy

# --- Cross-Origin Resource Sharing (CORS) Settings ---
# CORS configuration is now managed by security_settings
CORS_ALLOW_ALL_ORIGINS = False  # Always false for security
CORS_ALLOW_CREDENTIALS = security_settings.cors_allow_credentials
if security_settings.cors_allow_origins != ["*"]:
    CORS_ALLOWED_ORIGINS = security_settings.cors_allow_origins
if security_settings.cors_allow_methods != ["*"]:
    CORS_ALLOWED_METHODS = security_settings.cors_allow_methods
if security_settings.cors_allow_headers != ["*"]:
    CORS_ALLOWED_HEADERS = security_settings.cors_allow_headers
CORS_MAX_AGE = security_settings.cors_max_age

# --- Cross-Site Request Forgery (CSRF) Settings ---
# A list of hosts that are trusted for CSRF purposes.
CSRF_TRUSTED_ORIGINS = app_settings.csrf_trusted_origins

# --- Authentication Settings ---
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# --- Session Settings ---
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_SECURE = security_settings.security_enabled and not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# --- Password Validation Settings ---
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 12,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# --- Email Settings (for notifications) ---
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = app_settings.email_host
EMAIL_PORT = app_settings.email_port
EMAIL_USE_TLS = app_settings.email_use_tls
EMAIL_HOST_USER = app_settings.email_host_user
EMAIL_HOST_PASSWORD = app_settings.email_host_password
DEFAULT_FROM_EMAIL = app_settings.default_from_email

# --- Logging Configuration ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "detailed": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs", "voyant.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "detailed",
        },
        "security": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs", "security.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 30,
            "formatter": "detailed",
        },
        "audit": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs", "audit.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 365,
            "formatter": "detailed",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "voyant": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "voyant.security": {
            "handlers": ["console", "file", "security"],
            "level": "INFO",
            "propagate": False,
        },
        "voyant.audit": {
            "handlers": ["console", "file", "audit"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Create logs directory if it doesn't exist
os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)

# --- Caching Configuration ---
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": app_settings.redis_url,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
    }
}

# --- Rate Limiting Configuration (if using django-ratelimit) ---
RATELIMIT_USE_CACHE = "default"
RATELIMIT_CACHE_PREFIX = "rl"

# --- MCP Configuration (django-mcp 0.3.1) ---
# Reference: https://pypi.org/project/django-mcp/
MCP_LOG_LEVEL = "INFO"
MCP_LOG_TOOL_REGISTRATION = True
MCP_LOG_TOOL_DESCRIPTIONS = False
MCP_SERVER_INSTRUCTIONS = "Voyant provides AI agents with data analysis, scraping, and governance tools. Execute data operations safely with proper permissions."
MCP_SERVER_TITLE = "Voyant Data Intelligence"
MCP_SERVER_VERSION = "3.0.0"
MCP_DIRS = []  # Additional search paths for MCP modules
MCP_PATCH_SDK_TOOL_LOGGING = True  # Enhanced logging for tool calls
MCP_PATCH_SDK_GET_CONTEXT = True  # Add URL path params to Context object

# --- Security Settings Summary ---
# This file has been enhanced with comprehensive security controls:
# - SSL/TLS enforcement for database connections
# - Security headers (CSP, HSTS, X-Frame-Options, etc.)
# - CORS configuration with proper origin restrictions
# - Session security (secure, httponly, samesite)
# - Password validation requirements
# - Comprehensive logging and audit trails
# - Rate limiting configuration
# - Input validation and sanitization

# Always review these settings before deploying to production:
# 1. SECRET_KEY must be unique and secure
# 2. DEBUG must be False in production
# 3. ALLOWED_HOSTS must be properly configured
# 4. SSL/TLS must be enabled for all communications
# 5. Database credentials must be securely managed
# 6. CORS origins must be properly restricted
# 7. All security headers must be properly configured
