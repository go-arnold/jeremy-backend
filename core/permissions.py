from rest_framework.permissions import BasePermission, IsAdminUser, SAFE_METHODS


class IsAdminOrReadOnly(BasePermission):
    """Allow read to anyone, write only to admin users."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class IsOwnerOrAdmin(BasePermission):
    """Allow access to object owner or admin."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        owner = getattr(obj, "author", None) or getattr(obj, "user", None)
        return owner == request.user


class IsSelfOrAdmin(BasePermission):
    """For user profile endpoints — allow self or admin."""

    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj == request.user
