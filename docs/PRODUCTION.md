# Mise en production — vue d'ensemble des options

Ce document présente les options disponibles pour déployer le backend Art du Kivu en production,
et renvoie vers le bon guide selon l'option choisie. Il ne remplace pas `docs/DEPLOY.md` (procédure
détaillée) ni `docs/docker-production/` (fichiers Docker prêts à l'emploi) : il aide seulement à
choisir la bonne voie.

## Prérequis communs, quelle que soit l'option

Indépendamment de l'hébergement choisi, la mise en production nécessite dans tous les cas :

1. **PostgreSQL** joignable en connexion directe (pas uniquement via un pooler en mode
   transactionnel — voir la note sur les tests dans `docs/README.md`).
2. **Redis** joignable (utilisé par : le cache, Celery broker/backend, **et** le channel layer
   Channels + la présence temps réel). Une seule instance managée (Aiven, Upstash, Redis Cloud...)
   suffit pour les trois usages.
3. **Elasticsearch** joignable (cluster managé recommandé — Elastic Cloud, AWS OpenSearch — ou
   conteneur auto-hébergé, voir `docs/docker-production/docker-compose.yaml`).
4. **Cloudinary** configuré (stockage média non-live).
5. **MediaMTX** déployé (auto-hébergé, voir `docs/docker-production/mediamtx.yml`), avec
   `MEDIAMTX_RTMP_SERVER_URL`, `MEDIAMTX_HLS_BASE_URL` renseignés et le port RTMP (1935) ouvert
   publiquement (voir `docs/README.md`, section Streaming en direct). Le statut live est détecté
   par une tâche Celery qui interroge l'API MediaMTX toutes les 15s — vérifie que `worker` et
   `beat` tournent bien tous les deux.
6. **Un serveur ASGI capable de gérer le WebSocket**, pas seulement WSGI. Le projet est configuré
   pour tourner avec `gunicorn -k uvicorn.workers.UvicornWorker` contre `artdukivu.asgi:application`
   (voir `entrypoint.sh` et `docs/docker-production/Dockerfile`). Servir uniquement
   `artdukivu.wsgi:application` **cassera silencieusement** le chat en direct et le comptage de
   présence : les connexions WebSocket recevront une erreur 404/426 au lieu d'un upgrade.
7. **Un reverse proxy qui transmet les en-têtes d'upgrade WebSocket** (`Upgrade`,
   `Connection: upgrade`) sur les chemins `ws/live/...` — voir la configuration nginx fournie dans
   `docs/docker-production/nginx.conf`.
8. `DJANGO_SETTINGS_MODULE=settings.production` et toutes les variables listées dans
   `.env.example` renseignées (voir `docs/README.md`, section Variables d'environnement).

## Option A — Plateforme managée (PaaS : Render, Railway, Fly.io...)

C'est l'approche déjà utilisée par ce projet (le `Dockerfile` à la racine contient déjà un
healthcheck ciblant le port dynamique fourni par ce type de plateforme). Chaque type de processus
Django tourne comme un service séparé sur la plateforme, construit à partir du `Dockerfile` racine :

| Service | Commande |
|---|---|
| Web (API + WebSocket) | `./entrypoint.sh` (déjà configuré avec le worker Uvicorn) |
| Worker Celery | `celery -A artdukivu worker -l info -Q default,high_priority` |
| Beat Celery | `celery -A artdukivu beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler` |

PostgreSQL, Redis et Elasticsearch sont dans ce cas des services **managés externes** (par exemple
Supabase pour Postgres, Aiven pour Redis, Elastic Cloud pour Elasticsearch), référencés uniquement
par variables d'environnement — aucun conteneur de base de données à opérer soi-même.

**Avantages** : aucune infrastructure à maintenir, montée en charge simplifiée, TLS géré par la
plateforme.
**Inconvénients** : moins de contrôle fin sur le réseau (vérifier que la plateforme supporte bien
les connexions WebSocket longue durée sur le plan choisi), coût par service.

Voir `docs/DEPLOY.md` pour la procédure pas à pas (y compris la configuration des variables
d'environnement et la vérification post-déploiement des fonctionnalités temps réel).

## Option B — Docker Compose auto-hébergé (VPS, serveur dédié)

Fichiers prêts à l'emploi dans `docs/docker-production/` :

- `Dockerfile` — image de production (utilisateur non-root, healthcheck, serveur ASGI).
- `docker-compose.yaml` — pile complète : `api` (Gunicorn + worker Uvicorn), `worker` (Celery),
  `beat` (Celery beat), `elasticsearch`, `nginx` (reverse proxy TLS + WebSocket).
- `nginx.conf` — configuration du reverse proxy, y compris le mapping `Upgrade`/`Connection`
  nécessaire au WebSocket.

PostgreSQL et Redis restent volontairement des services **externes managés** dans ce
`docker-compose.yaml` (cohérent avec le reste du projet, qui utilise déjà Supabase et Aiven) — ils
ne sont **pas** inclus comme conteneurs. Pour un déploiement totalement autonome sans dépendance
externe, ajouter des services `postgres:16` et `redis:7` au `docker-compose.yaml` et adapter
`DB_HOST`/`REDIS_URL` en conséquence (voir les commentaires dans le fichier).

**Avantages** : contrôle total, coût fixe, pas de dépendance à une plateforme spécifique.
**Inconvénients** : maintenance du serveur (mises à jour de sécurité, sauvegardes, monitoring) à la
charge de l'équipe.

Voir `docs/DEPLOY.md` et le script `docs/deploy.sh` pour l'automatisation du déploiement de cette
pile.

## Quelle option choisir ?

- Équipe réduite, pas d'expertise infra dédiée, besoin d'aller vite : **Option A**.
- Besoin de maîtriser les coûts à grande échelle, contraintes de données/hébergement
  spécifiques, ou infrastructure déjà en place : **Option B**.

Les deux options partagent strictement le même code applicatif et les mêmes variables
d'environnement — il est possible de migrer de l'une à l'autre sans changement de code.
