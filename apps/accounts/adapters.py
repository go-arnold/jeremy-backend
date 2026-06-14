from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings


class AccountAdapter(DefaultAccountAdapter):
    """
    Overrides allauth's default email URLs so that confirmation and password-reset
    links in outgoing emails point directly to the decoupled frontend, not to
    Django's HTML views.
    """

    def get_email_confirmation_url(self, request, emailconfirmation):
        """Email confirmation link → frontend /verify-email?key=<key>."""
        return f"{settings.FRONTEND_URL}/verify-email?key={emailconfirmation.key}"

    def send_password_reset_mail(self, user, email, extra_email_context):
        """
        Inject a frontend password_reset_url into the template context so the
        email contains a link to the SPA instead of the backend /accounts/ URL.
        """
        from allauth.account.utils import user_pk_to_url_str
        from django.contrib.auth.tokens import default_token_generator

        uid = user_pk_to_url_str(user)
        token = default_token_generator.make_token(user)
        ctx = dict(extra_email_context) if extra_email_context else {}
        # Override the URL allauth would put in the email (its default points to
        # reverse('account_reset_password_from_key')).
        ctx["password_reset_url"] = (
            f"{settings.FRONTEND_URL}/password-reset-confirm/{uid}/{token}/"
        )
        super().send_password_reset_mail(user, email, ctx)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        return True

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        # Ensure username is always set (our model requires it)
        if not getattr(user, "username", None):
            email = data.get("email", "")
            user.username = email.split("@")[0][:30] if email else ""
        return user
