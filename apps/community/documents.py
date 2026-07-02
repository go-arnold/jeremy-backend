from django_elasticsearch_dsl import Document
from django_elasticsearch_dsl.registries import registry

from .models import CommunityPost


@registry.register_document
class CommunityPostDocument(Document):
    class Index:
        name = "community_posts"
        settings = {"number_of_shards": 1, "number_of_replicas": 0}

    class Django:
        model = CommunityPost
        fields = ["id", "content", "post_type"]
