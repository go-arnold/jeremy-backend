from rest_framework import serializers

from .models import HomeBanner


class HomeBannerSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = HomeBanner
        fields = ["image_url", "title", "subtitle", "cta_label", "cta_url"]

    def get_image_url(self, obj):
        return obj.image.url if obj.image else None
