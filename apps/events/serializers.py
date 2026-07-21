from rest_framework import serializers

from apps.artists.serializers import ArtistListSerializer
from apps.media_uploads.fields import CloudinaryUrlField, resolve_cloudinary_url

from .models import City, Event, EventScheduleItem


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "name", "slug", "country"]


class EventScheduleSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source="artist.name", read_only=True, default=None)

    class Meta:
        model = EventScheduleItem
        fields = ["id", "time", "title", "artist_name", "duration_minutes", "order"]


class EventListSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    image_url = serializers.SerializerMethodField()
    registration_progress = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "slug",
            "image_url",
            "date",
            "end_date",
            "city_name",
            "venue_name",
            "category",
            "status",
            "is_featured",
            "ticket_price",
            "registration_progress",
        ]

    def get_image_url(self, obj):
        return resolve_cloudinary_url(obj.image, "image")

    def get_registration_progress(self, obj):
        if obj.max_capacity:
            return round(obj.current_registrations / obj.max_capacity * 100)
        return None


class EventDetailSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    image_url = serializers.SerializerMethodField()
    schedule = EventScheduleSerializer(many=True, read_only=True)
    artists = ArtistListSerializer(many=True, read_only=True)
    registration_progress = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "image_url",
            "date",
            "end_date",
            "city",
            "venue_name",
            "venue_address",
            "category",
            "status",
            "is_featured",
            "ticket_price",
            "ticket_link",
            "max_capacity",
            "current_registrations",
            "registration_progress",
            "artists",
            "schedule",
            "created_at",
        ]

    def get_image_url(self, obj):
        return resolve_cloudinary_url(obj.image, "image")

    def get_registration_progress(self, obj):
        if obj.max_capacity:
            return round(obj.current_registrations / obj.max_capacity * 100)
        return None


class EventWriteSerializer(serializers.ModelSerializer):
    image = CloudinaryUrlField(resource_type="image", required=False, allow_blank=True)

    class Meta:
        model = Event
        fields = [
            "title",
            "slug",
            "description",
            "image",
            "date",
            "end_date",
            "venue_name",
            "venue_address",
            "city",
            "category",
            "status",
            "is_featured",
            "ticket_price",
            "ticket_link",
            "max_capacity",
            "artists",
        ]
        extra_kwargs = {"slug": {"required": False}}


class EventBulkUpdateItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=300, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False, allow_null=True)
    venue_name = serializers.CharField(max_length=200, required=False)
    venue_address = serializers.CharField(max_length=300, required=False, allow_blank=True)
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), required=False, allow_null=True)
    category = serializers.ChoiceField(choices=Event.CATEGORY_CHOICES, required=False)
    status = serializers.ChoiceField(choices=Event.STATUS_CHOICES, required=False)
    is_featured = serializers.BooleanField(required=False)
    ticket_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    ticket_link = serializers.URLField(required=False, allow_blank=True)
    max_capacity = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class EventBulkCreateSerializer(serializers.Serializer):
    items = EventWriteSerializer(many=True, min_length=1, max_length=100)


class EventBulkUpdateSerializer(serializers.Serializer):
    items = EventBulkUpdateItemSerializer(many=True, min_length=1, max_length=100)
