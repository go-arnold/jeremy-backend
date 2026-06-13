from rest_framework import serializers

from .models import Article, Category, Comment, Tag


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "color"]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


class AuthorBriefSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    avatar_url = serializers.SerializerMethodField()

    def get_avatar_url(self, obj):
        return obj.avatar.url if getattr(obj, "avatar", None) else None


class ArticleListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    featured_image_url = serializers.SerializerMethodField()
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Article
        fields = [
            "id", "title", "slug", "excerpt", "featured_image_url",
            "category", "author_name", "read_time", "view_count",
            "like_count", "is_featured", "published_at",
        ]

    def get_featured_image_url(self, obj):
        return obj.featured_image.url if obj.featured_image else None


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)
    author_avatar = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "author_name", "author_avatar", "content", "like_count", "created_at"]
        read_only_fields = ["id", "author_name", "like_count", "created_at"]

    def get_author_avatar(self, obj):
        if hasattr(obj.author, "avatar") and obj.author.avatar:
            return obj.author.avatar.url
        return None


class ArticleDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    featured_image_url = serializers.SerializerMethodField()
    author = AuthorBriefSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True, source="comments_set")

    class Meta:
        model = Article
        fields = [
            "id", "title", "slug", "excerpt", "content", "featured_image_url",
            "category", "tags", "author", "article_type", "read_time",
            "view_count", "like_count", "is_featured", "status",
            "published_at", "comments",
        ]

    def get_featured_image_url(self, obj):
        return obj.featured_image.url if obj.featured_image else None


class ArticleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = [
            "title", "slug", "excerpt", "content", "featured_image",
            "category", "tags", "article_type", "status",
            "is_featured", "read_time", "scheduled_at",
        ]
        extra_kwargs = {"slug": {"required": False}}

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Content cannot be empty.")
        return value
