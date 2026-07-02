from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from .models import WebTVVideo


@registry.register_document
class WebTVVideoDocument(Document):
    thumbnail_url = fields.KeywordField()

    class Index:
        name = "webtv_videos"
        settings = {"number_of_shards": 1, "number_of_replicas": 0}

    class Django:
        model = WebTVVideo
        fields = ["id", "title", "slug", "description"]

    def prepare_thumbnail_url(self, instance):
        return instance.thumbnail.url if instance.thumbnail else None
