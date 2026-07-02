from django.db import transaction
from django.utils import timezone

from .models import Newsletter, Subscriber


@transaction.atomic
def subscribe(email: str) -> dict:
    subscriber, created = Subscriber.objects.get_or_create(email=email)
    if not created and subscriber.is_confirmed and subscriber.is_active:
        return {"status": "already_subscribed"}
    if not subscriber.is_active:
        subscriber.is_active = True
        subscriber.save(update_fields=["is_active"])

    from .tasks import send_confirmation_email

    send_confirmation_email.delay(subscriber.id)
    return {"status": "confirmation_sent"}


def confirm_subscription(token) -> dict:
    try:
        subscriber = Subscriber.objects.get(confirm_token=token)
    except (Subscriber.DoesNotExist, ValueError, TypeError):
        return {"error": "invalid_token"}
    if not subscriber.is_confirmed:
        subscriber.is_confirmed = True
        subscriber.confirmed_at = timezone.now()
        subscriber.save(update_fields=["is_confirmed", "confirmed_at"])
    return {"status": "confirmed"}


def unsubscribe(token) -> dict:
    try:
        subscriber = Subscriber.objects.get(unsubscribe_token=token)
    except (Subscriber.DoesNotExist, ValueError, TypeError):
        return {"error": "invalid_token"}
    subscriber.is_active = False
    subscriber.unsubscribed_at = timezone.now()
    subscriber.save(update_fields=["is_active", "unsubscribed_at"])
    return {"status": "unsubscribed"}


@transaction.atomic
def create_newsletter(validated_data: dict, admin) -> Newsletter:
    return Newsletter.objects.create(created_by=admin, **validated_data)


@transaction.atomic
def send_newsletter(newsletter: Newsletter) -> dict:
    if newsletter.status != Newsletter.STATUS_DRAFT:
        return {"error": "already_sent"}
    recipient_count = Subscriber.objects.filter(is_confirmed=True, is_active=True).count()
    newsletter.status = Newsletter.STATUS_SENDING
    newsletter.recipient_count = recipient_count
    newsletter.save(update_fields=["status", "recipient_count"])

    from .tasks import send_newsletter_campaign

    send_newsletter_campaign.delay(newsletter.id)
    return {"status": "sending", "recipient_count": recipient_count}
