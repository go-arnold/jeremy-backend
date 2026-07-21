from django.urls import path

from .views import UserViewSet

urlpatterns = [
    path("", UserViewSet.as_view({"get": "list", "post": "create"}), name="user_list"),
    path(
        "<int:id>/",
        UserViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="user_detail",
    ),
    path(
        "<int:id>/favorites/",
        UserViewSet.as_view({"get": "favorites", "post": "favorites"}),
        name="user_favorites",
    ),
    path("<int:id>/history/", UserViewSet.as_view({"get": "history"}), name="user_history"),
    path("<int:id>/saved/", UserViewSet.as_view({"get": "saved"}), name="user_saved"),
    path("<int:id>/activity/", UserViewSet.as_view({"get": "activity"}), name="user_activity"),
    path("bulk_update/", UserViewSet.as_view({"post": "bulk_update"}), name="user_bulk_update"),
    path("bulk_delete/", UserViewSet.as_view({"post": "bulk_delete"}), name="user_bulk_delete"),
]
