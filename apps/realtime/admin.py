from django.contrib import admin

from .models import LiveChatMessage


@admin.register(LiveChatMessage)
class LiveChatMessageAdmin(admin.ModelAdmin):
    list_display = ("content_type", "object_id", "author", "created_at", "is_deleted")
    list_filter = ("content_type", "is_deleted")
    raw_id_fields = ("author",)
