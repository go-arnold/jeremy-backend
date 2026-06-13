from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.pagination import StandardPagination
from core.permissions import IsAdminOrReadOnly

from .models import WebTVVideo
from .serializers import VideoDetailSerializer, VideoListSerializer, VideoWriteSerializer
from .tasks import async_increment_view


class WebTVVideoViewSet(ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = StandardPagination
    search_fields = ["title", "description"]
    ordering_fields = ["published_at", "view_count"]
    lookup_field = "slug"

    def get_queryset(self):
        qs = WebTVVideo.objects.prefetch_related("artists")
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs.order_by("-published_at")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return VideoWriteSerializer
        if self.action == "retrieve":
            return VideoDetailSerializer
        return VideoListSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        async_increment_view.delay(instance.pk)
        return Response(VideoDetailSerializer(instance).data)

    @method_decorator(cache_page(60 * 15))
    @action(detail=False, methods=["get"])
    def premiers(self, request):
        qs = WebTVVideo.objects.filter(is_premier=True).order_by("-published_at")[:5]
        return Response(VideoListSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"])
    def view(self, request, slug=None):
        video = self.get_object()
        async_increment_view.delay(video.pk)
        return Response({"detail": "View counted."})
