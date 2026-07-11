from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from .models import Event


@registry.register_document
class EventDocument(Document):
    image_url = fields.KeywordField()

    class Index:
        name = "events"
        settings = {"number_of_shards": 1, "number_of_replicas": 0}

    class Django:
        model = Event
        fields = ["id", "title", "slug", "description", "venue_name"]

    def prepare_image_url(self, instance):
        return instance.image.url if instance.image else None
