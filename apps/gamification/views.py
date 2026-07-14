from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from apps.accounts.models import User
from core.throttling import ConsumptionRateThrottle

from . import services
from .models import Badge, UserBadge
from .serializers import (
    BadgeSerializer,
    ConsumptionRecordSerializer,
    MediaRankingItemSerializer,
    UserBadgeSerializer,
)


@extend_schema(tags=["Gamification"])
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def badge_catalog(request):
    badges = Badge.objects.filter(is_active=True)
    return Response(BadgeSerializer(badges, many=True).data)


@extend_schema(tags=["Gamification"])
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def user_badges(request, user_id):
    """Public — badges are meant to be shown off on a profile, not kept private."""
    user = get_object_or_404(User, pk=user_id)
    earned = UserBadge.objects.filter(user=user).select_related("badge")
    return Response(UserBadgeSerializer(earned, many=True).data)


@extend_schema(tags=["Gamification"])
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([ConsumptionRateThrottle])
def record_consumption(request):
    """Heartbeat the frontend player calls periodically (e.g. every 30s) while content is
    actively playing — accumulates real listening/watching time and returns any badges the
    user just unlocked."""
    ser = ConsumptionRecordSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    newly_earned = services.record_consumption(request.user, **ser.validated_data)
    return Response(
        {"newly_earned_badges": BadgeSerializer(newly_earned, many=True).data},
        status=status.HTTP_201_CREATED,
    )


@extend_schema(tags=["Gamification"])
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def my_media_ranking(request):
    ranking = services.get_media_ranking(request.user)
    return Response(MediaRankingItemSerializer(ranking, many=True).data)
