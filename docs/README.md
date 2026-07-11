# Art du Kivu — Backend API

Documentation technique complète de l'API backend de la plateforme **Art du Kivu**, dédiée à la
musique et aux arts congolais (région Goma / Kivu). Ce document décrit l'architecture, les
conventions, les fonctionnalités et le fonctionnement interne du service afin que toute personne
rejoignant le projet puisse devenir opérationnelle rapidement.

Ce fichier fait partie du dossier `docs/` du sous-projet `backend/`. Voir aussi :

- `docs/PRODUCTION.md` — options de mise en production (Docker ou hébergement managé)
- `docs/docker-production/` — Dockerfile et `docker-compose.yaml` prêts pour la production
- `docs/DEPLOY.md` et `docs/deploy.sh` — procédure et script de déploiement
- `docs/FRONTEND_INTEGRATION.md` — guide d'intégration complet pour les frontends (admin et client)

---

## Sommaire

1. [Vue d'ensemble](#vue-densemble)
2. [Glossaire du domaine](#glossaire-du-domaine)
3. [Stack technique](#stack-technique)
4. [Architecture du projet](#architecture-du-projet)
5. [Applications Django](#applications-django)
6. [Authentification](#authentification)
7. [Temps réel (WebSocket, présence, chat en direct)](#temps-réel-websocket-présence-chat-en-direct)
8. [Streaming en direct (Cloudflare Stream)](#streaming-en-direct-cloudflare-stream)
9. [Système d'engagement générique](#système-dengagement-générique)
10. [Page d'accueil agrégée](#page-daccueil-agrégée)
11. [Recherche (Elasticsearch)](#recherche-elasticsearch)
12. [Tâches asynchrones (Celery)](#tâches-asynchrones-celery)
13. [Cache](#cache)
14. [Pagination, tri, filtres](#pagination-tri-filtres)
15. [Limitation de débit (throttling)](#limitation-de-débit-throttling)
16. [Format des erreurs](#format-des-erreurs)
17. [Référence des endpoints](#référence-des-endpoints)
18. [Variables d'environnement](#variables-denvironnement)
19. [Installation et exécution locale](#installation-et-exécution-locale)
20. [Tests](#tests)
21. [Documentation API interactive](#documentation-api-interactive)
22. [Conventions de code](#conventions-de-code)

---

## Vue d'ensemble

Le backend est une API REST construite avec **Django 6** et **Django REST Framework**, exposée
sous le préfixe `/api/v1/`. Elle sert deux frontends Next.js du même monorepo :

- `frontend_admin/` — interface d'administration de contenu (CMS)
- `frontend_client/` — site public consulté par les visiteurs et utilisateurs

Le backend couvre l'ensemble des fonctionnalités du produit : profils d'artistes, articles et
magazine, événements, podcasts, radio (grille + direct), web-tv (catalogue + direct), émissions
live, un module "Live Music" indépendant, une communauté (posts, défis, sondages), les sorties
musicales, la recherche unifiée, les newsletters, l'analytics, et une page d'accueil agrégée.

Un chantier récent a ajouté trois capacités transversales à la plateforme :

- **Diffusion en direct** (audio et vidéo) via **Cloudflare Stream**, pour la radio, les émissions,
  le web-tv et le module Live Music.
- **Temps réel** (WebSocket) via **Django Channels**, pour le chat en direct et le comptage de
  spectateurs/auditeurs en ligne ("presence").
- **Engagement générique** (j'aime / commentaire / partage / enregistrer pour plus tard),
  réutilisable sur tout type de contenu via `ContentType` de Django, sans dupliquer de logique
  d'une app à l'autre.

## Glossaire du domaine

| Terme français      | Équivalent anglais | Notes |
|----------------------|--------------------|-------|
| Artiste              | Artist             | Musiciens congolais : genres, sorties, galerie |
| Émission             | Broadcast show     | Émission live programmée (radio/vidéo) |
| Sortie / Première    | Release / Premiere | Nouvelle sortie musicale |
| Communauté           | Community          | Contenu généré par les utilisateurs : talents, sondages, défis |
| Médiathèque          | Media library      | Navigateur Cloudinary côté admin |
| Web-TV               | Web TV             | Contenu vidéo (freestyles, sessions studio, documentaires) |
| Radio en direct       | Live radio         | Flux continu + chat en direct |
| Live Music           | Live Music         | Diffusion musicale en direct indépendante, avec sa propre grille de programmes |
| Son en direct        | Live track/session | Le flux "Live Music" actuellement diffusé |
| Grille               | Schedule / grid    | Programme horaire hebdomadaire (radio, live music) |
| À la une             | Featured           | Contenu mis en avant sur la page d'accueil |
| Hits du mois         | Hits of the month  | Classement des sorties les plus engagées ce mois-ci |

## Stack technique

| Domaine | Choix | Détails |
|---|---|---|
| Langage / Framework | Python 3.14, Django 6, DRF 3.17 | API REST sous `/api/v1/` |
| Base de données | PostgreSQL | Pool de connexions via `django-db-connection-pool` |
| Cache | Redis (Aiven, TLS) via `django-redis` | Localement remplacé par `LocMemCache` (voir plus bas) |
| Files / tâches planifiées | Celery + Redis (broker et backend) + `django-celery-beat` | |
| Temps réel | Django Channels + `channels-redis` | Connexion directe à `REDIS_URL`, indépendante du cache Django |
| Serveur ASGI (prod) | Gunicorn + worker `uvicorn.workers.UvicornWorker` | Requis pour le WebSocket (voir `entrypoint.sh`) |
| Serveur ASGI (dev) | `daphne` (déclenché automatiquement par `manage.py runserver`) | |
| Authentification | SimpleJWT (access 15 min / refresh 7 jours) + Google OAuth (`django-allauth`, `dj-rest-auth`) | |
| Stockage média | Cloudinary | Images, audio, vidéo non-live |
| Diffusion en direct | Cloudflare Stream | Ingestion RTMPS, lecture HLS/DASH |
| Recherche | Elasticsearch via `django-elasticsearch-dsl` | Resynchronisation planifiée (pas de signal temps réel, volontairement) |
| Documentation API | `drf-spectacular` | ReDoc + Swagger UI + schéma OpenAPI |
| Tests | `pytest-django`, `factory-boy` | Voir la section [Tests](#tests) pour une limitation connue |

## Architecture du projet

```
backend/
├── manage.py
├── requirements.txt
├── Dockerfile                 ← image de développement / simulation (voir aussi docs/docker-production)
├── docker-compose.yml         ← simulation locale (Postgres et Redis restent externes/managés)
├── entrypoint.sh
├── artdukivu/                 ← configuration du projet Django
│   ├── settings → voir settings/
│   ├── urls.py                ← montage de toutes les apps sous /api/v1/
│   ├── asgi.py                ← ProtocolTypeRouter (HTTP + WebSocket)
│   ├── wsgi.py
│   └── celery.py
├── settings/
│   ├── base.py                ← configuration commune (apps, cache, Celery, Channels, Cloudflare...)
│   ├── local.py                ← DEBUG=True, cache LocMemCache (pas de Redis local requis)
│   └── production.py          ← sécurité stricte, e-mails SMTP
├── core/                      ← utilitaires transverses réutilisables
│   ├── pagination.py           (StandardPagination 20/page, SmallPagination 10/page)
│   ├── permissions.py          (IsAdminOrReadOnly, IsOwnerOrAdmin, IsSelfOrAdmin)
│   ├── throttling.py           (anon_burst, user_burst, auth, upload)
│   ├── serializers.py          (BulkDeleteSerializer)
│   ├── exceptions.py           (gestionnaire d'erreurs uniforme)
│   └── utils.py                (slugs, invalidation de cache, temps de lecture)
├── docs/                      ← vous êtes ici
└── apps/
    ├── accounts/               Utilisateur custom, JWT, Google OAuth, favoris, historique d'écoute
    ├── artists/                Profils d'artistes, genres, sorties (héritées), galerie
    ├── articles/               Articles de blog et de magazine, catégories, tags, commentaires
    ├── events/                 Événements, villes, grille horaire, inscriptions
    ├── podcasts/                Séries et épisodes de podcast
    ├── radio/                   Grille radio hebdomadaire, direct, chat
    ├── webtv/                    Catalogue vidéo + direct + chat
    ├── community/               Posts communautaires, soumission de talents, défis, sondages
    ├── releases/                 Sorties musicales (source canonique — voir note plus bas)
    ├── emissions/                Émissions live programmées (audio/vidéo)
    ├── live_music/               Diffusion musicale en direct indépendante + grille + chat
    ├── engagement/                J'aime / commentaire / partage / enregistrer — générique
    ├── realtime/                  Channels : WebSocket, présence, modèle de chat générique
    ├── streaming/                 Client Cloudflare Stream, webhook, champs live réutilisables
    ├── home/                      Page d'accueil agrégée (bannière, à la une, hits, magazine)
    ├── analytics/                 Tableau de bord de statistiques globales
    ├── newsletter/                Abonnement/désabonnement, campagnes
    └── search/                    Recherche unifiée multi-index (Elasticsearch)
```

> **Note sur les sorties musicales** : `apps.artists.Release` et `apps.releases.MusicRelease`
> coexistent (héritage historique). `apps.releases.MusicRelease` est la source canonique pour
> tout nouveau développement (notamment le classement "hits du mois" de la page d'accueil et le
> système d'engagement) ; `apps.artists.Release` n'est pas utilisé par les nouvelles
> fonctionnalités et n'a pas été retouché.

## Applications Django

Chaque app suit une structure homogène : `models.py` (données uniquement), `serializers.py`
(sérialisation), `views.py` (fine — validation puis appel à `services.py`), `services.py` (logique
métier et requêtes), `tasks.py` (tâches Celery), `admin.py`, `urls.py`, `tests/`.

| App | Rôle | Point d'entrée URL |
|---|---|---|
| `accounts` | Utilisateur custom (email comme identifiant), JWT, OAuth Google, favoris, historique d'écoute | `/api/v1/auth/`, `/api/v1/users/` |
| `artists` | Profils d'artistes, genres, galerie | `/api/v1/artists/` |
| `articles` | Articles (blog et magazine), catégories, tags, commentaires dédiés | `/api/v1/articles/` |
| `events` | Événements, villes, grille horaire, inscriptions | `/api/v1/events/` |
| `podcasts` | Séries et épisodes (audio Cloudinary ou URL externe) | `/api/v1/podcasts/` |
| `radio` | Grille hebdomadaire, direct, chat, diffusion Cloudflare | `/api/v1/radio/` |
| `webtv` | Catalogue vidéo par catégorie + vidéo en direct + chat | `/api/v1/webtv/` |
| `community` | Posts (dont soumission de talents), défis, sondages | `/api/v1/community/` |
| `releases` | Sorties musicales (source canonique) | `/api/v1/releases/` |
| `emissions` | Émissions live programmées (audio/vidéo), diffusion Cloudflare | `/api/v1/emissions/` |
| `live_music` | Session live indépendante + grille de programmes + chat | `/api/v1/live_music/` |
| `engagement` | J'aime, commentaire, partage, enregistrement — génériques | monté en actions sur les ViewSets consommateurs |
| `realtime` | Consommateur WebSocket, présence Redis, modèle de chat générique | `ws/live/<room_type>/<room_id>/` |
| `streaming` | Client Cloudflare Stream et réception de webhook | `/api/v1/streaming/` |
| `home` | Agrégation de la page d'accueil | `/api/v1/home/` |
| `analytics` | Tableau de bord de statistiques | `/api/v1/analytics/` |
| `newsletter` | Abonnements et campagnes | `/api/v1/newsletter/` |
| `search` | Recherche unifiée multi-index | `/api/v1/search/` |

## Authentification

- **JWT** (`djangorestframework-simplejwt`) : jeton d'accès valable **15 minutes**, jeton de
  rafraîchissement valable **7 jours**, rotation activée avec liste noire après rotation.
- **Google OAuth** via `django-allauth` + `dj-rest-auth`, exposé sur `/api/v1/auth/google/`.
- Modèle utilisateur personnalisé `apps.accounts.User` (email comme identifiant), avec `handle`,
  `avatar`, `bio`, `role` (admin/editor/moderator/viewer), `favorite_artists`, `listen_count`.
- Permission par défaut : `IsAuthenticatedOrReadOnly`. Les écritures administratives utilisent
  `IsAdminOrReadOnly` (permission personnalisée basée sur `is_staff`).
- **Règle produit retenue pour les fonctionnalités temps réel** : être authentifié (JWT valide)
  suffit pour poster un message de chat en direct ou un commentaire — aucune contrainte de
  "profil complété" n'est appliquée. `handle`/`avatar` restent facultatifs et affichés avec repli
  sur le nom d'utilisateur s'ils sont absents.

Voir `docs/FRONTEND_INTEGRATION.md` pour le détail des appels (login, refresh, Google, etc.).

## Temps réel (WebSocket, présence, chat en direct)

Le temps réel repose sur **Django Channels**, avec un `channel layer` Redis (`channels-redis`)
connecté directement à `REDIS_URL` — indépendamment du cache Django (voir la note ci-dessous).

- **Point d'entrée WebSocket unique et paramétré** : `ws/live/<room_type>/<room_id>/`
  `room_type` ∈ `radio | live_music | webtv | emission`. Un salon = un `room_type` + un
  identifiant d'objet (par exemple l'identifiant du `WebTVVideo` actuellement en direct).
- **Authentification WebSocket** : le token JWT est transmis en paramètre de requête
  (`?token=...`) car un navigateur ne peut pas ajouter d'en-tête personnalisé à la poignée de
  main WebSocket. `apps.realtime.middleware.JWTAuthMiddleware` le valide et peuple
  `scope["user"]`. Les connexions anonymes sont acceptées (la présence doit compter tous les
  spectateurs, pas seulement les utilisateurs connectés) ; seule la création d'un message
  nécessite une authentification, via l'API REST (voir plus bas).
- **Présence** : implémentée avec un ensemble trié Redis (`ZSET`) par salon,
  `presence:<room_type>:<room_id>`, membre = identifiant de connexion (`channel_name`), score =
  horodatage du dernier battement de cœur ("heartbeat"). Une connexion compte comme "en ligne" si
  son battement date de moins de 30 secondes ; les entrées expirées sont balayées à chaque lecture
  du compteur (`ZREMRANGEBYSCORE`). Le client doit envoyer `{"type": "heartbeat"}` sur le socket
  toutes les 15 secondes environ.
- **Messages de chat** : créés via une action REST (`GET`/`POST /<ressource>/<id>/chat/`), **pas**
  directement sur le socket. La création REST déclenche un `channel_layer.group_send` qui pousse
  le message aux clients WebSocket déjà connectés au salon. Ce choix permet un chargement initial
  simple en HTTP (pagination classique) tout en gardant un vrai push temps réel pour la suite.
- **Deux implémentations de chat coexistent volontairement** :
  - `apps.radio.RadioChat` — modèle historique, conservé tel quel (déjà en production), qui
    bénéficie désormais de la présence et du push temps réel via le même consommateur.
  - `apps.realtime.LiveChatMessage` — modèle générique (`ContentType` + `object_id`), utilisé par
    les nouvelles surfaces (`live_music`, `webtv`), monté via
    `apps.realtime.mixins.LiveChatViewSetMixin`.
- **Événements poussés au client** sur le socket :
  - `{"event": "presence.count", "count": <int>}` — à chaque connexion/déconnexion/battement.
  - `{"event": "chat.message", "message": {...}}` — à chaque nouveau message créé via REST.

### Pourquoi la présence ne passe pas par `django_redis`

`get_redis_connection("default")` de `django_redis` exige que le **cache** Django utilise
réellement le backend `django_redis`. Or `settings/local.py` bascule volontairement `CACHES` sur
`LocMemCache` pour éviter d'exiger un Redis local en développement — alors que Celery (et
désormais la présence) continuent de parler directement au vrai Redis (Aiven) via `REDIS_URL`.
`apps.realtime.presence` construit donc son propre client `redis.from_url(settings.REDIS_URL, ...)`,
indépendant de la configuration du cache, exactement comme le fait déjà `CHANNEL_LAYERS`.

### `manage.py runserver` et WebSocket en local

`daphne` est placé en première position dans `INSTALLED_APPS` : c'est le mécanisme documenté par
Channels pour que `manage.py runserver` gère nativement les mises à niveau WebSocket en
développement. En production, ce n'est **pas** `daphne` qui sert l'application (voir
`entrypoint.sh` / `docs/docker-production/Dockerfile`), mais **Gunicorn avec un worker
`uvicorn.workers.UvicornWorker`**, pointé directement sur `artdukivu.asgi:application`.

## Streaming en direct (Cloudflare Stream)

Le stockage média classique (images, audio de podcast, vidéos non-live) reste sur **Cloudinary**.
Le **direct** (audio et vidéo) utilise **Cloudflare Stream** :

- `apps.streaming.client` — client HTTP minimal (`requests`) vers l'API Cloudflare Stream
  (`Live Inputs`) : création (`create_live_input`), lecture de statut (`get_live_input`),
  suppression (`delete_live_input`), construction des URLs de lecture HLS/DASH
  (`build_playback_urls`, basées sur `CLOUDFLARE_CUSTOMER_HOSTNAME`).
- `apps.streaming.fields.CloudflareLiveFields` — mixin de modèle abstrait apportant les champs
  `cf_live_input_uid`, `cf_rtmps_url`, `cf_rtmps_key` (jamais exposé publiquement, réservé aux
  admins), `cf_playback_hls_url`, `cf_playback_dash_url`, `live_started_at`. Hérité par
  `Emission`, `RadioProgram`, `WebTVVideo`, `MusicLiveSession`.
- `apps.streaming.services.start_live_input(name)` / `stop_live_input(uid)` — fonctions
  génériques appelées par le `services.py` de chaque app consommatrice (`start_live` /
  `end_live`), qui gèrent en plus leur propre champ de statut (`status="live"` ou `is_live=True`
  selon le modèle).
- **Actions d'administration** `POST .../<id>/go_live/` et `POST .../<id>/end_live/`
  (`IsAdminUser` uniquement) sur `EmissionViewSet`, `RadioProgramViewSet`, `WebTVVideoViewSet`,
  `MusicLiveSessionViewSet`. `go_live` renvoie les identifiants RTMPS à donner au logiciel de
  diffusion (OBS ou équivalent) ; ces champs ne sont **jamais** renvoyés par les endpoints publics
  de lecture.
- **Webhook** `POST /api/v1/streaming/webhook/` — reçoit les événements
  `live_input.connected` / `live_input.disconnected` de Cloudflare, vérifie la signature HMAC-SHA256
  (en-tête `Webhook-Signature`, secret `CLOUDFLARE_WEBHOOK_SECRET`), puis bascule automatiquement
  le statut de la ressource correspondante (retrouvée par `cf_live_input_uid`). C'est le signal
  fiable de "le diffuseur est réellement connecté", indépendant de l'intention déclarée par
  l'action `go_live`.

### Configuration du webhook Cloudflare Stream

```bash
curl -X PUT \
  "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/stream/webhook" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{"notificationUrl": "https://<domaine-backend>/api/v1/streaming/webhook/"}'
```

Le secret renvoyé par cet appel doit être copié dans `CLOUDFLARE_WEBHOOK_SECRET` (`.env`).

## Système d'engagement générique

`apps.engagement` fournit quatre modèles génériques, adossés à `django.contrib.contenttypes`
(`ContentType` + `object_id`), réutilisables sur **n'importe quel** modèle sans migration
supplémentaire ni duplication de vues :

| Modèle | Rôle | Contrainte |
|---|---|---|
| `Like` | J'aime | unique par (contenu, utilisateur) |
| `Comment` | Commentaire, avec réponses (`parent`) | — |
| `Share` | Partage (compteur) | utilisateur optionnel (partage possible en anonyme pour le comptage) |
| `SavedItem` | "Écouter/regarder plus tard" | unique par (contenu, utilisateur) ; **interdit sur le contenu actuellement en direct** |

`apps.engagement.mixins.EngagementActionsMixin` ajoute quatre actions DRF à n'importe quel
`ModelViewSet` : `POST .../like/` (bascule), `GET`/`POST .../comments/`, `POST .../share/`,
`POST`/`DELETE .../save/`. Monté sur : `PodcastEpisodeViewSet`, `WebTVVideoViewSet`,
`ReleaseViewSet`, `CommunityPostViewSet`, `EmissionViewSet`.

La règle "pas d'enregistrement pour le direct" est appliquée **au niveau service**
(`apps.engagement.services.toggle_save`, via `is_currently_live(instance)` qui vérifie
`status == "live"` ou `is_live is True`) plutôt que par un simple drapeau sur le ViewSet : un
enregistrement (`Emission`) redevient donc enregistrable une fois son statut passé à `recorded`.

Les modèles historiques (`apps.articles.Comment`/`ArticleLike`, `apps.community.PostLike`)
restent **inchangés** — aucune migration de données, pour ne pas introduire de régression sur du
code déjà en production. Seules les nouvelles intégrations utilisent le système générique.

## Page d'accueil agrégée

`GET /api/v1/home/` (cache 15 minutes) renvoie un unique payload :

```json
{
  "banner": { "image_url": "...", "title": "...", "subtitle": "...", "cta_label": "...", "cta_url": "..." },
  "a_la_une": {
    "artist_of_month": { "...": "Artist.is_featured=True" },
    "featured_podcast": { "...": "PodcastEpisode.is_featured=True" },
    "featured_event": { "...": "Event.is_featured=True" }
  },
  "hits_du_mois": [ "...MusicRelease classées par score d'engagement du mois..." ],
  "magazine": {
    "hero": { "...": "Article magazine mis en avant" },
    "articles": [ "...six articles magazine récents..." ]
  }
}
```

La bannière est un singleton administrable (`apps.home.HomeBanner`, `get_or_create(pk=1)`). Le
classement "hits du mois" pondère les interactions du mois courant (`Like` × 1, `Share` × 2,
`SavedItem` × 1) sur `MusicRelease` ; en l'absence totale d'engagement ce mois-ci (par exemple au
tout début de la mise en production), il retombe sur un tri `is_featured` puis `release_date`
décroissante, pour éviter une section vide.

## Recherche (Elasticsearch)

`django-elasticsearch-dsl` indexe : artistes, articles, événements, séries et épisodes de
podcast, sorties, vidéos web-tv, posts communautaires. La synchronisation automatique par signal
est **désactivée volontairement** (`ELASTICSEARCH_DSL_AUTOSYNC = False`,
`ELASTICSEARCH_DSL_SIGNAL_PROCESSOR = BaseSignalProcessor`) — un bug documenté dans
`settings/base.py` fait que les processeurs de signal fournis se déclenchent sur **tout**
enregistrement du projet, pas seulement les modèles indexés, ce qui provoquait des appels Celery
non désirés à chaque migration. La réindexation se fait via une tâche planifiée toutes les 5
minutes (`apps.search.tasks.resync_search_index`).

## Tâches asynchrones (Celery)

Broker et backend de résultats : le même Redis (Aiven) que le cache, avec `ssl_cert_reqs=CERT_NONE`
lorsque l'URL est en `rediss://`.

`CELERY_BEAT_SCHEDULE` (voir `settings/base.py`) :

| Tâche | Fréquence | Rôle |
|---|---|---|
| `apps.events.tasks.update_event_statuses` | 1 h | upcoming → live → past |
| `apps.artists.tasks.warm_featured_cache` | 30 min | préchauffe le cache des artistes à la une |
| `apps.radio.tasks.cleanup_old_chat` | 24 h | purge les messages de chat radio de plus de 7 jours |
| `apps.emissions.tasks.update_emission_statuses` | 1 h | scheduled → live → recorded |
| `apps.search.tasks.resync_search_index` | 5 min | resynchronise les index Elasticsearch |

Les compteurs de vues/écoutes (`view_count`, `play_count`) sont incrémentés de façon asynchrone
pour ne jamais bloquer la réponse HTTP.

## Cache

`django-redis`, préfixe `artdukivu`, TTL par défaut 15 minutes. Les listes publiques sûres
utilisent `@cache_page`. Invalidation ciblée par motif de clé (`core.utils.invalidate_resource_cache`)
lors des écritures. **Exception volontaire** : `radio/current/` n'est **pas** mis en cache car il
renvoie désormais un `listener_count` lu en direct depuis la présence Redis — le mettre en cache
figerait ce chiffre pour toute la durée du TTL.

En développement local, `settings/local.py` remplace `CACHES` par `LocMemCache` pour éviter
d'exiger un Redis local — Celery et la présence temps réel continuent, eux, de parler
directement au Redis managé via `REDIS_URL` (voir la section [Temps réel](#temps-réel-websocket-présence-chat-en-direct)).

## Pagination, tri, filtres

- `core.pagination.StandardPagination` — 20 éléments par page (max 100), utilisée par défaut.
- `core.pagination.SmallPagination` — 10 éléments par page (max 50), utilisée pour les flux de
  chat et de commentaires.
- Forme de réponse paginée :

```json
{
  "count": 123,
  "next": "http://.../?page=2",
  "previous": null,
  "total_pages": 7,
  "current_page": 1,
  "results": [ "..." ]
}
```

- Filtrage via `django-filter`, recherche via `SearchFilter` (`?search=`), tri via
  `OrderingFilter` (`?ordering=-champ`).

## Limitation de débit (throttling)

| Portée | Limite |
|---|---|
| `anon_burst` | 30 requêtes / minute |
| `user_burst` | 120 requêtes / minute |
| `auth` | 10 requêtes / minute (login, inscription) |
| `upload` | 5 requêtes / minute |

## Format des erreurs

Un gestionnaire d'exceptions unique (`core.exceptions.custom_exception_handler`) garantit que
**toute** erreur DRF renvoie la forme :

```json
{ "detail": "Message lisible.", "code": "some_error_code" }
```

Les exceptions non gérées (bug serveur) renvoient un `500` uniforme :

```json
{ "detail": "Une erreur inattendue est survenue.", "code": "server_error" }
```

sans jamais divulguer de trace d'exécution au client, y compris quand `DEBUG=True` côté serveur.

## Référence des endpoints

Tous les endpoints sont montés sous `/api/v1/`. Liste complète et exemples de requêtes/réponses :
voir `docs/FRONTEND_INTEGRATION.md`. Aperçu des préfixes :

```
/api/v1/auth/                  inscription, connexion, refresh, Google OAuth, mot de passe
/api/v1/users/                 profil, favoris, historique d'écoute
/api/v1/artists/                profils d'artistes, genres
/api/v1/articles/                articles (blog + magazine), catégories, tags, commentaires
/api/v1/events/                  événements, villes, inscriptions
/api/v1/podcasts/                 séries, épisodes (+ j'aime/commentaire/partage/enregistrer)
/api/v1/radio/                    grille, direct courant, chat
/api/v1/webtv/                     catalogue, vidéo en direct, chat, engagement
/api/v1/community/                  posts, soumission de talent, défis, sondages
/api/v1/releases/                    sorties musicales (+ engagement)
/api/v1/emissions/                   émissions live (+ engagement, go_live/end_live)
/api/v1/live_music/                   session live, grille de programmes, chat
/api/v1/streaming/                    webhook Cloudflare Stream
/api/v1/home/                          page d'accueil agrégée
/api/v1/analytics/                      tableau de bord de statistiques
/api/v1/newsletter/                      abonnement, campagnes
/api/v1/search/                           recherche unifiée
ws/live/<room_type>/<room_id>/            WebSocket : présence + chat en direct
```

## Variables d'environnement

Voir `.env.example` pour la liste exhaustive. Catégories principales :

| Catégorie | Variables |
|---|---|
| Base de données | `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` |
| Cloudinary | `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` |
| Cloudflare Stream | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_CUSTOMER_HOSTNAME`, `CLOUDFLARE_WEBHOOK_SECRET` |
| Redis | `REDIS_URL` (cache prod, Celery, Channels, présence) |
| Auth | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SECRET_KEY` |
| E-mail | `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` |
| Réseau | `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `FRONTEND_URL` |
| Recherche | `ELASTICSEARCH_URL` |

## Installation et exécution locale

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # puis renseigner les valeurs

DJANGO_SETTINGS_MODULE=settings.local python manage.py migrate
DJANGO_SETTINGS_MODULE=settings.local python manage.py seed_data   # jeu de données Faker
DJANGO_SETTINGS_MODULE=settings.local python manage.py runserver
```

`daphne` étant en tête des `INSTALLED_APPS`, `runserver` gère nativement HTTP **et** WebSocket en
local — aucune commande séparée n'est nécessaire pour tester le chat en direct.

Celery (dans un autre terminal, si les tâches asynchrones sont nécessaires) :

```bash
celery -A artdukivu worker -l info
celery -A artdukivu beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## Tests

```bash
DJANGO_SETTINGS_MODULE=settings.local python -m pytest
```

**Limitation connue, non liée aux fonctionnalités récentes** : dans cet environnement, la
création de la base de test par `pytest-django` reste bloquée indéfiniment — reproductible même
sur les tests déjà existants et non modifiés (`apps/accounts/tests/test_views.py`). L'hypothèse la
plus probable est que `DB_HOST`/`DB_PORT` pointent vers un pooler (mode transactionnel, port
6543), qui ne supporte généralement pas les commandes DDL de session comme `CREATE DATABASE`
qu'exige la création d'une base de test. À corriger en pointant les exécutions de tests vers une
connexion Postgres directe (port 5432, hors pooler), ou vers une instance locale dédiée aux tests.

## Documentation API interactive

- ReDoc : `/api/docs/`
- Swagger UI : `/api/schema/swagger-ui/`
- Schéma OpenAPI brut : `/api/schema/`

## Conventions de code

- Fichiers de moins de 300 lignes.
- Logique métier dans `services.py` (accès base de données) ou `utils.py` (fonctions pures, sans
  base de données).
- Vues volontairement fines : valider → appeler le service → sérialiser → répondre.
- `select_related`/`prefetch_related` dans les `QuerySet` des vues, jamais dans les sérialiseurs.
- Agrégats calculés via `annotate()` plutôt que `SerializerMethodField` quand c'est possible.
- Toutes les listes sont paginées (20 par défaut, 100 maximum).
- `bulk_create` pour les insertions de masse, transactions (`@transaction.atomic`) pour les
  écritures multi-étapes.
- Invalidation de cache explicite sur chaque écriture (motif de clé par ressource).
- Tâches Celery pour tout ce qui peut être différé : envoi d'e-mail, incrément de compteur,
  notifications.
