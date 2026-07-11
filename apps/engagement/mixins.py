from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.pagination import SmallPagination

from . import services
from .serializers import CommentCreateSerializer, CommentSerializer


class EngagementActionsMixin:
    """Adds like/comments/share/save actions to a ModelViewSet.

    Set `enable_save = False` on the ViewSet for content that is inherently
    live (emissions, live_music sessions, radio programs) — that content can
    be commented on and shared, but never saved for later.
    """

    enable_save = True

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, *args, **kwargs):
        instance = self.get_object()
        liked, count = services.toggle_like(instance, request.user)
        return Response({"liked": liked, "like_count": count})

    @action(detail=True, methods=["get", "post"], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def comments(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.method == "GET":
            qs = services.list_comments(instance)
            paginator = SmallPagination()
            page = paginator.paginate_queryset(qs, request, view=self)
            return paginator.get_paginated_response(CommentSerializer(page, many=True).data)

        ser = CommentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        comment = services.add_comment(
            instance, request.user, ser.validated_data["content"], ser.validated_data.get("parent")
        )
        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"comments/(?P<comment_id>\d+)",
        permission_classes=[permissions.IsAuthenticated],
    )
    def delete_comment(self, request, comment_id=None, *args, **kwargs):
        instance = self.get_object()
        result = services.delete_comment(instance, comment_id, request.user)
        if result is None:
            return Response({"detail": "Commentaire introuvable."}, status=status.HTTP_404_NOT_FOUND)
        if result is False:
            return Response(
                {"detail": "Vous ne pouvez supprimer que vos propres commentaires."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[permissions.AllowAny])
    def share(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user if request.user.is_authenticated else None
        count = services.record_share(instance, user)
        return Response({"share_count": count})

    @action(detail=True, methods=["post", "delete"], permission_classes=[permissions.IsAuthenticated])
    def save(self, request, *args, **kwargs):
        if not self.enable_save:
            return Response(
                {"detail": "Le contenu en direct ne peut pas être enregistré pour plus tard."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance = self.get_object()
        try:
            saved = services.toggle_save(instance, request.user)
        except services.LiveContentNotSavableError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"saved": saved})
