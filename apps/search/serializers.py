from rest_framework import serializers


class SearchResultSerializer(serializers.Serializer):
    type = serializers.CharField()
    id = serializers.IntegerField()
    slug = serializers.CharField(allow_null=True)
    title = serializers.CharField(allow_blank=True)
    image_url = serializers.CharField(allow_null=True)
    score = serializers.FloatField(allow_null=True)


class SearchResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    results = SearchResultSerializer(many=True)
