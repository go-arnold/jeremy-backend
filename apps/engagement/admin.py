from django.contrib import admin

from .models import Comment, Like, SavedItem, Share


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("content_type", "object_id", "user", "created_at")
    list_filter = ("content_type",)
    raw_id_fields = ("user",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("content_type", "object_id", "author", "created_at", "is_deleted")
    list_filter = ("content_type", "is_deleted")
    raw_id_fields = ("author", "parent")


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ("content_type", "object_id", "user", "created_at")
    list_filter = ("content_type",)
    raw_id_fields = ("user",)


@admin.register(SavedItem)
class SavedItemAdmin(admin.ModelAdmin):
    list_display = ("content_type", "object_id", "user", "created_at")
    list_filter = ("content_type",)
    raw_id_fields = ("user",)
