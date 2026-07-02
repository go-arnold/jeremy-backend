from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from .models import Article


@registry.register_document
class ArticleDocument(Document):
    image_url = fields.KeywordField()

    class Index:
        name = "articles"
        settings = {"number_of_shards": 1, "number_of_replicas": 0}

    class Django:
        model = Article
        fields = ["id", "title", "slug", "excerpt", "content"]

    def prepare_image_url(self, instance):
        return instance.featured_image.url if instance.featured_image else None

    def get_queryset(self, *args, **kwargs):
        # Drafts are private/staff-only content — never let them leak into public search.
        return super().get_queryset(*args, **kwargs).filter(status=Article.STATUS_PUBLISHED)
