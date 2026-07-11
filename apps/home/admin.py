from django.contrib import admin

from .models import HomeBanner


@admin.register(HomeBanner)
class HomeBannerAdmin(admin.ModelAdmin):
    list_display = ("title", "updated_at")

    def has_add_permission(self, request):
        # Singleton — only the get_or_create(pk=1) row should ever exist.
        return not HomeBanner.objects.exists()
