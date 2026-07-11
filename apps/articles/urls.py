from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ArticleViewSet, TagViewSet

router = DefaultRouter()
router.register("tags", TagViewSet, basename="tag")
router.register("", ArticleViewSet, basename="article")

urlpatterns = [path("", include(router.urls))]
