import os
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me")
DEBUG = os.getenv("DEBUG", "1") == "1"
ALLOWED_HOSTS: List[str] = [
    h for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h
] or ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "apps.users",
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
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"


def parse_db_url(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme in {"postgres", "postgresql"}:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username,
            "PASSWORD": parsed.password,
            "HOST": parsed.hostname,
            "PORT": parsed.port,
        }
    if parsed.scheme == "sqlite":
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": parsed.path or ":memory:",
        }
    raise ValueError("Unsupported DB scheme")


DATABASES = {"default": parse_db_url(os.getenv("DB_URL", "sqlite:///db.sqlite3"))}

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# Simplified password validators for bootstrap phase
AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.User"

CSRF_COOKIE_NAME = os.getenv("CSRF_COOKIE_NAME", "mh_csrf")
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")

REFRESH_COOKIE_NAME = os.getenv("REFRESH_COOKIE_NAME", "__Host-mh_rtk")
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")

JWT_ISSUER = os.getenv("JWT_ISSUER", "mentorhub")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "mentorhub")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
JWT_SIGNING_KEY = os.getenv("JWT_SIGNING_KEY", SECRET_KEY)
JWT_ACCESS_TTL_SEC = int(os.getenv("JWT_ACCESS_TTL_SEC", "600"))
JWT_REFRESH_TTL_SEC = int(os.getenv("JWT_REFRESH_TTL_SEC", "2592000"))

OTP_LENGTH = int(os.getenv("OTP_LENGTH", "6"))
OTP_TTL_SEC = int(os.getenv("OTP_TTL_SEC", "300"))
OTP_COOLDOWN_SEC = int(os.getenv("OTP_COOLDOWN_SEC", "60"))
OTP_MAX_PER_24H_PER_PHONE = int(os.getenv("OTP_MAX_PER_24H_PER_PHONE", "5"))
OTP_MAX_PER_HOUR_PER_IP = int(os.getenv("OTP_MAX_PER_HOUR_PER_IP", "20"))

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS: List[str] = [
    o for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o
]
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "config.utils.exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.users.auth.JWTAuthentication",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "MentorHub API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
