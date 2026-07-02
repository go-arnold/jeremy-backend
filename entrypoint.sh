#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

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
