from celery import shared_task


@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue="default")
def send_email_async(self, subject, body, from_email, to, html_body=None):
    """
    Generic async email task used by AccountAdapter for all allauth emails
    (email confirmation, password reset, etc.).

    Template rendering happens synchronously in the request cycle (fast — no I/O).
    Only the SMTP roundtrip is deferred here.
    """
    from django.core.mail import EmailMultiAlternatives

    try:
        msg = EmailMultiAlternatives(subject, body, from_email, to)
        if html_body:
            msg.attach_alternative(html_body, "text/html")
        msg.send()
    except Exception as exc:
        raise self.retry(exc=exc)
