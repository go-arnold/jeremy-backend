import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings

logger = logging.getLogger(__name__)


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
        # Ensure username is always set (our model requires it)
        if not getattr(user, "username", None):
            email = data.get("email", "")
            user.username = email.split("@")[0][:30] if email else ""
        logger.info(f"Populated user: {user}")
        return user
