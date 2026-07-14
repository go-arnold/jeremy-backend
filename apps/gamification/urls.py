from django.urls import path

from .views import badge_catalog, my_media_ranking, record_consumption, user_badges

urlpatterns = [
    path("badges/", badge_catalog, name="gamification-badge-catalog"),
    path("users/<int:user_id>/badges/", user_badges, name="gamification-user-badges"),
    path("consumption/", record_consumption, name="gamification-record-consumption"),
    path("media-ranking/", my_media_ranking, name="gamification-media-ranking"),
]
