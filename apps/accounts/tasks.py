from celery import shared_task


@shared_task(queue="default")
def send_welcome_email(user_id: int) -> None:
    from django.contrib.auth import get_user_model
    from django.core.mail import send_mail

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    send_mail(
        subject="Bienvenue sur Art du Kivu !",
        message=f"Bonjour {user.username},\n\nVotre compte a été créé avec succès.",
        from_email=None,  # uses DEFAULT_FROM_EMAIL
        recipient_list=[user.email],
        fail_silently=True,
    )


@shared_task(queue="default")
def send_password_reset_email(user_id: int, reset_url: str) -> None:
    from django.contrib.auth import get_user_model
    from django.core.mail import send_mail

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    send_mail(
        subject="Réinitialisation de mot de passe",
        message=f"Cliquez ici pour réinitialiser: {reset_url}",
        from_email=None,
        recipient_list=[user.email],
        fail_silently=True,
    )
