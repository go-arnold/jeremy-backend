from celery import shared_task


@shared_task(queue="default")
def update_emission_statuses() -> None:
    from django.utils import timezone
    from datetime import timedelta
    from .models import Emission

    now = timezone.now()
    # scheduled → live (within 5 minutes of scheduled time)
    window = now + timedelta(minutes=5)
    Emission.objects.filter(
        status=Emission.STATUS_SCHEDULED,
        scheduled_at__lte=window,
    ).update(status=Emission.STATUS_LIVE)
    # live → recorded (after scheduled + duration)
    live_emissions = Emission.objects.filter(status=Emission.STATUS_LIVE)
    past_ids = [
        e.pk for e in live_emissions
        if e.scheduled_at and (e.scheduled_at + timedelta(minutes=e.duration_minutes)) < now
    ]
    if past_ids:
        Emission.objects.filter(pk__in=past_ids).update(status=Emission.STATUS_RECORDED)
