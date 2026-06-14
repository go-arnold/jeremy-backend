from decouple import config
from .base import *  # noqa

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Disable throttling in local dev
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405

# Use simple in-memory cache for local (or Redis if available)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "artdukivu-local",
    }
}

# Email output to console in dev
# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@artdukivu.com")


# Show SQL queries
LOGGING["loggers"]["django.db.backends"] = {  # noqa: F405
    "handlers": ["console"],
    "level": "DEBUG",
    "propagate": False,
}
