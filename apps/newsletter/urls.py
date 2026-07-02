from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ConfirmSubscriptionView,
    NewsletterViewSet,
    SubscriberViewSet,
    SubscribeView,
    UnsubscribeView,
)

router = DefaultRouter()
router.register("campaigns", NewsletterViewSet, basename="newsletter-campaign")
router.register("subscribers", SubscriberViewSet, basename="newsletter-subscriber")

urlpatterns = [
    path("subscribe/", SubscribeView.as_view(), name="newsletter-subscribe"),
    path("confirm/<uuid:token>/", ConfirmSubscriptionView.as_view(), name="newsletter-confirm"),
    path("unsubscribe/<uuid:token>/", UnsubscribeView.as_view(), name="newsletter-unsubscribe"),
    path("", include(router.urls)),
]
