#!/usr/bin/env bash
#
# Deployment automation for the Art du Kivu backend — Docker Compose production stack
# (docs/docker-production/). See docs/DEPLOY.md for the full procedure this script automates,
# and docs/PRODUCTION.md for how this fits among the available production options.
#
# Usage:
#   docs/deploy.sh up          Build and (re)start the full stack, then verify health.
#   docs/deploy.sh down        Stop the stack (containers are removed, volumes are kept).
#   docs/deploy.sh restart     Restart api/worker/beat without a rebuild.
#   docs/deploy.sh status      Show container status.
#   docs/deploy.sh logs [svc]  Tail logs (all services, or one: api, worker, beat, nginx, elasticsearch).
#   docs/deploy.sh migrate     Run pending Django migrations inside the running api container.
#   docs/deploy.sh shell       Open a Django shell inside the running api container.
#
# The script is idempotent: running `up` again after a failed run is safe and expected.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STACK_DIR="$SCRIPT_DIR/docker-production"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$BACKEND_DIR/.env"
HEALTH_URL="http://localhost/api/v1/health/"
HEALTH_RETRIES=20
HEALTH_DELAY_SECONDS=5

log()  { printf '[deploy] %s\n' "$1"; }
fail() { printf '[deploy] ERROR: %s\n' "$1" >&2; exit 1; }

require_env_file() {
    [ -f "$ENV_FILE" ] || fail "$ENV_FILE introuvable. Copier .env.example vers .env et le renseigner avant de déployer."

    local required_vars=(
        DB_NAME DB_USER DB_PASSWORD DB_HOST DB_PORT
        CLOUDINARY_CLOUD_NAME CLOUDINARY_API_KEY CLOUDINARY_API_SECRET
        REDIS_URL SECRET_KEY ALLOWED_HOSTS
        MEDIAMTX_RTMP_SERVER_URL MEDIAMTX_HLS_BASE_URL
    )
    local missing=()
    for var in "${required_vars[@]}"; do
        # Matches "VAR=" followed by at least one non-whitespace character.
        grep -Eq "^${var}=\S+" "$ENV_FILE" || missing+=("$var")
    done
    if [ "${#missing[@]}" -gt 0 ]; then
        fail "variables manquantes ou vides dans .env : ${missing[*]}"
    fi
}

compose() {
    (cd "$STACK_DIR" && docker compose "$@")
}

cmd_up() {
    require_env_file
    log "construction et démarrage de la pile (elasticsearch, api, worker, beat, nginx)..."
    compose up -d --build

    log "attente de la disponibilité de l'API (jusqu'à $((HEALTH_RETRIES * HEALTH_DELAY_SECONDS))s)..."
    local attempt=1
    while [ "$attempt" -le "$HEALTH_RETRIES" ]; do
        if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
            log "API en ligne (${HEALTH_URL})."
            log "vérifications manuelles restantes : voir docs/DEPLOY.md section 'Vérification post-déploiement'"
            log "  - ws://<domaine>/ws/live/radio/live/ (chat + présence)"
            log "  - rtmp://<domaine>:1935/live/<clé> (ingestion MediaMTX, self-hosted)"
            compose ps
            return 0
        fi
        log "tentative ${attempt}/${HEALTH_RETRIES}..."
        attempt=$((attempt + 1))
        sleep "$HEALTH_DELAY_SECONDS"
    done

    fail "l'API n'a pas répondu à temps. Diagnostiquer avec : docs/deploy.sh logs api"
}

cmd_down() {
    log "arrêt de la pile (les volumes — données Elasticsearch, statiques, médias — sont conservés)..."
    compose down
}

cmd_restart() {
    log "redémarrage de api/worker/beat (sans reconstruction d'image)..."
    compose restart api worker beat
}

cmd_status() {
    compose ps
}

cmd_logs() {
    local service="${1:-}"
    if [ -n "$service" ]; then
        compose logs -f --tail=200 "$service"
    else
        compose logs -f --tail=200
    fi
}

cmd_migrate() {
    log "exécution des migrations Django dans le conteneur api..."
    compose exec api python manage.py migrate --noinput
}

cmd_shell() {
    compose exec api python manage.py shell
}

main() {
    local command="${1:-}"
    [ -n "$command" ] && shift || true

    case "$command" in
        up)       cmd_up ;;
        down)     cmd_down ;;
        restart)  cmd_restart ;;
        status)   cmd_status ;;
        logs)     cmd_logs "${1:-}" ;;
        migrate)  cmd_migrate ;;
        shell)    cmd_shell ;;
        *)
            printf 'Usage: %s {up|down|restart|status|logs [service]|migrate|shell}\n' "$0" >&2
            exit 1
            ;;
    esac
}

main "$@"
