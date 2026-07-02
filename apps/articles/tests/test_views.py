import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.articles.models import Category, Tag


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="admin@artdukivu.com", username="admin", password="pass12345")


@pytest.fixture
def other_staff(db):
    return User.objects.create_user(
        email="editor@artdukivu.com", username="editor", password="pass12345", is_staff=True
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name="News", slug="news")


@pytest.mark.django_db
def test_create_defaults_author_to_connected_user(api_client, admin_user, category):
    api_client.force_authenticate(user=admin_user)
    url = reverse("article-list")
    data = {"title": "Sample", "content": "Some content", "category": category.id}
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    from apps.articles.models import Article

    article = Article.objects.get(slug=response.data["slug"])
    assert article.author_id == admin_user.id


@pytest.mark.django_db
def test_admin_can_choose_explicit_author(api_client, admin_user, other_staff, category):
    api_client.force_authenticate(user=admin_user)
    url = reverse("article-list")
    data = {
        "title": "Sample 2",
        "content": "Some content",
        "category": category.id,
        "author": other_staff.id,
    }
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    from apps.articles.models import Article

    article = Article.objects.get(slug=response.data["slug"])
    assert article.author_id == other_staff.id


@pytest.mark.django_db
def test_tags_list_is_public(api_client):
    Tag.objects.create(name="Rumba", slug="rumba")
    url = reverse("tag-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] >= 1


@pytest.mark.django_db
def test_tags_create_requires_admin(api_client, admin_user):
    url = reverse("tag-list")

    response = api_client.post(url, {"name": "Afrobeat"}, format="json")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    api_client.force_authenticate(user=admin_user)
    response = api_client.post(url, {"name": "Afrobeat"}, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert Tag.objects.filter(slug="afrobeat").exists()
