from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


@api_view(["GET"])
@permission_classes([AllowAny])
@cache_page(60 * 15)
def home_view(request):
    """Aggregated homepage payload — cached 15 minutes."""
    from apps.artists.models import Artist
    from apps.articles.models import Article
    from apps.releases.models import MusicRelease
    from apps.artists.serializers import ArtistListSerializer
    from apps.articles.serializers import ArticleListSerializer
    from apps.releases.serializers import ReleaseListSerializer

    featured_artists = (
        Artist.objects.filter(is_featured=True)
        .prefetch_related("genres")
        .only("id", "name", "slug", "city", "photo", "is_featured")[:8]
    )
    latest_news = (
        Article.objects.filter(status="published")
        .select_related("author", "category")
        .only("id", "title", "slug", "excerpt", "featured_image", "category", "author", "published_at")
        .order_by("-published_at")[:6]
    )
    top_releases = (
        MusicRelease.objects.select_related("artist")
        .only("id", "title", "slug", "cover", "artist__name", "release_date", "format")
        .order_by("-release_date")[:10]
    )

    return Response({
        "featured_artists": ArtistListSerializer(featured_artists, many=True).data,
        "latest_news": ArticleListSerializer(latest_news, many=True).data,
        "top_releases": ReleaseListSerializer(top_releases, many=True).data,
    })


urlpatterns = [
    path("", home_view, name="home"),
]
