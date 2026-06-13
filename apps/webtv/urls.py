from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import WebTVVideoViewSet

router = DefaultRouter()
router.register("videos", WebTVVideoViewSet, basename="webtv-video")

urlpatterns = [path("", include(router.urls))]
