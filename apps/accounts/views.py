from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from django.shortcuts import redirect
from django.views import View
from rest_framework import generics, mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from core.permissions import IsSelfOrAdmin

from . import services
from .models import ListenHistory, User
from .serializers import (
    ListenHistorySerializer,
    UserAdminSerializer,
    UserPublicSerializer,
    UserSerializer,
)


class GoogleLoginView(SocialLoginView):
    """
    POST /api/v1/auth/google/
    Body: {"access_token": "<google_access_token>"}
    Returns JWT access + refresh tokens on success.
    """
    adapter_class = GoogleOAuth2Adapter


class EmailConfirmRedirectView(View):
    """
    Safety-net: /accounts/confirm-email/<key>/
    The AccountAdapter already puts the frontend URL directly in emails, but if
    a browser ever lands on this backend URL we redirect it cleanly to the SPA.
    """
    def get(self, request, key):
        return redirect(f"{settings.FRONTEND_URL}/verify-email?key={key}")


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


class UserViewSet(GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    lookup_field = "id"
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = User.objects.only(
            "id", "email", "username", "handle", "bio", "role",
            "is_active", "is_verified", "listen_count", "created_at",
        )
        if not self.request.user.is_staff:
            qs = qs.filter(pk=self.request.user.pk)
        return qs

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return UserAdminSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ("list",):
            return [permissions.IsAdminUser()]
        if self.action in ("retrieve", "update", "partial_update"):
            return [IsSelfOrAdmin()]
        return super().get_permissions()

    def partial_update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = UserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_user_profile(user, serializer.validated_data)
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=["get", "post"], url_path="favorites")
    def favorites(self, request, id=None):
        user = self.get_object()
        if request.method == "GET":
            from apps.artists.serializers import ArtistListSerializer
            return Response(ArtistListSerializer(services.get_user_favorites(user), many=True).data)
        artist_id = request.data.get("artist_id")
        if not artist_id:
            return Response({"detail": "artist_id required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from apps.artists.models import Artist
            artist = Artist.objects.get(pk=artist_id)
        except Artist.DoesNotExist:
            return Response({"detail": "Artist not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(services.toggle_favorite_artist(user, artist))

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, id=None):
        user = self.get_object()
        qs = ListenHistory.objects.filter(user=user).order_by("-listened_at")[:50]
        return Response(ListenHistorySerializer(qs, many=True).data)
