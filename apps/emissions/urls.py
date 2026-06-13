from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EmissionViewSet

router = DefaultRouter()
router.register("", EmissionViewSet, basename="emission")

urlpatterns = [path("", include(router.urls))]
