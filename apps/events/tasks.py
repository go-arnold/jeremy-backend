from celery import shared_task


@shared_task(queue="default")
def update_event_statuses() -> None:
    from django.utils import timezone
    from .models import Event

    now = timezone.now()
    # upcoming → live
    Event.objects.filter(status=Event.STATUS_UPCOMING, date__lte=now).update(status=Event.STATUS_LIVE)
    # live → past
    live_events = Event.objects.filter(status=Event.STATUS_LIVE)
    past_ids = [
        e.pk for e in live_events
        if e.end_date and e.end_date < now or (not e.end_date and e.date < now)
    ]
    if past_ids:
        Event.objects.filter(pk__in=past_ids).update(status=Event.STATUS_PAST)
