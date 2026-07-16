# Live, streaming et temps réel — guide complet

Ce document couvre **tout** ce qui touche au direct sur la plateforme Art du Kivu : diffusion
vidéo/audio (MediaMTX), présence et chat en temps réel (WebSocket), et l'engagement (j'aime,
commentaire, partage) sur le contenu live. Il est volontairement séparé de
`docs/FRONTEND_INTEGRATION.md` (qui couvre le reste de l'API) pour servir de référence autonome à
qui construit l'intégration live côté `frontend_admin` et `frontend_client`.

## Sommaire

1. [Vue d'ensemble et architecture](#vue-densemble-et-architecture)
2. [Concepts clés](#concepts-clés)
3. [Référence des endpoints — les 4 surfaces live](#référence-des-endpoints--les-4-surfaces-live)
4. [Détection du statut live (interne, rien à appeler depuis un frontend)](#détection-du-statut-live-interne-rien-à-appeler-depuis-un-frontend)
5. [Temps réel : WebSocket (présence + chat)](#temps-réel-websocket-présence--chat)
6. [Engagement sur le contenu live](#engagement-sur-le-contenu-live)
7. [Intégration côté admin (frontend_admin)](#intégration-côté-admin-frontend_admin)
8. [Intégration côté client (frontend_client)](#intégration-côté-client-frontend_client)
9. [Gestion des erreurs et cas limites](#gestion-des-erreurs-et-cas-limites)
10. [Checklist de test de bout en bout](#checklist-de-test-de-bout-en-bout)

---

## Vue d'ensemble et architecture

```
                         ┌─────────────────────┐
   OBS Studio  ──RTMP──▶ │      MediaMTX        │ ──HLS──▶  frontend_client (lecteur vidéo/audio)
  (ou équivalent)        │  (auto-hébergé)      │
                         └──────────┬───────────┘
                                    │ sondé toutes les 15s (GET /v3/paths/list)
                                    ▼
                         ┌─────────────────────┐
                         │   Django API (api)   │ ◀──WebSocket (ws/live/...)── frontend_client
                         │  apps.streaming       │ ◀──WebSocket──────────────── frontend_admin
                         │  apps.emissions       │
                         │  apps.radio           │ ◀──REST (go_live/end_live)── frontend_admin
                         │  apps.webtv           │
                         │  apps.live_music      │
                         │  apps.realtime        │
                         │  apps.engagement      │
                         └─────────────────────┘
```

- **Ingestion** : un logiciel de diffusion (OBS Studio ou équivalent) pousse un flux RTMP vers
  **MediaMTX**, un serveur média auto-hébergé (remplace Cloudflare Stream). Voir
  `docs/README.md` section "Streaming en direct" pour le détail de l'infrastructure.
- **Lecture** : MediaMTX ré-encode le flux en HLS, servi sous `/live-hls/live/<clé>/index.m3u8`
  sur le même domaine que l'API (HTTPS, pas de port séparé côté client).
- **Statut** : une tâche Celery (`apps.streaming.tasks.sync_live_status`, toutes les 15s)
  interroge l'API MediaMTX pour savoir quels `stream_key` sont réellement en train d'être
  publiés, et bascule le statut de la ressource correspondante (`Emission`, `RadioProgram`,
  `WebTVVideo`, `MusicLiveSession`) en base — **le frontend n'a jamais besoin d'appeler quoi que
  ce soit pour ça**, il lit simplement le champ `status`/`is_live` de la ressource. Un délai de
  quelques secondes entre la connexion/déconnexion réelle d'OBS et la mise à jour du statut est
  donc normal.
- **Présence + chat** : indépendants de MediaMTX, gérés par Django Channels
  (`apps.realtime`) — un salon WebSocket par surface live, avec un compteur de spectateurs et
  un flux de messages.
- **Engagement** : j'aime / commentaire / partage génériques (`apps.engagement`), utilisables
  sur le contenu live comme sur le contenu enregistré — **sauf l'enregistrement pour plus tard
  ("save"), toujours refusé tant que le contenu est en direct**.

## Concepts clés

| Concept | Ce que c'est |
|---|---|
| `stream_key` | Identifiant aléatoire (32 caractères hex) généré au premier `go_live` — sert à la fois de nom de chemin RTMP et de secret de diffusion (le "Stream key" à donner à OBS). Jamais renvoyé par les endpoints publics de lecture, uniquement par `go_live` (réservé admin). |
| `rtmp_server_url` | Constante (ne change jamais), ex. `rtmp://art-du-kivu-api.kelor.tech:1935/live` — le champ "Serveur" d'OBS. |
| `playback_hls_url` | URL HLS publique, ex. `https://art-du-kivu-api.kelor.tech/live-hls/live/<clé>/index.m3u8` — vide tant que la ressource n'est pas en direct. |
| `room_type` | Identifie le salon WebSocket : `radio`, `emission`, `webtv`, `live_music`. |
| `room_id` | L'identifiant de la ressource dans ce salon (voir tableau plus bas — radio utilise un id fixe `"live"`, les autres utilisent le `pk` numérique de la ressource). |
| Statut live | `Emission.status` / `RadioProgram.status` / `MusicLiveSession.status` valent `"live"` quand en direct ; `WebTVVideo` utilise un booléen `is_live`. |

**Idempotence** : rappeler `go_live` sur une ressource déjà en direct **réutilise** le même
`stream_key` (OBS n'a jamais besoin d'être reconfiguré) et ne réinitialise pas `live_started_at`.

## Référence des endpoints — les 4 surfaces live

Le motif est identique sur les 4 surfaces ; seul le préfixe change. `{id}` = `slug` pour
Émissions/Web TV/Live Music, `id` numérique pour Radio.

| Action | Méthode | Endpoint | Auth |
|---|---|---|---|
| Liste / détail | GET | `/{préfixe}/` , `/{préfixe}/{id}/` | Public |
| Créer / modifier / supprimer | POST / PATCH / DELETE | `/{préfixe}/{id}/` | Admin (`IsAdminOrReadOnly`) |
| **Démarrer le direct** | POST | `/{préfixe}/{id}/go_live/` | **Admin uniquement** |
| **Arrêter le direct** | POST | `/{préfixe}/{id}/end_live/` | **Admin uniquement** |
| Chat (lecture) | GET | `/{préfixe}/{id}/chat/` | Public |
| Chat (écrire) | POST | `/{préfixe}/{id}/chat/` | Authentifié |
| Supprimer un message | DELETE | `/{préfixe}/{id}/chat/{message_id}/` | Auteur ou admin |
| Spectateurs en ligne (lecture ponctuelle) | GET | `/{préfixe}/{id}/online-count/` | Public |
| J'aime | POST | `/{préfixe}/{id}/like/` | Authentifié |
| Commentaires | GET / POST | `/{préfixe}/{id}/comments/` | Public (lecture) / Authentifié (écriture) |
| Partager | POST | `/{préfixe}/{id}/share/` | Public |
| Enregistrer pour plus tard | POST / DELETE | `/{préfixe}/{id}/save/` | Authentifié — **toujours 400 tant que le contenu est en direct** |

Préfixes réels et particularités par surface :

### Émissions — `/api/v1/emissions/`
- `{id}` = `slug`. Statuts : `scheduled` → `live` → `recorded`.
- `GET /api/v1/emissions/live/` — l'émission actuellement en direct (404 si aucune).
- `go_live` / `end_live` renvoient `{"status", "rtmp_server_url", "stream_key", "playback_hls_url"}`.
- Chat, commentaires, partage **et** enregistrement disponibles (le "save" redevient possible dès
  que `status` repasse à `recorded`).
- Pas de champ `online_followers`/`listener_count` dédié dans le serializer — utiliser
  `/online-count/` ou le WebSocket.

### Radio — `/api/v1/radio/`
- Deux ressources distinctes : `program/{id}/` (grille + go_live/end_live, `{id}` numérique) et
  `chat/` (`RadioChatViewSet`, **pas** monté via `LiveChatViewSetMixin` — modèle historique
  `RadioChat`, indépendant de tout `room_id` de programme : un seul salon continu).
- `GET /api/v1/radio/current/` — le programme actuellement diffusé (calculé sur l'heure locale
  Africa/Lubumbashi), avec `listener_count` lu en direct depuis la présence WebSocket. **Non mis
  en cache**, contrairement aux autres listes.
- Chat : `GET`/`POST /api/v1/radio/chat/`, suppression `DELETE /api/v1/radio/chat/{id}/`
  (auteur ou admin). Room WebSocket : `room_type="radio"`, `room_id="live"` (fixe, un seul salon
  pour toute la radio — pas par programme).
- **Pas de j'aime/commentaire/partage/save générique sur `RadioProgram`** (pas de
  `EngagementActionsMixin` monté) — seul le chat existe.

### Web TV — `/api/v1/webtv/videos/`
- `{id}` = `slug`. Champ `is_live` (booléen, pas de champ `status`).
- `GET /api/v1/webtv/videos/live/` — la vidéo actuellement en direct (404 si aucune).
- `GET /api/v1/webtv/videos/premiers/` — les 5 dernières premières (VOD, sans rapport avec le live).
- `go_live`/`end_live` renvoient `{"is_live", "rtmp_server_url", "stream_key", "playback_hls_url"}`.
- Toutes les actions d'engagement disponibles, y compris "save" (refusé tant que `is_live=true`).
- Room WebSocket : `room_type="webtv"`, `room_id=<pk numérique de la vidéo>`.

### Live Music — `/api/v1/live_music/sessions/`
- `{id}` = `slug`. Concept indépendant de Radio/Émissions (voir `docs/README.md`).
- `GET /api/v1/live_music/sessions/current/` — la session actuellement en direct (404 si aucune).
- `GET /api/v1/live_music/programme/` — grille de programmes (`?day=0..6`, lundi=0),
  **sans rapport avec le live actuel** — c'est un planning informatif, pas une ressource "live".
- `go_live`/`end_live` renvoient `{"status", "rtmp_server_url", "stream_key", "playback_hls_url"}`.
- Toutes les actions d'engagement disponibles.
- Room WebSocket : `room_type="live_music"`, `room_id=<pk numérique de la session>`.

## Détection du statut live (interne, rien à appeler depuis un frontend)

Il n'y a **aucun webhook** — l'image officielle MediaMTX est `FROM scratch` (aucun shell, aucun
`curl`/`wget` dedans), donc elle ne peut exécuter aucune commande pour nous notifier activement.
À la place, une tâche Celery (`apps.streaming.tasks.sync_live_status`, toutes les 15s) interroge
l'API MediaMTX (`GET /v3/paths/list`) et bascule automatiquement le statut de la ressource
correspondante. Mentionné ici uniquement pour que l'équipe frontend comprenne pourquoi
`status`/`is_live` se met à jour tout seul, avec un délai de quelques secondes, sans qu'aucun
appel explicite ne soit nécessaire de leur côté.

## Temps réel : WebSocket (présence + chat)

**Connexion** : `wss://<domaine>/ws/live/<room_type>/<room_id>/?token=<jwt_access_token>`

- `room_type` ∈ `radio | emission | webtv | live_music`.
- `room_id` : voir le tableau par surface ci-dessus (`"live"` fixe pour radio, `pk` numérique
  sinon).
- `?token=` est **facultatif** — les connexions anonymes sont acceptées (la présence doit
  compter tous les spectateurs, pas seulement les connectés). Sans token, `scope["user"]` est
  anonyme côté serveur ; poster un message de chat reste impossible sans authentification (ça se
  fait via REST, pas sur le socket — voir plus bas), mais **regarder** le compteur de présence et
  recevoir les messages des autres ne nécessite pas de connexion.
- Un jeton expiré ou invalide ne fait pas échouer la connexion WebSocket — il retombe simplement
  sur un utilisateur anonyme.

**Heartbeat** — envoyer sur le socket toutes les ~15 secondes, sinon le compteur de présence
expire côté serveur après 30s d'inactivité :

```json
{ "type": "heartbeat" }
```

**Événements reçus du serveur** :

```json
{ "event": "presence.count", "count": 128 }
{ "event": "chat.message", "message": { "id": 42, "username": "...", "handle": "...", "avatar_url": "...", "message": "...", "created_at": "..." } }
```

**Écrire un message de chat** — **pas** sur le socket, via REST (`POST /{préfixe}/{id}/chat/`,
voir tableau plus haut) ; le serveur pousse ensuite le message à tous les sockets connectés au
salon via `chat.message`. Ce choix permet un chargement initial simple en HTTP (pagination
classique via `GET`) tout en gardant le push temps réel pour la suite.

**Throttle** : le POST de chat est limité à 20 requêtes/minute par utilisateur authentifié
(scope `chat`), en plus des 120 req/min générales.

## Engagement sur le contenu live

Voir `docs/FRONTEND_INTEGRATION.md` section "Système d'engagement générique" pour le détail
complet des 4 actions (`like`, `comments`, `share`, `save`) — elles fonctionnent à l'identique sur
le contenu live, à une seule exception :

> **"save" est toujours refusé (400) tant que la ressource est en direct.** Le frontend doit
> soit masquer le bouton "enregistrer" quand `status === "live"` / `is_live === true`, soit
> gérer le 400 gracieusement (message "disponible une fois le direct terminé").

## Intégration côté admin (frontend_admin)

Flux complet pour un panneau "Démarrer/Arrêter un direct" :

```ts
// 1. Démarrer le direct
async function goLive(resourcePath: string, id: string) {
  const res = await api.post(`/${resourcePath}/${id}/go_live/`);
  // { status/is_live, rtmp_server_url, stream_key, playback_hls_url }
  return res.data;
}

// 2. Afficher UNE FOIS à l'opérateur (jamais stocké, jamais ré-affiché après coup) :
//    - Serveur RTMP  : res.data.rtmp_server_url
//    - Clé de flux   : res.data.stream_key
//    Dans OBS : Paramètres → Flux → Service = "Personnalisé..." → coller ces deux valeurs.

// 3. Arrêter le direct
async function endLive(resourcePath: string, id: string) {
  await api.post(`/${resourcePath}/${id}/end_live/`);
}
```

**Composant React minimal (panneau admin)** :

```tsx
function GoLiveButton({ resourcePath, id, status }: { resourcePath: string; id: string; status: string }) {
  const [credentials, setCredentials] = useState<{ rtmp_server_url: string; stream_key: string } | null>(null);

  const handleGoLive = async () => {
    const data = await goLive(resourcePath, id);
    setCredentials({ rtmp_server_url: data.rtmp_server_url, stream_key: data.stream_key });
  };

  if (status === "live") {
    return <button onClick={() => endLive(resourcePath, id)}>Arrêter le direct</button>;
  }

  return (
    <div>
      <button onClick={handleGoLive}>Démarrer le direct</button>
      {credentials && (
        <div className="obs-credentials">
          <p>Serveur : <code>{credentials.rtmp_server_url}</code></p>
          <p>Clé de flux : <code>{credentials.stream_key}</code></p>
          <p className="warning">À configurer dans OBS maintenant — cette clé ne sera plus jamais affichée.</p>
        </div>
      )}
    </div>
  );
}
```

**`status`/`is_live` passe à "live" dès `go_live`** (intention de l'admin), et la tâche de
sondage (toutes les 15s) le confirme dès qu'elle détecte qu'OBS publie réellement. Un délai de
grâce de 45s après `go_live` empêche la tâche de repasser le statut à "non live" si l'opérateur
n'a pas encore eu le temps d'ouvrir OBS et de cliquer "Démarrer la diffusion" — au-delà de ces
45s sans connexion réelle détectée, le statut redescend automatiquement. Le panneau admin peut
simplement re-poller la ressource (`GET /{préfixe}/{id}/`) ou se connecter au WebSocket du
salon — le champ `status`/`is_live` de la ressource reste la source de vérité.

**Modération du chat** (admin) : `DELETE /{préfixe}/{id}/chat/{message_id}/` fonctionne pour tout
message, pas seulement les siens (permission `IsAdminUser` OU auteur).

## Intégration côté client (frontend_client)

**1. Découvrir s'il y a un direct** — appeler l'endpoint `.../live/` ou `.../current/` de la
surface concernée (voir tableau plus haut) au chargement de la page, ou en polling léger
(10-15s) si le WebSocket n'est pas déjà branché pour autre chose.

**2. Lecteur HLS** (`hls.js`, fonctionne identiquement pour audio/vidéo) :

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

Pour de l'audio seul (radio, live music), un `<audio src={hlsUrl} />` (ou `hls.js` attaché à un
élément `<audio>`) fonctionne de la même façon.

**3. Présence + chat** (hook React réutilisable pour les 4 surfaces) :

```tsx
function useLiveRoom(roomType: string, roomId: string, accessToken?: string) {
  const [onlineCount, setOnlineCount] = useState(0);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const url = `${WS_BASE_URL}/ws/live/${roomType}/${roomId}/${accessToken ? `?token=${accessToken}` : ""}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.event === "presence.count") setOnlineCount(data.count);
      if (data.event === "chat.message") setMessages((prev) => [...prev, data.message]);
    };

    const heartbeat = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "heartbeat" }));
    }, 15000);

    return () => {
      clearInterval(heartbeat);
      ws.close();
    };
  }, [roomType, roomId, accessToken]);

  const sendMessage = async (resourcePath: string, id: string, message: string) => {
    // Écriture via REST, pas sur le socket — le serveur relaie ensuite via chat.message.
    await api.post(`/${resourcePath}/${id}/chat/`, { message });
  };

  return { onlineCount, messages, sendMessage };
}
```

**4. Charger l'historique du chat au montage** (avant que le WebSocket ne pousse les nouveaux
messages) : `GET /{préfixe}/{id}/chat/` (paginé, `SmallPagination`, 10/page), à afficher en plus
des messages reçus en temps réel ensuite.

**5. Engagement** : j'aime/commentaire/partage utilisables normalement (voir
`docs/FRONTEND_INTEGRATION.md`) ; masquer ou désactiver le bouton "enregistrer" tant que le
contenu est en direct (voir section précédente).

**6. Reconnexion** : un salon WebSocket ne garde aucun historique côté client — à la
reconnexion (perte réseau, veille mobile), re-fetcher l'historique du chat via REST (`GET
.../chat/`) puis rouvrir le socket ; ne pas supposer que les messages manqués pendant la
déconnexion seront rejoués.

## Gestion des erreurs et cas limites

| Situation | Comportement |
|---|---|
| `go_live`/`end_live` appelé par un non-admin | `403 Forbidden` |
| `save` sur du contenu en direct | `400 Bad Request`, `{"detail": "Le contenu en direct ne peut pas être enregistré pour plus tard."}` |
| Chat POST sans authentification | `401 Unauthorized` |
| Chat POST au-delà de 20/min | `429 Too Many Requests` |
| WebSocket avec un token JWT expiré/invalide | Connexion acceptée quand même, mais anonyme (pas d'erreur, pas de fermeture) |
| `.../live/` ou `.../current/` sans direct en cours | `404 Not Found` avec un message lisible |
| OBS déconnecté brutalement (crash, coupure réseau) | Le statut repasse automatiquement à "non live" au prochain sondage (≤ 15s, après le délai de grâce de 45s) — pas besoin d'appeler `end_live` manuellement, mais l'action admin reste disponible pour forcer l'arrêt à tout moment |

## Checklist de test de bout en bout

1. `POST /{préfixe}/{id}/go_live/` (admin) → noter `rtmp_server_url` + `stream_key` ; `status`/
   `is_live` passe à "live" immédiatement dans la réponse.
2. Configurer OBS (Personnalisé → Serveur + Clé de flux) et démarrer la diffusion **dans les 45s**
   (délai de grâce — au-delà, sans connexion détectée, le statut redescend tout seul).
3. Vérifier que `GET /{préfixe}/{id}/` reste à `status="live"` / `is_live=true` une fois OBS
   effectivement connecté (le prochain sondage, ≤ 15s, le confirme).
4. Vérifier que `playback_hls_url` charge dans un lecteur `hls.js`.
5. Ouvrir `wss://<domaine>/ws/live/<room_type>/<room_id>/` (deux onglets/clients) et confirmer
   que `presence.count` s'incrémente/décrémente à la connexion/déconnexion.
6. Poster un message via `POST .../chat/` et confirmer qu'il apparaît en temps réel dans les deux
   onglets via `chat.message`.
7. Arrêter OBS (pas `end_live`) et confirmer que le statut repasse tout seul à "non live" au
   sondage suivant (≤ 15s, une fois le délai de grâce de 45s dépassé).
8. Rappeler `go_live` et confirmer que `stream_key` est **identique** à la première fois
   (idempotence — OBS n'a pas besoin d'être reconfiguré).
