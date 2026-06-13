from django.contrib import admin

from .models import Article, Category, Comment, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "color")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "article_type", "is_featured", "published_at")
    list_filter = ("status", "article_type", "is_featured", "category")
    search_fields = ("title", "excerpt")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("author",)
    date_hierarchy = "published_at"
    filter_horizontal = ("tags",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "article", "created_at")
    raw_id_fields = ("author", "article", "parent")
