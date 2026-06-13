from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ReleaseViewSet

router = DefaultRouter()
router.register("", ReleaseViewSet, basename="release")

urlpatterns = [path("", include(router.urls))]
