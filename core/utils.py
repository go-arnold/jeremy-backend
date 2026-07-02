import re

from django.core.cache import cache
from django.utils.text import slugify


def make_slug(text: str, model_class, field: str = "slug") -> str:
    base = slugify(text)
    slug = base
    counter = 1
    while model_class.objects.filter(**{field: slug}).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def invalidate_cache_pattern(pattern: str) -> None:
    try:
        cache.delete_pattern(f"*{pattern}*")
    except AttributeError:
        # delete_pattern is Redis-only; LocMemCache (local dev) lacks it, so this is a no-op there.
        pass


def invalidate_resource_cache(resource: str) -> None:
    invalidate_cache_pattern(f":{resource}:")


def gen_unique_slug(text: str, model_class, used_slugs: set, field: str = "slug") -> str:
    base = slugify(text)
    slug = base
    counter = 1
    while model_class.objects.filter(**{field: slug}).exists() or slug in used_slugs:
        slug = f"{base}-{counter}"
        counter += 1
    used_slugs.add(slug)
    return slug


def read_time_minutes(text: str) -> int:
    word_count = len(re.findall(r"\w+", text))
    return max(1, round(word_count / 200))
