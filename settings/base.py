import ssl
from datetime import timedelta
from pathlib import Path

import cloudinary
from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="insecure-dev-key-change-in-production")

DEBUG = False

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# ── Applications ──────────────────────────────────────────────────────────────
# `daphne` must be first: it's how Channels makes `manage.py runserver` handle
# WebSocket upgrades locally (production instead runs gunicorn with a uvicorn
# worker directly against artdukivu.asgi:application — see entrypoint.sh).
DJANGO_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "channels",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "corsheaders",
    "cloudinary",
    "cloudinary_storage",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
    "django_elasticsearch_dsl",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.artists",
    "apps.articles",
    "apps.events",
    "apps.podcasts",
    "apps.radio",
    "apps.webtv",
    "apps.community",
    "apps.releases",
    "apps.emissions",
    "apps.analytics",
    "apps.newsletter",
    "apps.search",
    "apps.engagement",
    "apps.realtime",
    "apps.streaming",
    "apps.live_music",
    "apps.home",
    "apps.media_uploads",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

SITE_ID = 1

# ── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "artdukivu.urls"

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

WSGI_APPLICATION = "artdukivu.wsgi.application"
ASGI_APPLICATION = "artdukivu.asgi.application"

# ── Database with connection pooling ─────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "dj_db_conn_pool.backends.postgresql",
        "NAME": config("DB_NAME", default="artdukivu"),
        "USER": config("DB_USER", default="matabar"),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="db"),
        "PORT": config("DB_PORT", default="5433"),
        "POOL_OPTIONS": {
            "POOL_SIZE": 10,
            "MAX_OVERFLOW": 5,
            "RECYCLE": 3600,
        },
    }
}

# ── Auth ──────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = "fr-cd"
TIME_ZONE = "Africa/Lubumbashi"
USE_I18N = True
USE_TZ = True

# ── Static / Media ────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Cloudinary ────────────────────────────────────────────────────────────────
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": config("CLOUDINARY_CLOUD_NAME"),
    "API_KEY": config("CLOUDINARY_API_KEY"),
    "API_SECRET": config("CLOUDINARY_API_SECRET"),
}

cloudinary.config(
    cloud_name=config("CLOUDINARY_CLOUD_NAME"),
    api_key=config("CLOUDINARY_API_KEY"),
    api_secret=config("CLOUDINARY_API_SECRET"),
)

DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

# ── Redis / Cache ─────────────────────────────────────────────────────────────
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")

_redis_options: dict = {"CLIENT_CLASS": "django_redis.client.DefaultClient"}
if REDIS_URL.startswith("rediss://"):
    _redis_options["CONNECTION_POOL_KWARGS"] = {
        "ssl_cert_reqs": ssl.CERT_NONE,
    }

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": _redis_options,
        "KEY_PREFIX": "artdukivu",
        "TIMEOUT": 60 * 15,
    }
}

# ── Channels (WebSocket chat + presence) ─────────────────────────────────────
_channel_layer_config = {"hosts": [REDIS_URL]}
if REDIS_URL.startswith("rediss://"):
    _channel_layer_config = {"hosts": [{"address": REDIS_URL, "ssl_cert_reqs": None}]}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": _channel_layer_config,
    }
}

# ── Cloudflare Stream (live ingest/playback) ─────────────────────────────────
CLOUDFLARE_ACCOUNT_ID = config("CLOUDFLARE_ACCOUNT_ID", default="")
CLOUDFLARE_API_TOKEN = config("CLOUDFLARE_API_TOKEN", default="")
CLOUDFLARE_CUSTOMER_HOSTNAME = config("CLOUDFLARE_CUSTOMER_HOSTNAME", default="")
CLOUDFLARE_WEBHOOK_SECRET = config("CLOUDFLARE_WEBHOOK_SECRET", default="")

# ── Elasticsearch ─────────────────────────────────────────────────────────────
# Point at a managed cluster (Elastic Cloud, AWS OpenSearch, ...) in production
# by overriding ELASTICSEARCH_URL — the local docker-compose service is single-node
# and unsecured, meant for local/staging only.
ELASTICSEARCH_DSL = {
    "default": {
        "hosts": config("ELASTICSEARCH_URL", default="http://localhost:9200"),
    }
}
# django_elasticsearch_dsl's RealTimeSignalProcessor/CelerySignalProcessor
# both connect to Django's post_save/post_delete GLOBALLY (every model in the
# project, not just indexed ones) with no sender filter. CelerySignalProcessor
# additionally calls Task.delay() unconditionally inside that handler, before
# any "is this model even indexed" check — confirmed with a live test: a
# fresh test-DB migration (which saves unrelated models like Site/ContentType
# via post_migrate) tried to publish to the Celery broker and blew up on a
# refused connection. Disable it entirely and resync via our own scheduled
# task (apps.search.tasks.resync_search_index) instead — search freshness
# lags by one beat interval, an acceptable trade for never letting
# Elasticsearch sit in the critical path of an unrelated DB write.
ELASTICSEARCH_DSL_SIGNAL_PROCESSOR = "django_elasticsearch_dsl.signals.BaseSignalProcessor"
ELASTICSEARCH_DSL_AUTOSYNC = False

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# ── Celery ────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": ssl.CERT_NONE} if REDIS_URL.startswith("rediss://") else None
CELERY_REDIS_BACKEND_USE_SSL = {"ssl_cert_reqs": ssl.CERT_NONE} if REDIS_URL.startswith("rediss://") else None

CELERY_BEAT_SCHEDULE = {
    "update-event-statuses": {
        "task": "apps.events.tasks.update_event_statuses",
        "schedule": 3600,
    },
    "warm-featured-cache": {
        "task": "apps.artists.tasks.warm_featured_cache",
        "schedule": 1800,
    },
    "cleanup-expired-chat": {
        "task": "apps.radio.tasks.cleanup_old_chat",
        "schedule": 86400,
    },
    "update-emission-statuses": {
        "task": "apps.emissions.tasks.update_emission_statuses",
        "schedule": 3600,
    },
    "resync-search-index": {
        "task": "apps.search.tasks.resync_search_index",
        "schedule": 300,
    },
}

# ── DRF ───────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "core.throttling.AnonBurstThrottle",
        "core.throttling.UserBurstThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon_burst": "30/min",
        "user_burst": "120/min",
        "auth": "10/min",
        "upload": "5/min",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}

# ── SimpleJWT ─────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ── Frontend ──────────────────────────────────────────────────────────────────
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:3000")

# ── dj-rest-auth / allauth ────────────────────────────────────────────────────
REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_COOKIE": None,
    "JWT_AUTH_REFRESH_COOKIE": None,
    "JWT_AUTH_HTTPONLY": False,
    "REGISTER_SERIALIZER": "apps.accounts.serializers.RegisterSerializer",
    "USER_DETAILS_SERIALIZER": "apps.accounts.serializers.UserSerializer",
}

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = config("ACCOUNT_EMAIL_VERIFICATION", default="optional")
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_SUBJECT_PREFIX = ""
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"

ACCOUNT_ADAPTER = "apps.accounts.adapters.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.accounts.adapters.SocialAccountAdapter"

# Google already verifies emails; skip redundant allauth verification for social logins
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_REQUIRED = True

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": config("GOOGLE_CLIENT_ID", default=""),
            "secret": config("GOOGLE_CLIENT_SECRET", default=""),
            "key": "",
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "VERIFIED_EMAIL": True,
    }
}

DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@artdukivu.com")

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://localhost:3001",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True

# ── Spectacular (API docs) ────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "Art du Kivu API",
    "DESCRIPTION": "Congolese music & arts platform API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_SETTINGS": {"deepLinking": True},
    # Strips "/api/v1" before auto-deriving a tag from the first remaining path
    # segment. Without this every operation falls under the path prefix itself
    # (a single "v1" tag for the whole API) instead of grouping by resource.
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "TAGS": [
        {"name": "System", "description": "Health checks and infrastructure endpoints"},
        {"name": "Auth", "description": "Registration, login, JWT and Google OAuth"},
        {"name": "Users", "description": "User profiles, favorites, listen history"},
        {"name": "Artists", "description": "Artist profiles, genres, releases, gallery"},
        {"name": "Articles", "description": "Blog articles"},
        {"name": "Events", "description": "Events, schedules, registrations"},
        {"name": "Podcasts", "description": "Podcast series and episodes"},
        {"name": "Radio", "description": "Live radio program schedule and chat"},
        {"name": "Web TV", "description": "Video content: freestyles, studio, docs"},
        {"name": "Community", "description": "Talent posts, challenges, polls"},
        {"name": "Releases", "description": "Music releases and premieres"},
        {"name": "Emissions", "description": "Scheduled live broadcast shows"},
        {"name": "Analytics", "description": "Site-wide aggregate statistics dashboard"},
        {"name": "Newsletter", "description": "Subscribe/unsubscribe and admin campaign sending"},
        {"name": "Search", "description": "Unified full-text search across all content types"},
        {"name": "Home", "description": "Aggregated homepage payload"},
        {"name": "Streaming", "description": "Cloudflare Stream live ingest control and webhooks"},
        {"name": "Live Music", "description": "Live music session, schedule grid and live chat"},
        {"name": "Media", "description": "Signed direct-to-Cloudinary upload for audio/video/image"},
    ],
}

# ── Logging ───────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {module} {message}", "style": "{"},
        "simple": {"format": "{levelname} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO"},
        "apps": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
