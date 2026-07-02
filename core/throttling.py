from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AnonBurstThrottle(AnonRateThrottle):
    scope = "anon_burst"


class UserBurstThrottle(UserRateThrottle):
    scope = "user_burst"


class AuthRateThrottle(AnonRateThrottle):
    scope = "auth"


class UploadRateThrottle(UserRateThrottle):
    scope = "upload"
