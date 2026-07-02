#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

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

echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:${PORT:-8000} \
    --workers=1 \
    --threads=2 \
    --timeout=300 \
    --access-logfile - \
    --error-logfile - \
    artdukivu.wsgi:application
