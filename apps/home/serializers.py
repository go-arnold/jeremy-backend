from rest_framework import serializers

from apps.media_uploads.fields import CloudinaryUrlField, resolve_cloudinary_url

from .models import HomeBanner


class HomeBannerSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = HomeBanner
        fields = ["image_url", "title", "subtitle", "cta_label", "cta_url"]

    def get_image_url(self, obj):
        return resolve_cloudinary_url(obj.image, "image")


class HomeBannerWriteSerializer(serializers.ModelSerializer):
    image = CloudinaryUrlField(resource_type="image", required=False, allow_blank=True)

    class Meta:
        model = HomeBanner
        fields = ["image", "title", "subtitle", "cta_label", "cta_url"]
