from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.pagination import StandardPagination
from core.permissions import IsAdminOrReadOnly
from core.serializers import BulkDeleteSerializer
from core.throttling import UploadThrottleMixin

from . import services
from .models import City, Event
from .serializers import (
    CitySerializer,
    EventBulkCreateSerializer,
    EventBulkUpdateSerializer,
    EventDetailSerializer,
    EventListSerializer,
    EventWriteSerializer,
)


@extend_schema(tags=["Events"])
class EventViewSet(UploadThrottleMixin, ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = StandardPagination
    search_fields = ["title", "description", "venue_name"]
    ordering_fields = ["date", "created_at"]
    lookup_field = "slug"

    def get_queryset(self):
        qs = Event.objects.select_related("city").prefetch_related("artists").order_by("date")
        city = self.request.query_params.get("city")
        if city:
            qs = qs.filter(city__slug=city)
        event_status = self.request.query_params.get("status")
        if event_status:
            qs = qs.filter(status=event_status)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return EventWriteSerializer
        if self.action == "retrieve":
            return EventDetailSerializer
        return EventListSerializer

    def perform_create(self, serializer):
        serializer.instance = services.create_event(dict(serializer.validated_data))

    def perform_update(self, serializer):
        serializer.instance = services.update_event(serializer.instance, dict(serializer.validated_data))

    def perform_destroy(self, instance):
        services.delete_event(instance)

    @method_decorator(cache_page(60 * 30))
    @action(detail=False, methods=["get"])
    def featured(self, request):
        event = Event.objects.filter(is_featured=True, status=Event.STATUS_UPCOMING).first()
        if not event:
            return Response({"detail": "Aucun événement à la une."}, status=status.HTTP_404_NOT_FOUND)
        return Response(EventDetailSerializer(event).data)

    @method_decorator(cache_page(60 * 60))
    @action(detail=False, methods=["get"])
    def cities(self, request):
        return Response(CitySerializer(City.objects.all(), many=True).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def register(self, request, slug=None):
        event = self.get_object()
        result = services.register_for_event(event, request.user)
        if result.get("error") == "full":
            return Response(
                {"detail": "Cet événement est complet.", "code": "full"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if result.get("error") == "already_registered":
            return Response(
                {"detail": "Vous êtes déjà inscrit à cet événement.", "code": "already_registered"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Inscription réussie."}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_create(self, request):
        ser = EventBulkCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        created = services.bulk_create_events(ser.validated_data["items"])
        return Response(
            {"created": len(created), "items": EventListSerializer(created, many=True).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_update(self, request):
        ser = EventBulkUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_update_events(ser.validated_data["items"])
        return Response({"updated": count})

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_delete(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_delete_events(ser.validated_data["ids"])
        return Response({"deleted": count})
