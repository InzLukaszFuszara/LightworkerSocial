"""Django settings for the LightworkerSocial project."""

import os
from pathlib import Path

from django.utils.translation import gettext_lazy as _

from .email import email_settings

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-only-change-me-in-production",
)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "behave_django",
    "accounts",
    "posts",
    "chat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DJANGO_DB_PATH", BASE_DIR / "db.sqlite3"),
    }
}

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
MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT", BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# E-mail via SMTP – see config/email.py for the environment variables.
_email = email_settings(os.environ, debug=DEBUG)
EMAIL_BACKEND = _email["EMAIL_BACKEND"]
EMAIL_HOST = _email["EMAIL_HOST"]
EMAIL_PORT = _email["EMAIL_PORT"]
EMAIL_HOST_USER = _email["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = _email["EMAIL_HOST_PASSWORD"]
EMAIL_USE_TLS = _email["EMAIL_USE_TLS"]
EMAIL_USE_SSL = _email["EMAIL_USE_SSL"]
EMAIL_TIMEOUT = _email["EMAIL_TIMEOUT"]
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
