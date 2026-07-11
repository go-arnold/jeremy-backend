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
5. [Artistes](#artistes)
6. [Articles et magazine](#articles-et-magazine)
7. [Événements](#événements)
8. [Podcasts](#podcasts)
9. [Radio](#radio)
10. [Web TV](#web-tv)
11. [Émissions live](#émissions-live)
12. [Live Music](#live-music)
13. [Communauté](#communauté)
14. [Sorties musicales (releases)](#sorties-musicales-releases)
15. [Système d'engagement générique](#système-dengagement-générique)
16. [Diffusion en direct (Cloudflare Stream) côté frontend](#diffusion-en-direct-cloudflare-stream-côté-frontend)
17. [Temps réel : WebSocket (chat + présence)](#temps-réel--websocket-chat--présence)
18. [Page d'accueil](#page-daccueil)
19. [Recherche](#recherche)
20. [Newsletter](#newsletter)
21. [Analytics](#analytics)
22. [Exemple de client HTTP avec rafraîchissement automatique du token](#exemple-de-client-http-avec-rafraîchissement-automatique-du-token)

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
| Détail / mise à jour partielle | GET / PATCH | `/users/{id}/` |
| Favoris (artistes) | GET / POST | `/users/{id}/favorites/` |
| Historique d'écoute | GET | `/users/{id}/history/` |

## Artistes

| Action | Méthode | Endpoint |
|---|---|---|
| Liste (filtrable par genre, ville) | GET | `/artists/` |
| Détail | GET | `/artists/{slug}/` |
| Création/édition (admin) | POST / PATCH | `/artists/` / `/artists/{slug}/` |

`Artist.is_featured=True` marque l'"artiste du mois" repris sur la page d'accueil.

## Articles et magazine

| Action | Méthode | Endpoint |
|---|---|---|
| Liste (filtrable par `article_type=blog|magazine`, catégorie) | GET | `/articles/` |
| Détail | GET | `/articles/{slug}/` |
| Commentaires (spécifiques aux articles, modèle historique) | GET / POST | `/articles/{slug}/comments/` |
| J'aime (spécifique aux articles, modèle historique) | POST | `/articles/{slug}/like/` |
| Tags | GET | `/articles/tags/` |

**Note** : les articles utilisent leur propre modèle de commentaire/j'aime (antérieur au système
d'engagement générique) — ne pas confondre avec les actions `/comments/`, `/like/` génériques
décrites plus bas, qui elles s'appliquent aux podcasts, vidéos web-tv, sorties, posts communauté
et émissions.

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
| Catégories disponibles | GET | `/podcasts/series/categories/` |
| Épisodes d'une série | GET | `/podcasts/series/{slug}/episodes/` |
| Liste des épisodes (filtrable par `series`, `category`, `is_featured`) | GET | `/podcasts/episodes/` |
| Détail d'un épisode | GET | `/podcasts/episodes/{slug}/` |
| Incrémenter le compteur d'écoute | POST | `/podcasts/episodes/{slug}/play/` |
| J'aime / commentaires / partage / enregistrer | — | voir [engagement générique](#système-dengagement-générique) |

Le détail d'un épisode (`EpisodeDetailSerializer`) contient tout ce qu'il faut pour un lecteur
audio : `title`, `duration` (chaîne, ex. `"42:10"`), `description` (utilisé comme légende/infos),
`audio_url` (résout `audio_file` Cloudinary ou `audio_url` externe), `cover_url`,
`episode_number`, `season_number`, `guests`, `published_at`.

## Radio

| Action | Méthode | Endpoint |
|---|---|---|
| Grille (filtrable par `?day=0..6`, lundi=0) | GET | `/radio/program/` |
| Programme en cours (statut, URL de lecture, auditeurs en ligne) | GET | `/radio/current/` |
| Chat (lecture) | GET | `/radio/chat/` |
| Chat (poster un message — authentifié) | POST | `/radio/chat/` |
| Diffuser en direct (admin) | POST | `/radio/program/{id}/go_live/` |
| Arrêter le direct (admin) | POST | `/radio/program/{id}/end_live/` |

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
  "cf_playback_hls_url": "https://customer-xxx.cloudflarestream.com/<uid>/manifest/video.m3u8",
  "cf_playback_dash_url": "https://customer-xxx.cloudflarestream.com/<uid>/manifest/video.mpd",
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
| Détail | GET | `/webtv/videos/{slug}/` |
| Vidéo en direct actuelle | GET | `/webtv/videos/live/` |
| Premières (5 dernières) | GET | `/webtv/videos/premiers/` |
| Incrémenter le compteur de vues | POST | `/webtv/videos/{slug}/view/` |
| Chat en direct (lecture/écriture) | GET / POST | `/webtv/videos/{slug}/chat/` |
| Spectateurs en ligne (lecture ponctuelle, hors WebSocket) | GET | `/webtv/videos/{slug}/online-count/` |
| Diffuser en direct (admin) | POST | `/webtv/videos/{slug}/go_live/` |
| Arrêter le direct (admin) | POST | `/webtv/videos/{slug}/end_live/` |
| J'aime / commentaires / partage / enregistrer | — | voir [engagement générique](#système-dengagement-générique) |

Catégories disponibles : `freestyles`, `studio_sessions`, `docs`, `interviews`, `premiers`.

Le catalogue "pas en direct" (toutes les autres vidéos) s'obtient en filtrant côté client sur
`is_live=false`, ou via `?is_live=false` si un filtre dédié est ajouté côté backend (à date, le
filtrage disponible est par `category` — trier côté client ou demander l'ajout du filtre si
nécessaire).

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

```json
// GET /live_music/sessions/current/
{
  "id": 7,
  "title": "Session acoustique — Alesh",
  "slug": "session-acoustique-alesh",
  "artist_names": ["Alesh"],
  "status": "live",
  "cf_playback_hls_url": "https://customer-xxx.cloudflarestream.com/<uid>/manifest/video.m3u8",
  "online_followers": 128,
  "live_started_at": "2026-07-11T18:00:00Z"
}
```

`online_followers` est lu en direct depuis la présence WebSocket à chaque appel (pas de cache).
Pour un compteur qui se met à jour sans polling, brancher le WebSocket (voir plus bas) plutôt que
d'appeler cet endpoint en boucle.

## Communauté

| Action | Méthode | Endpoint |
|---|---|---|
| Liste des posts (filtrable par `?type=talent|art|news`) | GET | `/community/posts/` |
| Créer un post (authentifié) | POST | `/community/posts/` |
| Soumettre un talent (chanson ou vidéo, authentifié) | POST | `/community/posts/submit_talent/` |
| J'aime un post (authentifié, historique — pas le système générique) | POST | `/community/posts/{id}/like/` |
| Commentaires / partage / enregistrer (système générique) | — | voir [engagement générique](#système-dengagement-générique) |
| Défis | GET | `/community/challenges/` |
| Sondages (liste, vote) | GET / POST | `/community/polls/`, `/community/polls/{id}/vote/` |

```http
POST /api/v1/community/posts/submit_talent/
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Mon freestyle du dimanche",
  "media": [
    { "type": "song", "url": "https://res.cloudinary.com/.../audio.mp3" }
  ]
}
```

`media` accepte un ou plusieurs éléments, chacun avec `type` égal à `"song"` ou `"video"` (le
fichier doit avoir été téléversé au préalable vers Cloudinary par le frontend ; ce endpoint
n'accepte que la référence, pas un fichier brut). La réponse renvoie le post créé avec
`post_type: "talent"`.

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
**web-tv (vidéos)**, **releases (sorties)**, **community (posts)**, **emissions**. Le motif est
strictement le même partout — seul le préfixe de ressource change.

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

## Diffusion en direct (Cloudflare Stream) côté frontend

Trois surfaces exposent des champs de lecture Cloudflare Stream une fois en direct :
`RadioProgram`, `Emission`, `WebTVVideo`, `MusicLiveSession`, tous avec la même forme :

```json
{
  "cf_playback_hls_url": "https://customer-<hash>.cloudflarestream.com/<uid>/manifest/video.m3u8",
  "cf_playback_dash_url": "https://customer-<hash>.cloudflarestream.com/<uid>/manifest/video.mpd"
}
```

Ces champs sont vides tant que la ressource n'est pas en direct. **Les champs `cf_rtmps_url` et
`cf_rtmps_key` ne sont jamais renvoyés par les endpoints de lecture publics** — ils ne sont
disponibles que dans la réponse de l'action admin `go_live` (à usage du logiciel de diffusion,
type OBS Studio), jamais persistés côté client.

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
  // res.data.cf_rtmps_url / cf_rtmps_key : à afficher UNE FOIS à l'opérateur pour
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
