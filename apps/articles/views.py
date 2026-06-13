from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.pagination import StandardPagination
from core.permissions import IsAdminOrReadOnly, IsOwnerOrAdmin

from . import services
from .models import Article, Category, Comment
from .serializers import (
    ArticleDetailSerializer,
    ArticleListSerializer,
    ArticleWriteSerializer,
    CategorySerializer,
    CommentSerializer,
)
from .tasks import async_increment_view


class ArticleViewSet(ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = StandardPagination
    search_fields = ["title", "excerpt", "content"]
    ordering_fields = ["published_at", "view_count", "like_count"]
    lookup_field = "slug"

    def get_queryset(self):
        qs = (
            Article.objects.filter(status=Article.STATUS_PUBLISHED)
            .select_related("author", "category")
            .prefetch_related("tags")
            .only(
                "id", "title", "slug", "excerpt", "featured_image",
                "is_featured", "read_time", "view_count", "like_count",
                "published_at", "author__username", "category__name", "category__slug",
            )
        )
        article_type = self.request.query_params.get("type")
        if article_type:
            qs = qs.filter(article_type=article_type)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__slug=category)
        is_featured = self.request.query_params.get("is_featured")
        if is_featured:
            qs = qs.filter(is_featured=is_featured.lower() == "true")
        if self.request.user and self.request.user.is_staff:
            qs = Article.objects.select_related("author", "category").prefetch_related("tags")
        return qs.order_by("-published_at")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ArticleWriteSerializer
        if self.action == "retrieve":
            return ArticleDetailSerializer
        return ArticleListSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        async_increment_view.delay(instance.pk)
        serializer = ArticleDetailSerializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @method_decorator(cache_page(60 * 60))
    @action(detail=False, methods=["get"])
    def categories(self, request):
        cats = Category.objects.all()
        return Response(CategorySerializer(cats, many=True).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, slug=None):
        article = self.get_object()
        result = services.toggle_like(article, request.user)
        return Response(result)

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, slug=None):
        article = self.get_object()
        if request.method == "GET":
            qs = Comment.objects.filter(article=article, parent=None).select_related("author")
            page = self.paginate_queryset(qs)
            return self.get_paginated_response(CommentSerializer(page, many=True).data)
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        comment = services.add_comment(
            article, request.user,
            request.data.get("content", ""),
            request.data.get("parent_id"),
        )
        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)
