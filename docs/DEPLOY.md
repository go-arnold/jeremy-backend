# Guide de déploiement

Procédure de référence pour déployer le backend Art du Kivu en production. Ce document suppose
que le choix entre les options décrites dans `docs/PRODUCTION.md` a déjà été fait. Il couvre les
deux : le déploiement automatisé de la pile Docker (`docs/deploy.sh`), et le déploiement sur une
plateforme managée (PaaS).

## 1. Checklist avant tout déploiement

- [ ] `SECRET_KEY` généré (valeur unique, longue, jamais celle par défaut de `settings/base.py`).
- [ ] Base de données PostgreSQL provisionnée, **accessible en connexion directe** (pas
      uniquement via un pooler en mode transactionnel — voir `docs/README.md`, section Tests,
      pour le problème que cela cause).
- [ ] Redis provisionné et accessible (cache, Celery, Channels, présence partagent la même
      instance via `REDIS_URL`).
- [ ] Elasticsearch accessible (cluster managé, ou le conteneur fourni dans
      `docs/docker-production/docker-compose.yaml`).
- [ ] Compte Cloudinary configuré (`CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`,
      `CLOUDINARY_API_SECRET`).
- [ ] MediaMTX déployé (auto-hébergé, `docs/docker-production/mediamtx.yml`) avec
      `MEDIAMTX_RTMP_SERVER_URL`, `MEDIAMTX_HLS_BASE_URL` renseignés, et le port RTMP (1935)
      ouvert publiquement. Le statut live est détecté par une tâche Celery qui interroge l'API
      MediaMTX toutes les 15s (`apps.streaming.tasks.sync_live_status`) — pas de webhook, pas de
      secret à configurer pour ça.
- [ ] Nom de domaine et certificat TLS prêts (ou plateforme gérant le TLS automatiquement).
- [ ] `ALLOWED_HOSTS` et `CORS_ALLOWED_ORIGINS` renseignés avec les domaines réels (frontend admin
      et frontend client).
- [ ] `.env` complet et copié à l'emplacement attendu (racine de `backend/` — voir `.env.example`).

## 2. Option Docker (auto-hébergé)

### 2.1. Préparation

```bash
cd backend
cp .env.example .env    # puis renseigner toutes les valeurs (voir checklist ci-dessus)
```

### 2.2. Déploiement automatisé

```bash
docs/deploy.sh up
```

Le script (`docs/deploy.sh`) :

1. Vérifie que `.env` existe et que les variables critiques ne sont pas vides.
2. Construit les images (`Dockerfile` en deux étapes — voir `docs/docker-production/Dockerfile`)
   et démarre `elasticsearch`, `mediamtx`, `api`, `worker`, `beat`, `nginx`.
3. Attend que `GET /api/v1/health/` réponde (jusqu'à ~100 secondes), avec un message d'erreur
   explicite en cas d'échec.
4. Rappelle les vérifications manuelles restantes (WebSocket, ingestion MediaMTX).

Autres commandes disponibles :

```bash
docs/deploy.sh status              # état des conteneurs
docs/deploy.sh logs api            # suivre les logs d'un service (api, worker, beat, nginx, elasticsearch)
docs/deploy.sh migrate             # exécuter les migrations sans redémarrer la pile
docs/deploy.sh shell               # shell Django dans le conteneur api
docs/deploy.sh restart             # redémarrer api/worker/beat sans reconstruire les images
docs/deploy.sh down                # arrêter la pile (les volumes sont conservés)
```

### 2.3. Mises à jour ultérieures

```bash
git pull
docs/deploy.sh up        # reconstruit les images modifiées et relance un déploiement complet
```

Les migrations et la (re)création des index de recherche sont exécutées automatiquement à chaque
démarrage du service `api` (voir la commande définie dans
`docs/docker-production/docker-compose.yaml`).

## 3. Option plateforme managée (PaaS)

1. Connecter le dépôt à la plateforme (Render, Railway, Fly.io ou équivalent), en pointant vers
   `backend/Dockerfile` (racine du sous-projet, pas celui de `docs/docker-production/`).
2. Créer trois services à partir de la même image :
   - **Web** : commande par défaut (`./entrypoint.sh`, déjà configurée pour Gunicorn + worker
     Uvicorn — nécessaire au WebSocket).
   - **Worker** : `celery -A artdukivu worker -l info -Q default,high_priority`
   - **Beat** : `celery -A artdukivu beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`
3. Renseigner toutes les variables de `.env.example` dans la configuration de la plateforme, plus
   `DJANGO_SETTINGS_MODULE=settings.production`.
4. Vérifier explicitement dans la documentation de la plateforme que le plan choisi pour le
   service **Web** supporte les connexions WebSocket de longue durée (certains plans "starter"
   imposent un timeout de requête incompatible avec un chat en direct).
5. **Limite à connaître** : le live streaming (MediaMTX) a besoin d'exposer un port RTMP brut
   (1935/TCP) — la plupart des plans "web" PaaS ne routent que du HTTP(S) et ne conviennent pas
   pour ça. Si tu choisis cette option, prévois un service séparé (VPS/VM classique) juste pour
   `mediamtx`, ou accepte que le live streaming reste indisponible sur ce déploiement.

## 4. Vérification post-déploiement

À exécuter après **tout** déploiement, quelle que soit l'option :

```bash
# 1. Santé générale de l'API
curl -sf https://<domaine>/api/v1/health/

# 2. Page d'accueil agrégée
curl -sf https://<domaine>/api/v1/home/ | head -c 300

# 3. Documentation interactive accessible
curl -o /dev/null -s -w "%{http_code}\n" https://<domaine>/api/docs/

# 4. WebSocket (présence + chat) — nécessite `websocat` ou un client équivalent
websocat "wss://<domaine>/ws/live/radio/live/"
# Une connexion réussie renvoie immédiatement : {"event": "presence.count", "count": 1}

# 5. Live streaming (MediaMTX) — test RTMP + HLS de bout en bout, voir
#    docs/vps-deployment/RUNBOOK.md Phase 8 pour la commande ffmpeg complète.
curl -I https://<domaine>/live-hls/live/<clé-de-test>/index.m3u8
```

Si l'étape 4 échoue avec un code HTTP 404 ou 426 au lieu d'un upgrade WebSocket, le service sert
probablement encore du WSGI pur (`artdukivu.wsgi:application`) au lieu de l'ASGI attendu — revoir
la commande de démarrage du service **Web** (section 2 ou 3 ci-dessus).

## 5. Rollback

**Docker** : `docker compose -f docs/docker-production/docker-compose.yaml down`, puis redéployer
la révision précédente du dépôt avec `docs/deploy.sh up`. Les volumes (`static_files`,
`media_files`, `es_data`) ne sont pas supprimés par `down`.

**PaaS** : utiliser la fonctionnalité de rollback native de la plateforme (redéploiement du build
précédent). Vérifier que les migrations de la révision abandonnée n'étaient pas irréversibles
avant de revenir en arrière côté base de données.

## 6. Sauvegardes

- **PostgreSQL** : sauvegardes automatiques gérées par le fournisseur managé (Supabase ou
  équivalent) — vérifier la rétention configurée.
- **Elasticsearch** : reconstruit intégralement par `resync_search_index` (tâche planifiée toutes
  les 5 minutes) — aucune sauvegarde dédiée n'est nécessaire, seule la source de vérité
  (PostgreSQL) compte.
- **Médias Cloudinary** : gérés par Cloudinary, hors périmètre de ce backend.
