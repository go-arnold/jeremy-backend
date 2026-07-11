from rest_framework import serializers

from .models import Newsletter, Subscriber


class SubscribeSerializer(serializers.Serializer):
    email = serializers.EmailField()


class SubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscriber
        fields = ["id", "email", "is_confirmed", "is_active", "subscribed_at", "confirmed_at"]


class NewsletterSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Newsletter
        fields = [
            "id",
            "subject",
            "body_html",
            "status",
            "created_by_name",
            "recipient_count",
            "created_at",
            "sent_at",
        ]
        read_only_fields = ["status", "recipient_count", "created_at", "sent_at"]


class NewsletterWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Newsletter
        fields = ["subject", "body_html"]
