from celery import shared_task
from django.db.models import F


@shared_task(queue="default")
def async_increment_view(video_id: int) -> None:
    from .models import WebTVVideo

    WebTVVideo.objects.filter(pk=video_id).update(view_count=F("view_count") + 1)
