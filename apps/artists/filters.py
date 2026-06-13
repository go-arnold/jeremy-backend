import django_filters

from .models import Artist


class ArtistFilter(django_filters.FilterSet):
    genre = django_filters.CharFilter(field_name="genres__slug", lookup_expr="iexact")
    city = django_filters.CharFilter(lookup_expr="icontains")
    is_featured = django_filters.BooleanFilter()

    class Meta:
        model = Artist
        fields = ["genre", "city", "is_featured"]
