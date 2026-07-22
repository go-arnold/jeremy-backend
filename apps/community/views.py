from django.db.models import Count, Q
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.engagement.mixins import EngagementActionsMixin
from core.pagination import StandardPagination
from core.permissions import IsOwnerOrAdmin
from core.schema_examples import MEDIA_ITEM_EXAMPLE
from core.serializers import BulkDeleteSerializer
from core.throttling import UploadThrottleMixin

from . import services
from .models import Challenge, CommunityPost, Poll
from .serializers import (
    ChallengeBulkCreateSerializer,
    ChallengeBulkUpdateSerializer,
    ChallengeParticipationSerializer,
    ChallengeSerializer,
    CommunityPostSerializer,
    CommunityPostWriteSerializer,
    PollSerializer,
    PollWriteSerializer,
    TalentSubmissionSerializer,
)


@extend_schema(tags=["Community"])
@extend_schema_view(
    create=extend_schema(
        examples=[
            OpenApiExample(
                "Nouveau post",
                value={
                    "title": "Mon nouveau titre",
                    "content": "Regardez ce que j'ai créé !",
                    "media": MEDIA_ITEM_EXAMPLE,
                    "post_type": "art",
                },
                request_only=True,
            )
        ]
    )
)
class CommunityPostViewSet(EngagementActionsMixin, ModelViewSet):
    pagination_class = StandardPagination
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        qs = CommunityPost.objects.select_related("author")
        # "post_type" is the documented/frontend-used param name (COMMUNAUTE_BACKEND_
        # REQUIREMENTS.md §3.2/3.1bis); "type" is kept as an alias for any existing caller.
        post_type = self.request.query_params.get("post_type") or self.request.query_params.get("type")
        if post_type:
            qs = qs.filter(post_type=post_type)
        challenge_slug = self.request.query_params.get("challenge")
        if challenge_slug:
            qs = qs.filter(challenge__slug=challenge_slug)
        # Annotated so CommunityPostSerializer.get_comment_count avoids running 4 separate
        # engagement COUNT queries per post on every paginated list request.
        qs = qs.annotate(
            live_comment_count=Count("engagement_comments", filter=Q(engagement_comments__is_deleted=False))
        )
        return qs.order_by("-created_at")

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        if self.action in ("partial_update", "destroy"):
            return [IsOwnerOrAdmin()]
        # Everything else (list/retrieve, and the engagement actions mounted by
        # EngagementActionsMixin — like/comments/share/save/submit_talent) defers to
        # whatever permission_classes each @action declared, instead of hardcoding
        # AllowAny and silently discarding those declarations.
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ("create", "partial_update"):
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

    @extend_schema(
        examples=[
            OpenApiExample(
                "Soumission de talent",
                value={
                    "title": "Ma nouvelle chanson",
                    "content": "Enregistrée ce week-end.",
                    "media": MEDIA_ITEM_EXAMPLE,
                },
                request_only=True,
            )
        ]
    )
    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def submit_talent(self, request):
        ser = TalentSubmissionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        post = services.create_post(
            {
                "title": ser.validated_data["title"],
                "media": ser.validated_data["media"],
                "content": ser.validated_data["content"],
                "post_type": CommunityPost.TYPE_TALENT,
            },
            request.user,
        )
        return Response(CommunityPostSerializer(post).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_delete(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_delete_posts(ser.validated_data["ids"])
        return Response({"deleted": count})


@extend_schema(tags=["Community"])
@extend_schema_view(
    create=extend_schema(
        examples=[
            OpenApiExample(
                "Nouveau défi",
                value={
                    "title": "Défi du mois : reprise acoustique",
                    "description": "Proposez votre reprise acoustique préférée.",
                    "cover": "https://res.cloudinary.com/artdukivu/image/upload/v1721581234/community/challenges/cover.jpg",
                    "prize": "Mise en avant sur la page d'accueil",
                    "deadline": "2026-09-01T00:00:00Z",
                },
                request_only=True,
            )
        ]
    )
)
class ChallengeViewSet(UploadThrottleMixin, ModelViewSet):
    pagination_class = StandardPagination
    lookup_field = "slug"

    def get_queryset(self):
        return Challenge.objects.filter(is_active=True)

    def get_serializer_class(self):
        return ChallengeSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAdminUser()]
        # Defers to each @action's own permission_classes (bulk_create/update/delete are
        # IsAdminUser, join is IsAuthenticated) instead of hardcoding AllowAny and silently
        # discarding those declarations.
        return super().get_permissions()

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

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def join(self, request, slug=None):
        challenge = self.get_object()
        result = services.join_challenge(challenge, request.user)
        if result.get("error") == "already_joined":
            return Response(
                {"detail": "Vous participez déjà à ce défi.", "code": "already_joined"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Participation enregistrée."}, status=status.HTTP_201_CREATED)

    @extend_schema(
        examples=[
            OpenApiExample(
                "Réponse au défi",
                value={
                    "title": "Ma reprise acoustique",
                    "content": "Voici ma participation !",
                    "media": MEDIA_ITEM_EXAMPLE,
                },
                request_only=True,
            )
        ]
    )
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def participate(self, request, slug=None):
        challenge = self.get_object()
        ser = ChallengeParticipationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = services.participate_in_challenge(challenge, request.user, **ser.validated_data)
        if result.get("error") == "already_joined":
            return Response(
                {"detail": "Vous participez déjà à ce défi.", "code": "already_joined"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(CommunityPostSerializer(result["post"]).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        examples=[
            OpenApiExample(
                "Résultat épinglé",
                value={
                    "title": "Et le gagnant est...",
                    "content": "Merci à tous les participants !",
                    "media": MEDIA_ITEM_EXAMPLE,
                },
                request_only=True,
            )
        ]
    )
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def publish_result(self, request, slug=None):
        challenge = self.get_object()
        ser = ChallengeParticipationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        post = services.publish_challenge_result(challenge, request.user, **ser.validated_data)
        return Response(CommunityPostSerializer(post).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Community"])
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
        # Defers to each @action's own permission_classes (bulk_delete is IsAdminUser, vote is
        # IsAuthenticated) instead of hardcoding AllowAny and silently discarding those
        # declarations — see the identical fix on CommunityPostViewSet/ChallengeViewSet above.
        return super().get_permissions()

    def perform_create(self, serializer):
        poll = services.create_poll(dict(serializer.validated_data))
        serializer.instance = poll

    def perform_update(self, serializer):
        serializer.instance = services.update_poll(serializer.instance, dict(serializer.validated_data))

    def perform_destroy(self, instance):
        services.delete_poll(instance)

    @extend_schema(
        examples=[
            OpenApiExample(
                "Nouveau sondage",
                value={
                    "question": "Quel est votre genre musical préféré ?",
                    "options": [{"text": "Afrobeat"}, {"text": "Rumba"}, {"text": "Hip-hop"}],
                    "expires_at": "2026-08-15T00:00:00Z",
                },
                request_only=True,
            )
        ]
    )
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

    @extend_schema(
        examples=[OpenApiExample("Voter pour une option", value={"option_id": 3}, request_only=True)]
    )
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def vote(self, request, pk=None):
        poll = self.get_object()
        option_id = request.data.get("option_id")
        if not option_id:
            return Response({"detail": "option_id est requis."}, status=status.HTTP_400_BAD_REQUEST)
        result = services.vote_poll(poll, request.user, option_id)
        if result.get("error") == "invalid_option":
            return Response(
                {"detail": "Option invalide.", "code": "invalid_option"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if result.get("error") == "already_voted":
            return Response(
                {"detail": "Vous avez déjà voté à ce sondage.", "code": "already_voted"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        poll.refresh_from_db()
        return Response(PollSerializer(poll).data)
