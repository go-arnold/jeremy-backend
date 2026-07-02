FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy all project files (including entrypoint.sh)
COPY . .

# Create required directories
RUN mkdir -p /app/staticfiles /app/mediafiles

# Setup system user and group
RUN addgroup --system django && adduser --system --ingroup django django

# Make sure entrypoint is executable
RUN chmod +x /app/entrypoint.sh

# Give the django user ownership of EVERYTHING in /app so background tasks don't get Permission Denied
RUN chown -R django:django /app

# Switch to non-root user
USER django

EXPOSE 8000

# Healthcheck targeting Render's dynamic port
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/api/v1/health/ || exit 1

# Execute your script
CMD ["./entrypoint.sh"]
