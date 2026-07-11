#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Force one explicit, shared settings module for every process this script starts (migrate,
# collectstatic, search_index, Celery worker, Celery beat, Gunicorn). Without this, each of
# those processes independently falls back to ITS OWN default when DJANGO_SETTINGS_MODULE
# isn't set externally: artdukivu/asgi.py defaults to settings.production but
# artdukivu/celery.py defaults to settings.local — if a deployment forgets to export the
# variable, Gunicorn and Celery would silently run under different settings (DEBUG, email
# backend, cache backend) in the same container. Respects an explicit external value if one
# is already set.
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-settings.production}"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Elasticsearch is a separate service (ELASTICSEARCH_URL, default
# http://elasticsearch:9200) — this app only ever connects out to it, it
# never listens on 9200 itself. Wait briefly, but never block startup on it:
# search degrading is not worth taking the whole API down for.
echo "Checking Elasticsearch availability..."
for i in $(seq 1 15); do
    if curl -sf "${ELASTICSEARCH_URL:-http://elasticsearch:9200}" >/dev/null 2>&1; then
        echo "Elasticsearch is up."
        break
    fi
    echo "Elasticsearch not ready yet (${i}/15)..."
    sleep 2
done
python manage.py search_index --create -f || echo "Could not create search indices — continuing without search."

echo "Starting Celery Worker..."
celery -A artdukivu worker --loglevel=info --concurrency=1 -Q default,high_priority &

echo "Starting Celery Beat..."
celery -A artdukivu beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler &

echo "Starting Gunicorn (Uvicorn worker, ASGI — required for WebSocket chat/presence)..."
exec gunicorn --bind 0.0.0.0:${PORT:-8000} \
    --worker-class=uvicorn.workers.UvicornWorker \
    --workers=1 \
    --timeout=300 \
    --access-logfile - \
    --error-logfile - \
    artdukivu.asgi:application
