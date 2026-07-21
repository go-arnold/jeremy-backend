from django.urls import path

from .views import HomeBannerView, home_view

urlpatterns = [
    path("", home_view, name="home"),
    path("banner/", HomeBannerView.as_view(), name="home_banner"),
]
