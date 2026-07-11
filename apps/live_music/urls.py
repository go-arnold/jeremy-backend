from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MusicLiveSessionViewSet, MusicLiveSlotViewSet

router = DefaultRouter()
router.register("sessions", MusicLiveSessionViewSet, basename="live-music-session")
router.register("programme", MusicLiveSlotViewSet, basename="live-music-slot")

urlpatterns = [path("", include(router.urls))]
