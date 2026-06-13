from django.db import transaction
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.pagination import StandardPagination
from core.permissions import IsOwnerOrAdmin

from .models import Challenge, CommunityPost, Poll, PollOption, PollVote, PostLike
from .serializers import (
    ChallengeSerializer,
    CommunityPostSerializer,
    CommunityPostWriteSerializer,
    PollSerializer,
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
        serializer.save(author=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        post = self.get_object()
        like, created = PostLike.objects.get_or_create(post=post, user=request.user)
        if not created:
            like.delete()
            CommunityPost.objects.filter(pk=post.pk).update(like_count=post.likes.count())
            return Response({"action": "unliked"})
        CommunityPost.objects.filter(pk=post.pk).update(like_count=post.likes.count())
        return Response({"action": "liked"}, status=status.HTTP_201_CREATED)


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


class PollViewSet(ModelViewSet):
    pagination_class = StandardPagination

    def get_queryset(self):
        return Poll.objects.filter(is_active=True).prefetch_related("options")

    def get_serializer_class(self):
        return PollSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    @transaction.atomic
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def vote(self, request, pk=None):
        poll = self.get_object()
        option_id = request.data.get("option_id")
        if not option_id:
            return Response({"detail": "option_id required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            option = PollOption.objects.get(pk=option_id, poll=poll)
        except PollOption.DoesNotExist:
            return Response({"detail": "Invalid option"}, status=status.HTTP_400_BAD_REQUEST)
        if PollVote.objects.filter(poll=poll, user=request.user).exists():
            return Response({"detail": "Already voted"}, status=status.HTTP_400_BAD_REQUEST)
        PollVote.objects.create(poll=poll, user=request.user, option=option)
        PollOption.objects.filter(pk=option.pk).update(vote_count=option.vote_count + 1)
        Poll.objects.filter(pk=poll.pk).update(vote_count=poll.vote_count + 1)
        poll.refresh_from_db()
        return Response(PollSerializer(poll).data)
