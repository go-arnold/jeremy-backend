from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PodcastEpisodeViewSet, PodcastSeriesViewSet

router = DefaultRouter()
router.register("episodes", PodcastEpisodeViewSet, basename="episode")
router.register("", PodcastSeriesViewSet, basename="podcast")

urlpatterns = [path("", include(router.urls))]
