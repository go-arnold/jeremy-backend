from celery import shared_task


@shared_task(queue="default")
def async_increment_view(video_id: int) -> None:
    from .models import WebTVVideo
    WebTVVideo.objects.filter(pk=video_id).update(
        view_count=WebTVVideo.objects.values_list("view_count", flat=True).get(pk=video_id) + 1
    )
