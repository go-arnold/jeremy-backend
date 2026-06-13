from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RadioChatViewSet, RadioProgramViewSet, current_program

router = DefaultRouter()
router.register("program", RadioProgramViewSet, basename="radio-program")
router.register("chat", RadioChatViewSet, basename="radio-chat")

urlpatterns = [
    path("", include(router.urls)),
    path("current/", current_program, name="radio-current"),
]
