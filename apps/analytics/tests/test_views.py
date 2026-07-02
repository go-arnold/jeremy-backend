import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="admin@artdukivu.com", username="admin", password="pass12345")


@pytest.fixture
def user(db):
    return User.objects.create_user(email="user@artdukivu.com", username="user", password="pass12345")


@pytest.mark.django_db
def test_dashboard_requires_admin(api_client, user):
    url = reverse("analytics-dashboard")

    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    api_client.force_authenticate(user=user)
    response = api_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_dashboard_returns_counts(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    url = reverse("analytics-dashboard")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["counts"]["users"] >= 1
    assert "top_articles" in response.data
