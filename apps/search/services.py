from elasticsearch.dsl import Q, Search

INDEX_TYPE_MAP = {
    "artists": "artist",
    "articles": "article",
    "events": "event",
    "podcast_series": "podcast_series",
    "podcast_episodes": "podcast_episode",
    "releases": "release",
    "webtv_videos": "webtv_video",
    "community_posts": "community_post",
}

SEARCH_FIELDS = [
    "name^3",
    "title^3",
    "artist_name^2",
    "bio",
    "description",
    "excerpt",
    "content",
    "city",
    "venue_name",
    "genres",
]

MAX_PAGE_SIZE = 50


def _display_title(data: dict, content_type: str) -> str:
    if content_type == "community_post":
        content = data.get("content") or ""
        return f"{content[:80]}…" if len(content) > 80 else content
    return data.get("title") or data.get("name") or ""


def _image_url(data: dict):
    return (
        data.get("photo_url") or data.get("image_url") or data.get("cover_url") or data.get("thumbnail_url")
    )


def unified_search(query: str, content_type: str = None, page: int = 1, page_size: int = 20) -> dict:
    page = max(page, 1)
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
    indices = [content_type] if content_type in INDEX_TYPE_MAP else list(INDEX_TYPE_MAP.keys())

    # Only fetch the fields the response actually renders — search-only fields
    # like "description"/"bio" match queries but are never returned.
    source_fields = ["id", "slug", "title", "name", "artist_name", "content"]
    source_fields += ["photo_url", "image_url", "cover_url", "thumbnail_url"]
    search = (
        Search(using="default", index=indices)
        .query(Q("multi_match", query=query, fields=SEARCH_FIELDS, fuzziness="AUTO"))
        .source(includes=source_fields)
        .extra(from_=(page - 1) * page_size, size=page_size, track_total_hits=True)
    )
    response = search.execute()

    results = []
    for hit in response:
        content_type_name = INDEX_TYPE_MAP.get(hit.meta.index, hit.meta.index)
        data = hit.to_dict()
        results.append(
            {
                "type": content_type_name,
                "id": data.get("id"),
                "slug": data.get("slug"),
                "title": _display_title(data, content_type_name),
                "image_url": _image_url(data),
                "score": hit.meta.score,
            }
        )

    return {
        "count": response.hits.total.value,
        "page": page,
        "page_size": page_size,
        "results": results,
    }
