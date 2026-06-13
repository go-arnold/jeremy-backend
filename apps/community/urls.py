from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChallengeViewSet, CommunityPostViewSet, PollViewSet

router = DefaultRouter()
router.register("posts", CommunityPostViewSet, basename="community-post")
router.register("challenges", ChallengeViewSet, basename="challenge")
router.register("polls", PollViewSet, basename="poll")

urlpatterns = [path("", include(router.urls))]
