from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from .models import PodcastEpisode, PodcastSeries


@registry.register_document
class PodcastSeriesDocument(Document):
    cover_url = fields.KeywordField()

    class Index:
        name = "podcast_series"
        settings = {"number_of_shards": 1, "number_of_replicas": 0}

    class Django:
        model = PodcastSeries
        fields = ["id", "title", "slug", "description"]

    def prepare_cover_url(self, instance):
        return instance.cover.url if instance.cover else None


@registry.register_document
class PodcastEpisodeDocument(Document):
    cover_url = fields.KeywordField()

    class Index:
        name = "podcast_episodes"
        settings = {"number_of_shards": 1, "number_of_replicas": 0}

    class Django:
        model = PodcastEpisode
        fields = ["id", "title", "slug", "description"]

    def prepare_cover_url(self, instance):
        return instance.cover.url if instance.cover else None
