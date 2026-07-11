from decouple import config

from .base import *  # noqa

DEBUG = False

# base.py falls back to a known, publicly-visible insecure default so that local/dev settings
# never need a real SECRET_KEY — production must not inherit that silently. Omitting the
# `default=` here means decouple raises UndefinedValueError (fail fast at startup) instead.
SECRET_KEY = config("SECRET_KEY")

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", default="", cast=lambda v: [s.strip() for s in v.split(",") if s.strip()]
)

# Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# This app always sits behind a reverse proxy (nginx) that terminates TLS and forwards to
# Gunicorn over plain HTTP — without this, Django can never tell the original request was
# HTTPS, so SECURE_SSL_REDIRECT above would redirect every single request, including ones
# that already arrived over HTTPS, producing an infinite redirect loop. Safe only because
# Django is never reachable directly (bound to 127.0.0.1, nginx is the sole public entry
# point) — nginx, not the client, is what sets X-Forwarded-Proto (see the reverse-proxy
# configs under docs/docker-production/ and docs/vps-deployment/).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@artdukivu.com")
