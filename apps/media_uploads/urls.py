from django.urls import path

from .views import upload_signature

urlpatterns = [
    path("upload-signature/", upload_signature, name="media-upload-signature"),
]
