from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from .models import Artist


@registry.register_document
class ArtistDocument(Document):
    photo_url = fields.KeywordField()
    genres = fields.TextField()

    class Index:
        name = "artists"
        settings = {"number_of_shards": 1, "number_of_replicas": 0}

    class Django:
        model = Artist
        fields = ["id", "name", "slug", "bio", "city"]

    def prepare_photo_url(self, instance):
        return instance.photo.url if instance.photo else None

    def prepare_genres(self, instance):
        return list(instance.genres.values_list("name", flat=True))
