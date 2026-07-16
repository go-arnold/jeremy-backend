#!/usr/bin/env bash
#
# Applies changes made to the shared .env file (e.g. ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS,
# FRONTEND_URL, MEDIAMTX_WEBHOOK_SECRET) to the running stack.
#
# `docker compose restart` does NOT reload env_file contents — it just restarts the existing
# container process with whatever environment it already has. Recreating the containers
# (without rebuilding the image, since no code changed) is what actually picks up new values.
# db/redis/elasticsearch/nginx are untouched — api/worker/beat/mediamtx are recreated (mediamtx
# also reads MEDIAMTX_WEBHOOK_SECRET from .env, via its own `environment:` block).
#
# Usage: ./reload-env.sh

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

docker compose up -d --force-recreate --no-build api worker beat mediamtx

echo "api/worker/beat/mediamtx recreated with the current .env values."
echo "Check they came back healthy: docker compose ps"
