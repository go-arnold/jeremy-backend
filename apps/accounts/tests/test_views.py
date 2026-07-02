import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="test@artdukivu.com",
        username="testuser",
        password="securepass123",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email="admin@artdukivu.com",
        username="admin",
        password="adminpass123",
    )


@pytest.mark.django_db
def test_register(api_client):
    url = reverse("auth_register")
    data = {
        "email": "new@artdukivu.com",
        "password1": "StrongPass123!",
        "password2": "StrongPass123!",
    }
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_201_CREATED
    assert "access" in response.data


@pytest.mark.django_db
def test_login(api_client, user):
    url = reverse("auth_login")
    response = api_client.post(url, {"email": user.email, "password": "securepass123"})
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data


@pytest.mark.django_db
def test_me_authenticated(api_client, user):
    api_client.force_authenticate(user=user)
    url = reverse("auth_me")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["email"] == user.email


@pytest.mark.django_db
def test_me_unauthenticated(api_client):
    url = reverse("auth_me")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_user_list_admin_only(api_client, user, admin_user):
    url = reverse("user_list")
    api_client.force_authenticate(user=user)
    response = api_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    api_client.force_authenticate(user=admin_user)
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_bulk_update_rejects_non_admin(api_client, user):
    """Regression: bulk_update is wired via manual path(), not a router, so
    it must not fall back to the class-level IsAuthenticated permission."""
    url = reverse("user_bulk_update")
    api_client.force_authenticate(user=user)
    response = api_client.post(
        url, {"items": [{"id": user.id, "is_staff": True, "role": "admin"}]}, format="json"
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    user.refresh_from_db()
    assert user.is_staff is False


@pytest.mark.django_db
def test_bulk_delete_rejects_non_admin(api_client, user, admin_user):
    url = reverse("user_bulk_delete")
    api_client.force_authenticate(user=user)
    response = api_client.post(url, {"ids": [admin_user.id]}, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert User.objects.filter(pk=admin_user.pk).exists()


@pytest.mark.django_db
def test_bulk_update_allows_admin(api_client, user, admin_user):
    url = reverse("user_bulk_update")
    api_client.force_authenticate(user=admin_user)
    response = api_client.post(url, {"items": [{"id": user.id, "is_verified": True}]}, format="json")
    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.is_verified is True
