# Production image for the Art du Kivu backend.
#
# Build context MUST be the backend/ directory (see docker-compose.yaml in this folder:
# `context: ../..`), because this Dockerfile needs requirements.txt, manage.py, entrypoint.sh
# and the apps/ tree, none of which live inside docs/.
#
# Two-stage build: the first stage compiles/installs Python dependencies (needs gcc/libpq-dev),
# the second stage only copies the resulting virtualenv and the application code, so build
# tools never ship in the final image.

# ---- Stage 1: build dependencies ----------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && pip install -r requirements.txt

# ---- Stage 2: runtime image ----------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# libpq5 (runtime client lib for psycopg2) + curl (healthcheck) — no compiler needed here.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY . .

RUN mkdir -p /app/staticfiles /app/mediafiles \
    && addgroup --system django && adduser --system --ingroup django django \
    && chmod +x /app/entrypoint.sh \
    && chown -R django:django /app

USER django

EXPOSE 8000

# Generic healthcheck; docker-compose.yaml's `api` service overrides the command to run the
# ASGI/Uvicorn worker instead of relying on entrypoint.sh (which also starts Celery worker/beat
# in-process — appropriate for a single-service PaaS deployment, but redundant here since
# worker/beat run as their own containers in this compose stack).
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
  CMD curl -f http://localhost:${PORT:-8000}/api/v1/health/ || exit 1

CMD ["./entrypoint.sh"]
