import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.newsletter.models import Newsletter, Subscriber


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="admin@artdukivu.com", username="admin", password="pass12345")


@pytest.mark.django_db
def test_subscribe_creates_unconfirmed_subscriber(api_client):
    url = reverse("newsletter-subscribe")
    response = api_client.post(url, {"email": "fan@example.com"}, format="json")
    assert response.status_code == status.HTTP_200_OK
    subscriber = Subscriber.objects.get(email="fan@example.com")
    assert subscriber.is_confirmed is False


@pytest.mark.django_db
def test_confirm_subscription(api_client):
    subscriber = Subscriber.objects.create(email="fan2@example.com")
    url = reverse("newsletter-confirm", kwargs={"token": subscriber.confirm_token})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    subscriber.refresh_from_db()
    assert subscriber.is_confirmed is True


@pytest.mark.django_db
def test_confirm_subscription_invalid_token(api_client):
    import uuid

    url = reverse("newsletter-confirm", kwargs={"token": uuid.uuid4()})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_unsubscribe(api_client):
    subscriber = Subscriber.objects.create(email="fan3@example.com", is_confirmed=True)
    url = reverse("newsletter-unsubscribe", kwargs={"token": subscriber.unsubscribe_token})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    subscriber.refresh_from_db()
    assert subscriber.is_active is False


@pytest.mark.django_db
def test_campaign_crud_requires_admin(api_client, admin_user):
    url = reverse("newsletter-campaign-list")

    response = api_client.post(url, {"subject": "Hello", "body_html": "<p>Hi</p>"}, format="json")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    api_client.force_authenticate(user=admin_user)
    response = api_client.post(url, {"subject": "Hello", "body_html": "<p>Hi</p>"}, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert Newsletter.objects.filter(subject="Hello", status=Newsletter.STATUS_DRAFT).exists()


@pytest.mark.django_db
def test_send_campaign_marks_sending(api_client, admin_user):
    Subscriber.objects.create(email="confirmed@example.com", is_confirmed=True, is_active=True)
    newsletter = Newsletter.objects.create(subject="Promo", body_html="<p>Promo</p>", created_by=admin_user)
    api_client.force_authenticate(user=admin_user)
    url = reverse("newsletter-campaign-send", kwargs={"pk": newsletter.pk})
    response = api_client.post(url)
    assert response.status_code == status.HTTP_200_OK
    newsletter.refresh_from_db()
    assert newsletter.status == Newsletter.STATUS_SENDING
    assert newsletter.recipient_count == 1


@pytest.mark.django_db
def test_send_campaign_twice_rejected(api_client, admin_user):
    newsletter = Newsletter.objects.create(
        subject="Promo", body_html="<p>Promo</p>", status=Newsletter.STATUS_SENT, created_by=admin_user
    )
    api_client.force_authenticate(user=admin_user)
    url = reverse("newsletter-campaign-send", kwargs={"pk": newsletter.pk})
    response = api_client.post(url)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
