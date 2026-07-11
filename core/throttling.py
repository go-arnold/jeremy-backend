from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AnonBurstThrottle(AnonRateThrottle):
    scope = "anon_burst"


class UserBurstThrottle(UserRateThrottle):
    scope = "user_burst"


class AuthRateThrottle(AnonRateThrottle):
    scope = "auth"


class UploadRateThrottle(UserRateThrottle):
    scope = "upload"


class UploadThrottleMixin:
    """Adds the stricter `upload` throttle scope on top of the default ones for create/update
    actions — for ViewSets whose write serializer accepts a CloudinaryField (image/audio/video).
    """

    def get_throttles(self):
        if self.action in ("create", "update", "partial_update"):
            return [UploadRateThrottle()] + super().get_throttles()
        return super().get_throttles()
