import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.artists.models import Artist, Genre


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email="admin@artdukivu.com", username="admin", password="pass"
    )


@pytest.fixture
def genre(db):
    return Genre.objects.create(name="Rumba", slug="rumba")


@pytest.fixture
def artist(db, genre):
    a = Artist.objects.create(name="Fally Ipupa", slug="fally-ipupa", city="Kinshasa")
    a.genres.add(genre)
    return a


@pytest.mark.django_db
def test_artist_list(api_client, artist):
    url = reverse("artist-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] >= 1


@pytest.mark.django_db
def test_artist_detail(api_client, artist):
    url = reverse("artist-detail", kwargs={"slug": artist.slug})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["name"] == "Fally Ipupa"


@pytest.mark.django_db
def test_artist_create_requires_admin(api_client, artist):
    url = reverse("artist-list")
    data = {"name": "New Artist", "city": "Goma"}
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_artist_create_admin(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    url = reverse("artist-list")
    data = {"name": "New Artist", "city": "Bukavu", "genres": []}
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_artist_filter_by_genre(api_client, artist, genre):
    url = reverse("artist-list") + f"?genre={genre.slug}"
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] >= 1


@pytest.mark.django_db
def test_genres_endpoint(api_client, genre):
    url = reverse("artist-genres")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 1
