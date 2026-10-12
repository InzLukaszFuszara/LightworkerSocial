"""Django settings for the LightworkerSocial project.

Configuration comes from environment variables, so the same settings work
locally (SQLite, DEBUG) and on Railway (PostgreSQL, gunicorn, WhiteNoise).
"""

import importlib.util
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from .database import database_settings
from .email import email_settings
from .log_config import logging_config

BASE_DIR = Path(__file__).resolve().parent.parent


def env_flag(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# Railway sets RAILWAY_ENVIRONMENT_NAME in builds and deployments.
ON_RAILWAY = bool(os.environ.get("RAILWAY_ENVIRONMENT_NAME"))
DEBUG = env_flag("DJANGO_DEBUG", default=not ON_RAILWAY)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("Set the DJANGO_SECRET_KEY environment variable.")
    SECRET_KEY = "django-insecure-dev-only-change-me-in-production"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
RAILWAY_PUBLIC_DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
if RAILWAY_PUBLIC_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RAILWAY_PUBLIC_DOMAIN}")
if ON_RAILWAY:
    # Host header used by Railway's deployment healthchecks.
    ALLOWED_HOSTS.append("healthcheck.railway.app")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "posts",
    "chat",
]
# The BDD test runner is a development dependency (requirements-dev.txt).
if importlib.util.find_spec("behave_django"):
    INSTALLED_APPS.append("behave_django")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "chat.context_processors.chat",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": database_settings(os.environ, BASE_DIR)}

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "posts:home"
LOGOUT_REDIRECT_URL = "posts:home"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization: Polish (default) and English.
LANGUAGE_CODE = "pl"
LANGUAGES = [
    ("pl", _("Polish")),
    ("en", _("English")),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Europe/Warsaw"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
# On Railway, uploads must live on a volume – the container disk is wiped on
# every deploy. RAILWAY_VOLUME_MOUNT_PATH is set when a volume is attached.
_volume = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
_default_media = Path(_volume) / "media" if _volume else BASE_DIR / "media"
MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT") or _default_media)
# Django serves uploaded files itself (fine for a small site; use S3 or a CDN
# for heavy traffic). Always on in DEBUG.
SERVE_MEDIA = env_flag("DJANGO_SERVE_MEDIA", default=True)

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Hashed, compressed static files served by WhiteNoise in production.
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

# HTTPS behind Railway's proxy.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_flag("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]  # Railway healthchecks use plain HTTP
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "0"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_flag("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
    SECURE_REFERRER_POLICY = "same-origin"

# INFO to stdout, warnings and errors to stderr (see config/log_config.py).
LOGGING = logging_config(os.environ.get("DJANGO_LOG_LEVEL", "INFO"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# E-mail via Mailgun or SMTP – see config/email.py for the environment variables.
_email = email_settings(os.environ, debug=DEBUG)
EMAIL_BACKEND = _email["EMAIL_BACKEND"]
EMAIL_HOST = _email["EMAIL_HOST"]
EMAIL_PORT = _email["EMAIL_PORT"]
EMAIL_HOST_USER = _email["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = _email["EMAIL_HOST_PASSWORD"]
EMAIL_USE_TLS = _email["EMAIL_USE_TLS"]
EMAIL_USE_SSL = _email["EMAIL_USE_SSL"]
EMAIL_TIMEOUT = _email["EMAIL_TIMEOUT"]
MAILGUN_API_KEY = _email["MAILGUN_API_KEY"]
MAILGUN_DOMAIN = _email["MAILGUN_DOMAIN"]
MAILGUN_API_URL = _email["MAILGUN_API_URL"]
DEFAULT_FROM_EMAIL = _email["DEFAULT_FROM_EMAIL"]
SERVER_EMAIL = DEFAULT_FROM_EMAIL
ACCOUNT_ACTIVATION_DAYS = int(os.environ.get("ACCOUNT_ACTIVATION_DAYS", "3"))
ACCOUNT_ACTIVATION_RESEND_SECONDS = 60

# Application specific limits.
POST_MAX_LENGTH = 2000
POST_EXCERPT_LENGTH = 250
POST_IMAGE_MAX_BYTES = 5 * 1024 * 1024  # 5 MiB
POST_MAX_IMAGES = 20
POSTS_PER_PAGE = 12  # multiple of 3 -> full rows of tiles
THUMBNAIL_SIZE = (480, 480)

# Messenger.
CHAT_MESSAGE_MAX_LENGTH = 250
CHAT_IMAGE_MAX_BYTES = 5 * 1024 * 1024  # 5 MiB
CHAT_ONLINE_TIMEOUT = 90  # seconds without a heartbeat before a user is offline
CHAT_HEARTBEAT_SECONDS = 25
CHAT_POLL_SECONDS = 3
CHAT_MUTE_CHOICES = [5, 15, 60, 1440]  # minutes offered in the UI
CHAT_MAX_MUTE_MINUTES = 7 * 24 * 60
