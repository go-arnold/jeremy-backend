from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.pagination import StandardPagination
from core.permissions import IsOwnerOrAdmin
from core.serializers import BulkDeleteSerializer

from . import services
from .models import Challenge, CommunityPost, Poll
from .serializers import (
    ChallengeBulkCreateSerializer,
    ChallengeBulkUpdateSerializer,
    ChallengeSerializer,
    CommunityPostSerializer,
    CommunityPostWriteSerializer,
    PollSerializer,
    PollWriteSerializer,
)


class CommunityPostViewSet(ModelViewSet):
    pagination_class = StandardPagination
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        qs = CommunityPost.objects.select_related("author")
        post_type = self.request.query_params.get("type")
        if post_type:
            qs = qs.filter(post_type=post_type)
        return qs.order_by("-created_at")

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        if self.action == "destroy":
            return [IsOwnerOrAdmin()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.action == "create":
            return CommunityPostWriteSerializer
        return CommunityPostSerializer

    def perform_create(self, serializer):
        serializer.instance = services.create_post(dict(serializer.validated_data), self.request.user)

    def perform_destroy(self, instance):
        services.delete_post(instance)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        post = self.get_object()
        result = services.toggle_post_like(post, request.user)
        code = status.HTTP_201_CREATED if result["action"] == "liked" else status.HTTP_200_OK
        return Response(result, status=code)

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_delete(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_delete_posts(ser.validated_data["ids"])
        return Response({"deleted": count})


class ChallengeViewSet(ModelViewSet):
    pagination_class = StandardPagination
    lookup_field = "slug"

    def get_queryset(self):
        return Challenge.objects.filter(is_active=True)

    def get_serializer_class(self):
        return ChallengeSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.instance = services.create_challenge(dict(serializer.validated_data))

    def perform_update(self, serializer):
        serializer.instance = services.update_challenge(serializer.instance, dict(serializer.validated_data))

    def perform_destroy(self, instance):
        services.delete_challenge(instance)

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_create(self, request):
        ser = ChallengeBulkCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        created = services.bulk_create_challenges(ser.validated_data["items"])
        return Response(
            {"created": len(created), "items": ChallengeSerializer(created, many=True).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_update(self, request):
        ser = ChallengeBulkUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_update_challenges(ser.validated_data["items"])
        return Response({"updated": count})

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_delete(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_delete_challenges(ser.validated_data["ids"])
        return Response({"deleted": count})


class PollViewSet(ModelViewSet):
    pagination_class = StandardPagination

    def get_queryset(self):
        return Poll.objects.filter(is_active=True).prefetch_related("options")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return PollWriteSerializer
        return PollSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        poll = services.create_poll(dict(serializer.validated_data))
        serializer.instance = poll

    def perform_update(self, serializer):
        serializer.instance = services.update_poll(serializer.instance, dict(serializer.validated_data))

    def perform_destroy(self, instance):
        services.delete_poll(instance)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            PollSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_delete(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_delete_polls(ser.validated_data["ids"])
        return Response({"deleted": count})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def vote(self, request, pk=None):
        poll = self.get_object()
        option_id = request.data.get("option_id")
        if not option_id:
            return Response({"detail": "option_id required"}, status=status.HTTP_400_BAD_REQUEST)
        result = services.vote_poll(poll, request.user, option_id)
        if result.get("error") == "invalid_option":
            return Response({"detail": "Invalid option."}, status=status.HTTP_400_BAD_REQUEST)
        if result.get("error") == "already_voted":
            return Response({"detail": "Already voted."}, status=status.HTTP_400_BAD_REQUEST)
        poll.refresh_from_db()
        return Response(PollSerializer(poll).data)
