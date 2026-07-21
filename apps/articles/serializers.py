from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.media_uploads.fields import CloudinaryUrlField

from .models import Article, Category, Comment, Tag

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "color"]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]
        extra_kwargs = {"slug": {"required": False}}


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
            "id",
            "title",
            "slug",
            "excerpt",
            "featured_image_url",
            "category",
            "author_name",
            "read_time",
            "view_count",
            "like_count",
            "is_featured",
            "published_at",
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
            "id",
            "title",
            "slug",
            "excerpt",
            "content",
            "featured_image_url",
            "category",
            "tags",
            "author",
            "article_type",
            "read_time",
            "view_count",
            "like_count",
            "is_featured",
            "status",
            "published_at",
            "comments",
        ]

    def get_featured_image_url(self, obj):
        return obj.featured_image.url if obj.featured_image else None


class CategoryField(serializers.PrimaryKeyRelatedField):
    """Accepts either a numeric Category id or its slug — `Article.category` is nullable at the
    DB level (on_delete=SET_NULL), but DRF's auto-generated field derives `required=True` from
    the FK's `blank` attribute, which was never set. That mismatch made a missing/empty category
    hard-fail creation instead of falling back to "uncategorized"; declaring the field explicitly
    with required=False fixes that, and the slug fallback tolerates either identifier shape."""

    def to_internal_value(self, data):
        if isinstance(data, str) and not data.isdigit():
            try:
                return self.get_queryset().get(slug=data)
            except Category.DoesNotExist:
                self.fail("does_not_exist", pk_value=data)
        return super().to_internal_value(data)


class ArticleWriteSerializer(serializers.ModelSerializer):
    # Optional: only an admin may set this explicitly (enforced in the view,
    # not here) — everyone else is authored as the connected user.
    author = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    featured_image = CloudinaryUrlField(resource_type="image", required=False, allow_blank=True)
    category = CategoryField(queryset=Category.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Article
        fields = [
            "title",
            "slug",
            "excerpt",
            "content",
            "featured_image",
            "category",
            "tags",
            "author",
            "article_type",
            "status",
            "is_featured",
            "read_time",
            "scheduled_at",
        ]
        extra_kwargs = {"slug": {"required": False}}

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Le contenu ne peut pas être vide.")
        return value


class ArticleBulkUpdateItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=300, required=False)
    excerpt = serializers.CharField(required=False, allow_blank=True)
    content = serializers.CharField(required=False)
    category = CategoryField(queryset=Category.objects.all(), required=False, allow_null=True)
    article_type = serializers.ChoiceField(choices=Article.TYPE_CHOICES, required=False)
    status = serializers.ChoiceField(choices=Article.STATUS_CHOICES, required=False)
    is_featured = serializers.BooleanField(required=False)
    read_time = serializers.IntegerField(min_value=1, required=False)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)


class ArticleBulkCreateSerializer(serializers.Serializer):
    items = ArticleWriteSerializer(many=True, min_length=1, max_length=100)


class ArticleBulkUpdateSerializer(serializers.Serializer):
    items = ArticleBulkUpdateItemSerializer(many=True, min_length=1, max_length=100)
