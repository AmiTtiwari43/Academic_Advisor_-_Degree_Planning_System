"""
Test settings for Academic Advisor & Degree Planning System.
Enforces real PostgreSQL and fast password hashing.
"""

from .base import *  # noqa: F403

DEBUG = False

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Ensure test runners don't require HTTPS
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
