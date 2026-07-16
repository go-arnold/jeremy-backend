from django.urls import path

from .views import mediamtx_webhook

urlpatterns = [
    path("mediamtx-webhook/", mediamtx_webhook, name="mediamtx-webhook"),
]
