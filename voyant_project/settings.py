"""Django settings for Voyant."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent


def _get_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _parse_database_url(url: str) -> dict[str, str | int]:
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


SECRET_KEY = _get_env("VOYANT_SECRET_KEY", "voyant-insecure-dev-key")
DEBUG = _get_env("VOYANT_DEBUG", "false").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = [h for h in _get_env("VOYANT_ALLOWED_HOSTS", "*").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "ninja",
    "voyant_app",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "voyant.api.middleware.RequestIdMiddleware",
    "voyant.api.middleware.TenantMiddleware",
    "voyant.api.middleware.SomaContextMiddleware",
    "voyant.api.middleware.APIVersionMiddleware",
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

DATABASE_URL = _get_env(
    "DATABASE_URL", "postgresql://voyant:voyant@localhost:45432/voyant"
)
DATABASES = {"default": _parse_database_url(DATABASE_URL)}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOW_ALL_ORIGINS = _get_env("CORS_ORIGINS", "*") == "*"
if not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = [
        origin for origin in _get_env("CORS_ORIGINS", "").split(",") if origin
    ]

CSRF_TRUSTED_ORIGINS = [
    origin for origin in _get_env("CSRF_TRUSTED_ORIGINS", "").split(",") if origin
]
