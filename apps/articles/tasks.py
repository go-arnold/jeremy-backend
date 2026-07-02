from celery import shared_task


@shared_task(queue="default")
def async_increment_view(article_id: int) -> None:
    from .models import Article

    Article.objects.filter(pk=article_id).update(
        view_count=Article.objects.values_list("view_count", flat=True).get(pk=article_id) + 1
    )


@shared_task(queue="default")
def publish_scheduled_articles() -> None:
    from django.utils import timezone

    from .models import Article

    qs = Article.objects.filter(
        status=Article.STATUS_DRAFT,
        scheduled_at__lte=timezone.now(),
        scheduled_at__isnull=False,
    )
    for article in qs:
        article.status = Article.STATUS_PUBLISHED
        article.published_at = article.scheduled_at
    Article.objects.bulk_update(qs, ["status", "published_at"])
