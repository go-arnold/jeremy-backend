from django.contrib import admin

from .models import WebTVVideo


@admin.register(WebTVVideo)
class WebTVVideoAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_premier", "view_count", "published_at")
    list_filter = ("category", "is_premier", "is_live")
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("artists",)
