# Guide d'intégration frontend

Ce guide s'adresse aux développeurs de `frontend_admin/` et `frontend_client/` (Next.js). Il
couvre l'authentification, les conventions communes à toute l'API, la référence des endpoints par
domaine, et des exemples de code pour les fonctionnalités transversales récentes (temps réel,
diffusion en direct, engagement).

## Sommaire

1. [Base URL et environnements](#base-url-et-environnements)
2. [Authentification](#authentification)
3. [Conventions communes](#conventions-communes)
4. [Utilisateurs](#utilisateurs)
5. [Profil : signets, activité, gamification](#profil--signets-activité-gamification)
6. [Artistes](#artistes)
7. [Articles et magazine](#articles-et-magazine)
8. [Événements](#événements)
9. [Podcasts](#podcasts)
10. [Radio](#radio)
11. [Web TV](#web-tv)
12. [Émissions live](#émissions-live)
13. [Live Music](#live-music)
14. [Communauté](#communauté)
15. [Sorties musicales (releases)](#sorties-musicales-releases)
16. [Système d'engagement générique](#système-dengagement-générique)
17. [Upload de médias (audio/vidéo/image)](#upload-de-médias-audiovidéoimage)
18. [Diffusion en direct (MediaMTX) côté frontend](#diffusion-en-direct-mediamtx-côté-frontend)
19. [Temps réel : WebSocket (chat + présence)](#temps-réel--websocket-chat--présence)
20. [Page d'accueil](#page-daccueil)
21. [Recherche](#recherche)
22. [Newsletter](#newsletter)
23. [Analytics](#analytics)
24. [Exemple de client HTTP avec rafraîchissement automatique du token](#exemple-de-client-http-avec-rafraîchissement-automatique-du-token)

---

## Base URL et environnements

| Environnement | URL de base |
|---|---|
| Local | `http://localhost:8000/api/v1/` |
| WebSocket local | `ws://localhost:8000/ws/` |
| Production | `https://<domaine-backend>/api/v1/` |
| WebSocket production | `wss://<domaine-backend>/ws/` |

Documentation interactive : `/api/docs/` (ReDoc), `/api/schema/swagger-ui/` (Swagger UI),
`/api/schema/` (OpenAPI brut — utilisable pour générer un client typé, ex. `openapi-typescript`).

## Authentification

JWT (`SimpleJWT`) : jeton d'accès valable **15 minutes**, jeton de rafraîchissement valable
**7 jours**. Envoyer le jeton d'accès dans l'en-tête `Authorization: Bearer <token>` pour toute
requête HTTP authentifiée.

| Action | Méthode | Endpoint | Corps |
|---|---|---|---|
| Inscription | POST | `/auth/register/` | `{ email, password1, password2, username? }` |
| Connexion | POST | `/auth/login/` | `{ email, password }` → `{ access, refresh, user }` |
| Rafraîchir le token | POST | `/auth/token/refresh/` | `{ refresh }` → `{ access }` |
| Déconnexion | POST | `/auth/logout/` | `{ refresh }` |
| Connexion Google | POST | `/auth/google/` | `{ access_token }` (jeton Google obtenu côté client) |
| Vérification d'e-mail | POST | `/auth/verify-email/` | `{ key }` |
| Réinitialisation mot de passe | POST | `/auth/password/reset/` | `{ email }` |
| Confirmation réinitialisation | POST | `/auth/password/reset/confirm/` | `{ uid, token, new_password1, new_password2 }` |
| Profil courant | GET / PATCH | `/auth/me/` | — |

Le profil utilisateur (`UserSerializer`) expose : `id`, `email`, `username`, `handle`, `bio`,
`role`, `is_verified`, `is_online`, `listen_count`, `avatar_url`, `created_at`.

**Règle d'accès aux fonctionnalités temps réel** : être authentifié suffit pour poster un
message de chat en direct ou un commentaire — il n'y a pas de condition de "profil complété"
(`handle`/`avatar` restent facultatifs, l'UI doit prévoir un repli sur `username` si absents).

## Conventions communes

### Pagination

Toutes les listes utilisent la même forme de réponse :

```json
{
  "count": 123,
  "next": "http://.../ressource/?page=2",
  "previous": null,
  "total_pages": 7,
  "current_page": 1,
  "results": []
}
```

Paramètres : `?page=`, `?page_size=` (max 100 sur les listes standards, 50 sur les flux de
chat/commentaires), `?search=` (recherche texte sur les champs indexés), `?ordering=-champ` (tri).

### Erreurs

```json
{ "detail": "Message lisible destiné à l'utilisateur.", "code": "some_error_code" }
```

Toujours lire `detail` pour l'affichage, et `code` pour la logique conditionnelle (ex. afficher un
formulaire différent sur `code === "already_voted"`). Les erreurs serveur (500) renvoient
systématiquement `code: "server_error"` sans détail technique.

### Limitation de débit

| Portée | Limite | S'applique à |
|---|---|---|
| Anonyme | 30 req/min | Toute requête non authentifiée |
| Authentifié | 120 req/min | Toute requête authentifiée |
| Auth (login/inscription) | 10 req/min | `/auth/login/`, `/auth/register/` |
| Upload | 5 req/min | Endpoints de téléversement |

Un dépassement renvoie `429 Too Many Requests`. Prévoir un backoff exponentiel côté client sur ces
endpoints, en particulier `/auth/login/`.

---

## Utilisateurs

| Action | Méthode | Endpoint |
|---|---|---|
| Liste (admin) | GET | `/users/` |
| Créer un utilisateur (admin) | POST | `/users/` |
| Détail / mise à jour partielle | GET / PATCH | `/users/{id}/` |
| Supprimer un utilisateur (admin) | DELETE | `/users/{id}/` |
| Favoris (artistes) | GET / POST | `/users/{id}/favorites/` |
| Historique d'écoute | GET | `/users/{id}/history/` |
| Signets (profil > signets) | GET | `/users/{id}/saved/` |
| Activité (profil > activité) | GET | `/users/{id}/activity/` |

`POST /users/` (admin) contourne le flux de vérification par e-mail de l'auto-inscription —
l'utilisateur créé est `is_verified: true` par défaut :

```json
POST /users/
{ "email": "nouveau@artdukivu.com", "username": "nouveau_membre", "password": "...", "role": "editor" }
```

`DELETE /users/{id}/` refuse la suppression de son propre compte par cette voie
(`400 { "detail": "Vous ne pouvez pas supprimer votre propre compte." }`) — utiliser la
déconnexion/suppression de compte self-service pour ce cas, pas cet endpoint admin.

`/saved/` et `/activity/` ne sont lisibles que par l'utilisateur lui-même ou un admin (contrairement
à `/favorites/`et `/history/`, publiques à tout utilisateur authentifié) — voir la section
[Profil](#profil--signets-activité-gamification) pour le détail des deux formes de réponse.

## Profil : signets, activité, gamification

Trois besoins distincts du profil ("Aperçu / Activité / Badges" côté frontend) sont couverts par des
endpoints d'agrégation qui traversent plusieurs types de contenu et, pour l'activité, plusieurs
systèmes d'engagement (le générique et celui, historique, propre aux articles).

### Signets — `GET /users/{id}/saved/`

Renvoie tout ce que l'utilisateur a mis de côté ("écouter/regarder plus tard"), tous types de
contenu confondus (Web TV, podcasts, sorties musicales, posts communauté), triés du plus récent au
plus ancien. Le live n'est jamais mis en signet (cohérent avec la règle "pas de save sur du direct"
du [système d'engagement](#système-dengagement-générique)).

```json
[
  {
    "saved_at": "2026-07-10T18:32:00Z",
    "kind": "webtv",
    "id": 42,
    "slug": "freestyle-goma-vol-3",
    "title": "Freestyle Goma Vol. 3",
    "cover_url": "https://res.cloudinary.com/.../thumbnail.jpg"
  },
  {
    "saved_at": "2026-07-09T09:12:00Z",
    "kind": "community",
    "id": 17,
    "slug": null,
    "title": "Mon nouveau son...",
    "cover_url": "https://res.cloudinary.com/.../cover.jpg"
  }
]
```

`kind` ∈ `webtv | podcast | release | community` — utile pour router vers la bonne page côté
frontend. `slug` est `null` pour les types qui n'en ont pas (ex. posts communauté) — utiliser `id`
dans ce cas.

### Activité — `GET /users/{id}/activity/`

Le "log" des likes et commentaires de l'utilisateur, sur l'ensemble de l'app — à la fois le système
d'engagement générique (Web TV, podcasts, releases, communauté) et le système historique propre aux
articles de blog. Fenêtré sur les **dernières 24h** ; si l'utilisateur n'a pas été actif dans les
dernières 24h, l'endpoint bascule automatiquement sur son activité la plus récente (toutes dates
confondues) pour éviter un profil vide — l'UI n'a rien de spécial à gérer, la fenêtre est
transparente.

```json
[
  {
    "action": "comment",
    "created_at": "2026-07-14T20:05:00Z",
    "excerpt": "Toujours aussi propre !",
    "target": { "kind": "webtv", "id": 42, "slug": "freestyle-goma-vol-3", "title": "Freestyle Goma Vol. 3", "cover_url": "..." }
  },
  {
    "action": "like",
    "created_at": "2026-07-14T19:40:00Z",
    "target": { "kind": "article", "id": 8, "slug": "interview-artiste-du-mois", "title": "Interview : l'artiste du mois", "cover_url": "..." }
  }
]
```

`action` ∈ `like | comment`. `excerpt` (les 140 premiers caractères du commentaire) n'est présent
que pour `action: "comment"`. `target.kind` ∈ `webtv | podcast | release | community | article`.

### Badges et temps de consommation — `apps/gamification`

Les badges classent un utilisateur sur l'ensemble de la plateforme (toutes catégories de contenu
confondues), à partir du temps de consommation cumulé — pas d'un compteur par type de contenu. Un
badge, une fois débloqué, **n'est jamais retiré**, même si le seuil qui l'a déclenché change
ensuite côté admin. Les seuils sont des données (table `Badge`, modifiable depuis l'admin Django),
pas des constantes codées en dur — les niveaux (ex. "3h", "18h", ...) sont à ajuster librement sans
déploiement.

| Action | Méthode | Endpoint | Auth |
|---|---|---|---|
| Catalogue des badges actifs | GET | `/gamification/badges/` | Publique |
| Badges obtenus par un utilisateur | GET | `/gamification/users/{user_id}/badges/` | Publique (les badges sont faits pour être affichés sur un profil) |
| Heartbeat de consommation | POST | `/gamification/consumption/` | Authentifié |
| Classement des médias suivis | GET | `/gamification/media-ranking/` | Authentifié (soi-même uniquement) |

**Heartbeat** — le lecteur (audio/vidéo/radio) doit appeler cet endpoint périodiquement (ex.
toutes les 30s) **tant que le contenu joue réellement** (pause = pas d'appel) :

```json
POST /gamification/consumption/
{
  "content_type": "podcast",           // radio | podcast | webtv | live_music | release
  "object_id": 42,
  "seconds": 30,                        // borné à 3600 par appel — anti-abus
  "title": "Nom affiché (optionnel, dénormalisé pour le classement)",
  "cover_url": "https://... (optionnel)"
}
```

Réponse — badges nouvellement débloqués par ce heartbeat (souvent vide) :

```json
{ "newly_earned_badges": [{ "id": 3, "slug": "bronze", "name": "Bronze", "description": "...", "icon_url": null, "threshold_seconds": 10800, "order": 1 }] }
```

Utiliser cette réponse pour afficher une notification "badge débloqué !" côté client. Un badge à
`threshold_seconds: 0` est attribué automatiquement à l'inscription (aucun appel requis).

**Classement des médias suivis** (section "Aperçu" du profil — médias les plus consommés, classés
par heures) :

```json
GET /gamification/media-ranking/
[
  { "content_type": "podcast", "object_id": 42, "title": "...", "cover_url": "...", "total_seconds": 14400 }
]
```

## Artistes

| Action | Méthode | Endpoint |
|---|---|---|
| Liste (filtrable par genre, ville) | GET | `/artists/` |
| Détail (inclut `releases`, `videos`, `gallery`, `like_count`, `comment_count`) | GET | `/artists/{slug}/` |
| Création/édition (admin) | POST / PATCH | `/artists/` / `/artists/{slug}/` |
| Genres disponibles | GET | `/artists/genres/` |
| J'aime / commentaires / partage / enregistrer | — | voir [engagement générique](#système-dengagement-générique) |

`Artist.is_featured=True` marque l'"artiste du mois" repris sur la page d'accueil. `genres` se
crée/modifie en écriture comme une liste d'identifiants (`"genres": [1, 2]`) ; la lecture
(`ArtistDetailSerializer`) renvoie les objets complets `{id, name, slug}`.

### Associer un son, une vidéo ou une photo à un artiste (admin)

Chacune des trois galeries de la fiche artiste a son propre sous-endpoint CRUD, même forme
partout : `GET`/`POST` sur la collection, `PATCH`/`DELETE` sur un élément précis.

| Ressource | Liste / création | Détail (modifier/supprimer) |
|---|---|---|
| Sorties (releases) | GET / POST `/artists/{slug}/releases/` | PATCH / DELETE `/artists/{slug}/releases/{release_id}/` |
| Vidéos | GET / POST `/artists/{slug}/videos/` | PATCH / DELETE `/artists/{slug}/videos/{video_id}/` |
| Galerie photo | GET / POST `/artists/{slug}/gallery/` | PATCH / DELETE `/artists/{slug}/gallery/{photo_id}/` |

```json
POST /artists/aline-mwamba/videos/
{
  "title": "Clip officiel — Nouvel Album",
  "thumbnail": "https://res.cloudinary.com/artdukivu/image/upload/v.../thumb.jpg",
  "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "duration": "3:45"
}
```

L'association d'un artiste à un **podcast** ne passe pas par ces sous-endpoints : elle se fait via
le champ `guests` d'un épisode (voir [Podcasts](#podcasts)) — un invité peut pointer vers un
`artist_id`.

## Articles et magazine

| Action | Méthode | Endpoint |
|---|---|---|
| Liste (filtrable par `article_type=blog|magazine`, `category=<slug>`) | GET | `/articles/` |
| Détail | GET | `/articles/{slug}/` |
| Création/édition (admin) | POST / PATCH | `/articles/` / `/articles/{slug}/` |
| Commentaires (spécifiques aux articles, modèle historique) | GET / POST | `/articles/{slug}/comments/` |
| J'aime (spécifique aux articles, modèle historique) | POST | `/articles/{slug}/like/` |
| Tags | GET | `/articles/tags/` |
| Catégories (liste) | GET | `/articles/categories/` |
| Créer une catégorie (admin) | POST | `/articles/categories/` |
| Modifier / supprimer une catégorie (admin) | PATCH / DELETE | `/articles/categories/{id}/` |

**Note** : les articles utilisent leur propre modèle de commentaire/j'aime (antérieur au système
d'engagement générique) — ne pas confondre avec les actions `/comments/`, `/like/` génériques
décrites plus bas, qui elles s'appliquent aux podcasts, vidéos web-tv, sorties, posts communauté
et émissions.

Le champ `category` en écriture (`POST`/`PATCH /articles/`) accepte **soit l'id numérique, soit le
slug** de la catégorie (`"category": "arts-visuels"` ou `"category": 5` fonctionnent tous les
deux) — et il est facultatif : un article peut être créé sans catégorie.

### Statut brouillon / programmé / publié

`status` ∈ `draft | published`. Un article `draft` avec `scheduled_at` renseigné (date future)
bascule **automatiquement** à `published` une fois cette date passée (tâche planifiée, vérifiée
toutes les 5 minutes) — pas besoin d'un appel PATCH manuel au moment voulu :

```json
POST /articles/
{ "title": "...", "content": "...", "status": "draft", "scheduled_at": "2026-08-15T08:00:00Z" }
```

Le "magazine" de la page d'accueil correspond aux `Article` avec `article_type="magazine"` — voir
[Page d'accueil](#page-daccueil).

## Événements

| Action | Méthode | Endpoint |
|---|---|---|
| Liste | GET | `/events/` |
| Détail (avec grille horaire, artistes) | GET | `/events/{slug}/` |
| Inscription | POST | `/events/{slug}/register/` |

`Event.is_featured=True` marque l'"événement à la une" repris sur la page d'accueil.

## Podcasts

| Action | Méthode | Endpoint |
|---|---|---|
| Liste des séries (filtrable par `category`, `is_featured`) | GET | `/podcasts/series/` |
| Création/édition d'une série (admin) | POST / PATCH | `/podcasts/series/` / `/podcasts/series/{slug}/` |
| Catégories disponibles | GET | `/podcasts/series/categories/` |
| Épisodes d'une série | GET | `/podcasts/series/{slug}/episodes/` |
| Liste des épisodes (filtrable par `series`, `category`, `is_featured`, `guest_artist`) | GET | `/podcasts/episodes/` |
| Détail d'un épisode | GET | `/podcasts/episodes/{slug}/` |
| Création/édition d'un épisode (admin) | POST / PATCH | `/podcasts/episodes/` / `/podcasts/episodes/{slug}/` |
| Incrémenter le compteur d'écoute | POST | `/podcasts/episodes/{slug}/play/` |
| J'aime / commentaires / partage / enregistrer | — | voir [engagement générique](#système-dengagement-générique) |

`audio_url` (résolution automatique : `audio_file` Cloudinary si présent, sinon `audio_url`
externe) est maintenant présent **à la fois sur la liste et le détail** — plus besoin d'un appel
détail supplémentaire par épisode juste pour obtenir de quoi jouer l'audio.

### Invités (`guests`)

Un invité peut être lié à un artiste existant, à un utilisateur existant, ou n'être qu'un nom
libre (aucun compte) — les trois formes coexistent dans la même liste :

```json
{
  "guests": [
    { "name": "Aline Mwamba", "artist_id": 12, "user_id": null },
    { "name": "Jean Dupont", "artist_id": null, "user_id": 8 },
    { "name": "Invité surprise", "artist_id": null, "user_id": null }
  ]
}
```

`name` est toujours requis et toujours ce qu'il faut afficher tel quel (le "jina" de l'invité) —
`artist_id`/`user_id` ne servent qu'à faire un lien cliquable vers la fiche artiste/profil quand
ils sont présents. Un épisode donné n'a jamais `artist_id` **et** `user_id` renseignés à la fois
sur un même invité.

Pour lister les épisodes où un artiste donné est invité : `GET /podcasts/episodes/?guest_artist=12`.

### Podcast autonome vs série (`is_series`)

`PodcastSeries` peut porter son propre audio (`audio_file`/`audio_url`, `cover_url`, `duration`) —
c'est ce qui permet d'afficher un podcast comme un contenu **autonome**, sans épisode du tout.
`is_series` passe automatiquement à `true` dès qu'un **second** épisode est rattaché à la série (le
premier épisode ne suffit pas à lui seul — il reste équivalent au cas autonome) ; ce champ ne
redescend jamais à `false` ensuite, même si des épisodes sont supprimés. Utiliser `is_series` pour
décider l'affichage : `false` → jouer l'audio de la série elle-même ; `true` → afficher la liste
d'épisodes.

```json
GET /podcasts/series/mon-podcast/
{
  "title": "Mon Podcast", "audio_url": "https://...", "duration": "38:20",
  "is_series": false, "episode_count": 1
}
```

### Statut brouillon / programmé / publié (épisodes)

Même mécanique que les articles : `status` ∈ `draft | published` sur `PodcastEpisode`. Un épisode
`draft` n'apparaît jamais dans les réponses publiques (seuls les comptes admin le voient) ; s'il
porte un `published_at` déjà passé au moment de sa création, il reste `draft` jusqu'à ce que la
tâche planifiée (vérifiée toutes les 5 minutes) le bascule en `published` — ne pas compter sur
`published_at` seul pour décider de la visibilité, toujours vérifier `status`.

Le détail d'un épisode (`EpisodeDetailSerializer`) contient tout ce qu'il faut pour un lecteur
audio : `title`, `duration` (chaîne, ex. `"42:10"`), `description` (utilisé comme légende/infos),
`audio_url`, `cover_url`, `episode_number`, `season_number`, `guests`, `status`, `published_at`,
`transcript` (texte intégral de la transcription, facultatif — vide si non fournie par l'admin).

## Radio

| Action | Méthode | Endpoint |
|---|---|---|
| Grille (filtrable par `?day=0..6`, lundi=0) | GET | `/radio/program/` |
| Programme en cours (statut, URL de lecture, auditeurs en ligne) | GET | `/radio/current/` |
| Chat (lecture) | GET | `/radio/chat/` |
| Chat (poster un message — authentifié) | POST | `/radio/chat/` |
| Diffuser en direct (admin) | POST | `/radio/program/{id}/go_live/` |
| Arrêter le direct (admin) | POST | `/radio/program/{id}/end_live/` |
| J'aime / commentaires / partage / enregistrer | — | voir [engagement générique](#système-dengagement-générique) |

`GET /radio/current/` n'est **pas** mis en cache côté serveur (contrairement aux autres listes) :
`listener_count` y est lu en direct depuis la présence WebSocket, l'appeler en polling toutes les
10-15 secondes est acceptable si le frontend ne branche pas le WebSocket pour cet indicateur.

```json
{
  "id": 33,
  "title": "Jazz du Lac",
  "day_name": "Saturday",
  "start_time": "12:00:00",
  "end_time": "14:00:00",
  "status": "live",
  "stream_url": "",
  "playback_hls_url": "https://art-du-kivu-api.kelor.tech/live-hls/processed/live/audio_<clé>/index.m3u8",
  "listener_count": 42
}
```

Le chat radio utilise son propre modèle (`RadioChat`, préexistant), avec la même mécanique de
présence/push que les autres salons — voir [Temps réel](#temps-réel--websocket-chat--présence),
`room_type = "radio"`, `room_id = "live"` (canal continu, un seul salon).

## Web TV

| Action | Méthode | Endpoint |
|---|---|---|
| Catalogue (filtrable par `category`) | GET | `/webtv/videos/` |
| Détail (inclut `artist_names`, comme la liste) | GET | `/webtv/videos/{slug}/` |
| Vidéo en direct actuelle | GET | `/webtv/videos/live/` |
| Premières (5 dernières) | GET | `/webtv/videos/premiers/` |
| Incrémenter le compteur de vues | POST | `/webtv/videos/{slug}/view/` |
| Chat en direct (lecture/écriture) | GET / POST | `/webtv/videos/{slug}/chat/` |
| Spectateurs en ligne (lecture ponctuelle, hors WebSocket) | GET | `/webtv/videos/{slug}/online-count/` |
| Diffuser en direct (admin) | POST | `/webtv/videos/{slug}/go_live/` |
| Arrêter le direct (admin) | POST | `/webtv/videos/{slug}/end_live/` |
| J'aime / commentaires / partage / enregistrer | — | voir [engagement générique](#système-dengagement-générique) |

Catégories disponibles : `freestyles`, `studio_sessions`, `docs`, `interviews`, `premiers`,
`concerts`.

Le catalogue "pas en direct" (toutes les autres vidéos) s'obtient en filtrant côté client sur
`is_live=false`, ou via `?is_live=false` si un filtre dédié est ajouté côté backend (à date, le
filtrage disponible est par `category` — trier côté client ou demander l'ajout du filtre si
nécessaire).

### `broadcast_mode` : direct fichier vs direct caméra

`broadcast_mode` ∈ `playout | camera`, présent sur liste et détail :
- **`playout`** (par défaut) : une vidéo pré-enregistrée, `video_url` obligatoire.
- **`camera`** : un direct caméra pur (pas de fichier existant) — `video_url` **facultatif**,
  la lecture se fait via `playback_hls_url` une fois `go_live` appelé, exactement comme les
  autres surfaces live. Ne plus envoyer d'URL factice/placeholder pour ce cas — laisser
  `video_url` vide.

## Émissions live

| Action | Méthode | Endpoint |
|---|---|---|
| Liste (filtrable par `status=live|scheduled|recorded`) | GET | `/emissions/` |
| Détail | GET | `/emissions/{slug}/` |
| Émission en direct actuelle | GET | `/emissions/live/` |
| Diffuser en direct (admin) | POST | `/emissions/{slug}/go_live/` |
| Arrêter le direct (admin) | POST | `/emissions/{slug}/end_live/` |
| Commentaires / partage | — | voir [engagement générique](#système-dengagement-générique) (pas d'enregistrement possible tant que `status="live"`) |

## Live Music

Fonctionnalité indépendante de Radio et des Émissions : une session live musicale + sa propre
grille de programmes + son propre chat.

| Action | Méthode | Endpoint |
|---|---|---|
| Sessions (liste/détail) | GET | `/live_music/sessions/` , `/live_music/sessions/{slug}/` |
| Son en direct actuel | GET | `/live_music/sessions/current/` |
| Grille de programmes (filtrable par `?day=0..6`) | GET | `/live_music/programme/` |
| Chat (lecture/écriture) | GET / POST | `/live_music/sessions/{slug}/chat/` |
| Diffuser en direct (admin) | POST | `/live_music/sessions/{slug}/go_live/` |
| Arrêter le direct (admin) | POST | `/live_music/sessions/{slug}/end_live/` |
| J'aime / commentaires / partage / enregistrer | — | voir [engagement générique](#système-dengagement-générique) |

```json
// GET /live_music/sessions/current/
{
  "id": 7,
  "title": "Session acoustique — Alesh",
  "slug": "session-acoustique-alesh",
  "artist_names": ["Alesh"],
  "status": "live",
  "cover_url": "https://res.cloudinary.com/.../cover.jpg",
  "scheduled_at": "2026-07-11T18:00:00Z",
  "playback_hls_url": "https://art-du-kivu-api.kelor.tech/live-hls/processed/live/audio_<clé>/index.m3u8",
  "online_followers": 128,
  "live_started_at": "2026-07-11T18:00:00Z"
}
```

`cover_url` (image de fond, sessions et créneaux de la grille) et `scheduled_at` (date/heure prévue
d'une session) sont facultatifs — à prévoir en absence pour les sessions pas encore programmées.

`online_followers` est lu en direct depuis la présence WebSocket à chaque appel (pas de cache).
Pour un compteur qui se met à jour sans polling, brancher le WebSocket (voir plus bas) plutôt que
d'appeler cet endpoint en boucle.

## Communauté

| Action | Méthode | Endpoint |
|---|---|---|
| Liste des posts (filtrable par `?post_type=talent|art|news|challenge_response`, `?challenge=<slug>`) | GET | `/community/posts/` |
| Créer un post (authentifié) | POST | `/community/posts/` |
| Modifier son propre post (auteur ou admin) | PATCH | `/community/posts/{id}/` |
| Supprimer (auteur ou admin) | DELETE | `/community/posts/{id}/` |
| Soumettre un talent (chanson, vidéo ou image, authentifié) | POST | `/community/posts/submit_talent/` |
| J'aime un post (authentifié, historique — pas le système générique) | POST | `/community/posts/{id}/like/` |
| Commentaires / partage / enregistrer (système générique) | — | voir [engagement générique](#système-dengagement-générique) |
| Défis (liste, détail) | GET | `/community/challenges/`, `/community/challenges/{slug}/` |
| Répondre à un défi | POST | `/community/challenges/{slug}/participate/` |
| Publier le résultat épinglé (admin) | POST | `/community/challenges/{slug}/publish_result/` |
| Sondages (liste, vote) | GET / POST | `/community/polls/`, `/community/polls/{id}/vote/` |

```http
POST /api/v1/community/posts/submit_talent/
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Mon freestyle du dimanche",
  "content": "Enregistré ce week-end, dites-moi ce que vous en pensez !",
  "media": [
    { "type": "song", "url": "https://res.cloudinary.com/.../audio.mp3" }
  ]
}
```

`title` et `content` sont désormais tous les deux requis (texte descriptif de la soumission, pas
seulement un titre) ; `media` accepte un ou plusieurs éléments, chacun avec `type` égal à `"song"`,
`"video"` ou `"image"` (le fichier doit avoir été téléversé au préalable vers Cloudinary par le
frontend ; ce endpoint n'accepte que la référence, pas un fichier brut — voir [Upload de
médias](#upload-de-médiasaudiovidéoimage)). La réponse renvoie le post créé avec
`post_type: "talent"`. `POST /community/posts/` (le endpoint générique, pas `submit_talent`)
accepte aussi `title` depuis cette session — les deux formes sont désormais équivalentes côté
champs disponibles.

Modifier son propre post (`PATCH /community/posts/{id}/`) n'autorise que `title`/`content`/
`media`/`post_type` — jamais `challenge` ni `is_pinned_result`, qui restent contrôlés côté serveur.
Un utilisateur qui n'est ni l'auteur ni admin reçoit `403`.

### Défis — répondre, savoir si on a déjà participé, résultat épinglé

Répondre à un défi suit exactement la même forme que `submit_talent` :

```http
POST /api/v1/community/challenges/reprise-acoustique/participate/
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Ma reprise acoustique",
  "content": "Voici ma participation !",
  "media": [{ "type": "song", "url": "https://res.cloudinary.com/.../audio.mp3" }]
}
```

La réponse est un `CommunityPost` avec `post_type: "challenge_response"` et `challenge:
"reprise-acoustique"` (le slug du défi). Une seconde tentative de participation au même défi par
le même utilisateur renvoie `400 { "detail": "Vous participez déjà à ce défi.", "code":
"already_joined" }` — un utilisateur ne peut répondre qu'une fois par défi.

`GET /community/challenges/{slug}/` (et la liste) expose `has_participated: boolean` pour
l'utilisateur authentifié courant (toujours `false` pour un appel anonyme) — utiliser ce champ
pour masquer le bouton "Participer" et afficher "Vous avez déjà participé" à la place, plutôt que
de se fier à l'erreur `already_joined` pour piloter l'UI.

Les participations d'un défi s'affichent comme des posts normaux (mêmes likes/commentaires/
partage/signets que les talents) via le filtre déjà existant sur la liste des posts :

```
GET /community/posts/?post_type=challenge_response&challenge=reprise-acoustique
```

Un résultat de défi épinglé (annoncé par l'admin une fois le défi terminé) se publie via
`POST /community/challenges/{slug}/publish_result/` (réservé au staff), même forme de corps que
`participate/`. Le post créé porte `is_pinned_result: true` — l'afficher épinglé en tête de la
liste des participations plutôt que trié par date comme les autres.

## Sorties musicales (releases)

| Action | Méthode | Endpoint |
|---|---|---|
| Liste (filtrable par `format`, `artist`) | GET | `/releases/` |
| Détail | GET | `/releases/{slug}/` |
| Sortie à la une | GET | `/releases/featured/` |
| Calendrier des sorties à venir (60 jours) | GET | `/releases/calendar/` |
| J'aime / commentaires / partage / enregistrer | — | voir [engagement générique](#système-dengagement-générique) |

C'est le modèle canonique pour toute nouvelle intégration liée aux sorties musicales (ne pas
utiliser les endpoints hérités d'`apps.artists` s'il devait en exister un équivalent).

---

## Système d'engagement générique

Quatre actions identiques sont disponibles sur les ressources suivantes : **podcasts (épisodes)**,
**web-tv (vidéos)**, **releases (sorties)**, **community (posts)**, **emissions**, **radio
(programs)**, **live_music (sessions)**, **artists**. Le motif est strictement le même partout —
seul le préfixe de ressource change.

| Action | Méthode | Endpoint | Authentification |
|---|---|---|---|
| Basculer j'aime | POST | `/<ressource>/{id_ou_slug}/like/` | requise |
| Lire les commentaires | GET | `/<ressource>/{id_ou_slug}/comments/` | non |
| Poster un commentaire | POST | `/<ressource>/{id_ou_slug}/comments/` | requise |
| Enregistrer un partage | POST | `/<ressource>/{id_ou_slug}/share/` | facultative (anonyme comptabilisé) |
| Enregistrer pour plus tard | POST | `/<ressource>/{id_ou_slug}/save/` | requise |
| Retirer des enregistrements | DELETE | `/<ressource>/{id_ou_slug}/save/` | requise |

```http
POST /api/v1/podcasts/episodes/ep-16-1-specific-road-team/like/
Authorization: Bearer <token>
```
```json
{ "liked": true, "like_count": 12 }
```

```http
POST /api/v1/webtv/videos/mon-freestyle/comments/
Authorization: Bearer <token>
Content-Type: application/json

{ "content": "Superbe session !", "parent": null }
```
```json
{
  "id": 45,
  "username": "arnold",
  "handle": "",
  "avatar_url": null,
  "content": "Superbe session !",
  "parent": null,
  "created_at": "2026-07-11T18:22:03Z"
}
```

```http
POST /api/v1/releases/mon-single/save/
Authorization: Bearer <token>
```
```json
{ "saved": true }
```

**Contenu en direct** : `save` renvoie `400 { "detail": "Le contenu en direct ne peut pas être
enregistré pour plus tard." }` tant que la ressource est en statut `live` (`status == "live"` ou
`is_live == true` selon le modèle). Le frontend doit masquer ou désactiver le bouton
"enregistrer" pour tout contenu marqué en direct plutôt que de compter sur cette erreur pour
l'UX — l'erreur reste une garde-fou serveur, pas le mécanisme principal d'affichage.

---

## Upload de médias (audio/vidéo/image)

Les champs qui acceptent un média (`video_url` sur les vidéos web-tv, `audio_url` sur les
épisodes de podcast, `preview_url` sur les sorties, `media` sur les posts communauté) attendent
une **URL déjà hébergée sur Cloudinary** — pas un fichier brut envoyé à ces endpoints. Le fichier
doit être envoyé **directement à Cloudinary depuis le frontend** (jamais via notre API), pour
rester rapide même sur de grosses vidéos et ne jamais charger notre serveur avec le transfert
binaire.

### Étape 1 — demander une signature

```http
POST /api/v1/media/upload-signature/
Authorization: Bearer <token>
Content-Type: application/json

{ "context": "webtv_video" }
```

`context` est une valeur fixe parmi une liste blanche (pas de dossier/type arbitraire) :

| Contexte | Type | Accès |
|---|---|---|
| `webtv_video` | vidéo | admin |
| `webtv_thumbnail` | image | admin |
| `podcast_audio` | audio | admin |
| `podcast_cover` | image | admin |
| `release_cover` | image | admin |
| `release_preview` | audio | admin |
| `artist_photo`, `artist_cover`, `artist_gallery_photo` | image | admin |
| `emission_cover`, `radio_cover`, `challenge_cover` | image | admin |
| `community_image` | image | **tout utilisateur authentifié** |
| `community_video` | vidéo | **tout utilisateur authentifié** |
| `community_song` | audio | **tout utilisateur authentifié** |
| `user_avatar` | image | **tout utilisateur authentifié** (soi-même) |

Réponse :

```json
{
  "timestamp": 1732000000,
  "signature": "a1b2c3...",
  "api_key": "235241863688864",
  "cloud_name": "dc4scpfuz",
  "folder": "webtv/videos",
  "resource_type": "video",
  "upload_url": "https://api.cloudinary.com/v1_1/dc4scpfuz/video/upload"
}
```

### Étape 2 — uploader directement à Cloudinary

```ts
async function uploadToCloudinary(file: File, context: string, token: string) {
  const sigRes = await fetch(`${API_BASE}/media/upload-signature/`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ context }),
  });
  const sig = await sigRes.json();

  const form = new FormData();
  form.append("file", file);
  form.append("api_key", sig.api_key);
  form.append("timestamp", String(sig.timestamp));
  form.append("signature", sig.signature);
  form.append("folder", sig.folder);

  const uploadRes = await fetch(sig.upload_url, { method: "POST", body: form });
  const uploaded = await uploadRes.json();
  return uploaded.secure_url; // à envoyer tel quel dans video_url / audio_url / media[].url
}
```

### Étape 3 — créer/mettre à jour l'entité avec l'URL obtenue

```http
POST /api/v1/webtv/videos/
Authorization: Bearer <token>
Content-Type: application/json

{ "title": "...", "video_url": "https://res.cloudinary.com/dc4scpfuz/video/upload/v.../webtv/videos/xyz.mp4", ... }
```

### UI attendue côté frontend : les deux options, toujours

Le champ (`video_url`, `audio_url`, `preview_url`, `media[].url`) accepte indifféremment une
URL externe (YouTube, Vimeo, un autre CDN…) **ou** une URL Cloudinary issue d'un upload — c'est
le composant d'interface qui doit proposer les deux à l'utilisateur, pas l'API. Un simple
`<input type="file">` HTML ouvre nativement le sélecteur de fichiers sur desktop et la
galerie/appareil photo sur mobile — aucun code spécifique mobile n'est nécessaire.

```tsx
function MediaField({ context, value, onChange }: { context: string; value: string; onChange: (url: string) => void }) {
  const [mode, setMode] = useState<"upload" | "url">("upload");
  const [uploading, setUploading] = useState(false);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const url = await uploadToCloudinary(file, context, getAccessToken());
      onChange(url);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      <div role="tablist">
        <button type="button" onClick={() => setMode("upload")}>Choisir un fichier</button>
        <button type="button" onClick={() => setMode("url")}>Ou coller un lien</button>
      </div>
      {mode === "upload" ? (
        <input type="file" accept="video/*" onChange={handleFileChange} disabled={uploading} />
      ) : (
        <input type="url" placeholder="https://..." value={value} onChange={(e) => onChange(e.target.value)} />
      )}
      {uploading && <p>Envoi en cours…</p>}
    </div>
  );
}
```

`accept="video/*"` (ou `"audio/*"`, `"image/*"` selon le champ) filtre les fichiers proposés par
le sélecteur natif — c'est un confort pour l'utilisateur, **pas** une validation ; la vraie
validation reste celle faite côté serveur au moment de la création/mise à jour de l'entité.

### Validation stricte côté serveur

Si l'URL fournie pointe vers **notre** compte Cloudinary, le backend vérifie — via l'API
Cloudinary, donc sur le **contenu binaire réellement stocké**, pas juste l'extension du nom de
fichier — que la ressource existe bien et correspond au type attendu (`video_url` doit être une
vraie vidéo, pas une image maquillée en `.mp4`). Une URL externe (ex. un lien YouTube existant)
n'est pas concernée par cette vérification — elle est acceptée telle quelle, comme aujourd'hui.

En cas d'échec :

```json
{ "video_url": ["Aucun média correspondant trouvé sur Cloudinary — vérifiez que l'upload a bien abouti."] }
```
ou
```json
{ "video_url": ["Ce champ attend un contenu de type « video », pas « image »."] }
```

---

## Diffusion en direct (MediaMTX) côté frontend

> **Guide dédié** : `docs/LIVE_STREAMING.md` couvre en détail les 4 surfaces live (endpoints
> complets, WebSocket présence/chat, engagement sur le contenu live) avec des guides
> d'intégration séparés pour `frontend_admin` et `frontend_client`. Ce qui suit est un résumé.

Le live est auto-hébergé via **MediaMTX** (remplace Cloudflare Stream). Quatre surfaces exposent
un champ de lecture une fois en direct : `RadioProgram`, `Emission`, `WebTVVideo`,
`MusicLiveSession`, tous avec la même forme :

```json
{
  "playback_hls_url": "https://art-du-kivu-api.kelor.tech/live-hls/processed/live/<clé>/index.m3u8"
}
```

Ce champ est vide tant que la ressource n'est pas en direct. **Les champs `rtmp_server_url` et
`stream_key` ne sont jamais renvoyés par les endpoints de lecture publics** — ils ne sont
disponibles que dans la réponse de l'action admin `go_live` (à usage du logiciel de diffusion,
type OBS Studio), jamais persistés côté client.

**Seul Web TV diffuse de la vidéo** — Radio, Émissions et Live Music sont strictement audio (la
vidéo est supprimée côté serveur si l'opérateur en envoie quand même). `stream_key` est préfixé
en conséquence (`audio_...` / `video_...`) et **toujours régénéré à chaque `go_live`**, jamais
réutilisé — reconfigurer OBS avec la nouvelle clé à chaque démarrage. Détails complets, y compris
le pourquoi de ce choix : `docs/LIVE_STREAMING.md`.

### Configuration côté OBS (ou équivalent)

`go_live` renvoie exactement les deux champs attendus par le mode "Custom..." d'OBS :

```json
{
  "status": "live",
  "rtmp_server_url": "rtmp://art-du-kivu-api.kelor.tech:1935/live",
  "stream_key": "audio_3f9a2b1c8e4d5f6a7b8c9d0e1f2a3b4c",
  "playback_hls_url": "https://art-du-kivu-api.kelor.tech/live-hls/processed/audio_3f9a2b1c.../index.m3u8"
}
```

Dans OBS : Paramètres → Flux → Service = *Personnalisé...* → **Serveur** = `rtmp_server_url`,
**Clé de flux** = `stream_key`. Contrairement à l'ancienne intégration Cloudflare (RTMPS
obligatoire, source probable des déconnexions répétées observées avec OBS), c'est du RTMP
classique — le même protocole que Twitch/YouTube/Facebook utilisent par défaut.

**Rappeler `go_live`, même sur une ressource déjà en direct, renvoie une clé différente à chaque
fois** — pas d'idempotence ici (voir `docs/LIVE_STREAMING.md` pour le pourquoi). Le panneau admin
doit donc toujours ré-afficher/reconfigurer OBS après chaque appel, pas seulement au premier.

### Lecture HLS avec `hls.js` (React)

```tsx
import Hls from "hls.js";
import { useEffect, useRef } from "react";

function LivePlayer({ hlsUrl }: { hlsUrl: string }) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !hlsUrl) return;

    if (Hls.isSupported()) {
      const hls = new Hls();
      hls.loadSource(hlsUrl);
      hls.attachMedia(video);
      return () => hls.destroy();
    }
    // Safari lit le HLS nativement, sans hls.js.
    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = hlsUrl;
    }
  }, [hlsUrl]);

  return <video ref={videoRef} controls autoPlay playsInline />;
}
```

Pour de l'audio seul (radio, live music), un simple `<audio src={hlsUrl} />` avec un lecteur
compatible HLS (ou `hls.js` attaché à un élément `<audio>`) fonctionne de la même façon.

### Panneau d'administration : démarrer/arrêter un direct

```ts
async function goLive(resourcePath: string, id: string) {
  const res = await api.post(`/${resourcePath}/${id}/go_live/`);
  // res.data.rtmp_server_url / stream_key : à afficher UNE FOIS à l'opérateur pour
  // configuration OBS — ne jamais les stocker ni les ré-afficher après coup.
  return res.data;
}

async function endLive(resourcePath: string, id: string) {
  await api.post(`/${resourcePath}/${id}/end_live/`);
}
```

---

## Temps réel : WebSocket (chat + présence)

Un seul point d'entrée WebSocket paramétré, pour toutes les surfaces live :

```
wss://<domaine>/ws/live/<room_type>/<room_id>/?token=<jwt access token>
```

| `room_type` | `room_id` | Ressource associée |
|---|---|---|
| `radio` | `live` (fixe — canal continu) | `RadioProgram` en cours |
| `emission` | identifiant de l'`Emission` | `Emission` |
| `webtv` | identifiant du `WebTVVideo` | `WebTVVideo` |
| `live_music` | identifiant du `MusicLiveSession` | `MusicLiveSession` |

Le paramètre `?token=` est **facultatif** : les connexions anonymes sont acceptées (la présence
doit compter tous les spectateurs, pas seulement les comptes connectés). Sans token, la connexion
n'a accès qu'à la présence/aux messages poussés ; poster un message reste soumis à
authentification, mais via l'API REST (`POST .../chat/`), jamais sur le socket lui-même.

### Événements reçus

```json
{ "event": "presence.count", "count": 42 }
{ "event": "chat.message", "message": { "id": 12, "username": "...", "message": "...", "created_at": "..." } }
```

### Message à envoyer (heartbeat)

Le client doit envoyer un battement de cœur toutes les **15 secondes environ** pour rester compté
comme "en ligne" (fenêtre de tolérance serveur : 30 secondes) :

```json
{ "type": "heartbeat" }
```

### Exemple de hook React

```ts
import { useEffect, useRef, useState } from "react";

function useLiveRoom(roomType: string, roomId: string, token?: string) {
  const [onlineCount, setOnlineCount] = useState(0);
  const [messages, setMessages] = useState<any[]>([]);
  const wsRef = useRef<WebSocket>();

  useEffect(() => {
    if (!roomId) return;

    const base = process.env.NEXT_PUBLIC_WS_BASE_URL; // ex: wss://api.artdukivu.com
    const url = new URL(`${base}/ws/live/${roomType}/${roomId}/`);
    if (token) url.searchParams.set("token", token);

    const ws = new WebSocket(url.toString());
    wsRef.current = ws;

    const heartbeat = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "heartbeat" }));
      }
    }, 15000);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.event === "presence.count") setOnlineCount(data.count);
      if (data.event === "chat.message") setMessages((prev) => [...prev, data.message]);
    };

    return () => {
      clearInterval(heartbeat);
      ws.close();
    };
  }, [roomType, roomId, token]);

  return { onlineCount, messages };
}
```

Poster un message reste un appel REST classique (`POST /<ressource>/{id}/chat/` avec
`{ "message": "..." }`, `Authorization: Bearer <token>` requis) — il sera automatiquement relayé
à tous les sockets connectés au même salon via l'événement `chat.message` ci-dessus ; ne pas
l'ajouter manuellement à la liste locale de messages en plus de la réponse HTTP pour éviter un
doublon (préférer déduire l'affichage uniquement de l'événement WebSocket une fois le POST validé,
ou dédupliquer par `id`).

---

## Page d'accueil

```
GET /api/v1/home/
```

Réponse agrégée, mise en cache 15 minutes côté serveur :

```json
{
  "banner": { "image_url": "...", "title": "...", "subtitle": "...", "cta_label": "...", "cta_url": "..." },
  "a_la_une": {
    "artist_of_month": { "...": "ArtistListSerializer" },
    "featured_podcast": { "...": "EpisodeListSerializer" },
    "featured_event": { "...": "EventListSerializer" }
  },
  "hits_du_mois": [ "...MusicRelease (ReleaseListSerializer), classées par engagement du mois..." ],
  "magazine": {
    "hero": { "...": "ArticleListSerializer, magazine mis en avant" },
    "articles": [ "...six articles magazine récents..." ]
  }
}
```

Chaque sous-section peut être `null` (aucun artiste/podcast/événement à la une configuré) — le
frontend doit gérer l'absence de contenu (masquer la section plutôt que planter).

### Bannière d'accueil configurable (admin)

```
GET / PATCH /api/v1/home/banner/
```

Singleton (une seule bannière) — `GET` public, `PATCH` réservé au staff :

```json
PATCH /home/banner/
{ "title": "Bienvenue sur Art du Kivu", "cta_label": "Écouter", "cta_url": "https://..." }
```

**Propagation** : cet endpoint reflète le changement immédiatement, mais `GET /home/` (page
d'accueil agrégée) est mis en cache serveur 15 minutes — la nouvelle bannière peut mettre jusqu'à
15 minutes à apparaître sur `/home/` après un `PATCH` réussi sur `/home/banner/`.

## Recherche

```
GET /api/v1/search/?q=<terme>&type=<optionnel>&page=1&page_size=20
```

`type` restreint à un type de contenu parmi : `artists`, `articles`, `events`, `podcast_series`,
`podcast_episodes`, `releases`, `webtv_videos`, `community_posts` (la radio, les émissions et le
live music ne sont pas encore indexés dans la recherche unifiée à ce jour).

```json
{ "count": 12, "page": 1, "page_size": 20, "results": [
  { "type": "artists", "id": 4, "slug": "alesh-3", "title": "Alesh", "image_url": null, "score": 8.2 }
] }
```

Une requête vide (`q=""`) court-circuite volontairement sans appeler Elasticsearch et renvoie une
liste vide. En cas d'indisponibilité d'Elasticsearch, l'API renvoie `503` avec un message lisible
— prévoir un état de dégradation (ex. masquer la recherche, pas une page d'erreur bloquante).

## Newsletter

| Action | Méthode | Endpoint |
|---|---|---|
| S'abonner | POST | `/newsletter/subscribe/` |
| Confirmer l'abonnement | GET | `/newsletter/confirm/{token}/` |
| Se désabonner | GET | `/newsletter/unsubscribe/{token}/` |

## Analytics

Réservé à l'interface d'administration (`IsAdminUser`) :

```
GET /api/v1/analytics/dashboard/
```

---

## Exemple de client HTTP avec rafraîchissement automatique du token

```ts
import axios from "axios";

const api = axios.create({ baseURL: process.env.NEXT_PUBLIC_API_BASE_URL });

api.interceptors.request.use((config) => {
  const token = getAccessToken(); // à implémenter selon le stockage choisi
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = getRefreshToken();
      if (refresh) {
        const { data } = await axios.post(
          `${process.env.NEXT_PUBLIC_API_BASE_URL}/auth/token/refresh/`,
          { refresh }
        );
        setAccessToken(data.access);
        original.headers.Authorization = `Bearer ${data.access}`;
        return api(original);
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

Ce client couvre tous les endpoints REST de ce guide ; seul le WebSocket (section
[Temps réel](#temps-réel--websocket-chat--présence)) nécessite une connexion séparée, le token
étant alors transmis en paramètre de requête plutôt qu'en en-tête.
