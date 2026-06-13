from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.pagination import StandardPagination
from core.permissions import IsAdminOrReadOnly

from .models import City, Event, EventRegistration
from .serializers import (
    CitySerializer,
    EventDetailSerializer,
    EventListSerializer,
    EventWriteSerializer,
)


class EventViewSet(ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = StandardPagination
    search_fields = ["title", "description", "venue_name"]
    ordering_fields = ["date", "created_at"]
    lookup_field = "slug"

    def get_queryset(self):
        qs = (
            Event.objects.select_related("city")
            .prefetch_related("artists")
            .order_by("date")
        )
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

    @method_decorator(cache_page(60 * 30))
    @action(detail=False, methods=["get"])
    def featured(self, request):
        event = Event.objects.filter(is_featured=True, status=Event.STATUS_UPCOMING).first()
        if not event:
            return Response({"detail": "No featured event"}, status=status.HTTP_404_NOT_FOUND)
        return Response(EventDetailSerializer(event).data)

    @method_decorator(cache_page(60 * 60))
    @action(detail=False, methods=["get"])
    def cities(self, request):
        return Response(CitySerializer(City.objects.all(), many=True).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def register(self, request, slug=None):
        event = self.get_object()
        if event.max_capacity and event.current_registrations >= event.max_capacity:
            return Response({"detail": "Event is full."}, status=status.HTTP_400_BAD_REQUEST)
        reg, created = EventRegistration.objects.get_or_create(event=event, user=request.user)
        if not created:
            return Response({"detail": "Already registered."}, status=status.HTTP_400_BAD_REQUEST)
        Event.objects.filter(pk=event.pk).update(current_registrations=event.current_registrations + 1)
        return Response({"detail": "Registered successfully."}, status=status.HTTP_201_CREATED)
