from allauth.account.signals import email_confirmed
from django.dispatch import receiver


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
