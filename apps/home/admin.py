from django.contrib import admin

from .models import FeaturedContent, HomeBanner


@admin.register(HomeBanner)
class HomeBannerAdmin(admin.ModelAdmin):
    list_display = ("title", "updated_at")

    def has_add_permission(self, request):
        # Singleton — only the get_or_create(pk=1) row should ever exist.
        return not HomeBanner.objects.exists()


@admin.register(FeaturedContent)
class FeaturedContentAdmin(admin.ModelAdmin):
    list_display = ("content_type", "object_id", "order", "created_at")
    list_editable = ("order",)
    list_filter = ("content_type",)
    ordering = ("order",)
