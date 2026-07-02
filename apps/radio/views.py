from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.pagination import SmallPagination
from core.permissions import IsAdminOrReadOnly, IsOwnerOrAdmin
from core.serializers import BulkDeleteSerializer

from . import services
from .models import RadioChat, RadioProgram
from .serializers import (
    RadioChatSerializer,
    RadioProgramBulkCreateSerializer,
    RadioProgramBulkUpdateSerializer,
    RadioProgramSerializer,
    RadioProgramWriteSerializer,
)


@extend_schema(tags=["Radio"])
class RadioProgramViewSet(ModelViewSet):
    queryset = RadioProgram.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "id"

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return RadioProgramWriteSerializer
        return RadioProgramSerializer

    def get_queryset(self):
        qs = RadioProgram.objects.all().order_by("day_of_week", "start_time")
        day = self.request.query_params.get("day")
        if day is not None:
            qs = qs.filter(day_of_week=day)
        return qs

    def perform_create(self, serializer):
        serializer.instance = services.create_program(dict(serializer.validated_data))

    def perform_update(self, serializer):
        serializer.instance = services.update_program(serializer.instance, dict(serializer.validated_data))

    def perform_destroy(self, instance):
        services.delete_program(instance)

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_create(self, request):
        ser = RadioProgramBulkCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        created = services.bulk_create_programs(ser.validated_data["items"])
        return Response(
            {"created": len(created), "items": RadioProgramSerializer(created, many=True).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_update(self, request):
        ser = RadioProgramBulkUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_update_programs(ser.validated_data["items"])
        return Response({"updated": count})

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_delete(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_delete_programs(ser.validated_data["ids"])
        return Response({"deleted": count})


@extend_schema(tags=["Radio"])
class RadioChatViewSet(ModelViewSet):
    pagination_class = SmallPagination
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return RadioChat.objects.filter(is_deleted=False).select_related("user").order_by("-created_at")[:50]

    def get_serializer_class(self):
        return RadioChatSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        if self.action == "destroy":
            return [IsOwnerOrAdmin()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])


@extend_schema(tags=["Radio"])
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
@method_decorator(cache_page(60))
def current_program(request):
    now = timezone.now()
    current_day = now.weekday()
    current_time = now.time()

    program = RadioProgram.objects.filter(
        status=RadioProgram.STATUS_LIVE,
        day_of_week=current_day,
        start_time__lte=current_time,
        end_time__gte=current_time,
    ).first()

    if not program:
        program = (
            RadioProgram.objects.filter(
                day_of_week=current_day,
                start_time__lte=current_time,
            )
            .order_by("-start_time")
            .first()
        )

    if not program:
        return Response({"detail": "No program currently."}, status=status.HTTP_404_NOT_FOUND)
    return Response(RadioProgramSerializer(program).data)
