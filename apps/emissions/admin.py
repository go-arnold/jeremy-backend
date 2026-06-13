from django.contrib import admin

from .models import Emission


@admin.register(Emission)
class EmissionAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "scheduled_at", "viewer_count", "total_views")
    list_filter = ("status",)
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("hosts",)
