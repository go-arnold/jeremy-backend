# Communauté — besoins backend (Défis, Talents, Sondages)

Document de coordination frontend → backend pour la refonte de la page
Communauté. Basé sur une lecture de `docs/Art_du_Kivu_API.yaml` (état actuel).
Chaque section liste : ce qui existe déjà (OK, rien à faire), ce qui manque,
et la forme proposée pour combler le manque — à valider/ajuster côté backend.

Le frontend est développé **dès maintenant** contre ces formes proposées :
tout ce qui n'existe pas encore est isolé derrière des fonctions de service
dédiées (`lib/services/community.ts`) qui échouent proprement (404 géré,
UI de repli) tant que la route n'existe pas, pour ne rien bloquer.

---

## 1. Talents — ✅ déjà supporté, aucun changement requis

`POST /api/v1/community/posts/submit_talent/` existe et fonctionne
(`title`, `content`, `media`, réponse `CommunityPost` avec `post_type`).
Rien à demander ici.

---

## 2. Sondages — ✅ déjà supporté, aucun changement requis

`GET /community/polls/`, `GET /community/polls/{id}/`,
`POST /community/polls/{id}/vote/` existent et couvrent le besoin
(question, options, vote_count, percentage, expires_at, is_active).
Rien à demander ici.

---

## 3. Défis — plusieurs manques bloquants

### 3.1. Soumettre une réponse à un défi (média + titre + description)

**Aujourd'hui** : `POST /community/challenges/{slug}/join/` attend le body
`ChallengeRequest` complet (title/slug/description/deadline/prize/
participant_count/is_active) — c'est le schéma de **création** d'un défi,
pas d'une **réponse** à un défi. Il n'y a aucun champ pour un média, un titre
ou une description de la participation.

**Besoin** : un endpoint qui accepte, comme `submit_talent`, un média +
titre + description, et qui les publie comme une participation rattachée au
défi.

**Proposition** — réutiliser exactement la forme de `submit_talent` :

```
POST /api/v1/community/challenges/{slug}/participate/
Body: { "title": string, "content": string, "media": [{ "type": "image"|"video"|"song", "url": string }] }
Response: CommunityPost (avec un champ challenge en plus, voir 3.2)
```

Le endpoint `join/` actuel peut soit être supprimé/déprécié, soit conservé
tel quel s'il sert un autre usage — mais il ne doit plus être ce que le
frontend appelle pour "Participer".

### 3.1bis. ⚠️ Constaté en prod : `?post_type=` non appliqué pour une valeur inconnue

En testant le filtre "Défis" avec `GET /community/posts/?post_type=challenge_response`,
l'API retourne actuellement **la liste complète non filtrée** (talents/art/news inclus)
au lieu d'une liste vide ou d'une erreur 400 — vraisemblablement parce que
`challenge_response` n'existe pas encore dans `PostTypeEnum` (voir 3.2) et que le
filtre est silencieusement ignoré pour toute valeur qu'il ne reconnaît pas.

Ce n'est pas bloquant : le frontend re-filtre déjà côté client par sécurité
(`keepMatchingType()` dans `CommunautePageClient.tsx`), donc l'empty state "Aucune
participation aux défis" s'affiche correctement dès aujourd'hui. Mais une fois
`challenge_response` ajouté à l'enum (3.2), **merci de vérifier que le filtre
`post_type` renvoie bien un `results: []` (et pas la liste complète) pour toute
valeur d'enum valide sans résultat** — sinon la pagination ("voir plus") du
frontend paraîtra cassée (des pages entières filtrées à zéro côté client alors que
`next` reste non-null côté API).

### 3.2. Lier une participation à son défi + nouveau `post_type`

**Aujourd'hui** : `CommunityPost.post_type` (`PostTypeEnum`) n'a que
`talent | art | news`. Aucun champ ne relie un post à un `Challenge`.

**Besoin** :
- Ajouter la valeur `challenge_response` à `PostTypeEnum`.
- Ajouter un champ `challenge` (slug ou objet `{id, slug, title}`) sur
  `CommunityPost`, non-null uniquement quand `post_type == "challenge_response"`.

Ainsi une participation au défi peut être affichée comme un post normal
(mêmes likes/comments/share/signets que les talents) tout en sachant à quel
défi elle appartient, et peut être filtrée via
`GET /community/posts/?post_type=challenge_response`.

### 3.3. Indicateur "déjà participé" par utilisateur

**Aujourd'hui** : `Challenge` (schéma) n'expose aucune information sur la
participation de l'utilisateur courant.

**Besoin** : ajouter au schéma `Challenge` (retourné par
`GET /community/challenges/` et `GET /community/challenges/{slug}/`, pour un
utilisateur authentifié) un champ :

```
"has_participated": boolean
```

Sans ce champ, impossible de masquer le bouton "Participer" et d'afficher
à la place "Vous avez déjà participé" comme demandé.

### 3.4. Liste paginée des participations à un défi

**Besoin** : soit
- (a) une route dédiée `GET /community/challenges/{slug}/participations/`
  paginée (mêmes query params `page`/`page_size` que le reste de l'API), soit
- (b) simplement filtrer les posts existants via
  `GET /community/posts/?post_type=challenge_response&challenge={slug}`.

(b) est préféré car il réutilise l'infrastructure de pagination des posts
déjà en place côté frontend — pas besoin d'un nouvel endpoint si le filtre
`challenge` est supporté sur `GET /community/posts/`.

### 3.5. Résultat de défi épinglé (posté par l'admin)

**Aujourd'hui** : rien de prévu pour qu'un admin publie un "résultat" de
défi expiré, visible épinglé au-dessus des participations/posts.

**Besoin** : un moyen de marquer un post comme "résultat épinglé" d'un
défi. Proposition la plus simple, sans nouveau modèle :

```
CommunityPost.is_pinned_result: boolean (default false)
CommunityPost.challenge: <slug du défi concerné>
```

Publié par l'admin via l'admin Django ou une route
`POST /community/challenges/{slug}/publish_result/` (réservée au staff),
qui crée un `CommunityPost` avec `post_type="challenge_response"`,
`is_pinned_result=true`. Le frontend fera simplement : si un post du défi a
`is_pinned_result=true`, l'afficher en premier, épinglé visuellement, dans
la liste des participations / au sommet de la colonne centrale.

---

## 4. Tendances (hashtags) — ✅ faisable 100% côté frontend

Aucun changement backend nécessaire : le frontend calcule les tendances en
scannant les champs `content` des posts déjà récupérés (regex `#\w+`),
compte les occurrences et affiche le top N. Cette section est informative,
pas une demande.

---

## 5. Récapitulatif des changements demandés (ordre de priorité)

| # | Changement | Modèle/Endpoint | Bloquant pour |
|---|---|---|---|
| 1 | Nouvel endpoint réponse à un défi (média+titre+desc) | `POST /community/challenges/{slug}/participate/` | Bouton "Participer" |
| 2 | `post_type: "challenge_response"` + champ `challenge` sur `CommunityPost` | `CommunityPost` | Affichage des participations comme posts, filtre Défis |
| 3 | `has_participated` sur `Challenge` | `Challenge` | Masquer "Participer" si déjà fait |
| 4 | Filtre `?challenge={slug}` sur `GET /community/posts/` | `community/posts/` | Pagination des participations par défi |
| 5 | `is_pinned_result` sur `CommunityPost` + route de publication admin | `CommunityPost` | Résultat de défi épinglé |

Tant que ces points ne sont pas livrés, le frontend :
- affiche le bouton "Participer" pour tout défi actif, sans distinction
  "déjà participé" (point 3 non disponible) ;
- n'affiche pas encore de participations sous les cartes de défis
  (points 2/4 non disponibles) — un état vide explicite est utilisé à la
  place ;
- n'affiche aucun résultat épinglé (point 5 non disponible).

Chaque section concernée du code frontend renvoie vers ce document via un
commentaire `// voir docs/COMMUNAUTE_BACKEND_REQUIREMENTS.md §X.X`.
