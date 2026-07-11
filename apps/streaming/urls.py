from django.urls import path

from .views import cloudflare_webhook

urlpatterns = [
    path("webhook/", cloudflare_webhook, name="cloudflare-webhook"),
]
