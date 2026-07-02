from unittest.mock import patch

import pytest
from django.urls import reverse
from elasticsearch import exceptions as es_exceptions
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_empty_query_short_circuits_without_calling_es(api_client):
    url = reverse("search")
    with patch("apps.search.views.services.unified_search") as mocked:
        response = api_client.get(url, {"q": "  "})
    assert response.status_code == status.HTTP_200_OK
    assert response.data == {"count": 0, "page": 1, "page_size": 20, "results": []}
    mocked.assert_not_called()


@pytest.mark.django_db
def test_invalid_pagination_params_return_400(api_client):
    url = reverse("search")
    response = api_client.get(url, {"q": "test", "page": "abc"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_search_success_delegates_to_service(api_client):
    fake_result = {"count": 1, "page": 1, "page_size": 20, "results": [{"type": "artist", "id": 1}]}
    url = reverse("search")
    with patch("apps.search.views.services.unified_search", return_value=fake_result) as mocked:
        response = api_client.get(url, {"q": "Agathe", "type": "artists"})
    assert response.status_code == status.HTTP_200_OK
    assert response.data == fake_result
    mocked.assert_called_once_with("Agathe", "artists", 1, 20)


@pytest.mark.django_db
def test_search_returns_503_when_es_unreachable(api_client):
    url = reverse("search")
    with patch(
        "apps.search.views.services.unified_search",
        side_effect=es_exceptions.ConnectionError("boom"),
    ):
        response = api_client.get(url, {"q": "test"})
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
