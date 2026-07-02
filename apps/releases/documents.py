from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from .models import MusicRelease


@registry.register_document
class MusicReleaseDocument(Document):
    cover_url = fields.KeywordField()
    artist_name = fields.TextField()

    class Index:
        name = "releases"
        settings = {"number_of_shards": 1, "number_of_replicas": 0}

    class Django:
        model = MusicRelease
        fields = ["id", "title", "slug", "description"]

    def prepare_cover_url(self, instance):
        return instance.cover.url if instance.cover else None

    def prepare_artist_name(self, instance):
        return instance.artist.name
