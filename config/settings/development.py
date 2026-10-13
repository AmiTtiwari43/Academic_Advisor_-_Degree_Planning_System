"""
Development settings for Academic Advisor & Degree Planning System.
"""

from .base import *  # noqa: F403
from .base import env

DEBUG = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Ensure local dev hosts are permitted
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "[::1]"])

# Disable HTTPS redirection in local dev
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
