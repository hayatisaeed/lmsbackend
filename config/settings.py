import os
from datetime import timedelta
from pathlib import Path
from typing import List
from urllib.parse import urlparse
import socket
from dotenv import load_dotenv

load_dotenv()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return None

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me")

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]
if DEBUG:
    ALLOWED_HOSTS = ["*"]


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
    "django_filters",
    "storages",
    "phonenumber_field",
    "apps.api",
    "apps.users",
    "apps.courses",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
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


# Convert the Path to string explicitly here
default_db = str(BASE_DIR / "db.sqlite3")
DATABASES = {"default": parse_db_url(os.getenv("DB_URL", f"sqlite:///{default_db}"))}

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_TASK_ALWAYS_EAGER = (
    os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
)

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

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# Media settings
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.User"

AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "")
AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME")
AWS_QUERYSTRING_AUTH = os.getenv("AWS_QUERYSTRING_AUTH", "true").lower() == "true"
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
ALLOWED_ANSWER_MIME = [
    m
    for m in os.getenv(
        "ALLOWED_ANSWER_MIME", "image/png,image/jpeg,application/pdf"
    ).split(",")
    if m
]

CSRF_COOKIE_NAME = os.getenv("CSRF_COOKIE_NAME", "mh_csrf")
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "false").lower() == "true"
CSRF_COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
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
OTP_API_URL = os.getenv("OTP_API_URL", "")
OTP_API_TOKEN = os.getenv("OTP_API_TOKEN", "")

IDENTITY_API_URL = os.getenv("IDENTITY_API_URL", "")
IDENTITY_API_TOKEN = os.getenv("IDENTITY_API_TOKEN", "")
IDENTITY_API_TIMEOUT = float(os.getenv("IDENTITY_API_TIMEOUT", "2.5"))
IDENTITY_API_RETRIES = int(os.getenv("IDENTITY_API_RETRIES", "2"))
IDENTITY_MAX_ATTEMPTS = int(os.getenv("IDENTITY_MAX_ATTEMPTS", "2"))
DATA_ENCRYPTION_KEY = os.getenv("DATA_ENCRYPTION_KEY", None)
AGE_THRESHOLD = int(os.getenv("AGE_THRESHOLD", "18"))

API_KEY = os.getenv("API_KEY", "")

# Users Avatar Image
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']


# Full origins with scheme (https://...), comma-separated
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]

# CORS (only if you actually need cross-origin API calls)
CORS_ALLOW_CREDENTIALS = True
if DEBUG:
    CORS_ORIGIN_ALLOW_ALL = True
else:
    CORS_ALLOWED_ORIGINS = ALLOWED_ORIGINS

# CSRF must be URL origins (with scheme), not hostnames
if not DEBUG:
    CSRF_TRUSTED_ORIGINS = ALLOWED_ORIGINS

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    #"EXCEPTION_HANDLER": "config.utils.exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.users.auth.JWTAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_RATES": {
        "courses_answer_file_delete": "10/min",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Courses/Exams API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.getenv("JWT_ACCESS_LIFETIME_MIN", "30"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.getenv("JWT_REFRESH_LIFETIME_DAYS", "7"))
    ),
    "SIGNING_KEY": JWT_SIGNING_KEY,
    "ALGORITHM": JWT_ALG,
    "AUDIENCE": JWT_AUDIENCE,
    "ISSUER": JWT_ISSUER,
}
