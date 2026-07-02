from celery import shared_task


@shared_task(queue="default")
def cleanup_old_chat() -> None:
    from datetime import timedelta

    from django.utils import timezone

    from .models import RadioChat

    cutoff = timezone.now() - timedelta(days=7)
    deleted, _ = RadioChat.objects.filter(created_at__lt=cutoff).delete()
    return deleted


@shared_task(queue="default")
def update_program_statuses() -> None:
    from django.utils import timezone

    from .models import RadioProgram

    now = timezone.now()
    current_day = now.weekday()
    current_time = now.time()

    RadioProgram.objects.filter(
        day_of_week=current_day,
        start_time__lte=current_time,
        end_time__gte=current_time,
        status=RadioProgram.STATUS_UPCOMING,
    ).update(status=RadioProgram.STATUS_LIVE)

    RadioProgram.objects.filter(
        status=RadioProgram.STATUS_LIVE,
    ).exclude(
        day_of_week=current_day,
        start_time__lte=current_time,
        end_time__gte=current_time,
    ).update(status=RadioProgram.STATUS_ENDED)
