"""
Base settings for Academic Advisor & Degree Planning System.
Modular Monolith architecture with multi-institution tenant isolation.
"""

from pathlib import Path

import environ

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Initialize environment parser
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DATABASE_URL=(
        str,
        "postgres://postgres:postgres_dev_password@localhost:5432/degree_planning_dev",
    ),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:5173", "http://127.0.0.1:5173"]),
    CSRF_TRUSTED_ORIGINS=(list, ["http://localhost:5173", "http://127.0.0.1:5173"]),
)

# Read .env file if it exists
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

# Security
# Secret key is read strictly from environment; no fallback string literal is committed
SECRET_KEY = env("DJANGO_SECRET_KEY")

DEBUG = env("DJANGO_DEBUG")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
]

LOCAL_APPS = [
    "common.apps.CommonConfig",
    "institutions.apps.InstitutionsConfig",
    "accounts.apps.AccountsConfig",
    "curriculum.apps.CurriculumConfig",
    "rule_engine.apps.RuleEngineConfig",
    "academic_records.apps.AcademicRecordsConfig",
    "degree_audit.apps.DegreeAuditConfig",
    "eligibility.apps.EligibilityConfig",
    "planning.apps.PlanningConfig",
    "advising.apps.AdvisingConfig",
    "career_mapping.apps.CareerMappingConfig",
    "analytics.apps.AnalyticsConfig",
    "notifications.apps.NotificationsConfig",
    "audit_log.apps.AuditLogConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.ActiveMembershipMiddleware",
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
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database
DATABASES = {"default": env.db("DATABASE_URL")}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",
        "user": "1000/day",
        "login": "5/minute",
        "password_reset": "5/minute",
    },
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

# OpenAPI Documentation
SPECTACULAR_SETTINGS = {
    "TITLE": "Academic Advisor & Degree Planning System API",
    "DESCRIPTION": "Multi-institution curriculum rules, degree audit, multi-semester planning, and advisor workflow platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Session & Cookie Defaults
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds
CSRF_COOKIE_HTTPONLY = False  # Allows frontend SPA to read CSRF cookie for X-CSRFToken header
CSRF_COOKIE_SAMESITE = "Lax"

# CORS & CSRF
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
