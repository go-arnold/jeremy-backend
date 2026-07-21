# Manques & écarts côté backend — audit complet

> Audit exhaustif du frontend admin (`app/`, `components/`, `lib/api.ts`) croisé avec
> la spec OpenAPI (`Art du Kivu API.yaml`) et le comportement réel constaté.
> Objectif : lister tout ce qui **manque**, **diffère** ou **bloque** côté backend.

**Légende de sévérité**
- 🔴 **Bloquant** — une fonctionnalité ne peut pas marcher correctement.
- 🟠 **Écart de contrat** — un champ/format diffère, ou un contournement est en place.
- 🟡 **Infrastructure** — l'endpoint existe mais l'environnement pose problème.
- 🟢 **À confirmer** — comportement probable, à valider en conditions réelles.

> ⚠️ **La spec `Art du Kivu API.yaml` est datée (19 juin) et incomplète.** Le backend
> a évolué depuis (modules `live_music`, `newsletter`, `analytics`, `search`, actions
> `go_live`/`end_live`, `bulk_delete`) : ces routes sont appelées par le frontend et
> semblent fonctionner, mais ne figurent pas dans le YAML. Les contraintes de **champs**
> (types, `maxLength`) restent en revanche fiables pour les schémas documentés.

---

## 0. LE point transversal le plus impactant 🔴

### Toutes les URL en écriture sont limitées à `maxLength: 200`
Dans les schémas d'écriture, **chaque champ URL est plafonné à 200 caractères** :
`photo`, `cover`, `audio_url`, `video_url`, `stream_url`, `preview_url`, `image_url`, `thumbnail`.

Une URL **Cloudinary** (`https://res.cloudinary.com/<cloud>/<type>/upload/v<version>/<folder>/<public_id>.<ext>`,
souvent + transformations) **dépasse fréquemment 200 caractères**. Résultat :
- le backend **tronque ou rejette** l'URL → la valeur stockée est incomplète ;
- les champs `*_url` renvoyés (photo_url, **cover_url**, audio_url…) sont donc **incomplets/cassés**.

**C'est la cause racine du « cover_url renvoie un lien incomplet » ET d'une partie des échecs de lecture audio/vidéo.**

**Demande backend :** porter ces champs à `maxLength` ≥ 500 (idéalement `TextField`/URLField sans limite serrée),
**ou** stocker un fichier (`audio_file`, `video_file`, upload direct) plutôt qu'une URL.
Champs concernés (schémas write) : `ArtistWriteRequest.photo` / `.cover`, `EpisodeWriteRequest.audio_url` / `.cover`,
`VideoWriteRequest.video_url` / `.thumbnail`, `ReleaseWriteRequest.preview_url` / `.cover`, `EmissionWriteRequest.stream_url`.

---

## 1. Endpoints manquants ou incomplets

### Utilisateurs 🔴
| Manque | Impact frontend |
|--------|-----------------|
| **`POST /users/`** (création) | `usersApi` n'a pas de `create` — aucune création d'utilisateur via l'admin (seule voie : `POST /auth/register/`, avec vérif email). |
| **`DELETE /users/{id}/`** | Pas de suppression unitaire ; le frontend contourne via **`POST /users/bulk_delete/`** (commentaire explicite dans `lib/api.ts`). À exposer proprement. |
| **Envoi d'email à un utilisateur** | L'action « envoyer un email » n'a aucun endpoint. |

*Existant et câblé : `GET /users/`, `GET /users/{id}/`, `PATCH /users/{id}/` (rôle/activation), `POST /users/bulk_delete/`.*

### Notifications 🔴
| Manque | Impact |
|--------|--------|
| **Aucun endpoint `/notifications/`** | La cloche de la topbar **fabrique** des notifications à partir de `articles.list` + `events.list` (voir `components/admin/navbar.tsx`). Pas de vrai système : pas de « marquer lu » persistant, pas de temps réel. |

### Galerie artiste (photos) 🔴
| Manque | Impact |
|--------|--------|
| **`POST`/`DELETE /artists/{slug}/gallery/`** | `/artists/{slug}/gallery/` est **GET only**. Impossible d'**ajouter/supprimer** une photo à la galerie d'un artiste. L'affichage (fiche artiste) est déjà prêt côté front, mais l'ajout est impossible. |

### Podcasts ↔ Artiste 🟠
| Manque | Impact |
|--------|--------|
| **Route « podcasts d'un artiste »** | Aucun lien direct artiste → podcasts. Seule existe la relation `guests` (artiste invité d'un épisode). Pour lister/afficher les podcasts d'un artiste sur sa fiche, il faut soit une route dédiée, soit un filtre **`GET /podcasts/episodes/?guest=<artistId>`**. |

### Catégories (articles & podcasts) 🟠
| Manque | Impact |
|--------|--------|
| **`POST /articles/categories/`** et **`POST /podcasts/categories/`** | Les catégories sont **GET only** → impossible d'en créer depuis l'admin (il faut les créer en base). |
| **Forme de réponse instable** | `/articles/categories/` (et `/podcasts/categories/`, `/artists/genres/`) peut renvoyer un **tableau brut** ou un objet **paginé `{results:[…]}`**. Le frontend a été rendu défensif (normalisation), **mais** c'était la cause du bug « catégories vides » qui **bloquait la création d'articles**. À stabiliser sur un format unique. |

---

## 2. Écarts de contrat par domaine

### Articles — `POST/PATCH /articles/` 🟠
| Écart | Détail |
|-------|--------|
| **`author`** | À confirmer 🟢 : le backend accepte-t-il l'assignation d'auteur, ou force-t-il l'auteur = utilisateur connecté ? Le sélecteur d'auteur du frontend l'envoie mais peut être ignoré. |
| **Pas de statut `scheduled`** | Le backend ne connaît que `draft|published`. La « programmation » = `status=published` + `scheduled_at` futur (contourné côté front). Pas de vrai état « programmé ». |
| **`featured_image` = string (URL, max 200)** | Voir §0. |

### Podcasts — épisodes 🟠
| Écart | Détail |
|-------|--------|
| **La liste ne renvoie pas `audio_url`** | `GET /podcasts/episodes/` omet `audio_url` → pour lire un épisode, le front fait un **appel détail supplémentaire** par épisode (N+1). Idéalement inclure `audio_url` dans la liste. |
| **`audio_url` max 200** | Voir §0 — casse la lecture des fichiers longs. |
| **Pas de statut brouillon/publié** | Un épisode n'a pas d'état de publication (seulement `published_at`). |
| **Invités « non-artistes »** 🟢 | Le champ `guests` est **non typé (`{}`)** dans la spec. Le frontend envoie désormais un mélange **IDs d'artistes + noms libres**. **À confirmer** que le backend stocke bien les noms libres (sinon fournir le format attendu, ex. `[{name, artist_id?}]`). |

### Web TV / Vidéos — `POST/PATCH /webtv/videos/` 🔴
| Écart | Détail |
|-------|--------|
| **Pas d'upload de fichier vidéo** | Champ **`video_url` (URI, max 200)** : il faut fournir une URL, pas un fichier vidéo. Pas de stockage vidéo natif. |
| **Backend ne distingue pas « playout » vs « direct caméra »** | Le front doit **mémoriser le mode en `localStorage`** (`webtv_playout`, `webtv_camera`) — fragile, non partagé entre navigateurs/utilisateurs. Il faudrait un champ backend (ex. `broadcast_mode`). |
| **`CAMERA_PLACEHOLDER`** | `video_url` étant **requis**, une entrée « direct caméra » (sans fichier) envoie une URL bidon (`res.cloudinary.com/demo/…/dog.mp4`). À permettre : `video_url` nullable pour les directs caméra. |
| **`artists` (association)** 🟢 | Le schéma vidéo a `artists: integer[]` ; le front l'envoie désormais. **À confirmer** que le détail vidéo **renvoie** aussi `artists` (sinon impossible de précharger la sélection à l'édition). |

### Émissions / Radio / Live Music — actions live 🟠
| Écart | Détail |
|-------|--------|
| **Identifiants RTMP parfois non renvoyés** | `go_live` doit renvoyer les identifiants de diffusion, mais le front gère le cas « non renvoyés » (toasts d'avertissement dans `emissions`, `webtv`). |
| **Noms de champs RTMP instables** | Le front doit tester plusieurs formes (`cf_rtmps_*`, `rtmps_*`, …) via `extractStreamCreds` — voir `lib/api.ts`. À figer un contrat unique. |
| **Délai HLS (~15 s MediaMTX)** | `playback_hls_url` n'est disponible que ~15 s après le `go_live` → le front tolère l'absence temporaire. |
| **`live_music` absent de la spec** 🟢 | Module `live_music/*` non documenté : confirmer les routes (`sessions`, `programme`, `go_live`/`end_live`, `current`). |

### Communauté 🟠
| Écart | Détail |
|-------|--------|
| **Posts non éditables** | `/community/posts/{id}/` = **GET + DELETE** seulement (pas de PATCH) → modération uniquement (masquer/supprimer), pas d'édition. À confirmer si voulu. |

---

## 3. Fonctionnalités « factices » / contournements côté front

| Zone | Contournement actuel | Correctif backend souhaité |
|------|----------------------|----------------------------|
| **Notifications** (topbar) | Reconstruites depuis articles + events. | Vrai modèle de notifications. |
| **Web TV mode live** | `localStorage` (`webtv_playout`/`webtv_camera`). | Champ `broadcast_mode` persistant. |
| **Web TV caméra** | `CAMERA_PLACEHOLDER` (URL bidon). | `video_url` nullable pour les directs. |
| **Statistiques** | Comptes agrégés via `analyticsApi.dashboard()` ; **pas de séries temporelles** (courbes = placeholders). | Endpoint analytics temporel (vues/jour, écoutes/jour…). |
| **Lecture audio épisode** | Appel détail par épisode (liste sans `audio_url`). | Inclure `audio_url` dans la liste. |
| **Barre live** (spectateurs/messages) | Compteurs affichés seulement si fournis, sinon masqués. | Exposer viewers/messages temps réel si souhaité. |

---

## 4. Paramètres — page 100 % statique, aucune persistance backend 🔴

La page **Paramètres** (`app/admin/parametres/page.tsx`) est aujourd'hui **entièrement factice** :
tous les champs utilisent `defaultValue`, les interrupteurs sont des `<Toggle>` à état **local**,
et le bouton **« Sauvegarder »** ne fait qu'afficher un toast — **aucun appel API**, **aucune lecture**,
**aucune écriture**. Il n'existe **aucun module de configuration** côté backend (`/settings/` absent de la spec et de `lib/api.ts`).

Pour rendre la page fonctionnelle, il faut un **module de réglages** (idéalement un singleton admin-only) :

### A. Réglages du site — `GET /settings/` + `PATCH /settings/` 🔴
| Champ | Type | Écran |
|-------|------|-------|
| `site_name` | string | Nom du site |
| `site_url` | url | URL du site |
| `slogan` | string | Slogan |
| `description` | text | Description |
| `logo` | upload (image) | Logo principal |
| `favicon` | upload (image) | Favicon |
| `default_language` | enum `fr\|en\|sw` | Langue par défaut |
| `timezone` | string | Fuseau horaire |
| `date_format` | enum | Format de date |
| `currency` | enum `CDF\|USD\|EUR` | Devise |

### B. Thème — `GET/PATCH /settings/theme/` (ou inclus dans `/settings/`) 🟠
| Champ | Type |
|-------|------|
| `dark_mode_default` | bool |
| `primary_color` | string (hex) |
| `display_font` | enum |

### C. Préférences de notifications — `GET/PATCH /settings/notifications/` 🔴
Interrupteurs à persister : `new_comments`, `new_subscribers`, `weekly_reports`, `security_alerts`.
(Aujourd'hui purement visuels.)

### D. Configuration SMTP — `GET/PATCH /settings/smtp/` + **`POST /settings/smtp/test/`** 🔴
| Champ | Type |
|-------|------|
| `host` | string |
| `port` | int |
| `username` | string |
| `password` | write-only |
| `from_email` | email |

+ un endpoint de **test d'envoi** (« Tester la configuration »). **Directement lié au 🔴 « email de vérification non envoyé »** : sans SMTP configurable/testable, l'onboarding reste cassé.

### E. Sécurité — `GET/PATCH /settings/security/` 🔴
| Champ | Type |
|-------|------|
| `two_factor_required` | bool |
| `lockout_enabled` / `lockout_threshold` | bool / int (défaut 5) |
| `session_timeout` | enum (30m/1h/4h/24h) |

+ **2FA réelle (TOTP)** si l'option est activée : endpoints `setup` / `verify` / `disable` côté auth — **grosse fonctionnalité** à part entière (pas seulement un flag).

### F. Upload logo / favicon 🟠
Réutiliser le flux Cloudinary existant (`/media/upload-signature/`) **ou** un endpoint dédié — mais rappel du **§0** : le champ qui stocke l'URL doit accepter > 200 caractères.

> Note : l'URL de l'API et le lien Swagger affichés dans l'onglet « Sécurité » sont **codés en dur** (affichage informatif uniquement) — pas besoin de backend pour ça.

---

## 5. Manques backend issus du document « Texte en vert » (PATRICK & CIKU)

> Ce document liste surtout des améliorations **côté client** ; ci-dessous, uniquement les points qui **nécessitent le backend**.

### Communauté — création de post incomplète 🔴
`CommunityPostWrite` n'accepte que **`content` + `post_type`**. Or le besoin est **titre + description + média** (audio **ou** vidéo **ou** photo) à l'envoi, puis affichage dans le feed **sans doublon** titre/description.
- Manque : **`title`** et surtout **`media` (upload audio/vidéo/photo)** dans `POST /community/posts/`. Le modèle **lecture** a bien `title`/`media`, mais **l'écriture ne les accepte pas** → impossible d'envoyer un post média.

### Partage — endpoints manquants 🟠
Seuls **`/emissions/{slug}/share/`** et **`/webtv/videos/{slug}/share/`** existent. Le partage est demandé aussi sur **podcasts, artistes, posts communauté, radio/live-music**. → Ajouter les `.../share/` correspondants (ou un endpoint de partage générique).

### Podcasts — likes / favoris (signets) 🟠
Un épisode n'expose que `POST /podcasts/episodes/{slug}/play/`. Sont demandés : **likes, favoris/signets**, et l'affichage de l'invité-artiste avec « suivre / mettre en favori ». → Endpoints like/bookmark d'épisode manquants.

### Profil (client) — activité, historique, badges 🟠
`/users/{id}/history/` et `/users/{id}/favorites/` existent. **Manquent** : le système de **badges** (progression/accomplissement), le **temps d'écoute** cumulé, et le flux **d'activité** (likes/commentaires de l'utilisateur). Édition via `PATCH /auth/me/` (existe) — **confirmer** qu'il accepte **photo de profil + couverture + nom d'affichage**.

### Home — bannière dynamique configurable (plus tard) 🟠
La grande bannière d'accueil doit être pilotée depuis l'**Admin (Paramètres)** : radio en direct (lien), à la une (artiste/son du mois, top 30), concert/événement à venir. → Nécessite un modèle **« à la une » / config home** exposé en écriture (lié au **§4 Paramètres**).

### Extraction de durée des médias 🟢
Éviter la durée par défaut `0:00`. Côté admin c'est géré à l'upload (`onDuration`), **mais** pour un média fourni **par URL**, seul le backend peut calculer la durée de façon fiable.

### Points du PDF déjà couverts ailleurs dans ce document
- **Admin — live « direct » à la création sans liens RTMP** → §2 (identifiants RTMP parfois non renvoyés). ✅
- **Invités + transcription podcast** → §2 Podcasts (invités non-artistes à confirmer). ✅
- **Google OAuth** → §6 Infrastructure (contrat `access_token`/`code`, Client ID) ; la **redirection** après login est purement front. ✅

---

## 6. Infrastructure 🟡

| Problème | Impact |
|----------|--------|
| **CORS lecture audio/vidéo (front client)** | La source (Cloudinary/externe) ne renvoie pas `Access-Control-Allow-Origin` → erreur `No 'Access-Control-Allow-Origin' header` côté **frontend client** (l'admin lit en `<audio>`/HLS simple, souvent sans CORS ; le client, avec waveform/Web Audio, exige CORS). **Correctif :** servir via un fichier propre (`audio_file`), un proxy backend, ou configurer les en-têtes CORS de la source. Le front admin bloque déjà à la création les URLs non lisibles (pages/embeds). |
| **Email de vérification** | Si SMTP non configuré, l'inscription bloque la connexion (« email non vérifié »). |
| **Cold start hébergement (~10 s)** | Premier appel très lent (offre gratuite qui endort le service). |
| **Expiration JWT courte** | Gérée par refresh auto côté front, mais prévoir une durée d'access raisonnable. |
| **Google OAuth** | `POST /auth/google/` attend `access_token` **ou** `code` (pas `id_token`) ; Client ID à aligner front/back. |
| **Erreurs 500 peu explicites** | Des validations renvoient `500 {"detail":"An unexpected error occurred."}` au lieu d'un `400` clair (ex. URL trop longue, image invalide). Rend le diagnostic difficile. |

---

## 7. Récapitulatif priorisé

### 🔴 À traiter en priorité côté backend
1. **Allonger la limite des URL en écriture** (`maxLength` 200 → ≥ 500) — débloque `cover_url`/audio/vidéo tronqués (§0).
2. **CORS** sur la lecture des fichiers audio/vidéo côté client (ou `audio_file`/proxy).
3. **Module Paramètres** : `/settings/` (site, thème, notifications, **SMTP + test**, sécurité) — la page est aujourd'hui 100 % factice (§4). Inclut la **2FA (TOTP)** si activée.
4. **Posts communauté avec média** : `title` + **`media` (audio/vidéo/photo)** en écriture (§5).
5. **Gestion utilisateurs** : `POST /users/` (création) + `DELETE /users/{id}/` unitaire.
6. **Galerie artiste** : `POST`/`DELETE /artists/{slug}/gallery/` (ajout de photos).
7. **Notifications** : vrai modèle + endpoints.
8. **Upload vidéo** (ou assumer le modèle « par URL ») + `broadcast_mode` pour distinguer playout/caméra.

### 🟠 Autres besoins backend (issus du §5)
- **Partage** : endpoints `.../share/` pour podcasts, artistes, posts, radio/live-music.
- **Likes/favoris** d'épisodes podcast.
- **Profil** : badges, temps d'écoute, flux d'activité ; confirmer photo/couverture sur `PATCH /auth/me/`.
- **Bannière home** configurable via Paramètres.

### 🟠 Écarts à clarifier / aligner
- Format **unique** pour `/…/categories/` et `/artists/genres/` (tableau vs paginé).
- `author` writable sur les articles (à confirmer).
- Statut brouillon/programmé pour **articles** et **épisodes**.
- `audio_url` dans la **liste** des épisodes (éviter le N+1).
- Contrat RTMP unique (`go_live`) + `video_url` nullable pour les directs caméra.
- Route/filtre **podcasts d'un artiste** ; confirmation du stockage des **invités non-artistes**.
- Le détail **vidéo** doit renvoyer `artists`.

### 🟡 Infrastructure
- Cold start, durée JWT, SMTP, config Google OAuth, messages d'erreur `400` explicites.

### 🟢 À confirmer en conditions réelles (spec datée)
- Existence/contrat réel de `live_music/*`, `newsletter/*`, `analytics/dashboard/`, `search/`, `articles/tags/`, `*/go_live`, `*/end_live`, `*/bulk_delete` (appelés par le front, absents du YAML).

---
