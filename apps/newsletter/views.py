from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from core.pagination import StandardPagination
from core.throttling import AuthRateThrottle

from . import services
from .models import Newsletter, Subscriber
from .serializers import (
    NewsletterSerializer,
    NewsletterWriteSerializer,
    SubscriberSerializer,
    SubscribeSerializer,
)

_DETAIL_RESPONSE = inline_serializer("DetailResponse", fields={"detail": serializers.CharField()})


@extend_schema(
    tags=["Newsletter"],
    request=SubscribeSerializer,
    responses=_DETAIL_RESPONSE,
    examples=[
        OpenApiExample("Nouvelle inscription", value={"email": "lecteur@example.com"}, request_only=True)
    ],
)
class SubscribeView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        ser = SubscribeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        services.subscribe(ser.validated_data["email"])
        return Response({"detail": "Vérifiez votre boîte mail pour confirmer votre abonnement."})


@extend_schema(tags=["Newsletter"], responses=_DETAIL_RESPONSE)
class ConfirmSubscriptionView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        result = services.confirm_subscription(token)
        if result.get("error") == "invalid_token":
            return Response(
                {"detail": "Lien de confirmation invalide.", "code": "invalid_token"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"detail": "Abonnement confirmé avec succès."})


@extend_schema(tags=["Newsletter"], responses=_DETAIL_RESPONSE)
class UnsubscribeView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        result = services.unsubscribe(token)
        if result.get("error") == "invalid_token":
            return Response(
                {"detail": "Lien de désabonnement invalide.", "code": "invalid_token"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"detail": "Vous avez été désabonné avec succès."})


@extend_schema(tags=["Newsletter"])
@extend_schema_view(
    create=extend_schema(
        examples=[
            OpenApiExample(
                "Nouvelle newsletter",
                value={
                    "subject": "Nouveautés du mois",
                    "body_html": "<p>Voici les sorties de ce mois-ci...</p>",
                },
                request_only=True,
            )
        ]
    )
)
class NewsletterViewSet(ModelViewSet):
    queryset = Newsletter.objects.select_related("created_by").all()
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return NewsletterWriteSerializer
        return NewsletterSerializer

    def perform_create(self, serializer):
        serializer.instance = services.create_newsletter(dict(serializer.validated_data), self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.status != Newsletter.STATUS_DRAFT:
            raise ValidationError("Seule une newsletter à l'état brouillon peut être modifiée.")
        serializer.save()

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        newsletter = self.get_object()
        result = services.send_newsletter(newsletter)
        if result.get("error") == "already_sent":
            return Response(
                {"detail": "Cette newsletter a déjà été envoyée ou est en cours d'envoi."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(result)


@extend_schema(tags=["Newsletter"])
class SubscriberViewSet(ReadOnlyModelViewSet):
    queryset = Subscriber.objects.all().order_by("-subscribed_at")
    serializer_class = SubscriberSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardPagination
    filterset_fields = ["is_confirmed", "is_active"]
    search_fields = ["email"]
