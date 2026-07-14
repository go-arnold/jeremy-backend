from allauth.account.signals import email_confirmed
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(email_confirmed)
def mark_user_verified(sender, request, email_address, **kwargs):
    """Keeps User.is_verified in sync with allauth's own EmailAddress.verified.

    The two are separate by design (allauth owns EmailAddress, this project added
    User.is_verified as a convenience field for serializers) — without this, a user who
    successfully confirms their email stays is_verified=False forever.
    """
    user = email_address.user
    if not user.is_verified:
        user.is_verified = True
        user.save(update_fields=["is_verified"])


@receiver(post_save, sender=User)
def award_default_badges_on_signup(sender, instance, created, **kwargs):
    """Badges with threshold_seconds=0 (e.g. 'Nouveau membre') apply to everyone — award them
    immediately at signup rather than waiting for the user's first consumption heartbeat."""
    if created:
        from apps.gamification.services import award_default_badges

        award_default_badges(instance)
