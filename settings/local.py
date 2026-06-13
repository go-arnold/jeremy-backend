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
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Show SQL queries
LOGGING["loggers"]["django.db.backends"] = {  # noqa: F405
    "handlers": ["console"],
    "level": "DEBUG",
    "propagate": False,
}
