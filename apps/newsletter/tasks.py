from celery import shared_task
from django.conf import settings
from django.utils import timezone


@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue="default")
def send_confirmation_email(self, subscriber_id):
    from django.core.mail import EmailMultiAlternatives

    from .models import Subscriber

    try:
        subscriber = Subscriber.objects.get(pk=subscriber_id)
    except Subscriber.DoesNotExist:
        return

    confirm_url = f"{settings.FRONTEND_URL}/newsletter/confirm/{subscriber.confirm_token}/"
    try:
        msg = EmailMultiAlternatives(
            "Confirmez votre abonnement à la newsletter Art du Kivu",
            f"Cliquez sur ce lien pour confirmer votre abonnement : {confirm_url}",
            settings.DEFAULT_FROM_EMAIL,
            [subscriber.email],
        )
        msg.send()
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=300, queue="default")
def send_newsletter_campaign(self, newsletter_id):
    from django.core.mail import EmailMultiAlternatives

    from .models import Newsletter, Subscriber

    try:
        newsletter = Newsletter.objects.get(pk=newsletter_id)
    except Newsletter.DoesNotExist:
        return

    emails = list(
        Subscriber.objects.filter(is_confirmed=True, is_active=True).values_list("email", flat=True)
    )
    batch_size = 50
    try:
        # BCC batching keeps this to len(emails)/50 SMTP round-trips instead of
        # one per recipient. Not resumable: a mid-run retry re-sends batches
        # already delivered before the failure.
        for i in range(0, len(emails), batch_size):
            batch = emails[i : i + batch_size]
            msg = EmailMultiAlternatives(
                newsletter.subject,
                "",
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_FROM_EMAIL],
                bcc=batch,
            )
            msg.attach_alternative(newsletter.body_html, "text/html")
            msg.send()
    except Exception as exc:
        raise self.retry(exc=exc)

    newsletter.status = Newsletter.STATUS_SENT
    newsletter.sent_at = timezone.now()
    newsletter.save(update_fields=["status", "sent_at"])
