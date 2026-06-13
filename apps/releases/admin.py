from django.contrib import admin

from .models import MusicRelease


@admin.register(MusicRelease)
class MusicReleaseAdmin(admin.ModelAdmin):
    list_display = ("title", "artist", "format", "release_date", "is_featured", "is_premiere")
    list_filter = ("format", "is_featured", "is_premiere")
    search_fields = ("title", "artist__name")
    raw_id_fields = ("artist",)
    date_hierarchy = "release_date"
