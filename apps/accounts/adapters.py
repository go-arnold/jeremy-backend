import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter, get_adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from django.conf import settings

logger = logging.getLogger(__name__)


class LoggingGoogleOAuth2Adapter(GoogleOAuth2Adapter):
    """Identical to allauth's GoogleOAuth2Adapter, except it logs Google's actual response
    (status + body) before raising — allauth's own `_fetch_user_info` swallows both into a
    single generic "Request to user info failed" message, which makes real failures (wrong
    token type, insufficient scope, expired token, ...) indistinguishable from the logs alone.
    """

    def _fetch_user_info(self, access_token):
        headers = {"Authorization": f"Bearer {access_token}"}
        with get_adapter().get_requests_session() as sess:
            resp = sess.get(self.identity_url, headers=headers)
            if not resp.ok:
                logger.error(
                    "Google userinfo request failed: status=%s body=%s",
                    resp.status_code,
                    resp.text[:500],
                )
                raise OAuth2Error("Request to user info failed")
            return resp.json()


class AccountAdapter(DefaultAccountAdapter):
    def send_mail(self, template_prefix, email, context):
        from .tasks import send_email_async

        msg = self.render_mail(template_prefix, email, context)

        html_body = None
        for content, mimetype in getattr(msg, "alternatives", []):
            if mimetype == "text/html":
                html_body = content
                break

        logger.info(f"Sending email asynchronously to {msg.to}")
        send_email_async.delay(
            subject=msg.subject,
            body=msg.body,
            from_email=msg.from_email,
            to=msg.to,
            html_body=html_body,
        )

    def get_email_confirmation_url(self, request, emailconfirmation):
        logger.info(f"Generating email confirmation URL for {emailconfirmation.key}")
        return f"{settings.FRONTEND_URL}/verify-email?key={emailconfirmation.key}"

    def send_password_reset_mail(self, user, email, extra_email_context):
        logger.info(f"Sending password reset email to {email}")
        from allauth.account.utils import user_pk_to_url_str
        from django.contrib.auth.tokens import default_token_generator

        uid = user_pk_to_url_str(user)
        token = default_token_generator.make_token(user)
        ctx = dict(extra_email_context) if extra_email_context else {}
        # Override the URL allauth would put in the email (its default points to
        # reverse('account_reset_password_from_key')).
        ctx["password_reset_url"] = f"{settings.FRONTEND_URL}/password-reset-confirm/{uid}/{token}/"
        super().send_password_reset_mail(user, email, ctx)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        logger.info(f"Checking if signup is open for social login: {sociallogin}")
        return True

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        email = data.get("email", "")
        base_username = getattr(user, "username", None) or (email.split("@")[0][:30] if email else "user")
        user.username = self._unique_username(base_username)
        logger.info(f"Populated user: {user}")
        return user

    def _unique_username(self, base: str) -> str:
        """`username` is unique on our User model, but allauth derives it from the email's
        local part with no collision check — two different people (or a Google login
        colliding with an existing manual signup) sharing the same local part before the '@'
        would otherwise crash with an uncaught IntegrityError during the OAuth callback."""
        from .models import User

        base = (base or "user")[:30]
        if not User.objects.filter(username=base).exists():
            return base
        suffix = 2
        while True:
            candidate = f"{base[: 30 - len(str(suffix))]}{suffix}"
            if not User.objects.filter(username=candidate).exists():
                return candidate
            suffix += 1
