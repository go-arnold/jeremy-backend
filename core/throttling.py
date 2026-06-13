from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AnonBurstThrottle(AnonRateThrottle):
    scope = "anon_burst"


class UserBurstThrottle(UserRateThrottle):
    scope = "user_burst"


class AuthRateThrottle(AnonRateThrottle):
    """Applied to login / register endpoints."""
    scope = "auth"


class UploadRateThrottle(UserRateThrottle):
    """Applied to file upload endpoints."""
    scope = "upload"
