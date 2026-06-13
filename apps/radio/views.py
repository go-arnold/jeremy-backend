from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.pagination import SmallPagination
from core.permissions import IsAdminOrReadOnly, IsOwnerOrAdmin

from .models import RadioChat, RadioProgram
from .serializers import RadioChatSerializer, RadioProgramSerializer, RadioProgramWriteSerializer


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


class RadioChatViewSet(ModelViewSet):
    pagination_class = SmallPagination
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return (
            RadioChat.objects.filter(is_deleted=False)
            .select_related("user")
            .order_by("-created_at")[:50]
        )

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


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
@method_decorator(cache_page(60))
def current_program(request):
    """Returns the currently live or most recent program."""
    from django.utils import timezone
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
        program = RadioProgram.objects.filter(
            day_of_week=current_day,
            start_time__lte=current_time,
        ).order_by("-start_time").first()

    if not program:
        return Response({"detail": "No program currently."}, status=status.HTTP_404_NOT_FOUND)
    return Response(RadioProgramSerializer(program).data)
