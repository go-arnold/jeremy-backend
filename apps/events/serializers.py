from rest_framework import serializers

from apps.artists.serializers import ArtistListSerializer

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
            "id", "title", "slug", "image_url", "date", "end_date",
            "city_name", "venue_name", "category", "status",
            "is_featured", "ticket_price", "registration_progress",
        ]

    def get_image_url(self, obj):
        return obj.image.url if obj.image else None

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
            "id", "title", "slug", "description", "image_url", "date", "end_date",
            "city", "venue_name", "venue_address", "category", "status",
            "is_featured", "ticket_price", "ticket_link", "max_capacity",
            "current_registrations", "registration_progress",
            "artists", "schedule", "created_at",
        ]

    def get_image_url(self, obj):
        return obj.image.url if obj.image else None

    def get_registration_progress(self, obj):
        if obj.max_capacity:
            return round(obj.current_registrations / obj.max_capacity * 100)
        return None


class EventWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "title", "slug", "description", "image", "date", "end_date",
            "venue_name", "venue_address", "city", "category", "status",
            "is_featured", "ticket_price", "ticket_link", "max_capacity", "artists",
        ]
        extra_kwargs = {"slug": {"required": False}}
