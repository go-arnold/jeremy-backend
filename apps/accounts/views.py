from dj_rest_auth.registration.views import RegisterView, SocialLoginView, VerifyEmailView
from dj_rest_auth.views import LoginView, LogoutView, PasswordResetConfirmView, PasswordResetView
from django.conf import settings
from django.shortcuts import redirect
from django.views import View
from drf_spectacular.utils import OpenApiExample, extend_schema, inline_serializer
from rest_framework import generics, mixins, permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.views import TokenRefreshView

from apps.artists.models import Artist
from apps.artists.serializers import ArtistListSerializer
from core.permissions import IsSelfOrAdmin
from core.serializers import BulkDeleteSerializer
from core.throttling import UploadThrottleMixin

from . import profile_services, services
from .adapters import LoggingGoogleOAuth2Adapter
from .models import ListenHistory, User
from .serializers import (
    ActivityEntrySerializer,
    BulkDeleteResultSerializer,
    BulkUpdateResultSerializer,
    FavoriteActionResponseSerializer,
    FavoriteToggleSerializer,
    ListenHistorySerializer,
    SavedItemSerializer,
    UserAdminCreateSerializer,
    UserAdminSerializer,
    UserBulkUpdateSerializer,
    UserSerializer,
)


@extend_schema(tags=["Auth"])
class GoogleLoginView(SocialLoginView):
    adapter_class = LoggingGoogleOAuth2Adapter


# Thin subclasses purely to attach an OpenAPI tag: extend_schema() can't wrap
# `SomeThirdPartyView.as_view()` directly when the view doesn't implement every
# HTTP method (it unconditionally sets kwargs on all of Django's
# http_method_names), so the class itself must carry the decorator instead.
@extend_schema(tags=["Auth"])
class TaggedRegisterView(RegisterView):
    pass


@extend_schema(tags=["Auth"])
class TaggedLoginView(LoginView):
    pass


_LOGOUT_RESPONSE = inline_serializer("LogoutResponse", fields={"detail": serializers.CharField()})


@extend_schema(tags=["Auth"], methods=["GET"], responses=_LOGOUT_RESPONSE)
@extend_schema(
    tags=["Auth"],
    methods=["POST"],
    request=None,
    responses=_LOGOUT_RESPONSE,
    examples=[
        OpenApiExample("Déconnexion réussie", value={"detail": "Déconnexion réussie."}, response_only=True)
    ],
)
class TaggedLogoutView(LogoutView):
    pass


@extend_schema(tags=["Auth"])
class TaggedTokenRefreshView(TokenRefreshView):
    pass


@extend_schema(tags=["Auth"])
class TaggedVerifyEmailView(VerifyEmailView):
    pass


@extend_schema(tags=["Auth"])
class TaggedPasswordResetView(PasswordResetView):
    pass


@extend_schema(tags=["Auth"])
class TaggedPasswordResetConfirmView(PasswordResetConfirmView):
    pass


class EmailConfirmRedirectView(View):
    # The AccountAdapter already puts the frontend URL directly in emails, but if
    # a browser ever lands on this backend URL we redirect it cleanly to the SPA.
    def get(self, request, key):
        return redirect(f"{settings.FRONTEND_URL}/verify-email?key={key}")


@extend_schema(tags=["Auth"])
class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


@extend_schema(tags=["Users"])
class UserViewSet(UploadThrottleMixin, GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    lookup_field = "id"
    permission_classes = [permissions.IsAuthenticated]

    # None of these custom actions call self.paginate_queryset() — they return a plain array.
    # drf-spectacular otherwise auto-wraps ANY `responses=Serializer(many=True)` declaration in
    # a "Paginated...List" envelope whenever `view.pagination_class` is truthy, regardless of
    # whether the action itself actually paginates — this override keeps the generated docs
    # honest for these four, while `list` (the only action that really does paginate) keeps the
    # default.
    _UNPAGINATED_ACTIONS = {"favorites", "history", "saved", "activity"}

    @property
    def pagination_class(self):
        if self.action in self._UNPAGINATED_ACTIONS:
            return None
        from core.pagination import StandardPagination

        return StandardPagination

    def get_queryset(self):
        qs = User.objects.only(
            "id",
            "email",
            "username",
            "handle",
            "bio",
            "role",
            "is_active",
            "is_verified",
            "listen_count",
            "avatar",
            "created_at",
        )
        if not self.request.user.is_staff:
            qs = qs.filter(pk=self.request.user.pk)
        return qs

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return UserAdminSerializer
        return UserSerializer

    def get_permissions(self):
        # Authoritative permission check per action. Do NOT rely on the
        # `permission_classes` kwarg passed to `@action` below — that kwarg
        # is only honored when the view is dispatched through a DRF router
        # (SimpleRouter forwards each action's own kwargs into as_view()).
        # These routes are wired via manual `path()` in user_urls.py, which
        # bypasses that mechanism entirely, so it must be enforced here.
        if self.action in ("list", "create", "destroy", "bulk_update", "bulk_delete"):
            return [permissions.IsAdminUser()]
        if self.action in ("retrieve", "update", "partial_update", "saved", "activity"):
            return [IsSelfOrAdmin()]
        return super().get_permissions()

    @extend_schema(
        request=UserAdminSerializer,
        responses=UserAdminSerializer,
        description=(
            "Self-edits are restricted to the fields in UserSerializer (role/is_verified "
            "read-only); an admin editing another user gets the full UserAdminSerializer shape "
            "(role/is_active/is_verified all writable) — see get_serializer_class()."
        ),
    )
    def partial_update(self, request, *args, **kwargs):
        user = self.get_object()
        # Bug fixed: this used to hardcode UserSerializer regardless of caller, silently
        # dropping role/is_active/is_verified (read-only on that serializer) even when an admin
        # was editing someone else — get_serializer_class() already has the correct branching,
        # it just wasn't being used here.
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_user_profile(user, serializer.validated_data)
        return Response(serializer_class(user).data)

    @extend_schema(methods=["GET"], responses=ArtistListSerializer(many=True))
    @extend_schema(
        methods=["POST"],
        request=FavoriteToggleSerializer,
        responses=FavoriteActionResponseSerializer,
        examples=[OpenApiExample("Ajouter/retirer un favori", value={"artist_id": 12}, request_only=True)],
    )
    @action(detail=True, methods=["get", "post"], url_path="favorites")
    def favorites(self, request, id=None):
        user = self.get_object()
        if request.method == "GET":
            return Response(ArtistListSerializer(services.get_user_favorites(user), many=True).data)

        ser = FavoriteToggleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            artist = Artist.objects.get(pk=ser.validated_data["artist_id"])
        except Artist.DoesNotExist:
            return Response({"detail": "Artiste introuvable."}, status=status.HTTP_404_NOT_FOUND)
        return Response(services.toggle_favorite_artist(user, artist))

    @extend_schema(responses=ListenHistorySerializer(many=True))
    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, id=None):
        user = self.get_object()
        qs = ListenHistory.objects.filter(user=user).order_by("-listened_at")[:50]
        return Response(ListenHistorySerializer(qs, many=True).data)

    @extend_schema(responses=SavedItemSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="saved")
    def saved(self, request, id=None):
        """Profil > signets — every non-live content item this user bookmarked to consume later."""
        user = self.get_object()
        return Response(SavedItemSerializer(profile_services.get_saved_items(user), many=True).data)

    @extend_schema(responses=ActivityEntrySerializer(many=True))
    @action(detail=True, methods=["get"], url_path="activity")
    def activity(self, request, id=None):
        """Profil > activité — this user's likes/comments across the whole app, last 24h
        (falls back to their most recent activity if they haven't been active in 24h)."""
        user = self.get_object()
        return Response(ActivityEntrySerializer(profile_services.get_activity_feed(user), many=True).data)

    @extend_schema(
        request=UserAdminCreateSerializer,
        responses=UserAdminSerializer,
        examples=[
            OpenApiExample(
                "Créer un utilisateur (admin)",
                value={
                    "email": "nouveau@artdukivu.com",
                    "username": "nouveau_membre",
                    "password": "UnMotDePasseSolide123",
                    "role": "editor",
                },
                request_only=True,
            )
        ],
    )
    def create(self, request, *args, **kwargs):
        ser = UserAdminCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = services.create_user_admin(dict(ser.validated_data))
        return Response(UserAdminSerializer(user).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.pk == request.user.pk:
            return Response(
                {"detail": "Vous ne pouvez pas supprimer votre propre compte."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=UserBulkUpdateSerializer, responses=BulkUpdateResultSerializer)
    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        ser = UserBulkUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_update_users(ser.validated_data["items"])
        return Response({"updated": count})

    @extend_schema(request=BulkDeleteSerializer, responses=BulkDeleteResultSerializer)
    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ids = [i for i in ser.validated_data["ids"] if i != request.user.pk]
        count = services.bulk_delete_users(ids)
        return Response({"deleted": count})
