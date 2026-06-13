import re

from django.core.cache import cache
from django.utils.text import slugify


def make_slug(text: str, model_class, field: str = "slug") -> str:
    """Generate a unique slug for a model instance."""
    base = slugify(text)
    slug = base
    counter = 1
    while model_class.objects.filter(**{field: slug}).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def invalidate_cache_pattern(pattern: str) -> None:
    """Delete all cache keys matching a pattern (requires Redis backend)."""
    try:
        cache.delete_pattern(f"*{pattern}*")
    except AttributeError:
        # LocMemCache doesn't support delete_pattern; clear all in dev
        pass


def invalidate_resource_cache(resource: str) -> None:
    """Invalidate all cache keys for a given resource (e.g. 'artists')."""
    invalidate_cache_pattern(f":{resource}:")


def read_time_minutes(text: str) -> int:
    """Estimate reading time in minutes (200 words/min)."""
    word_count = len(re.findall(r"\w+", text))
    return max(1, round(word_count / 200))
