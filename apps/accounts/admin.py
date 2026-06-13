from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ListenHistory, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "username", "role", "is_verified", "is_active", "created_at")
    list_filter = ("role", "is_active", "is_verified", "is_staff")
    search_fields = ("email", "username", "handle")
    ordering = ("-created_at",)
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Profile", {"fields": ("bio", "handle", "avatar", "cover_image", "role", "is_verified", "google_id")}),
        ("Stats", {"fields": ("listen_count",)}),
    )


@admin.register(ListenHistory)
class ListenHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "content_type", "title", "listened_at")
    list_filter = ("content_type",)
    raw_id_fields = ("user",)
