# Déploiement sur le VPS partagé — art-du-kivu-api.kelor.tech

Ce runbook déploie le backend Art du Kivu sur un VPS Ubuntu 24.04 qui héberge déjà un autre
service (`icarm-api`, natif via systemd + nginx). Toute la pile applicative (Postgres, Redis,
Elasticsearch, API, worker, beat) tourne en conteneurs Docker, isolée du reste — le nginx déjà
en place sur la machine reste l'unique point d'entrée public (port 80/443), exactement comme
pour `icarm-api`.

Diagnostic initial (voir conversation) : Ubuntu 24.04, 4 vCPU, 7.8 Go RAM, 69 Go disque libre,
Docker absent, ports 5432/6379/9200 libres, `ufw` inactif, certbot 2.9.0 déjà installé.

## Principes de sécurité appliqués

- Postgres/Redis/Elasticsearch ne publient **aucun port** vers l'hôte — seuls les conteneurs
  `api`/`worker`/`beat` du même stack peuvent les joindre (réseau Docker interne).
- Le conteneur `api` publie son port uniquement sur `127.0.0.1:8010` — jamais `0.0.0.0`. Comme
  `ufw` est inactif, c'est cette liaison en loopback (pas une règle de pare-feu) qui empêche
  toute connexion directe depuis l'extérieur.
- Rien de ce qui suit ne modifie `icarm-api`, son fichier nginx, son socket ou son certificat.

## Phase 1 — Installer Docker

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
docker --version
docker compose version
```

## Phase 2 — Transférer le projet

Depuis ta machine locale (remplace par ta méthode habituelle : git clone sur le VPS si le repo
est accessible, ou `rsync`/`scp` depuis ton poste) :

```bash
# Sur le VPS, si le repo est accessible en clone :
cd /opt/art-du-kivu-backend
git clone <url-du-repo> .
# — ou, depuis ta machine locale, si tu préfères rsync (à adapter) :
# rsync -avz --exclude venv --exclude __pycache__ ./backend/ root@45.151.122.103:/opt/art-du-kivu-backend/
```

Vérifie que `docs/vps-deployment/` (ce dossier) est bien présent une fois transféré.

## Phase 3 — Préparer `.env`

```bash
cd /opt/art-du-kivu-backend
cp .env.example .env   # si .env n'a pas déjà été transféré
```

Édite `.env` (`nano .env`) et renseigne au minimum :

- `DB_NAME`, `DB_USER`, `DB_PASSWORD` — choisis un **nouveau** mot de passe fort dédié à ce
  Postgres auto-hébergé (ne réutilise pas un mot de passe existant). `DB_HOST`/`DB_PORT` sont
  déjà forcés à `db`/`5432` par `docker-compose.yaml` — inutile de les régler ici.
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
- `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_CUSTOMER_HOSTNAME` — laisse
  `CLOUDFLARE_WEBHOOK_SECRET` vide pour l'instant (voir Phase 8).
- `SECRET_KEY` — génère une valeur unique, par ex. :
  `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
- `ALLOWED_HOSTS=art-du-kivu-api.kelor.tech` et `CORS_ALLOWED_ORIGINS=` (laisse vide ou mets un
  placeholder — tu pourras l'affiner en Phase 9 sans tout redéployer).
- `FRONTEND_URL=` — idem, à ajuster en Phase 9.
- `REDIS_URL` et `ELASTICSEARCH_URL` : laisse n'importe quelle valeur, `docker-compose.yaml` les
  **remplace** de toute façon par `redis://redis:6379/0` et `http://elasticsearch:9200`.

**Ne colle jamais le contenu de ce fichier dans une conversation** (avec moi ou qui que ce soit)
une fois qu'il contient de vraies valeurs.

## Phase 4 — Préparer les dossiers static/media

```bash
cd /opt/art-du-kivu-backend
mkdir -p staticfiles mediafiles
chmod 777 staticfiles mediafiles
```

(`chmod 777` est un raccourci pragmatique ici : le conteneur `api` tourne avec un utilisateur
interne non-root dont l'UID exact n'est pas connu à l'avance côté hôte. Ces deux dossiers ne
contiennent que des fichiers statiques/médias déjà publics — pas de données sensibles.)

## Phase 5 — Premier démarrage (sans toucher à nginx)

```bash
cd /opt/art-du-kivu-backend/docs/vps-deployment
docker compose up -d --build
docker compose ps
```

Attends que tous les services soient `healthy` (peut prendre 1-2 minutes, Elasticsearch est le
plus lent à démarrer). Puis vérifie **en local, sans passer par nginx** :

```bash
curl -s http://127.0.0.1:8010/api/v1/health/
```

Tu dois obtenir `{"status": "ok"}`. Si ça échoue, avant de continuer :

```bash
docker compose logs api --tail=100
docker compose logs db --tail=50
```

**Ne passe pas à la Phase 6 tant que cette vérification n'est pas au vert.**

## Phase 6 — Vhost nginx (HTTP seulement, pas encore SSL)

```bash
sudo cp /opt/art-du-kivu-backend/docs/vps-deployment/nginx-art-du-kivu-api.conf \
    /etc/nginx/sites-available/art-du-kivu-api

sudo ln -s /etc/nginx/sites-available/art-du-kivu-api /etc/nginx/sites-enabled/art-du-kivu-api

# Vérifie la syntaxe AVANT de recharger — une erreur ici pourrait empêcher nginx de recharger
# la config d'icarm-api aussi (nginx recharge tous les sites d'un coup).
sudo nginx -t
```

Si `nginx -t` affiche `syntax is ok` / `test is successful` :

```bash
sudo systemctl reload nginx
curl -s http://art-du-kivu-api.kelor.tech/api/v1/health/
```

Si `nginx -t` échoue, **ne recharge pas** — colle-moi l'erreur avant de continuer.

## Phase 7 — Certificat SSL (Certbot)

```bash
sudo certbot --nginx -d art-du-kivu-api.kelor.tech
```

Certbot va automatiquement réécrire `/etc/nginx/sites-available/art-du-kivu-api` pour ajouter le
bloc HTTPS (443) et la redirection HTTP→HTTPS, exactement comme il l'a déjà fait pour
`icarm-api-drf.kelor.tech`. Réponds à ses questions (e-mail, redirection automatique HTTP→HTTPS
recommandée : oui).

Vérifie :

```bash
curl -s https://art-du-kivu-api.kelor.tech/api/v1/health/
curl -o /dev/null -s -w "%{http_code}\n" https://art-du-kivu-api.kelor.tech/api/docs/
```

## Phase 8 — Webhook Cloudflare Stream (maintenant que le domaine est joignable)

```bash
curl -X PUT \
  "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/stream/webhook" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{"notificationUrl": "https://art-du-kivu-api.kelor.tech/api/v1/streaming/webhook/"}'
```

Copie le secret renvoyé dans `.env` (`CLOUDFLARE_WEBHOOK_SECRET=...`), puis :

```bash
cd /opt/art-du-kivu-backend/docs/vps-deployment
./reload-env.sh
```

Vérifie que le webhook répond correctement (403 attendu sans signature valide — c'est le
comportement normal, pas une erreur) :

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://art-du-kivu-api.kelor.tech/api/v1/streaming/webhook/
```

## Phase 9 — Ajuster `FRONTEND_URL` / `ALLOWED_HOSTS` / `CORS_ALLOWED_ORIGINS`

Dès que tu as les URLs définitives des frontends (admin + client) :

```bash
nano /opt/art-du-kivu-backend/.env
# FRONTEND_URL=https://...
# ALLOWED_HOSTS=art-du-kivu-api.kelor.tech
# CORS_ALLOWED_ORIGINS=https://admin.example.com,https://www.example.com

cd /opt/art-du-kivu-backend/docs/vps-deployment
./reload-env.sh
```

Cette même commande (`./reload-env.sh`) est ce que tu utiliseras à chaque fois que tu modifies
`.env` par la suite — elle ne touche ni la base de données, ni Redis, ni Elasticsearch, ni
nginx, uniquement `api`/`worker`/`beat`.

## Vérification complète après déploiement

```bash
curl -s https://art-du-kivu-api.kelor.tech/api/v1/health/
curl -s https://art-du-kivu-api.kelor.tech/api/v1/home/ | head -c 300
curl -o /dev/null -s -w "%{http_code}\n" https://art-du-kivu-api.kelor.tech/api/docs/
# WebSocket (installe `websocat` si besoin, ou teste depuis le frontend directement)
websocat "wss://art-du-kivu-api.kelor.tech/ws/live/radio/live/"
```

## Opérations courantes

```bash
cd /opt/art-du-kivu-backend/docs/vps-deployment

docker compose ps                       # état des conteneurs
docker compose logs -f api               # suivre les logs de l'API
docker compose exec api python manage.py migrate   # migrations manuelles si besoin
./reload-env.sh                          # appliquer un changement de .env
docker compose down                      # arrêter (les volumes/données sont conservés)
docker compose up -d --build             # mise à jour après un `git pull`
```

## Recommandations non appliquées automatiquement (à ta discrétion)

- **Swap absent** (`free -h` montrait `0B`) : avec Elasticsearch + Postgres + Redis + Django +
  Celery sur 7.8 Go partagés avec `icarm-api`, un swap de sécurité (2 Go) éviterait un OOM-kill
  brutal en cas de pic mémoire. Je ne l'ai pas fait — dis-moi si tu veux la commande.
- **`ufw` inactif** : activer un pare-feu minimal (`22`, `80`, `443` uniquement) ajouterait une
  couche de défense en profondeur, utile même si nos ports sensibles sont déjà en loopback.
  Encore une fois, je ne l'ai pas fait sans ton accord explicite — c'est une action qui affecte
  aussi l'accès à `icarm-api` si mal configurée.
